#!/usr/bin/env python3
"""WebSocket Client v2 for Advanced Vision Distributed Architecture

Supports publishing to typed topics and subscribing with auto-reconnect.
Single-port architecture (8000) with topic-based routing.

Architecture v2 Changes:
- Single port: 8000 (instead of 8001-8005)
- Typed topics: vision.detection.yolo, vision.segmentation.sam, etc.
- Transport envelope with event_id, event_type, schema_family, etc.
- Improved auth, reconnect, observability
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Coroutine, Optional, Union

import websockets
from websockets.client import WebSocketClientProtocol

# Import v2 types
from advanced_vision.wss_server_v2 import (
    TransportEnvelope,
    SchemaFamily,
    Topic,
    YOLODetectionPayload,
    SAMSegmentationPayload,
    EagleClassificationPayload,
    QwenAnalysisPayload,
)


# =============================================================================
# Client Configuration
# =============================================================================

@dataclass
class ClientConfigV2:
    """Configuration for WebSocket v2 client"""
    host: str = "localhost"
    port: int = 8000
    path: str = "/"
    
    # Authentication
    auth_token: Optional[str] = None
    
    # Reconnection
    auto_reconnect: bool = True
    reconnect_delay: float = 1.0
    max_reconnect_delay: float = 30.0
    reconnect_backoff: float = 2.0
    connection_timeout: float = 10.0
    max_retries: int = 0  # 0 = unlimited
    
    # Ping/heartbeat
    ping_interval: float = 20.0
    enable_ping: bool = True
    
    # Buffering
    message_buffer_size: int = 1000


# =============================================================================
# Base WSS Client v2
# =============================================================================

class WSSClientV2:
    """WebSocket v2 client with auto-reconnect and topic support."""
    
    def __init__(self, config: Optional[ClientConfigV2] = None):
        self.config = config or ClientConfigV2()
        self.websocket: Optional[WebSocketClientProtocol] = None
        self._connected = False
        self._authenticated = False
        self._shutdown = False
        self._retry_count = 0
        self._reconnect_delay = self.config.reconnect_delay
        self._client_id: Optional[str] = None
        
        # Callbacks
        self.on_connect: Optional[Callable[[], None]] = None
        self.on_disconnect: Optional[Callable[[], None]] = None
        self.on_error: Optional[Callable[[Exception], None]] = None
        self.on_message: Optional[Callable[[TransportEnvelope], None]] = None
        
        # Subscriptions
        self._subscriptions: set[str] = set()
        self._pending_subscriptions: set[str] = set()
        
        # Message queue for offline buffering
        self._message_queue: asyncio.Queue = asyncio.Queue(maxsize=self.config.message_buffer_size)
        
        # Tasks
        self._processing_task: Optional[asyncio.Task] = None
        self._ping_task: Optional[asyncio.Task] = None
        
        # Stats
        self._stats = {
            "messages_sent": 0,
            "messages_received": 0,
            "reconnects": 0,
            "errors": 0,
        }
        
        # Buffer for incoming messages
        self._message_buffer: deque = deque(maxlen=100)
        
        self._logger = logging.getLogger("wss_client_v2")
    
    @property
    def url(self) -> str:
        """Build WebSocket URL"""
        return f"ws://{self.config.host}:{self.config.port}{self.config.path}"
    
    @property
    def is_connected(self) -> bool:
        """Check if client is connected"""
        return self._connected and self.websocket is not None
    
    @property
    def is_authenticated(self) -> bool:
        """Check if client is authenticated"""
        return self._authenticated
    
    async def connect(self) -> bool:
        """Connect to WebSocket server with retry logic"""
        while not self._shutdown:
            try:
                self._logger.info(f"🔌 Connecting to {self.url}...")
                
                self.websocket = await asyncio.wait_for(
                    websockets.connect(self.url),
                    timeout=self.config.connection_timeout
                )
                
                self._connected = True
                self._retry_count = 0
                self._reconnect_delay = self.config.reconnect_delay
                
                self._logger.info(f"✅ Connected to {self.url}")
                
                # Authenticate if token provided
                if self.config.auth_token:
                    if not await self._authenticate():
                        self._logger.error("❌ Authentication failed")
                        await self.websocket.close()
                        self._connected = False
                        return False
                
                # Resubscribe to previous topics
                if self._subscriptions:
                    await self._resubscribe()
                
                # Trigger callback
                if self.on_connect:
                    try:
                        self.on_connect()
                    except Exception as e:
                        self._logger.error(f"Error in on_connect callback: {e}")
                
                # Start message processing
                self._processing_task = asyncio.create_task(self._process_messages())
                
                # Start ping loop
                if self.config.enable_ping:
                    self._ping_task = asyncio.create_task(self._ping_loop())
                
                # Process queued messages
                await self._drain_queue()
                
                return True
                
            except asyncio.TimeoutError:
                self._logger.warning(f"⏱️ Connection timeout to {self.url}")
                await self._handle_reconnect()
                
            except websockets.exceptions.InvalidStatusCode as e:
                self._logger.error(f"❌ Connection rejected: {e.status_code}")
                if self.on_error:
                    self.on_error(e)
                return False
                
            except Exception as e:
                self._logger.error(f"❌ Connection error: {e}")
                self._stats["errors"] += 1
                if self.on_error:
                    self.on_error(e)
                await self._handle_reconnect()
                
        return False
    
    async def _authenticate(self) -> bool:
        """Authenticate with server."""
        if not self.config.auth_token:
            return True
        
        try:
            await self.websocket.send(json.dumps({
                "type": "auth",
                "auth_token": self.config.auth_token
            }))
            
            response = await asyncio.wait_for(self.websocket.recv(), timeout=5.0)
            data = json.loads(response)
            
            if data.get("type") == "auth_ok":
                self._authenticated = True
                self._client_id = data.get("client_id")
                self._logger.info(f"🔐 Authenticated (client_id: {self._client_id})")
                return True
            else:
                return False
                
        except Exception as e:
            self._logger.error(f"Authentication error: {e}")
            return False
    
    async def _resubscribe(self) -> None:
        """Resubscribe to topics after reconnection."""
        if self._subscriptions:
            topics = list(self._subscriptions)
            await self.subscribe(topics)
    
    async def _handle_reconnect(self):
        """Handle reconnection with backoff"""
        if not self.config.auto_reconnect or self._shutdown:
            return
        
        self._retry_count += 1
        self._stats["reconnects"] += 1
        
        if self.config.max_retries > 0 and self._retry_count > self.config.max_retries:
            self._logger.error(f"❌ Max retries ({self.config.max_retries}) exceeded")
            return
        
        self._logger.info(f"🔄 Reconnecting in {self._reconnect_delay:.1f}s (attempt {self._retry_count})...")
        await asyncio.sleep(self._reconnect_delay)
        
        # Exponential backoff
        self._reconnect_delay = min(
            self._reconnect_delay * self.config.reconnect_backoff,
            self.config.max_reconnect_delay
        )
    
    async def _process_messages(self):
        """Process incoming messages"""
        try:
            async for message in self.websocket:
                self._stats["messages_received"] += 1
                
                if isinstance(message, str):
                    await self._handle_text_message(message)
                elif isinstance(message, bytes):
                    await self._handle_binary_message(message)
                    
        except websockets.exceptions.ConnectionClosed as e:
            self._logger.info(f"🔌 Connection closed: {e}")
            self._connected = False
            self._authenticated = False
            
            if self.on_disconnect:
                try:
                    self.on_disconnect()
                except Exception as cb_error:
                    self._logger.error(f"Error in on_disconnect callback: {cb_error}")
            
            # Attempt reconnect
            if self.config.auto_reconnect and not self._shutdown:
                await self.connect()
                
        except Exception as e:
            self._logger.error(f"❌ Error processing messages: {e}")
            self._stats["errors"] += 1
            if self.on_error:
                self.on_error(e)
    
    async def _handle_text_message(self, message: str):
        """Handle text/JSON message"""
        try:
            data = json.loads(message)
            
            # Handle system messages
            msg_type = data.get("type")
            
            if msg_type == "pong":
                return
            elif msg_type == "error":
                self._logger.error(f"Server error: {data.get('error')}")
                return
            elif msg_type in ("subscribe_ack", "unsubscribe_ack", "publish_ack"):
                self._logger.debug(f"Received: {msg_type}")
                return
            
            # Try to parse as TransportEnvelope
            try:
                envelope = TransportEnvelope(**data)
                self._message_buffer.append({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "envelope": envelope
                })
                
                if self.on_message:
                    self.on_message(envelope)
            except Exception:
                # Not a valid envelope, treat as raw message
                if self.on_message:
                    # Create minimal envelope
                    envelope = TransportEnvelope(
                        event_type="raw",
                        schema_family=SchemaFamily.SYSTEM,
                        source="server",
                        payload={"raw_data": data}
                    )
                    self.on_message(envelope)
                    
        except json.JSONDecodeError:
            self._logger.warning(f"Received non-JSON message: {message[:100]}")
    
    async def _handle_binary_message(self, data: bytes):
        """Handle binary message"""
        # Create envelope for binary data
        envelope = TransportEnvelope(
            event_type="binary",
            schema_family=SchemaFamily.SYSTEM,
            source="server",
            payload={"size_bytes": len(data), "data": data.hex()[:100]}
        )
        
        if self.on_message:
            self.on_message(envelope)
    
    async def _ping_loop(self):
        """Send periodic ping messages."""
        while self._connected and not self._shutdown:
            try:
                await asyncio.sleep(self.config.ping_interval)
                if self._connected:
                    await self.websocket.send(json.dumps({"type": "ping"}))
            except Exception:
                break
    
    async def _drain_queue(self):
        """Send queued messages"""
        while not self._message_queue.empty() and self._connected:
            try:
                envelope = self._message_queue.get_nowait()
                if isinstance(envelope, TransportEnvelope):
                    await self._send_envelope(envelope)
                elif isinstance(envelope, dict):
                    await self.websocket.send(json.dumps(envelope))
            except asyncio.QueueEmpty:
                break
            except Exception as e:
                self._logger.error(f"Error draining queue: {e}")
                break
    
    async def _send_envelope(self, envelope: TransportEnvelope) -> bool:
        """Send envelope to server."""
        if not self._connected:
            return False
        
        try:
            await self.websocket.send(envelope.model_dump_json())
            self._stats["messages_sent"] += 1
            return True
        except websockets.exceptions.ConnectionClosed:
            await self._queue_message(envelope)
            self._connected = False
            return False
    
    async def _send_message(self, data: dict) -> bool:
        """Send JSON message to server."""
        if not self._connected:
            return False
        
        try:
            await self.websocket.send(json.dumps(data))
            self._stats["messages_sent"] += 1
            return True
        except websockets.exceptions.ConnectionClosed:
            await self._queue_message(data)
            self._connected = False
            return False
    
    async def _queue_message(self, message: Union[TransportEnvelope, dict]):
        """Queue message for later sending"""
        try:
            self._message_queue.put_nowait(message)
            self._logger.debug(f"📤 Queued message (queue size: {self._message_queue.qsize()})")
        except asyncio.QueueFull:
            self._logger.warning("⚠️ Message queue full, dropping message")
    
    async def subscribe(self, topics: Union[str, list[str]]) -> bool:
        """Subscribe to topics.
        
        Args:
            topics: Single topic or list of topics to subscribe to
        
        Returns:
            True if subscription request was sent
        """
        if isinstance(topics, str):
            topics = [topics]
        
        self._subscriptions.update(topics)
        
        if not self._connected:
            self._pending_subscriptions.update(topics)
            return False
        
        return await self._send_message({
            "type": "subscribe",
            "topics": topics
        })
    
    async def unsubscribe(self, topics: Union[str, list[str]]) -> bool:
        """Unsubscribe from topics."""
        if isinstance(topics, str):
            topics = [topics]
        
        for topic in topics:
            self._subscriptions.discard(topic)
        
        if not self._connected:
            return False
        
        return await self._send_message({
            "type": "unsubscribe",
            "topics": topics
        })
    
    async def get_stats(self) -> dict:
        """Request server statistics."""
        if not self._connected:
            return {}
        
        await self._send_message({"type": "get_stats"})
        return {}
    
    async def disconnect(self):
        """Disconnect from server"""
        self._shutdown = True
        
        if self._ping_task:
            self._ping_task.cancel()
            try:
                await self._ping_task
            except asyncio.CancelledError:
                pass
        
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
        
        if self.websocket:
            await self.websocket.close()
        
        self._connected = False
        self._authenticated = False
        self._logger.info(f"👋 Disconnected from {self.url}")
    
    def get_buffered_messages(self, count: int = 10) -> list:
        """Get buffered messages."""
        return list(self._message_buffer)[-count:]
    
    def get_client_stats(self) -> dict[str, Any]:
        """Get client statistics."""
        return {
            **self._stats,
            "connected": self._connected,
            "authenticated": self._authenticated,
            "subscriptions": list(self._subscriptions),
            "queue_size": self._message_queue.qsize(),
            "buffer_size": len(self._message_buffer),
        }


# =============================================================================
# Publisher Client v2
# =============================================================================

class WSSPublisherV2(WSSClientV2):
    """Publisher client for sending data to typed topics."""
    
    def __init__(
        self,
        config: Optional[ClientConfigV2] = None,
        default_topic: Optional[str] = None
    ):
        super().__init__(config)
        self.default_topic = default_topic
        self._trace_id: Optional[str] = None
    
    async def publish(
        self,
        envelope: TransportEnvelope,
        topic: Optional[str] = None
    ) -> bool:
        """Publish envelope to server.
        
        Args:
            envelope: TransportEnvelope to publish
            topic: Optional topic override
        
        Returns:
            True if published successfully
        """
        if not self._connected:
            await self._queue_message(envelope)
            return False
        
        # Add trace_id if not present
        if not envelope.trace_id and self._trace_id:
            envelope.trace_id = self._trace_id
        
        return await self._send_message({
            "type": "publish",
            "envelope": envelope.model_dump(),
            "topic": topic
        })
    
    async def publish_detection(
        self,
        frame_id: str,
        detections: list[dict],
        inference_time_ms: float,
        source: str = "yolo",
        **kwargs
    ) -> bool:
        """Publish YOLO detection results."""
        payload = YOLODetectionPayload(
            detections=detections,
            inference_time_ms=inference_time_ms,
            frame_id=frame_id,
            **kwargs
        )
        
        envelope = TransportEnvelope(
            event_type="detection",
            schema_family=SchemaFamily.DETECTION,
            source=source,
            frame_ref=frame_id,
            payload=payload.model_dump()
        )
        
        return await self.publish(envelope, Topic.VISION_DETECTION_YOLO.value)
    
    async def publish_segmentation(
        self,
        frame_id: str,
        roi_id: str,
        masks: list[dict],
        confidence: float,
        source: str = "sam",
        **kwargs
    ) -> bool:
        """Publish SAM segmentation results."""
        payload = SAMSegmentationPayload(
            masks=masks,
            roi_id=roi_id,
            confidence=confidence,
            frame_id=frame_id,
            **kwargs
        )
        
        envelope = TransportEnvelope(
            event_type="segmentation",
            schema_family=SchemaFamily.SEGMENTATION,
            source=source,
            frame_ref=frame_id,
            payload=payload.model_dump()
        )
        
        return await self.publish(envelope, Topic.VISION_SEGMENTATION_SAM.value)
    
    async def publish_classification(
        self,
        frame_id: str,
        roi_id: str,
        classification: str,
        confidence: float,
        source: str = "eagle",
        **kwargs
    ) -> bool:
        """Publish Eagle classification results."""
        payload = EagleClassificationPayload(
            classification=classification,
            confidence=confidence,
            roi_id=roi_id,
            frame_id=frame_id,
            **kwargs
        )
        
        envelope = TransportEnvelope(
            event_type="classification",
            schema_family=SchemaFamily.CLASSIFICATION,
            source=source,
            frame_ref=frame_id,
            payload=payload.model_dump()
        )
        
        return await self.publish(envelope, Topic.VISION_CLASSIFICATION_EAGLE.value)
    
    async def publish_analysis(
        self,
        frame_id: str,
        analysis: str,
        risk_level: str,
        recommendation: str,
        confidence: float,
        source: str = "qwen",
        **kwargs
    ) -> bool:
        """Publish Qwen/Kimi analysis results."""
        payload = QwenAnalysisPayload(
            analysis=analysis,
            risk_level=risk_level,
            recommendation=recommendation,
            confidence=confidence,
            frame_id=frame_id,
            **kwargs
        )
        
        envelope = TransportEnvelope(
            event_type="analysis",
            schema_family=SchemaFamily.ANALYSIS,
            source=source,
            frame_ref=frame_id,
            payload=payload.model_dump()
        )
        
        return await self.publish(envelope, Topic.VISION_ANALYSIS_QWEN.value)
    
    def set_trace_id(self, trace_id: str) -> None:
        """Set trace ID for subsequent publishes."""
        self._trace_id = trace_id
    
    def clear_trace_id(self) -> None:
        """Clear trace ID."""
        self._trace_id = None


# =============================================================================
# Subscriber Client v2
# =============================================================================

class WSSSubscriberV2(WSSClientV2):
    """Subscriber client for receiving data from typed topics."""
    
    def __init__(
        self,
        topics: Optional[Union[str, list[str]]] = None,
        config: Optional[ClientConfigV2] = None
    ):
        super().__init__(config)
        self._initial_topics = topics if isinstance(topics, list) else [topics] if topics else []
        self._topic_callbacks: dict[str, Callable[[TransportEnvelope], None]] = {}
        self._event_type_callbacks: dict[str, Callable[[TransportEnvelope], None]] = {}
        self._schema_family_callbacks: dict[str, Callable[[TransportEnvelope], None]] = {}
    
    async def connect(self) -> bool:
        """Connect and subscribe to initial topics."""
        result = await super().connect()
        
        if result and self._initial_topics:
            await self.subscribe(self._initial_topics)
        
        return result
    
    def on_topic(
        self,
        topic: str,
        callback: Callable[[TransportEnvelope], None]
    ) -> None:
        """Register callback for specific topic."""
        self._topic_callbacks[topic] = callback
    
    def on_event_type(
        self,
        event_type: str,
        callback: Callable[[TransportEnvelope], None]
    ) -> None:
        """Register callback for specific event type."""
        self._event_type_callbacks[event_type] = callback
    
    def on_schema_family(
        self,
        schema_family: Union[str, SchemaFamily],
        callback: Callable[[TransportEnvelope], None]
    ) -> None:
        """Register callback for specific schema family."""
        family = schema_family.value if isinstance(schema_family, SchemaFamily) else schema_family
        self._schema_family_callbacks[family] = callback
    
    async def _handle_text_message(self, message: str):
        """Handle text message with callback routing."""
        try:
            data = json.loads(message)
            
            # Handle system messages
            msg_type = data.get("type")
            if msg_type in ("pong", "error", "subscribe_ack", "unsubscribe_ack", "publish_ack"):
                return
            
            # Parse as TransportEnvelope
            try:
                envelope = TransportEnvelope(**data)
                
                # Route to callbacks
                await self._route_message(envelope)
                
            except Exception as e:
                self._logger.warning(f"Failed to parse envelope: {e}")
                
        except json.JSONDecodeError:
            self._logger.warning(f"Received non-JSON message: {message[:100]}")
    
    async def _route_message(self, envelope: TransportEnvelope) -> None:
        """Route message to appropriate callbacks."""
        # Topic callback
        if envelope.topic and envelope.topic in self._topic_callbacks:
            try:
                self._topic_callbacks[envelope.topic](envelope)
            except Exception as e:
                self._logger.error(f"Topic callback error: {e}")
        
        # Event type callback
        if envelope.event_type in self._event_type_callbacks:
            try:
                self._event_type_callbacks[envelope.event_type](envelope)
            except Exception as e:
                self._logger.error(f"Event type callback error: {e}")
        
        # Schema family callback
        if envelope.schema_family.value in self._schema_family_callbacks:
            try:
                self._schema_family_callbacks[envelope.schema_family.value](envelope)
            except Exception as e:
                self._logger.error(f"Schema family callback error: {e}")
        
        # General message callback
        if self.on_message:
            try:
                self.on_message(envelope)
            except Exception as e:
                self._logger.error(f"Message callback error: {e}")


# =============================================================================
# Convenience Functions
# =============================================================================

def create_publisher_v2(
    host: str = "localhost",
    port: int = 8000,
    auth_token: Optional[str] = None
) -> WSSPublisherV2:
    """Factory function to create a v2 publisher."""
    config = ClientConfigV2(host=host, port=port, auth_token=auth_token)
    return WSSPublisherV2(config)


def create_subscriber_v2(
    topics: Union[str, list[str]],
    host: str = "localhost",
    port: int = 8000,
    auth_token: Optional[str] = None
) -> WSSSubscriberV2:
    """Factory function to create a v2 subscriber."""
    config = ClientConfigV2(host=host, port=port, auth_token=auth_token)
    return WSSSubscriberV2(topics=topics, config=config)


# =============================================================================
# Demo Functions
# =============================================================================

async def demo_publisher_v2():
    """Demo: Publish to v2 topics"""
    publisher = create_publisher_v2()
    
    await publisher.connect()
    
    # Set trace ID for correlation
    publisher.set_trace_id(str(uuid.uuid4()))
    
    # Publish some test data
    for i in range(10):
        # YOLO detection
        await publisher.publish_detection(
            frame_id=f"frame_{i:04d}",
            detections=[{
                "class": "chart_panel",
                "confidence": 0.95,
                "bbox": [100, 100, 400, 300]
            }],
            inference_time_ms=15.5
        )
        
        # Eagle classification
        await publisher.publish_classification(
            frame_id=f"frame_{i:04d}",
            roi_id=f"roi_{i}",
            classification="order_ticket",
            confidence=0.92,
            inference_time_ms=350
        )
        
        await asyncio.sleep(0.5)
    
    await publisher.disconnect()


async def demo_subscriber_v2():
    """Demo: Subscribe to v2 topics"""
    subscriber = create_subscriber_v2(
        topics=[
            Topic.VISION_DETECTION_YOLO.value,
            Topic.VISION_CLASSIFICATION_EAGLE.value
        ]
    )
    
    def on_detection(envelope: TransportEnvelope):
        print(f"🎯 Detection: {envelope.payload.get('detections', [])}")
    
    def on_classification(envelope: TransportEnvelope):
        print(f"🦅 Classification: {envelope.payload.get('classification')}")
    
    subscriber.on_topic(Topic.VISION_DETECTION_YOLO.value, on_detection)
    subscriber.on_topic(Topic.VISION_CLASSIFICATION_EAGLE.value, on_classification)
    
    await subscriber.connect()
    
    # Keep listening
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        pass
    
    await subscriber.disconnect()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Advanced Vision WSS v2 Client")
    parser.add_argument("mode", choices=["pub", "sub"], help="Publisher or subscriber mode")
    parser.add_argument("--host", "-H", default="localhost", help="Server host")
    parser.add_argument("--port", "-p", type=int, default=8000, help="Server port")
    parser.add_argument("--topic", "-t", action="append", help="Topics to subscribe to")
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    
    if args.mode == "pub":
        asyncio.run(demo_publisher_v2())
    else:
        topics = args.topic or [Topic.VISION_DETECTION_YOLO.value]
        asyncio.run(demo_subscriber_v2())
