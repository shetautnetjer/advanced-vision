"""WebSocket Server (WSS) for Advanced Vision Trading System.

This module implements a multi-port WebSocket server architecture for real-time
communication between vision pipeline components and subscribers.

Port Assignments:
- 8001: UI Updates (screenshot previews, status updates)
- 8002: YOLO Detections (raw detection results)
- 8003: System Events (heartbeats, errors, diagnostics)
- 8004: Eagle2 Classifications (scout lane results)
- 8005: Trading Signals (final trading decisions)

All ports use JSON message schemas for consistency.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from pydantic import BaseModel

# WebSocket imports with graceful fallback
try:
    import websockets
    from websockets.server import WebSocketServerProtocol
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    WebSocketServerProtocol = Any  # type: ignore


# =============================================================================
# Message Schemas
# =============================================================================

class WSSMessage(BaseModel):
    """Base WebSocket message schema."""
    timestamp: str  # ISO 8601
    source: str     # Component that produced the message
    msg_type: str   # Message type for routing
    payload: dict[str, Any] = {}
    schema_version: str = "1.0"


class DetectionMessage(WSSMessage):
    """YOLO detection result message."""
    msg_type: str = "detection"
    payload: dict[str, Any] = {
        "detections": [],
        "inference_time_ms": 0.0,
        "frame_id": "",
    }


class ClassificationMessage(WSSMessage):
    """Eagle2 classification result message."""
    msg_type: str = "classification"
    payload: dict[str, Any] = {
        "event_type": "",
        "confidence": 0.0,
        "is_trading_relevant": False,
        "frame_id": "",
    }


class TradingSignalMessage(WSSMessage):
    """Final trading signal message."""
    msg_type: str = "trading_signal"
    payload: dict[str, Any] = {
        "signal_type": "",
        "risk_level": "",
        "recommendation": "",
        "confidence": 0.0,
        "frame_id": "",
    }


class UIUpdateMessage(WSSMessage):
    """UI update message for display clients."""
    msg_type: str = "ui_update"
    payload: dict[str, Any] = {
        "update_type": "",
        "data": {},
    }


class SystemEventMessage(WSSMessage):
    """System event message (heartbeats, errors)."""
    msg_type: str = "system_event"
    payload: dict[str, Any] = {
        "event_type": "heartbeat",
        "status": "ok",
        "details": {},
    }


# =============================================================================
# Server Configuration
# =============================================================================

@dataclass
class WSSServerConfig:
    """Configuration for WSS server."""
    host: str = "localhost"
    ports: list[int] = field(default_factory=lambda: [8001, 8002, 8003, 8004, 8005])
    
    # Port assignments
    ui_port: int = 8001
    detection_port: int = 8002
    system_port: int = 8003
    classification_port: int = 8004
    trading_port: int = 8005
    
    # Logging
    log_dir: Path = field(default_factory=lambda: Path("logs/wss"))
    log_format: str = "text"  # "text" or "json"
    log_level: str = "INFO"
    
    # Performance
    max_clients_per_port: int = 100
    heartbeat_interval: float = 30.0
    message_queue_size: int = 1000
    
    def __post_init__(self):
        self.log_dir = Path(self.log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)


# =============================================================================
# Port Router
# =============================================================================

class PortRouter:
    """Routes messages to appropriate ports based on schema type."""
    
    PORT_NAMES = {
        8001: "ui",
        8002: "detection",
        8003: "system",
        8004: "classification",
        8005: "trading",
    }
    
    SCHEMA_ROUTES = {
        "ui_update": 8001,
        "detection": 8002,
        "system_event": 8003,
        "classification": 8004,
        "trading_signal": 8005,
    }
    
    @classmethod
    def get_port_for_message(cls, msg_type: str) -> int | None:
        """Get target port for message type."""
        return cls.SCHEMA_ROUTES.get(msg_type)
    
    @classmethod
    def get_port_name(cls, port: int) -> str:
        """Get human-readable port name."""
        return cls.PORT_NAMES.get(port, f"port_{port}")


# =============================================================================
# Connection Manager
# =============================================================================

class ConnectionManager:
    """Manages WebSocket connections per port."""
    
    def __init__(self, max_clients: int = 100):
        self.connections: dict[int, set[WebSocketServerProtocol]] = {
            8001: set(),
            8002: set(),
            8003: set(),
            8004: set(),
            8005: set(),
        }
        self.max_clients = max_clients
        self._lock = asyncio.Lock()
        self._connection_stats: dict[int, dict] = {
            port: {"total_connections": 0, "current": 0, "peak": 0}
            for port in self.connections
        }
    
    async def connect(self, port: int, websocket: WebSocketServerProtocol) -> bool:
        """Register new connection."""
        async with self._lock:
            if len(self.connections[port]) >= self.max_clients:
                return False
            self.connections[port].add(websocket)
            self._connection_stats[port]["total_connections"] += 1
            self._connection_stats[port]["current"] = len(self.connections[port])
            self._connection_stats[port]["peak"] = max(
                self._connection_stats[port]["peak"],
                self._connection_stats[port]["current"]
            )
            return True
    
    async def disconnect(self, port: int, websocket: WebSocketServerProtocol) -> None:
        """Unregister connection."""
        async with self._lock:
            self.connections[port].discard(websocket)
            self._connection_stats[port]["current"] = len(self.connections[port])
    
    async def broadcast(self, port: int, message: str) -> int:
        """Broadcast message to all connections on port."""
        sent = 0
        dead_connections = []
        
        for conn in list(self.connections.get(port, [])):
            try:
                await conn.send(message)
                sent += 1
            except Exception:
                dead_connections.append(conn)
        
        # Clean up dead connections
        for conn in dead_connections:
            await self.disconnect(port, conn)
        
        return sent
    
    def get_stats(self) -> dict[int, dict]:
        """Get connection statistics."""
        return self._connection_stats.copy()


# =============================================================================
# WSS Logger
# =============================================================================

class WSSLogger:
    """Logs WSS messages in text or JSON format."""
    
    def __init__(self, config: WSSServerConfig):
        self.config = config
        self.log_dir = config.log_dir
        self.log_format = config.log_format
        
        # Setup loggers per port
        self.loggers: dict[int, logging.Logger] = {}
        self._setup_loggers()
    
    def _setup_loggers(self) -> None:
        """Setup file handlers for each port."""
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ) if self.log_format == "text" else logging.Formatter('%(message)s')
        
        for port in [8001, 8002, 8003, 8004, 8005]:
            logger = logging.getLogger(f"wss.port{port}")
            logger.setLevel(getattr(logging, self.config.log_level))
            
            # File handler
            log_file = self.log_dir / f"port_{port}.{self.log_format}.log"
            handler = logging.FileHandler(log_file)
            handler.setFormatter(formatter)
            
            # Avoid duplicate handlers
            logger.handlers = []
            logger.addHandler(handler)
            
            self.loggers[port] = logger
    
    def log(self, port: int, message: WSSMessage | str) -> None:
        """Log message to appropriate port log."""
        if isinstance(message, WSSMessage):
            if self.log_format == "json":
                log_entry = message.model_dump_json()
            else:
                log_entry = f"[{message.msg_type}] {message.source}: {message.payload}"
        else:
            log_entry = message
        
        logger = self.loggers.get(port)
        if logger:
            logger.info(log_entry)
    
    def log_system(self, level: str, message: str) -> None:
        """Log system-level message."""
        logger = logging.getLogger("wss.system")
        logger.log(getattr(logging, level, logging.INFO), message)


# =============================================================================
# WSS Server
# =============================================================================

class WSSServer:
    """Multi-port WebSocket server for Advanced Vision."""
    
    def __init__(self, config: WSSServerConfig | None = None):
        if not WEBSOCKETS_AVAILABLE:
            raise RuntimeError(
                "websockets package not installed. "
                "Install with: pip install websockets"
            )
        
        self.config = config or WSSServerConfig()
        self.connection_manager = ConnectionManager(self.config.max_clients_per_port)
        self.logger = WSSLogger(self.config)
        self._servers: list[asyncio.Task] = []
        self._running = False
        self._start_time: datetime | None = None
        self._message_counts: dict[int, int] = {p: 0 for p in self.config.ports}
        self._message_handlers: dict[str, Callable[[WSSMessage], None]] = {}
    
    async def _handle_connection(
        self,
        websocket: WebSocketServerProtocol,
        port: int,
    ) -> None:
        """Handle individual WebSocket connection."""
        client_info = f"{websocket.remote_address}"
        self.logger.log_system("INFO", f"Connection attempt on port {port} from {client_info}")
        
        if not await self.connection_manager.connect(port, websocket):
            self.logger.log_system("WARNING", f"Max clients reached on port {port}")
            await websocket.close(code=1013, reason="Server full")
            return
        
        self.logger.log_system("INFO", f"Client connected on port {port}: {client_info}")
        
        try:
            async for message in websocket:
                try:
                    # Parse and route message
                    data = json.loads(message)
                    await self._handle_message(port, data, websocket)
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({
                        "error": "Invalid JSON",
                        "timestamp": datetime.utcnow().isoformat(),
                    }))
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            await self.connection_manager.disconnect(port, websocket)
            self.logger.log_system("INFO", f"Client disconnected from port {port}: {client_info}")
    
    async def _handle_message(
        self,
        port: int,
        data: dict[str, Any],
        websocket: WebSocketServerProtocol,
    ) -> None:
        """Handle incoming message from client."""
        # Echo back for now - can be extended for request-response patterns
        response = {
            "type": "ack",
            "received": data,
            "port": port,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await websocket.send(json.dumps(response))
    
    async def _start_port_server(self, port: int) -> None:
        """Start server on specific port."""
        async def handler(websocket):
            await self._handle_connection(websocket, port)
        
        async with websockets.serve(handler, self.config.host, port):
            self.logger.log_system("INFO", f"WSS server started on {self.config.host}:{port}")
            # Keep server running
            while self._running:
                await asyncio.sleep(1)
    
    async def start(self) -> None:
        """Start all port servers."""
        self._running = True
        self._start_time = datetime.utcnow()
        
        # Start heartbeat task
        heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        
        # Start servers on all ports
        server_tasks = [
            asyncio.create_task(self._start_port_server(port))
            for port in self.config.ports
        ]
        
        self._servers = [heartbeat_task] + server_tasks
        
        try:
            await asyncio.gather(*self._servers, return_exceptions=True)
        except asyncio.CancelledError:
            pass
    
    async def stop(self) -> None:
        """Stop all servers."""
        self._running = False
        for task in self._servers:
            task.cancel()
        await asyncio.gather(*self._servers, return_exceptions=True)
        self.logger.log_system("INFO", "WSS server stopped")
    
    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeat messages."""
        while self._running:
            await asyncio.sleep(self.config.heartbeat_interval)
            
            uptime = (datetime.utcnow() - self._start_time).total_seconds() if self._start_time else 0
            stats = self.connection_manager.get_stats()
            
            heartbeat = SystemEventMessage(
                timestamp=datetime.utcnow().isoformat(),
                source="wss_server",
                msg_type="system_event",
                payload={
                    "event_type": "heartbeat",
                    "status": "ok",
                    "uptime_seconds": uptime,
                    "connections": stats,
                    "message_counts": self._message_counts,
                }
            )
            
            await self.publish(8003, heartbeat)
    
    async def publish(self, port: int, message: WSSMessage) -> int:
        """Publish message to specific port."""
        message_str = message.model_dump_json()
        
        # Log the message
        self.logger.log(port, message)
        
        # Update stats
        self._message_counts[port] = self._message_counts.get(port, 0) + 1
        
        # Broadcast to all clients on port
        return await self.connection_manager.broadcast(port, message_str)
    
    async def publish_by_type(self, msg_type: str, message: WSSMessage) -> int:
        """Publish message to appropriate port based on type."""
        port = PortRouter.get_port_for_message(msg_type)
        if port is None:
            raise ValueError(f"Unknown message type: {msg_type}")
        return await self.publish(port, message)
    
    def register_handler(self, msg_type: str, handler: Callable[[WSSMessage], None]) -> None:
        """Register handler for message type."""
        self._message_handlers[msg_type] = handler
    
    def get_stats(self) -> dict[str, Any]:
        """Get server statistics."""
        return {
            "running": self._running,
            "start_time": self._start_time.isoformat() if self._start_time else None,
            "uptime_seconds": (
                (datetime.utcnow() - self._start_time).total_seconds()
                if self._start_time else 0
            ),
            "connections": self.connection_manager.get_stats(),
            "message_counts": self._message_counts.copy(),
        }


# =============================================================================
# Convenience Functions
# =============================================================================

async def create_server(config: WSSServerConfig | None = None) -> WSSServer:
    """Factory function to create and configure WSS server."""
    return WSSServer(config)


def get_default_config() -> WSSServerConfig:
    """Get default server configuration."""
    return WSSServerConfig()


# =============================================================================
# Standalone Entry Point
# =============================================================================

if __name__ == "__main__":
    import sys
    
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
    config = WSSServerConfig()
    server = WSSServer(config)
    
    print(f"Starting WSS Server on ports: {config.ports}")
    print(f"Logs directory: {config.log_dir.absolute()}")
    
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        print("\nShutting down...")
        asyncio.run(server.stop())