"""WebSocket subscriber client for OpenClaw agents to receive vision feeds.

This module provides a non-blocking WebSocket client that allows OpenClaw agents
to subscribe to multiple vision feeds (YOLO, SAM, Eagle, Analysis) with schema
filtering and callback support.

Example usage:
    from advanced_vision.wss_agent_subscriber import WSSAgentSubscriber
    
    subscriber = WSSAgentSubscriber()
    subscriber.subscribe(8004, schema="trading", callback=handle_pattern)
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
from typing import Callable, Dict, List, Optional, Set, Any

import websockets
from websockets.exceptions import ConnectionClosed, InvalidURI

logger = logging.getLogger(__name__)


class FeedPort(Enum):
    """Standard ports for vision feed services."""
    YOLO = 8002        # Object detections
    SAM = 8003         # Segmentations
    EAGLE = 8004       # Classifications
    ANALYSIS = 8005    # Analysis results


class SchemaType(Enum):
    """Schema types for filtering messages."""
    UI = "ui"
    TRADING = "trading"
    BOTH = "both"


@dataclass
class FeedConfig:
    """Configuration for a single feed subscription."""
    port: int
    schema: SchemaType
    callback: Optional[Callable[[Dict[str, Any]], None]] = None
    host: str = "localhost"
    path: str = "/"
    
    @property
    def uri(self) -> str:
        """Generate WebSocket URI from config."""
        return f"ws://{self.host}:{self.port}{self.path}"


@dataclass
class MessageBuffer:
    """Ring buffer for storing recent messages."""
    max_size: int = 100
    
    def __post_init__(self):
        self._buffer: deque = deque(maxlen=self.max_size)
    
    def add(self, message: Dict[str, Any]) -> None:
        """Add a message to the buffer."""
        self._buffer.append({
            "timestamp": time.time(),
            "message": message
        })
    
    def get_recent(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get the most recent messages."""
        return list(self._buffer)[-count:]
    
    def clear(self) -> None:
        """Clear the buffer."""
        self._buffer.clear()


@dataclass
class Subscription:
    """Active subscription state."""
    config: FeedConfig
    websocket: Optional[websockets.WebSocketClientProtocol] = None
    task: Optional[asyncio.Task] = None
    connected: bool = False
    message_count: int = 0
    error_count: int = 0


class WSSAgentSubscriber:
    """WebSocket subscriber client for OpenClaw agents.
    
    This client allows agents to subscribe to multiple vision feeds
    simultaneously with schema filtering and callback support.
    
    Features:
        - Subscribe to multiple feeds (YOLO, SAM, Eagle, Analysis)
        - Schema filtering (ui, trading, both)
        - Ring buffer for recent frames
        - Callback triggering on specific events
        - Non-blocking operation
        - Automatic reconnection
    
    Example:
        subscriber = WSSAgentSubscriber()
        
        # Subscribe to trading patterns from Eagle
        subscriber.subscribe(8004, schema="trading", callback=on_pattern)
        
        # Subscribe to UI navigation events
        subscriber.subscribe(8002, schema="ui", callback=on_detection)
        
        # Start all subscriptions (non-blocking)
        subscriber.start()
        
        # Later...
        subscriber.stop()
    """
    
    # Feed port mappings
    FEED_PORTS = {
        "yolo": FeedPort.YOLO,
        "sam": FeedPort.SAM,
        "eagle": FeedPort.EAGLE,
        "analysis": FeedPort.ANALYSIS,
    }
    
    def __init__(
        self,
        host: str = "localhost",
        buffer_size: int = 100,
        reconnect_delay: float = 5.0,
        enable_logging: bool = True
    ):
        """Initialize the subscriber.
        
        Args:
            host: Default host for all feeds
            buffer_size: Size of the ring buffer for recent messages
            reconnect_delay: Delay between reconnection attempts in seconds
            enable_logging: Whether to log received messages
        """
        self.host = host
        self.buffer_size = buffer_size
        self.reconnect_delay = reconnect_delay
        self.enable_logging = enable_logging
        
        # Storage
        self._subscriptions: Dict[int, Subscription] = {}
        self._buffer = MessageBuffer(max_size=buffer_size)
        self._global_callbacks: List[Callable[[int, Dict[str, Any]], None]] = []
        
        # Event filtering
        self._event_filters: Dict[str, Callable[[Dict[str, Any]], bool]] = {}
        
        # State
        self._running = False
        self._main_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        
        # Statistics
        self._stats = {
            "total_messages": 0,
            "total_errors": 0,
            "connections_made": 0,
            "connections_lost": 0,
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
        port: int,
        schema: str = "both",
        callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        host: Optional[str] = None,
        path: str = "/"
    ) -> None:
        """Subscribe to a vision feed.
        
        Args:
            port: WebSocket port (8002-8005)
            schema: Schema filter - "ui", "trading", or "both"
            callback: Optional callback function for messages
            host: Override default host
            path: WebSocket path
        
        Example:
            # Subscribe to Eagle classifications with trading schema
            subscriber.subscribe(8004, schema="trading", callback=handle_pattern)
            
            # Subscribe to YOLO detections with UI schema
            subscriber.subscribe(8002, schema="ui", callback=handle_detection)
        """
        schema_type = SchemaType(schema.lower())
        config = FeedConfig(
            port=port,
            schema=schema_type,
            callback=callback,
            host=host or self.host,
            path=path
        )
        
        self._subscriptions[port] = Subscription(config=config)
        logger.info(f"Subscribed to feed on port {port} with schema '{schema}'")
    
    def subscribe_to_feed(
        self,
        feed_name: str,
        schema: str = "both",
        callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        host: Optional[str] = None
    ) -> None:
        """Subscribe to a feed by name.
        
        Args:
            feed_name: One of "yolo", "sam", "eagle", "analysis"
            schema: Schema filter - "ui", "trading", or "both"
            callback: Optional callback function for messages
            host: Override default host
        
        Raises:
            ValueError: If feed_name is not recognized
        """
        if feed_name.lower() not in self.FEED_PORTS:
            raise ValueError(
                f"Unknown feed '{feed_name}'. "
                f"Available: {list(self.FEED_PORTS.keys())}"
            )
        
        port = self.FEED_PORTS[feed_name.lower()].value
        self.subscribe(port, schema=schema, callback=callback, host=host)
    
    def add_global_callback(
        self,
        callback: Callable[[int, Dict[str, Any]], None]
    ) -> None:
        """Add a callback that receives all messages from all feeds.
        
        Args:
            callback: Function receiving (port, message) for every message
        """
        self._global_callbacks.append(callback)
    
    def remove_global_callback(
        self,
        callback: Callable[[int, Dict[str, Any]], None]
    ) -> None:
        """Remove a global callback."""
        if callback in self._global_callbacks:
            self._global_callbacks.remove(callback)
    
    def add_event_filter(
        self,
        event_type: str,
        filter_fn: Callable[[Dict[str, Any]], bool]
    ) -> None:
        """Add a filter for specific event types.
        
        Args:
            event_type: Event type to filter
            filter_fn: Function that returns True if message should be processed
        """
        self._event_filters[event_type] = filter_fn
    
    def get_recent_messages(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get recent messages from the ring buffer.
        
        Args:
            count: Number of messages to retrieve
        
        Returns:
            List of recent messages with timestamps
        """
        return self._buffer.get_recent(count)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get subscriber statistics."""
        stats = dict(self._stats)
        stats["subscriptions"] = {
            port: {
                "connected": sub.connected,
                "message_count": sub.message_count,
                "error_count": sub.error_count,
                "uri": sub.config.uri
            }
            for port, sub in self._subscriptions.items()
        }
        return stats
    
    def _should_process_message(
        self,
        subscription: Subscription,
        message: Dict[str, Any]
    ) -> bool:
        """Check if message should be processed based on schema filtering."""
        schema = subscription.config.schema
        
        if schema == SchemaType.BOTH:
            return True
        
        # Check message schema field
        msg_schema = message.get("schema", message.get("type", "")).lower()
        
        if schema == SchemaType.UI:
            return msg_schema in ("ui", "navigation", "interface")
        elif schema == SchemaType.TRADING:
            return msg_schema in ("trading", "pattern", "signal", "trade")
        
        return True
    
    async def _handle_message(
        self,
        port: int,
        subscription: Subscription,
        data: str
    ) -> None:
        """Process an incoming message."""
        try:
            message = json.loads(data)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse message from port {port}: {e}")
            subscription.error_count += 1
            self._stats["total_errors"] += 1
            return
        
        # Update statistics
        subscription.message_count += 1
        self._stats["total_messages"] += 1
        
        # Add to ring buffer
        self._buffer.add({
            "port": port,
            "feed": self._get_feed_name(port),
            **message
        })
        
        # Log if enabled
        if self.enable_logging:
            logger.debug(f"[{port}] {message.get('type', 'unknown')}: {message}")
        
        # Check schema filtering
        if not self._should_process_message(subscription, message):
            return
        
        # Check event filters
        event_type = message.get("type", "unknown")
        if event_type in self._event_filters:
            if not self._event_filters[event_type](message):
                return
        
        # Trigger subscription callback
        if subscription.config.callback:
            try:
                subscription.config.callback(message)
            except Exception as e:
                logger.error(f"Callback error for port {port}: {e}")
                subscription.error_count += 1
        
        # Trigger global callbacks
        for callback in self._global_callbacks:
            try:
                callback(port, message)
            except Exception as e:
                logger.error(f"Global callback error: {e}")
    
    def _get_feed_name(self, port: int) -> str:
        """Get feed name from port number."""
        for name, feed_port in self.FEED_PORTS.items():
            if feed_port.value == port:
                return name
        return "unknown"
    
    async def _connect_feed(self, port: int, subscription: Subscription) -> None:
        """Maintain connection to a feed with automatic reconnection."""
        config = subscription.config
        
        while self._running:
            try:
                logger.info(f"Connecting to {config.uri}...")
                
                async with websockets.connect(config.uri) as websocket:
                    subscription.websocket = websocket
                    subscription.connected = True
                    self._stats["connections_made"] += 1
                    
                    logger.info(f"Connected to feed on port {port}")
                    
                    async for message in websocket:
                        if not self._running:
                            break
                        await self._handle_message(port, subscription, message)
                        
            except ConnectionClosed as e:
                logger.warning(f"Connection to port {port} closed: {e}")
                self._stats["connections_lost"] += 1
                
            except InvalidURI as e:
                logger.error(f"Invalid URI for port {port}: {e}")
                subscription.error_count += 1
                break
                
            except Exception as e:
                logger.error(f"Error on port {port}: {e}")
                subscription.error_count += 1
                self._stats["total_errors"] += 1
            
            finally:
                subscription.connected = False
                subscription.websocket = None
            
            # Reconnection delay
            if self._running:
                logger.info(f"Reconnecting to port {port} in {self.reconnect_delay}s...")
                await asyncio.sleep(self.reconnect_delay)
    
    async def _run_all(self) -> None:
        """Run all subscriptions concurrently."""
        if not self._subscriptions:
            logger.warning("No subscriptions configured")
            return
        
        tasks = [
            asyncio.create_task(self._connect_feed(port, sub))
            for port, sub in self._subscriptions.items()
        ]
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    def start(self) -> None:
        """Start all subscriptions (non-blocking).
        
        This starts the event loop in a background thread if not already running.
        """
        if self._running:
            logger.warning("Subscriber already running")
            return
        
        self._running = True
        
        # Create new event loop for background operation
        try:
            self._loop = asyncio.get_event_loop()
            if self._loop.is_closed():
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
        except RuntimeError:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
        
        # Start the main task
        self._main_task = self._loop.create_task(self._run_all())
        
        logger.info(f"Started subscriber with {len(self._subscriptions)} subscription(s)")
    
    def stop(self) -> None:
        """Stop all subscriptions."""
        if not self._running:
            return
        
        self._running = False
        
        # Cancel all subscription tasks
        for subscription in self._subscriptions.values():
            if subscription.task and not subscription.task.done():
                subscription.task.cancel()
        
        # Cancel main task
        if self._main_task and not self._main_task.done():
            self._main_task.cancel()
        
        logger.info("Subscriber stopped")
    
    async def start_async(self) -> None:
        """Start subscriber in async context (blocking until stopped).
        
        Use this when running inside an existing async event loop.
        """
        self._running = True
        await self._run_all()
    
    def is_running(self) -> bool:
        """Check if subscriber is running."""
        return self._running
    
    def is_connected(self, port: Optional[int] = None) -> bool:
        """Check connection status.
        
        Args:
            port: Specific port to check, or None for all
        
        Returns:
            True if connected (to specified port or all ports)
        """
        if port is not None:
            sub = self._subscriptions.get(port)
            return sub.connected if sub else False
        
        return all(sub.connected for sub in self._subscriptions.values())


# Convenience function for quick subscription
def subscribe_to_feed(
    port: int,
    schema: str = "trading",
    callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    host: str = "localhost"
) -> WSSAgentSubscriber:
    """Quick-start function to create and start a subscriber.
    
    Args:
        port: WebSocket port
        schema: Schema filter ("ui", "trading", or "both")
        callback: Message callback function
        host: Feed host
    
    Returns:
        Running WSSAgentSubscriber instance
    
    Example:
        def on_pattern(msg):
            print(f"Pattern detected: {msg}")
        
        sub = subscribe_to_feed(8004, schema="trading", callback=on_pattern)
    """
    subscriber = WSSAgentSubscriber(host=host)
    subscriber.subscribe(port, schema=schema, callback=callback)
    subscriber.start()
    return subscriber
