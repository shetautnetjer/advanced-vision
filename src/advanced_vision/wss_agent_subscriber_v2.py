"""WebSocket subscriber client v2 for OpenClaw agents to receive vision feeds.

This module provides a non-blocking WebSocket client that allows OpenClaw agents
to subscribe to typed topics (vision.detection.yolo, vision.segmentation.sam, etc.)
with schema filtering and callback support.

This is the v2 refactor - uses single port (8000) with typed topics instead
of multiple ports (8001-8005) from v1.

Example usage:
    from advanced_vision.wss_agent_subscriber_v2 import WSSAgentSubscriberV2
    
    subscriber = WSSAgentSubscriberV2()
    subscriber.subscribe("vision.detection.yolo", callback=handle_detection)
    subscriber.subscribe("vision.classification.eagle", callback=handle_classification)
    subscriber.start()  # Non-blocking
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Union

import websockets
from websockets.exceptions import ConnectionClosed, InvalidURI

from advanced_vision.wss_server_v2 import TransportEnvelope, SchemaFamily, Topic
from advanced_vision.wss_client_v2 import WSSSubscriberV2, ClientConfigV2

logger = logging.getLogger(__name__)


# =============================================================================
# Topic Definitions (re-export for convenience)
# =============================================================================

class VisionTopic:
    """Convenience class for vision pipeline topics."""
    DETECTION_YOLO = Topic.VISION_DETECTION_YOLO.value
    SEGMENTATION_SAM = Topic.VISION_SEGMENTATION_SAM.value
    CLASSIFICATION_EAGLE = Topic.VISION_CLASSIFICATION_EAGLE.value
    ANALYSIS_QWEN = Topic.VISION_ANALYSIS_QWEN.value
    SYSTEM_HEARTBEAT = Topic.SYSTEM_HEARTBEAT.value
    SYSTEM_ERROR = Topic.SYSTEM_ERROR.value
    SYSTEM_METRICS = Topic.SYSTEM_METRICS.value
    
    ALL_VISION = [
        DETECTION_YOLO,
        SEGMENTATION_SAM,
        CLASSIFICATION_EAGLE,
        ANALYSIS_QWEN,
    ]


# =============================================================================
# Message Buffer
# =============================================================================

@dataclass
class MessageBuffer:
    """Ring buffer for storing recent messages."""
    max_size: int = 100
    
    def __post_init__(self):
        self._buffer: deque = deque(maxlen=self.max_size)
    
    def add(self, envelope: TransportEnvelope) -> None:
        """Add a message to the buffer."""
        self._buffer.append({
            "timestamp": time.time(),
            "envelope": envelope
        })
    
    def get_recent(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get the most recent messages."""
        return list(self._buffer)[-count:]
    
    def get_by_topic(self, topic: str, count: int = 10) -> List[Dict[str, Any]]:
        """Get recent messages for a specific topic."""
        matching = [
            item for item in self._buffer
            if item["envelope"].topic == topic
        ]
        return matching[-count:]
    
    def get_by_schema_family(self, family: SchemaFamily, count: int = 10) -> List[Dict[str, Any]]:
        """Get recent messages by schema family."""
        matching = [
            item for item in self._buffer
            if item["envelope"].schema_family == family
        ]
        return matching[-count:]
    
    def clear(self) -> None:
        """Clear the buffer."""
        self._buffer.clear()


# =============================================================================
# Subscription Config
# =============================================================================

@dataclass
class SubscriptionConfig:
    """Configuration for a single topic subscription."""
    topic: str
    callback: Optional[Callable[[TransportEnvelope], None]] = None
    filter_fn: Optional[Callable[[TransportEnvelope], bool]] = None


# =============================================================================
# Agent Subscriber v2
# =============================================================================

class WSSAgentSubscriberV2:
    """WebSocket v2 subscriber client for OpenClaw agents.
    
    This client allows agents to subscribe to typed vision topics
    with schema filtering and callback support.
    
    Features:
        - Subscribe to topics: vision.detection.yolo, vision.segmentation.sam, etc.
        - Schema filtering (detection, segmentation, classification, analysis, system)
        - Ring buffer for recent messages
        - Callback triggering on specific events
        - Non-blocking operation
        - Automatic reconnection
        - Single port (8000) architecture
    
    Example:
        subscriber = WSSAgentSubscriberV2()
        
        # Subscribe to YOLO detections
        subscriber.subscribe("vision.detection.yolo", callback=on_detection)
        
        # Subscribe to Eagle classifications
        subscriber.subscribe("vision.classification.eagle", callback=on_classification)
        
        # Subscribe to all analysis
        subscriber.subscribe("vision.analysis.qwen", callback=on_analysis)
        
        # Start all subscriptions (non-blocking)
        subscriber.start()
        
        # Later...
        subscriber.stop()
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 8000,
        buffer_size: int = 100,
        reconnect_delay: float = 5.0,
        enable_logging: bool = True,
        auth_token: Optional[str] = None,
    ):
        """Initialize the v2 subscriber.
        
        Args:
            host: Server host
            port: Server port (default 8000 for v2)
            buffer_size: Size of the ring buffer for recent messages
            reconnect_delay: Delay between reconnection attempts in seconds
            enable_logging: Whether to log received messages
            auth_token: Optional authentication token
        """
        self.host = host
        self.port = port
        self.buffer_size = buffer_size
        self.reconnect_delay = reconnect_delay
        self.enable_logging = enable_logging
        
        # Storage
        self._subscriptions: Dict[str, SubscriptionConfig] = {}
        self._buffer = MessageBuffer(max_size=buffer_size)
        self._global_callbacks: List[Callable[[TransportEnvelope], None]] = []
        
        # Internal subscriber
        config = ClientConfigV2(
            host=host,
            port=port,
            auth_token=auth_token,
            auto_reconnect=True,
            reconnect_delay=reconnect_delay,
        )
        self._subscriber = WSSSubscriberV2(config=config)
        
        # State
        self._running = False
        
        # Statistics
        self._stats = {
            "total_messages": 0,
            "total_errors": 0,
            "messages_by_topic": defaultdict(int),
        }
        
        # Setup logging
        if enable_logging:
            self._setup_logging()
    
    def _setup_logging(self) -> None:
        """Configure logging for received messages."""
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        if not logger.level:
            logger.setLevel(logging.INFO)
    
    def subscribe(
        self,
        topic: str,
        callback: Optional[Callable[[TransportEnvelope], None]] = None,
        filter_fn: Optional[Callable[[TransportEnvelope], bool]] = None,
    ) -> None:
        """Subscribe to a vision topic.
        
        Args:
            topic: Topic to subscribe to (e.g., "vision.detection.yolo")
            callback: Optional callback function for messages on this topic
            filter_fn: Optional filter function (returns True to process)
        
        Example:
            # Subscribe to YOLO detections
            subscriber.subscribe("vision.detection.yolo", callback=handle_detection)
            
            # Subscribe to all Eagle classifications with filter
            subscriber.subscribe(
                "vision.classification.eagle",
                callback=handle_pattern,
                filter_fn=lambda e: e.payload.get("confidence", 0) > 0.8
            )
        """
        self._subscriptions[topic] = SubscriptionConfig(
            topic=topic,
            callback=callback,
            filter_fn=filter_fn
        )
        
        # Register callback with internal subscriber
        if callback:
            self._subscriber.on_topic(topic, lambda env: self._handle_message(topic, env))
        
        logger.info(f"Subscribed to topic: {topic}")
    
    def subscribe_to_all_vision(self, callback: Optional[Callable[[TransportEnvelope], None]] = None) -> None:
        """Subscribe to all vision topics.
        
        Args:
            callback: Callback function for all vision messages
        """
        for topic in VisionTopic.ALL_VISION:
            self.subscribe(topic, callback)
    
    def add_global_callback(
        self,
        callback: Callable[[TransportEnvelope], None]
    ) -> None:
        """Add a callback that receives all messages from all topics.
        
        Args:
            callback: Function receiving every message
        """
        self._global_callbacks.append(callback)
        self._subscriber.on_message(callback)
    
    def remove_global_callback(
        self,
        callback: Callable[[TransportEnvelope], None]
    ) -> None:
        """Remove a global callback."""
        if callback in self._global_callbacks:
            self._global_callbacks.remove(callback)
    
    def _handle_message(self, topic: str, envelope: TransportEnvelope) -> None:
        """Process an incoming message."""
        # Update statistics
        self._stats["total_messages"] += 1
        self._stats["messages_by_topic"][topic] += 1
        
        # Add to ring buffer
        self._buffer.add(envelope)
        
        # Log if enabled
        if self.enable_logging:
            logger.debug(f"[{topic}] {envelope.event_type}: {envelope.payload}")
        
        # Get subscription config
        config = self._subscriptions.get(topic)
        if not config:
            return
        
        # Check filter
        if config.filter_fn and not config.filter_fn(envelope):
            return
        
        # Trigger subscription callback
        if config.callback:
            try:
                config.callback(envelope)
            except Exception as e:
                logger.error(f"Callback error for topic {topic}: {e}")
                self._stats["total_errors"] += 1
    
    def get_recent_messages(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get recent messages from the ring buffer.
        
        Args:
            count: Number of messages to retrieve
        
        Returns:
            List of recent messages with timestamps
        """
        return self._buffer.get_recent(count)
    
    def get_recent_by_topic(self, topic: str, count: int = 10) -> List[Dict[str, Any]]:
        """Get recent messages for a specific topic."""
        return self._buffer.get_by_topic(topic, count)
    
    def get_recent_by_schema_family(self, family: SchemaFamily, count: int = 10) -> List[Dict[str, Any]]:
        """Get recent messages by schema family."""
        return self._buffer.get_by_schema_family(family, count)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get subscriber statistics."""
        return {
            **self._stats,
            "subscriptions": {
                topic: {
                    "has_callback": config.callback is not None,
                    "has_filter": config.filter_fn is not None,
                }
                for topic, config in self._subscriptions.items()
            },
            "client_stats": self._subscriber.get_client_stats(),
        }
    
    def start(self) -> None:
        """Start all subscriptions (non-blocking).
        
        This starts the event loop in a background thread if not already running.
        """
        if self._running:
            logger.warning("Subscriber already running")
            return
        
        self._running = True
        
        # Subscribe to all configured topics
        topics = list(self._subscriptions.keys())
        if topics:
            asyncio.run(self._subscriber.subscribe(topics))
        
        # Connect in background
        asyncio.run(self._subscriber.connect())
        
        logger.info(f"Started v2 subscriber with {len(self._subscriptions)} subscription(s)")
    
    def stop(self) -> None:
        """Stop all subscriptions."""
        if not self._running:
            return
        
        self._running = False
        asyncio.run(self._subscriber.disconnect())
        
        logger.info("V2 subscriber stopped")
    
    async def start_async(self) -> None:
        """Start subscriber in async context (blocking until stopped).
        
        Use this when running inside an existing async event loop.
        """
        self._running = True
        
        # Subscribe to all configured topics
        topics = list(self._subscriptions.keys())
        if topics:
            await self._subscriber.subscribe(topics)
        
        await self._subscriber.connect()
    
    def is_running(self) -> bool:
        """Check if subscriber is running."""
        return self._running
    
    def is_connected(self) -> bool:
        """Check if subscriber is connected."""
        return self._subscriber.is_connected


# =============================================================================
# Convenience Functions
# =============================================================================

def subscribe_to_topic_v2(
    topic: str,
    callback: Optional[Callable[[TransportEnvelope], None]] = None,
    host: str = "localhost",
    port: int = 8000,
    auth_token: Optional[str] = None,
) -> WSSAgentSubscriberV2:
    """Quick-start function to create and start a v2 subscriber.
    
    Args:
        topic: Topic to subscribe to
        callback: Message callback function
        host: Server host
        port: Server port (default 8000 for v2)
        auth_token: Optional authentication token
    
    Returns:
        Running WSSAgentSubscriberV2 instance
    
    Example:
        def on_detection(envelope):
            print(f"Detection: {envelope.payload}")
        
        sub = subscribe_to_topic_v2("vision.detection.yolo", callback=on_detection)
    """
    subscriber = WSSAgentSubscriberV2(
        host=host,
        port=port,
        auth_token=auth_token
    )
    subscriber.subscribe(topic, callback=callback)
    subscriber.start()
    return subscriber


def subscribe_to_all_vision_v2(
    callback: Callable[[TransportEnvelope], None],
    host: str = "localhost",
    port: int = 8000,
    auth_token: Optional[str] = None,
) -> WSSAgentSubscriberV2:
    """Quick-start function to subscribe to all vision topics.
    
    Args:
        callback: Message callback function for all topics
        host: Server host
        port: Server port (default 8000 for v2)
        auth_token: Optional authentication token
    
    Returns:
        Running WSSAgentSubscriberV2 instance
    """
    subscriber = WSSAgentSubscriberV2(
        host=host,
        port=port,
        auth_token=auth_token
    )
    subscriber.subscribe_to_all_vision(callback=callback)
    subscriber.start()
    return subscriber


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    # Demo the v2 subscriber
    logging.basicConfig(level=logging.INFO)
    
    def on_detection(envelope: TransportEnvelope):
        print(f"🎯 Detection: {envelope.payload.get('detections', [])}")
    
    def on_classification(envelope: TransportEnvelope):
        print(f"🦅 Classification: {envelope.payload.get('classification')}")
    
    def on_analysis(envelope: TransportEnvelope):
        print(f"🧠 Analysis: {envelope.payload.get('analysis', '')[:50]}...")
    
    subscriber = WSSAgentSubscriberV2()
    subscriber.subscribe("vision.detection.yolo", callback=on_detection)
    subscriber.subscribe("vision.classification.eagle", callback=on_classification)
    subscriber.subscribe("vision.analysis.qwen", callback=on_analysis)
    
    subscriber.start()
    
    try:
        # Keep running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        subscriber.stop()
        print("Final stats:", subscriber.get_statistics())
