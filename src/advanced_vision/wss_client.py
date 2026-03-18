#!/usr/bin/env python3
"""
WebSocket Client for Advanced Vision Distributed Architecture
Supports publishing to feeds and subscribing with auto-reconnect
"""

import asyncio
import websockets
import json
import logging
from typing import Optional, Callable, Dict, Any, Union
from dataclasses import dataclass
from datetime import datetime
import time
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


@dataclass
class ClientConfig:
    """Configuration for WebSocket client"""
    host: str = "localhost"
    port: int = 8001
    path: str = "/"
    auto_reconnect: bool = True
    reconnect_delay: float = 1.0
    max_reconnect_delay: float = 30.0
    reconnect_backoff: float = 2.0
    ping_interval: float = 20.0
    connection_timeout: float = 10.0
    max_retries: int = 0  # 0 = unlimited


class WSSClient:
    """WebSocket client with auto-reconnect for Advanced Vision feeds"""
    
    def __init__(self, config: Optional[ClientConfig] = None):
        self.config = config or ClientConfig()
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self._connected = False
        self._shutdown = False
        self._retry_count = 0
        self._reconnect_delay = self.config.reconnect_delay
        
        # Callbacks
        self.on_message: Optional[Callable[[Union[str, bytes]], None]] = None
        self.on_json: Optional[Callable[[dict], None]] = None
        self.on_binary: Optional[Callable[[bytes], None]] = None
        self.on_connect: Optional[Callable[[], None]] = None
        self.on_disconnect: Optional[Callable[[], None]] = None
        self.on_error: Optional[Callable[[Exception], None]] = None
        
        # Message queue for offline buffering
        self._message_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        self._processing_task: Optional[asyncio.Task] = None
        
    @property
    def url(self) -> str:
        """Build WebSocket URL"""
        return f"ws://{self.config.host}:{self.config.port}{self.config.path}"
        
    @property
    def is_connected(self) -> bool:
        """Check if client is connected"""
        return self._connected and self.websocket is not None
        
    async def connect(self) -> bool:
        """Connect to WebSocket server with retry logic"""
        while not self._shutdown:
            try:
                print(f"🔗 Connecting to {self.url}...")
                
                self.websocket = await asyncio.wait_for(
                    websockets.connect(self.url),
                    timeout=self.config.connection_timeout
                )
                
                self._connected = True
                self._retry_count = 0
                self._reconnect_delay = self.config.reconnect_delay
                
                print(f"✅ Connected to {self.url}")
                
                if self.on_connect:
                    try:
                        self.on_connect()
                    except Exception as e:
                        print(f"Error in on_connect callback: {e}")
                        
                # Start message processing
                self._processing_task = asyncio.create_task(self._process_messages())
                
                # Process queued messages
                await self._drain_queue()
                
                return True
                
            except asyncio.TimeoutError:
                print(f"⏱️ Connection timeout to {self.url}")
                await self._handle_reconnect()
                
            except websockets.exceptions.InvalidStatusCode as e:
                print(f"❌ Connection rejected: {e.status_code}")
                if self.on_error:
                    self.on_error(e)
                await self._handle_reconnect()
                
            except Exception as e:
                print(f"❌ Connection error: {e}")
                if self.on_error:
                    self.on_error(e)
                await self._handle_reconnect()
                
        return False
        
    async def _handle_reconnect(self):
        """Handle reconnection with backoff"""
        if not self.config.auto_reconnect or self._shutdown:
            return
            
        self._retry_count += 1
        
        if self.config.max_retries > 0 and self._retry_count > self.config.max_retries:
            print(f"❌ Max retries ({self.config.max_retries}) exceeded")
            return
            
        print(f"🔄 Reconnecting in {self._reconnect_delay:.1f}s (attempt {self._retry_count})...")
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
                if isinstance(message, str):
                    await self._handle_text_message(message)
                elif isinstance(message, bytes):
                    await self._handle_binary_message(message)
                    
        except websockets.exceptions.ConnectionClosed as e:
            print(f"🔌 Connection closed: {e}")
            self._connected = False
            
            if self.on_disconnect:
                try:
                    self.on_disconnect()
                except Exception as cb_error:
                    print(f"Error in on_disconnect callback: {cb_error}")
                    
            # Attempt reconnect
            if self.config.auto_reconnect and not self._shutdown:
                await self.connect()
                
        except Exception as e:
            print(f"❌ Error processing messages: {e}")
            if self.on_error:
                self.on_error(e)
                
    async def _handle_text_message(self, message: str):
        """Handle text/JSON message"""
        if self.on_message:
            try:
                self.on_message(message)
            except Exception as e:
                print(f"Error in on_message callback: {e}")
                
        if self.on_json:
            try:
                data = json.loads(message)
                self.on_json(data)
            except json.JSONDecodeError:
                pass  # Not JSON, ignore for on_json
            except Exception as e:
                print(f"Error in on_json callback: {e}")
                
    async def _handle_binary_message(self, data: bytes):
        """Handle binary message"""
        if self.on_message:
            try:
                self.on_message(data)
            except Exception as e:
                print(f"Error in on_message callback: {e}")
                
        if self.on_binary:
            try:
                self.on_binary(data)
            except Exception as e:
                print(f"Error in on_binary callback: {e}")
                
    async def _drain_queue(self):
        """Send queued messages"""
        while not self._message_queue.empty() and self._connected:
            try:
                message = self._message_queue.get_nowait()
                if isinstance(message, dict):
                    await self.send_json(message)
                elif isinstance(message, bytes):
                    await self.send_binary(message)
                else:
                    await self.send_text(message)
            except asyncio.QueueEmpty:
                break
            except Exception as e:
                print(f"Error draining queue: {e}")
                break
                
    async def send_text(self, message: str) -> bool:
        """Send text message"""
        if not self._connected:
            await self._queue_message(message)
            return False
            
        try:
            await self.websocket.send(message)
            return True
        except websockets.exceptions.ConnectionClosed:
            await self._queue_message(message)
            self._connected = False
            return False
            
    async def send_json(self, data: dict) -> bool:
        """Send JSON message"""
        return await self.send_text(json.dumps(data))
        
    async def send_binary(self, data: bytes) -> bool:
        """Send binary message"""
        if not self._connected:
            await self._queue_message(data)
            return False
            
        try:
            await self.websocket.send(data)
            return True
        except websockets.exceptions.ConnectionClosed:
            await self._queue_message(data)
            self._connected = False
            return False
            
    async def _queue_message(self, message: Union[str, bytes, dict]):
        """Queue message for later sending"""
        try:
            self._message_queue.put_nowait(message)
            print(f"📤 Queued message (queue size: {self._message_queue.qsize()})")
        except asyncio.QueueFull:
            print("⚠️ Message queue full, dropping message")
            
    async def disconnect(self):
        """Disconnect from server"""
        self._shutdown = True
        
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
                
        if self.websocket:
            await self.websocket.close()
            
        self._connected = False
        print(f"👋 Disconnected from {self.url}")


class WSSPublisher(WSSClient):
    """Publisher client for sending data to feeds"""
    
    def __init__(self, feed_port: int, host: str = "localhost", config: Optional[ClientConfig] = None):
        if config is None:
            config = ClientConfig(host=host, port=feed_port)
        else:
            config.host = host
            config.port = feed_port
        super().__init__(config)
        self.feed_port = feed_port
        
    async def publish_frame(self, frame_data: bytes, metadata: Optional[dict] = None) -> bool:
        """Publish a binary frame (image)"""
        # Send metadata first if provided
        if metadata:
            success = await self.send_json({
                "type": "frame_metadata",
                "timestamp": datetime.utcnow().isoformat(),
                **metadata
            })
            if not success:
                return False
                
        # Send frame data
        return await self.send_binary(frame_data)
        
    async def publish_detection(self, boxes: list, classes: list, scores: list) -> bool:
        """Publish YOLO detection results"""
        return await self.send_json({
            "type": "detection",
            "timestamp": datetime.utcnow().isoformat(),
            "boxes": boxes,
            "classes": classes,
            "scores": scores
        })
        
    async def publish_segmentation(self, masks: list, classes: list) -> bool:
        """Publish MobileSAM segmentation results"""
        return await self.send_json({
            "type": "segmentation",
            "timestamp": datetime.utcnow().isoformat(),
            "masks": masks,
            "classes": classes
        })
        
    async def publish_classification(self, label: str, confidence: float, details: Optional[dict] = None) -> bool:
        """Publish Eagle Vision classification"""
        data = {
            "type": "classification",
            "timestamp": datetime.utcnow().isoformat(),
            "label": label,
            "confidence": confidence
        }
        if details:
            data["details"] = details
        return await self.send_json(data)
        
    async def publish_analysis(self, analysis_type: str, result: dict) -> bool:
        """Publish reviewer analysis results"""
        return await self.send_json({
            "type": "analysis",
            "analysis_type": analysis_type,
            "timestamp": datetime.utcnow().isoformat(),
            "result": result
        })


class WSSSubscriber(WSSClient):
    """Subscriber client for receiving data from feeds"""
    
    def __init__(self, feed_port: int, host: str = "localhost", config: Optional[ClientConfig] = None):
        if config is None:
            config = ClientConfig(host=host, port=feed_port)
        else:
            config.host = host
            config.port = feed_port
        super().__init__(config)
        self.feed_port = feed_port
        self._message_buffer: list = []
        self._buffer_size = 100
        
    def enable_buffering(self, size: int = 100):
        """Enable message buffering"""
        self._buffer_size = size
        self.on_message = self._buffer_message
        
    def _buffer_message(self, message: Union[str, bytes]):
        """Buffer incoming messages"""
        self._message_buffer.append({
            "timestamp": datetime.utcnow().isoformat(),
            "data": message
        })
        if len(self._message_buffer) > self._buffer_size:
            self._message_buffer.pop(0)
            
    def get_buffered_messages(self) -> list:
        """Get buffered messages"""
        return self._message_buffer.copy()
        
    def clear_buffer(self):
        """Clear message buffer"""
        self._message_buffer.clear()


async def demo_publisher():
    """Demo: Publish to a feed"""
    publisher = WSSPublisher(feed_port=8001)
    
    await publisher.connect()
    
    # Publish some test data
    for i in range(10):
        await publisher.publish_classification(
            label=f"test_object_{i}",
            confidence=0.95 - (i * 0.05),
            details={"bbox": [100, 100, 200, 200]}
        )
        await asyncio.sleep(1)
        
    await publisher.disconnect()


async def demo_subscriber():
    """Demo: Subscribe to a feed"""
    subscriber = WSSSubscriber(feed_port=8001)
    
    def on_json(data):
        print(f"📨 Received: {json.dumps(data, indent=2)}")
        
    def on_binary(data):
        print(f"📦 Received binary: {len(data)} bytes")
        
    subscriber.on_json = on_json
    subscriber.on_binary = on_binary
    
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
    
    parser = argparse.ArgumentParser(description="Advanced Vision WSS Client")
    parser.add_argument("mode", choices=["pub", "sub"], help="Publisher or subscriber mode")
    parser.add_argument("--port", "-p", type=int, default=8001, help="Feed port")
    parser.add_argument("--host", "-H", default="localhost", help="Server host")
    args = parser.parse_args()
    
    if args.mode == "pub":
        asyncio.run(demo_publisher())
    else:
        asyncio.run(demo_subscriber())
