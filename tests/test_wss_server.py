"""Tests for WSS Server.

Tests cover:
- Server starts on all ports (8001-8005)
- Clients can connect to each port
- Message broadcasting works
- Logging (text + JSON) works correctly
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

# Skip all tests if websockets not available
try:
    import websockets
    from websockets.client import connect as ws_connect
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    pytest.skip("websockets package not installed", allow_module_level=True)

from advanced_vision.wss_server import (
    WSSServer,
    WSSServerConfig,
    WSSMessage,
    DetectionMessage,
    ClassificationMessage,
    TradingSignalMessage,
    UIUpdateMessage,
    SystemEventMessage,
    PortRouter,
    ConnectionManager,
    WSSLogger,
    create_server,
    get_default_config,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def temp_log_dir():
    """Create temporary log directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def server_config(temp_log_dir):
    """Create test server configuration."""
    return WSSServerConfig(
        host="localhost",
        ports=[8001, 8002, 8003, 8004, 8005],
        log_dir=temp_log_dir,
        log_format="text",
        log_level="DEBUG",
        max_clients_per_port=10,
        heartbeat_interval=60.0,  # Long interval for tests
    )


@pytest.fixture
async def server(server_config):
    """Create and start test server."""
    srv = WSSServer(server_config)
    
    # Start server in background
    server_task = asyncio.create_task(srv.start())
    
    # Wait for server to start
    await asyncio.sleep(0.5)
    
    yield srv
    
    # Cleanup
    await srv.stop()
    server_task.cancel()
    try:
        await server_task
    except asyncio.CancelledError:
        pass


# =============================================================================
# Server Startup Tests
# =============================================================================

class TestServerStartup:
    """Test server starts correctly on all ports."""
    
    @pytest.mark.asyncio
    async def test_server_creates_instance(self, server_config):
        """Test server can be instantiated."""
        srv = WSSServer(server_config)
        assert srv is not None
        assert srv.config == server_config
        assert not srv._running
    
    @pytest.mark.asyncio
    async def test_default_config(self):
        """Test default configuration."""
        config = get_default_config()
        assert config.host == "localhost"
        assert 8001 in config.ports
        assert 8002 in config.ports
        assert 8003 in config.ports
        assert 8004 in config.ports
        assert 8005 in config.ports
    
    @pytest.mark.asyncio
    async def test_server_starts_on_all_ports(self, server_config):
        """Test server accepts connections on all configured ports."""
        srv = WSSServer(server_config)
        server_task = asyncio.create_task(srv.start())
        
        # Wait for startup
        await asyncio.sleep(0.5)
        
        try:
            # Test each port
            for port in server_config.ports:
                uri = f"ws://{server_config.host}:{port}"
                async with ws_connect(uri) as websocket:
                    assert websocket.open
        finally:
            await srv.stop()
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass
    
    @pytest.mark.asyncio
    async def test_server_port_8001_ui(self, server_config):
        """Test server starts on port 8001 (UI)."""
        srv = WSSServer(server_config)
        server_task = asyncio.create_task(srv.start())
        await asyncio.sleep(0.5)
        
        try:
            async with ws_connect(f"ws://localhost:8001") as ws:
                assert ws.open
        finally:
            await srv.stop()
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass
    
    @pytest.mark.asyncio
    async def test_server_port_8002_detection(self, server_config):
        """Test server starts on port 8002 (YOLO Detection)."""
        srv = WSSServer(server_config)
        server_task = asyncio.create_task(srv.start())
        await asyncio.sleep(0.5)
        
        try:
            async with ws_connect(f"ws://localhost:8002") as ws:
                assert ws.open
        finally:
            await srv.stop()
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass
    
    @pytest.mark.asyncio
    async def test_server_port_8003_system(self, server_config):
        """Test server starts on port 8003 (System Events)."""
        srv = WSSServer(server_config)
        server_task = asyncio.create_task(srv.start())
        await asyncio.sleep(0.5)
        
        try:
            async with ws_connect(f"ws://localhost:8003") as ws:
                assert ws.open
        finally:
            await srv.stop()
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass
    
    @pytest.mark.asyncio
    async def test_server_port_8004_classification(self, server_config):
        """Test server starts on port 8004 (Eagle2 Classification)."""
        srv = WSSServer(server_config)
        server_task = asyncio.create_task(srv.start())
        await asyncio.sleep(0.5)
        
        try:
            async with ws_connect(f"ws://localhost:8004") as ws:
                assert ws.open
        finally:
            await srv.stop()
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass
    
    @pytest.mark.asyncio
    async def test_server_port_8005_trading(self, server_config):
        """Test server starts on port 8005 (Trading Signals)."""
        srv = WSSServer(server_config)
        server_task = asyncio.create_task(srv.start())
        await asyncio.sleep(0.5)
        
        try:
            async with ws_connect(f"ws://localhost:8005") as ws:
                assert ws.open
        finally:
            await srv.stop()
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass


# =============================================================================
# Client Connection Tests
# =============================================================================

class TestClientConnections:
    """Test clients can connect and communicate."""
    
    @pytest.mark.asyncio
    async def test_client_can_connect(self, server_config):
        """Test basic client connection."""
        srv = WSSServer(server_config)
        server_task = asyncio.create_task(srv.start())
        await asyncio.sleep(0.5)
        
        try:
            async with ws_connect("ws://localhost:8001") as ws:
                assert ws.open
                # Send a test message
                test_msg = {"type": "test", "data": "hello"}
                await ws.send(json.dumps(test_msg))
                
                # Should receive ack
                response = await asyncio.wait_for(ws.recv(), timeout=2.0)
                response_data = json.loads(response)
                assert response_data["type"] == "ack"
        finally:
            await srv.stop()
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass
    
    @pytest.mark.asyncio
    async def test_multiple_clients_same_port(self, server_config):
        """Test multiple clients can connect to same port."""
        srv = WSSServer(server_config)
        server_task = asyncio.create_task(srv.start())
        await asyncio.sleep(0.5)
        
        try:
            async with ws_connect("ws://localhost:8001") as ws1:
                async with ws_connect("ws://localhost:8001") as ws2:
                    assert ws1.open
                    assert ws2.open
        finally:
            await srv.stop()
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass
    
    @pytest.mark.asyncio
    async def test_clients_different_ports(self, server_config):
        """Test clients can connect to different ports simultaneously."""
        srv = WSSServer(server_config)
        server_task = asyncio.create_task(srv.start())
        await asyncio.sleep(0.5)
        
        try:
            connections = []
            for port in server_config.ports:
                ws = await ws_connect(f"ws://localhost:{port}")
                connections.append(ws)
            
            for ws in connections:
                assert ws.open
            
            for ws in connections:
                await ws.close()
        finally:
            await srv.stop()
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass


# =============================================================================
# Message Broadcasting Tests
# =============================================================================

class TestMessageBroadcasting:
    """Test message broadcasting to clients."""
    
    @pytest.mark.asyncio
    async def test_broadcast_message(self, server_config):
        """Test server can broadcast messages to clients."""
        srv = WSSServer(server_config)
        server_task = asyncio.create_task(srv.start())
        await asyncio.sleep(0.5)
        
        try:
            # Connect subscriber client
            async with ws_connect("ws://localhost:8002") as subscriber:
                # Give server time to register connection
                await asyncio.sleep(0.1)
                
                # Create and publish detection message
                msg = DetectionMessage(
                    timestamp=datetime.utcnow().isoformat(),
                    source="test",
                    payload={
                        "detections": [{"class": "chart", "confidence": 0.95}],
                        "inference_time_ms": 15.0,
                        "frame_id": "frame_001",
                    }
                )
                
                # Publish via server
                sent = await srv.publish(8002, msg)
                assert sent >= 1  # At least our subscriber received it
                
                # Receive message
                received = await asyncio.wait_for(subscriber.recv(), timeout=2.0)
                data = json.loads(received)
                assert data["msg_type"] == "detection"
                assert data["source"] == "test"
        finally:
            await srv.stop()
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass
    
    @pytest.mark.asyncio
    async def test_broadcast_to_multiple_clients(self, server_config):
        """Test broadcast reaches multiple clients."""
        srv = WSSServer(server_config)
        server_task = asyncio.create_task(srv.start())
        await asyncio.sleep(0.5)
        
        try:
            # Connect multiple subscribers
            subscribers = []
            for _ in range(3):
                ws = await ws_connect("ws://localhost:8001")
                subscribers.append(ws)
            
            await asyncio.sleep(0.1)
            
            # Publish message
            msg = UIUpdateMessage(
                timestamp=datetime.utcnow().isoformat(),
                source="test",
                payload={"update_type": "status", "data": {"status": "ok"}}
            )
            sent = await srv.publish(8001, msg)
            assert sent == 3
            
            # All subscribers should receive
            for ws in subscribers:
                received = await asyncio.wait_for(ws.recv(), timeout=2.0)
                data = json.loads(received)
                assert data["msg_type"] == "ui_update"
                await ws.close()
        finally:
            await srv.stop()
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass
    
    @pytest.mark.asyncio
    async def test_message_routing_by_type(self, server_config):
        """Test message routing based on message type."""
        srv = WSSServer(server_config)
        server_task = asyncio.create_task(srv.start())
        await asyncio.sleep(0.5)
        
        try:
            async with ws_connect("ws://localhost:8005") as subscriber:
                await asyncio.sleep(0.1)
                
                msg = TradingSignalMessage(
                    timestamp=datetime.utcnow().isoformat(),
                    source="test_trading",
                    payload={
                        "signal_type": "BUY",
                        "risk_level": "LOW",
                        "confidence": 0.85,
                    }
                )
                
                sent = await srv.publish_by_type("trading_signal", msg)
                assert sent >= 1
                
                received = await asyncio.wait_for(subscriber.recv(), timeout=2.0)
                data = json.loads(received)
                assert data["msg_type"] == "trading_signal"
                assert data["payload"]["signal_type"] == "BUY"
        finally:
            await srv.stop()
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass


# =============================================================================
# Schema Routing Tests
# =============================================================================

class TestSchemaRouting:
    """Test schema-based message routing."""
    
    def test_port_router_mappings(self):
        """Test port router has correct mappings."""
        assert PortRouter.get_port_for_message("ui_update") == 8001
        assert PortRouter.get_port_for_message("detection") == 8002
        assert PortRouter.get_port_for_message("system_event") == 8003
        assert PortRouter.get_port_for_message("classification") == 8004
        assert PortRouter.get_port_for_message("trading_signal") == 8005
    
    def test_port_router_names(self):
        """Test port router returns correct names."""
        assert PortRouter.get_port_name(8001) == "ui"
        assert PortRouter.get_port_name(8002) == "detection"
        assert PortRouter.get_port_name(8003) == "system"
        assert PortRouter.get_port_name(8004) == "classification"
        assert PortRouter.get_port_name(8005) == "trading"
    
    def test_port_router_unknown(self):
        """Test port router handles unknown types."""
        assert PortRouter.get_port_for_message("unknown") is None
        assert PortRouter.get_port_name(9999) == "port_9999"


# =============================================================================
# Logging Tests
# =============================================================================

class TestLogging:
    """Test logging functionality."""
    
    @pytest.mark.asyncio
    async def test_text_logging(self, temp_log_dir):
        """Test text format logging."""
        config = WSSServerConfig(log_dir=temp_log_dir, log_format="text")
        logger = WSSLogger(config)
        
        msg = WSSMessage(
            timestamp=datetime.utcnow().isoformat(),
            source="test",
            msg_type="test",
            payload={"data": "value"}
        )
        
        logger.log(8001, msg)
        
        # Check log file exists
        log_file = temp_log_dir / "port_8001.text.log"
        assert log_file.exists()
        
        content = log_file.read_text()
        assert "test" in content
        assert "data" in content
    
    @pytest.mark.asyncio
    async def test_json_logging(self, temp_log_dir):
        """Test JSON format logging."""
        config = WSSServerConfig(log_dir=temp_log_dir, log_format="json")
        logger = WSSLogger(config)
        
        msg = WSSMessage(
            timestamp=datetime.utcnow().isoformat(),
            source="test",
            msg_type="detection",
            payload={"detections": []}
        )
        
        logger.log(8002, msg)
        
        # Check log file exists and contains valid JSON
        log_file = temp_log_dir / "port_8002.json.log"
        assert log_file.exists()
        
        content = log_file.read_text().strip()
        # Each line should be valid JSON
        for line in content.split('\n'):
            if line:
                data = json.loads(line)
                assert data["msg_type"] == "detection"
    
    @pytest.mark.asyncio
    async def test_logging_all_ports(self, temp_log_dir):
        """Test logging works on all ports."""
        config = WSSServerConfig(log_dir=temp_log_dir, log_format="json")
        logger = WSSLogger(config)
        
        for port in [8001, 8002, 8003, 8004, 8005]:
            msg = WSSMessage(
                timestamp=datetime.utcnow().isoformat(),
                source="test",
                msg_type="test",
                payload={"port": port}
            )
            logger.log(port, msg)
            
            log_file = temp_log_dir / f"port_{port}.json.log"
            assert log_file.exists()


# =============================================================================
# Connection Manager Tests
# =============================================================================

class TestConnectionManager:
    """Test connection manager functionality."""
    
    @pytest.mark.asyncio
    async def test_connection_tracking(self):
        """Test connection manager tracks connections."""
        cm = ConnectionManager(max_clients=5)
        
        # Mock websocket
        class MockWS:
            pass
        
        ws1 = MockWS()
        ws2 = MockWS()
        
        assert await cm.connect(8001, ws1)
        assert await cm.connect(8001, ws2)
        
        stats = cm.get_stats()
        assert stats[8001]["current"] == 2
        assert stats[8001]["total_connections"] == 2
    
    @pytest.mark.asyncio
    async def test_max_clients_limit(self):
        """Test max clients limit is enforced."""
        cm = ConnectionManager(max_clients=2)
        
        class MockWS:
            pass
        
        ws1, ws2, ws3 = MockWS(), MockWS(), MockWS()
        
        assert await cm.connect(8001, ws1)
        assert await cm.connect(8001, ws2)
        assert not await cm.connect(8001, ws3)  # Should fail at limit
    
    @pytest.mark.asyncio
    async def test_disconnect(self):
        """Test disconnect removes connection."""
        cm = ConnectionManager()
        
        class MockWS:
            pass
        
        ws = MockWS()
        await cm.connect(8001, ws)
        assert cm.get_stats()[8001]["current"] == 1
        
        await cm.disconnect(8001, ws)
        assert cm.get_stats()[8001]["current"] == 0


# =============================================================================
# Message Schema Tests
# =============================================================================

class TestMessageSchemas:
    """Test message schema validation."""
    
    def test_base_message(self):
        """Test base WSS message."""
        msg = WSSMessage(
            timestamp="2026-03-17T12:00:00Z",
            source="test",
            msg_type="test",
            payload={"key": "value"}
        )
        assert msg.timestamp == "2026-03-17T12:00:00Z"
        assert msg.schema_version == "1.0"
    
    def test_detection_message(self):
        """Test detection message schema."""
        msg = DetectionMessage(
            timestamp="2026-03-17T12:00:00Z",
            source="yolo",
            payload={
                "detections": [{"class": "chart", "bbox": [0, 0, 100, 100]}],
                "inference_time_ms": 15.5,
                "frame_id": "frame_001",
            }
        )
        assert msg.msg_type == "detection"
        assert len(msg.payload["detections"]) == 1
    
    def test_classification_message(self):
        """Test classification message schema."""
        msg = ClassificationMessage(
            timestamp="2026-03-17T12:00:00Z",
            source="eagle2",
            payload={
                "event_type": "chart_update",
                "confidence": 0.92,
                "is_trading_relevant": True,
            }
        )
        assert msg.msg_type == "classification"
        assert msg.payload["is_trading_relevant"] is True
    
    def test_trading_signal_message(self):
        """Test trading signal message schema."""
        msg = TradingSignalMessage(
            timestamp="2026-03-17T12:00:00Z",
            source="reviewer",
            payload={
                "signal_type": "HOLD",
                "risk_level": "MEDIUM",
                "recommendation": "WARN",
                "confidence": 0.75,
            }
        )
        assert msg.msg_type == "trading_signal"
        assert msg.payload["risk_level"] == "MEDIUM"
    
    def test_message_serialization(self):
        """Test message JSON serialization."""
        msg = WSSMessage(
            timestamp="2026-03-17T12:00:00Z",
            source="test",
            msg_type="test",
            payload={"nested": {"key": "value"}}
        )
        
        json_str = msg.model_dump_json()
        data = json.loads(json_str)
        
        assert data["timestamp"] == "2026-03-17T12:00:00Z"
        assert data["payload"]["nested"]["key"] == "value"


# =============================================================================
# Server Stats Tests
# =============================================================================

class TestServerStats:
    """Test server statistics."""
    
    @pytest.mark.asyncio
    async def test_initial_stats(self, server_config):
        """Test initial server stats."""
        srv = WSSServer(server_config)
        
        stats = srv.get_stats()
        assert stats["running"] is False
        assert stats["uptime_seconds"] == 0
        assert all(c == 0 for c in stats["message_counts"].values())
    
    @pytest.mark.asyncio
    async def test_message_counting(self, server_config):
        """Test message counts are tracked."""
        srv = WSSServer(server_config)
        server_task = asyncio.create_task(srv.start())
        await asyncio.sleep(0.5)
        
        try:
            # Publish some messages
            for _ in range(5):
                msg = WSSMessage(
                    timestamp=datetime.utcnow().isoformat(),
                    source="test",
                    msg_type="ui_update",
                    payload={}
                )
                await srv.publish(8001, msg)
            
            stats = srv.get_stats()
            assert stats["message_counts"][8001] == 5
        finally:
            await srv.stop()
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass


# =============================================================================
# Factory Function Tests
# =============================================================================

class TestFactoryFunctions:
    """Test factory convenience functions."""
    
    @pytest.mark.asyncio
    async def test_create_server(self, server_config):
        """Test create_server factory."""
        srv = await create_server(server_config)
        assert isinstance(srv, WSSServer)
        assert srv.config == server_config