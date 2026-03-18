"""WebSocket Server v2 (WSS) for Advanced Vision Trading System.

This module implements a single-port WebSocket server architecture with typed topics
for real-time communication between vision pipeline components and subscribers.

Architecture v2 Changes:
- Single port: 8000 (instead of 8001-8005)
- Typed topics: vision.detection.yolo, vision.segmentation.sam, vision.classification.eagle, vision.analysis.qwen
- Transport envelope with event_id, event_type, schema_family, created_at, source, frame_ref, trace_id
- Improved auth, reconnect, observability

Backward Compatibility:
- v1 files remain unchanged (wss_server.py, wss_client.py)
- Migration guide provided in docs/WSS_V2_ARCHITECTURE.md
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Coroutine

from pydantic import BaseModel, Field

# WebSocket imports with graceful fallback
try:
    import websockets
    from websockets.server import WebSocketServerProtocol
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    WebSocketServerProtocol = Any  # type: ignore


# =============================================================================
# Topic Definitions
# =============================================================================

class Topic(str, Enum):
    """Typed topics for vision pipeline components."""
    # Detection topics
    VISION_DETECTION_YOLO = "vision.detection.yolo"
    
    # Segmentation topics
    VISION_SEGMENTATION_SAM = "vision.segmentation.sam"
    
    # Classification topics
    VISION_CLASSIFICATION_EAGLE = "vision.classification.eagle"
    
    # Analysis topics
    VISION_ANALYSIS_QWEN = "vision.analysis.qwen"
    
    # System topics
    SYSTEM_HEARTBEAT = "system.heartbeat"
    SYSTEM_ERROR = "system.error"
    SYSTEM_METRICS = "system.metrics"


class SchemaFamily(str, Enum):
    """Schema families for message categorization."""
    DETECTION = "detection"
    SEGMENTATION = "segmentation"
    CLASSIFICATION = "classification"
    ANALYSIS = "analysis"
    SYSTEM = "system"


# Topic to schema family mapping
TOPIC_SCHEMA_FAMILY = {
    Topic.VISION_DETECTION_YOLO: SchemaFamily.DETECTION,
    Topic.VISION_SEGMENTATION_SAM: SchemaFamily.SEGMENTATION,
    Topic.VISION_CLASSIFICATION_EAGLE: SchemaFamily.CLASSIFICATION,
    Topic.VISION_ANALYSIS_QWEN: SchemaFamily.ANALYSIS,
    Topic.SYSTEM_HEARTBEAT: SchemaFamily.SYSTEM,
    Topic.SYSTEM_ERROR: SchemaFamily.SYSTEM,
    Topic.SYSTEM_METRICS: SchemaFamily.SYSTEM,
}


# =============================================================================
# Transport Envelope
# =============================================================================

class TransportEnvelope(BaseModel):
    """Standard transport envelope for all v2 messages.
    
    Fields:
        event_id: Unique event identifier (UUID)
        event_type: Semantic event type (e.g., "detection", "classification")
        schema_family: High-level category (detection, segmentation, classification, analysis, system)
        created_at: ISO 8601 timestamp
        source: Component that produced the event (e.g., "yolo", "sam", "eagle", "qwen")
        frame_ref: Reference to associated frame/image
        trace_id: Distributed tracing identifier
        payload: Event-specific data
    """
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str
    schema_family: SchemaFamily
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str
    frame_ref: str | None = None
    trace_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    
    # Optional v2 metadata
    topic: str | None = None  # Filled by server on receipt
    received_at: str | None = None  # Filled by server on receipt
    
    class Config:
        extra = "allow"


# =============================================================================
# Message Schemas for Each Component
# =============================================================================

class YOLODetectionPayload(BaseModel):
    """YOLO detection result payload."""
    detections: list[dict[str, Any]] = Field(default_factory=list)
    inference_time_ms: float = 0.0
    frame_id: str = ""
    confidence_threshold: float = 0.5
    model_version: str = "yolo11n"


class SAMSegmentationPayload(BaseModel):
    """MobileSAM segmentation result payload."""
    masks: list[dict[str, Any]] = Field(default_factory=list)
    roi_id: str = ""
    mask_area: int = 0
    confidence: float = 0.0
    frame_id: str = ""


class EagleClassificationPayload(BaseModel):
    """Eagle2 classification result payload."""
    classification: str = ""
    confidence: float = 0.0
    roi_id: str = ""
    frame_id: str = ""
    inference_time_ms: float | None = None
    reasoning: str | None = None


class QwenAnalysisPayload(BaseModel):
    """Qwen/Kimi analysis result payload."""
    analysis: str = ""
    risk_level: str = "none"  # none, low, medium, high, critical
    recommendation: str = "continue"  # continue, note, warn, hold, pause, escalate
    confidence: float = 0.0
    frame_id: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class SystemHeartbeatPayload(BaseModel):
    """System heartbeat payload."""
    status: str = "ok"
    uptime_seconds: float = 0.0
    active_connections: int = 0
    message_counts: dict[str, int] = Field(default_factory=dict)


class SystemErrorPayload(BaseModel):
    """System error payload."""
    error_type: str = ""
    error_message: str = ""
    component: str = ""
    severity: str = "warning"  # warning, error, critical


# =============================================================================
# Server Configuration
# =============================================================================

@dataclass
class WSSServerConfigV2:
    """Configuration for WSS v2 server."""
    host: str = "localhost"
    port: int = 8000  # Single port for all topics
    
    # Authentication
    auth_enabled: bool = False
    auth_token: str | None = None
    
    # Logging
    log_dir: Path = field(default_factory=lambda: Path("logs/wss_v2"))
    log_format: str = "jsonl"  # "jsonl" or "text"
    log_level: str = "INFO"
    
    # Performance
    max_clients: int = 100
    max_subscriptions_per_client: int = 10
    heartbeat_interval: float = 30.0
    message_queue_size: int = 1000
    
    # Observability
    enable_metrics: bool = True
    metrics_interval: float = 60.0
    
    def __post_init__(self):
        self.log_dir = Path(self.log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)


# =============================================================================
# Topic Router
# =============================================================================

class TopicRouter:
    """Routes messages to appropriate topics based on event type."""
    
    EVENT_TYPE_TO_TOPIC: dict[str, Topic] = {
        # YOLO detections
        "detection": Topic.VISION_DETECTION_YOLO,
        "detection_batch": Topic.VISION_DETECTION_YOLO,
        "yolo_detection": Topic.VISION_DETECTION_YOLO,
        
        # SAM segmentations
        "segmentation": Topic.VISION_SEGMENTATION_SAM,
        "segmentation_batch": Topic.VISION_SEGMENTATION_SAM,
        "sam_segmentation": Topic.VISION_SEGMENTATION_SAM,
        
        # Eagle classifications
        "classification": Topic.VISION_CLASSIFICATION_EAGLE,
        "classification_batch": Topic.VISION_CLASSIFICATION_EAGLE,
        "eagle_classification": Topic.VISION_CLASSIFICATION_EAGLE,
        
        # Qwen/Kimi analysis
        "analysis": Topic.VISION_ANALYSIS_QWEN,
        "reviewer_assessment": Topic.VISION_ANALYSIS_QWEN,
        "overseer_response": Topic.VISION_ANALYSIS_QWEN,
        "qwen_analysis": Topic.VISION_ANALYSIS_QWEN,
        
        # System events
        "heartbeat": Topic.SYSTEM_HEARTBEAT,
        "error": Topic.SYSTEM_ERROR,
        "metrics": Topic.SYSTEM_METRICS,
    }
    
    SOURCE_TO_TOPIC: dict[str, Topic] = {
        "yolo": Topic.VISION_DETECTION_YOLO,
        "sam": Topic.VISION_SEGMENTATION_SAM,
        "eagle": Topic.VISION_CLASSIFICATION_EAGLE,
        "qwen": Topic.VISION_ANALYSIS_QWEN,
        "kimi": Topic.VISION_ANALYSIS_QWEN,
        "chronos": Topic.VISION_ANALYSIS_QWEN,
    }
    
    @classmethod
    def get_topic_for_event(cls, event_type: str, source: str | None = None) -> Topic | None:
        """Get target topic for event type and optional source."""
        # First try event type mapping
        topic = cls.EVENT_TYPE_TO_TOPIC.get(event_type.lower())
        if topic:
            return topic
        
        # Fall back to source mapping
        if source:
            return cls.SOURCE_TO_TOPIC.get(source.lower())
        
        return None
    
    @classmethod
    def get_schema_family(cls, topic: Topic) -> SchemaFamily:
        """Get schema family for topic."""
        return TOPIC_SCHEMA_FAMILY.get(topic, SchemaFamily.SYSTEM)


# =============================================================================
# Connection Manager v2
# =============================================================================

@dataclass
class ClientConnection:
    """Represents a connected client."""
    websocket: WebSocketServerProtocol
    client_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    connected_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    subscriptions: set[str] = field(default_factory=set)
    auth_verified: bool = False
    last_activity: float = field(default_factory=time.time)
    message_count: int = 0


class ConnectionManagerV2:
    """Manages WebSocket connections with topic subscriptions."""
    
    def __init__(self, max_clients: int = 100, max_subscriptions: int = 10):
        self.connections: dict[str, ClientConnection] = {}  # client_id -> connection
        self.topic_subscribers: dict[str, set[str]] = defaultdict(set)  # topic -> set of client_ids
        self.max_clients = max_clients
        self.max_subscriptions = max_subscriptions
        self._lock = asyncio.Lock()
        self._connection_stats = {
            "total_connections": 0,
            "current_connections": 0,
            "peak_connections": 0,
            "total_messages": 0,
        }
    
    async def connect(self, websocket: WebSocketServerProtocol) -> ClientConnection | None:
        """Register new connection."""
        async with self._lock:
            if len(self.connections) >= self.max_clients:
                return None
            
            conn = ClientConnection(websocket=websocket)
            self.connections[conn.client_id] = conn
            self._connection_stats["total_connections"] += 1
            self._connection_stats["current_connections"] = len(self.connections)
            self._connection_stats["peak_connections"] = max(
                self._connection_stats["peak_connections"],
                self._connection_stats["current_connections"]
            )
            return conn
    
    async def disconnect(self, client_id: str) -> None:
        """Unregister connection."""
        async with self._lock:
            conn = self.connections.pop(client_id, None)
            if conn:
                # Remove from all topic subscriptions
                for topic in list(conn.subscriptions):
                    self.topic_subscribers[topic].discard(client_id)
                self._connection_stats["current_connections"] = len(self.connections)
    
    async def subscribe(self, client_id: str, topic: str) -> bool:
        """Subscribe client to topic."""
        async with self._lock:
            conn = self.connections.get(client_id)
            if not conn:
                return False
            
            if len(conn.subscriptions) >= self.max_subscriptions:
                return False
            
            conn.subscriptions.add(topic)
            self.topic_subscribers[topic].add(client_id)
            return True
    
    async def unsubscribe(self, client_id: str, topic: str) -> bool:
        """Unsubscribe client from topic."""
        async with self._lock:
            conn = self.connections.get(client_id)
            if not conn:
                return False
            
            conn.subscriptions.discard(topic)
            self.topic_subscribers[topic].discard(client_id)
            return True
    
    async def broadcast(self, topic: str, message: str) -> int:
        """Broadcast message to all subscribers of topic."""
        sent = 0
        dead_clients = []
        
        subscriber_ids = list(self.topic_subscribers.get(topic, set()))
        
        for client_id in subscriber_ids:
            conn = self.connections.get(client_id)
            if not conn:
                dead_clients.append(client_id)
                continue
            
            try:
                await conn.websocket.send(message)
                conn.message_count += 1
                conn.last_activity = time.time()
                sent += 1
            except Exception:
                dead_clients.append(client_id)
        
        # Clean up dead connections
        for client_id in dead_clients:
            await self.disconnect(client_id)
        
        self._connection_stats["total_messages"] += sent
        return sent
    
    def get_stats(self) -> dict[str, Any]:
        """Get connection statistics."""
        return {
            **self._connection_stats,
            "topic_subscriptions": {
                topic: len(subscribers)
                for topic, subscribers in self.topic_subscribers.items()
            },
        }
    
    def get_client_info(self, client_id: str) -> dict[str, Any] | None:
        """Get client connection info."""
        conn = self.connections.get(client_id)
        if not conn:
            return None
        
        return {
            "client_id": conn.client_id,
            "connected_at": conn.connected_at,
            "subscriptions": list(conn.subscriptions),
            "auth_verified": conn.auth_verified,
            "message_count": conn.message_count,
            "last_activity": conn.last_activity,
        }


# =============================================================================
# Durable Logger v2
# =============================================================================

class WSSLoggerV2:
    """Logs WSS v2 messages in JSONL format with rotation."""
    
    def __init__(self, config: WSSServerConfigV2):
        self.config = config
        self.log_dir = config.log_dir
        self.log_format = config.log_format
        
        # Setup log files
        self.events_log = self.log_dir / "events.jsonl"
        self.classifications_log = self.log_dir / "classifications.jsonl"
        
        # Ensure log files exist
        self.events_log.touch(exist_ok=True)
        self.classifications_log.touch(exist_ok=True)
        
        # Setup structured logging
        self._logger = logging.getLogger("wss_v2")
        self._setup_logger()
    
    def _setup_logger(self) -> None:
        """Setup file handlers for logging."""
        formatter = logging.Formatter('%(message)s')
        
        # Events handler
        events_handler = logging.FileHandler(self.events_log)
        events_handler.setFormatter(formatter)
        
        # Avoid duplicate handlers
        self._logger.handlers = []
        self._logger.addHandler(events_handler)
        self._logger.setLevel(getattr(logging, self.config.log_level))
    
    def log_event(self, envelope: TransportEnvelope) -> None:
        """Log event to events.jsonl."""
        try:
            log_entry = envelope.model_dump_json()
            self._logger.info(log_entry)
        except Exception as e:
            logging.error(f"Failed to log event: {e}")
    
    def log_classification(self, envelope: TransportEnvelope) -> None:
        """Log classification to classifications.jsonl."""
        try:
            log_entry = envelope.model_dump_json()
            with open(self.classifications_log, "a") as f:
                f.write(log_entry + "\n")
        except Exception as e:
            logging.error(f"Failed to log classification: {e}")
    
    def log_system(self, level: str, message: str) -> None:
        """Log system-level message."""
        logging.log(getattr(logging, level, logging.INFO), f"[WSSv2] {message}")


# =============================================================================
# WSS Server v2
# =============================================================================

class WSSServerV2:
    """Single-port WebSocket server with typed topics for Advanced Vision."""
    
    def __init__(self, config: WSSServerConfigV2 | None = None):
        if not WEBSOCKETS_AVAILABLE:
            raise RuntimeError(
                "websockets package not installed. "
                "Install with: pip install websockets"
            )
        
        self.config = config or WSSServerConfigV2()
        self.connection_manager = ConnectionManagerV2(
            max_clients=self.config.max_clients,
            max_subscriptions=self.config.max_subscriptions_per_client
        )
        self.logger = WSSLoggerV2(self.config)
        self._server_task: asyncio.Task | None = None
        self._running = False
        self._start_time: datetime | None = None
        self._message_counts: dict[str, int] = defaultdict(int)
        self._handlers: dict[str, Callable[[TransportEnvelope], Coroutine]] = {}
    
    async def _handle_connection(self, websocket: WebSocketServerProtocol) -> None:
        """Handle individual WebSocket connection."""
        client_info = f"{websocket.remote_address}"
        self.logger.log_system("INFO", f"Connection attempt from {client_info}")
        
        # Register connection
        conn = await self.connection_manager.connect(websocket)
        if not conn:
            self.logger.log_system("WARNING", f"Max clients reached, rejecting {client_info}")
            await websocket.close(code=1013, reason="Server full")
            return
        
        # Authenticate if enabled
        if self.config.auth_enabled:
            if not await self._authenticate(conn):
                await websocket.close(code=1008, reason="Authentication failed")
                return
        
        self.logger.log_system("INFO", f"Client connected: {conn.client_id} ({client_info})")
        
        try:
            async for message in websocket:
                try:
                    await self._handle_message(conn, message)
                except json.JSONDecodeError:
                    await self._send_error(websocket, "Invalid JSON")
                except Exception as e:
                    self.logger.log_system("ERROR", f"Message handling error: {e}")
                    await self._send_error(websocket, f"Server error: {str(e)}")
                    
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            await self.connection_manager.disconnect(conn.client_id)
            self.logger.log_system("INFO", f"Client disconnected: {conn.client_id}")
    
    async def _authenticate(self, conn: ClientConnection) -> bool:
        """Authenticate client connection."""
        if not self.config.auth_enabled or not self.config.auth_token:
            return True
        
        try:
            # Wait for auth message
            message = await asyncio.wait_for(conn.websocket.recv(), timeout=5.0)
            data = json.loads(message)
            
            auth_token = data.get("auth_token")
            if auth_token == self.config.auth_token:
                conn.auth_verified = True
                await conn.websocket.send(json.dumps({"type": "auth_ok"}))
                return True
            else:
                await conn.websocket.send(json.dumps({"type": "auth_failed"}))
                return False
                
        except asyncio.TimeoutError:
            await conn.websocket.send(json.dumps({"type": "auth_timeout"}))
            return False
        except Exception as e:
            self.logger.log_system("ERROR", f"Auth error: {e}")
            return False
    
    async def _handle_message(self, conn: ClientConnection, message: str) -> None:
        """Handle incoming message from client."""
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            await self._send_error(conn.websocket, "Invalid JSON")
            return
        
        msg_type = data.get("type", "unknown")
        
        # Handle subscription requests
        if msg_type == "subscribe":
            topics = data.get("topics", [])
            if isinstance(topics, str):
                topics = [topics]
            
            success_count = 0
            for topic in topics:
                if await self.connection_manager.subscribe(conn.client_id, topic):
                    success_count += 1
            
            await conn.websocket.send(json.dumps({
                "type": "subscribe_ack",
                "topics": topics,
                "subscribed_count": success_count,
            }))
            return
        
        # Handle unsubscription requests
        if msg_type == "unsubscribe":
            topics = data.get("topics", [])
            if isinstance(topics, str):
                topics = [topics]
            
            for topic in topics:
                await self.connection_manager.unsubscribe(conn.client_id, topic)
            
            await conn.websocket.send(json.dumps({
                "type": "unsubscribe_ack",
                "topics": topics,
            }))
            return
        
        # Handle publish requests from clients (optional)
        if msg_type == "publish":
            envelope_data = data.get("envelope", {})
            try:
                envelope = TransportEnvelope(**envelope_data)
                await self.publish(envelope)
                await conn.websocket.send(json.dumps({"type": "publish_ack", "event_id": envelope.event_id}))
            except Exception as e:
                await self._send_error(conn.websocket, f"Invalid envelope: {e}")
            return
        
        # Handle ping
        if msg_type == "ping":
            await conn.websocket.send(json.dumps({"type": "pong", "timestamp": datetime.now(timezone.utc).isoformat()}))
            return
        
        # Handle get_stats
        if msg_type == "get_stats":
            stats = self.get_stats()
            await conn.websocket.send(json.dumps({"type": "stats", "data": stats}))
            return
        
        # Default: echo back
        await conn.websocket.send(json.dumps({
            "type": "ack",
            "received": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }))
    
    async def _send_error(self, websocket: WebSocketServerProtocol, error: str) -> None:
        """Send error response."""
        try:
            await websocket.send(json.dumps({
                "type": "error",
                "error": error,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }))
        except Exception:
            pass
    
    async def _server_loop(self) -> None:
        """Main server loop."""
        async def handler(websocket):
            await self._handle_connection(websocket)
        
        async with websockets.serve(handler, self.config.host, self.config.port):
            self.logger.log_system("INFO", f"WSS v2 server started on {self.config.host}:{self.config.port}")
            
            # Start heartbeat task
            heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            metrics_task = asyncio.create_task(self._metrics_loop()) if self.config.enable_metrics else None
            
            self._running = True
            self._start_time = datetime.now(timezone.utc)
            
            try:
                while self._running:
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                pass
            finally:
                heartbeat_task.cancel()
                if metrics_task:
                    metrics_task.cancel()
                try:
                    await heartbeat_task
                except asyncio.CancelledError:
                    pass
    
    async def start(self) -> None:
        """Start the server."""
        self._server_task = asyncio.create_task(self._server_loop())
        try:
            await self._server_task
        except asyncio.CancelledError:
            pass
    
    async def stop(self) -> None:
        """Stop the server."""
        self._running = False
        if self._server_task:
            self._server_task.cancel()
            try:
                await self._server_task
            except asyncio.CancelledError:
                pass
        self.logger.log_system("INFO", "WSS v2 server stopped")
    
    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeat messages."""
        while self._running:
            await asyncio.sleep(self.config.heartbeat_interval)
            
            uptime = (datetime.now(timezone.utc) - self._start_time).total_seconds() if self._start_time else 0
            stats = self.connection_manager.get_stats()
            
            envelope = TransportEnvelope(
                event_type="heartbeat",
                schema_family=SchemaFamily.SYSTEM,
                source="wss_server_v2",
                payload={
                    "status": "ok",
                    "uptime_seconds": uptime,
                    "active_connections": stats["current_connections"],
                    "total_connections": stats["total_connections"],
                    "message_counts": dict(self._message_counts),
                }
            )
            
            await self.publish(envelope)
    
    async def _metrics_loop(self) -> None:
        """Send periodic metrics."""
        while self._running:
            await asyncio.sleep(self.config.metrics_interval)
            
            stats = self.connection_manager.get_stats()
            envelope = TransportEnvelope(
                event_type="metrics",
                schema_family=SchemaFamily.SYSTEM,
                source="wss_server_v2",
                payload={
                    "connection_stats": stats,
                    "message_counts": dict(self._message_counts),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
            
            await self.publish(envelope)
    
    async def publish(self, envelope: TransportEnvelope, topic: str | None = None) -> int:
        """Publish message to appropriate topic."""
        # Determine topic if not specified
        if topic is None:
            topic = self._determine_topic(envelope)
        
        # Fill in server-side fields
        envelope.topic = topic
        envelope.received_at = datetime.now(timezone.utc).isoformat()
        
        # Log the event
        self.logger.log_event(envelope)
        
        # Also log classifications separately
        if envelope.schema_family == SchemaFamily.CLASSIFICATION:
            self.logger.log_classification(envelope)
        
        # Update stats
        self._message_counts[topic] += 1
        
        # Broadcast to subscribers
        message_str = envelope.model_dump_json()
        return await self.connection_manager.broadcast(topic, message_str)
    
    def _determine_topic(self, envelope: TransportEnvelope) -> str:
        """Determine topic for envelope."""
        # Try event type mapping
        topic = TopicRouter.get_topic_for_event(envelope.event_type, envelope.source)
        if topic:
            return topic.value
        
        # Fall back to schema family
        return f"system.{envelope.schema_family.value}"
    
    def register_handler(self, event_type: str, handler: Callable[[TransportEnvelope], Coroutine]) -> None:
        """Register handler for event type."""
        self._handlers[event_type] = handler
    
    def get_stats(self) -> dict[str, Any]:
        """Get server statistics."""
        uptime = 0
        if self._start_time:
            uptime = (datetime.now(timezone.utc) - self._start_time).total_seconds()
        
        return {
            "running": self._running,
            "start_time": self._start_time.isoformat() if self._start_time else None,
            "uptime_seconds": uptime,
            "config": {
                "host": self.config.host,
                "port": self.config.port,
                "auth_enabled": self.config.auth_enabled,
            },
            "connections": self.connection_manager.get_stats(),
            "message_counts": dict(self._message_counts),
        }


# =============================================================================
# Convenience Functions
# =============================================================================

async def create_server_v2(config: WSSServerConfigV2 | None = None) -> WSSServerV2:
    """Factory function to create and configure WSS v2 server."""
    return WSSServerV2(config)


def get_default_config_v2() -> WSSServerConfigV2:
    """Get default server configuration."""
    return WSSServerConfigV2()


# =============================================================================
# Standalone Entry Point
# =============================================================================

if __name__ == "__main__":
    import sys
    from enum import Enum
    
    if not WEBSOCKETS_AVAILABLE:
        print("Error: websockets package not installed.")
        print("Install with: pip install websockets")
        sys.exit(1)
    
    # Setup console logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create and start server
    config = WSSServerConfigV2()
    server = WSSServerV2(config)
    
    print(f"Starting WSS v2 Server on {config.host}:{config.port}")
    print(f"Logs directory: {config.log_dir.absolute()}")
    print(f"Available topics:")
    for topic in Topic:
        print(f"  - {topic.value}")
    
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        print("\nShutting down...")
        asyncio.run(server.stop())
