"""Tests for WSS Server v2.

Tests cover:
- Server starts on single port 8000
- Clients can connect and subscribe to typed topics
- Message broadcasting works with topic routing
- Durable logging (events.jsonl, classifications.jsonl)
- Authentication (when enabled)
- Reconnection handling
- Transport envelope validation

Equivalent to v1 tests (~50 tests).
"""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
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

from advanced_vision.wss_server_v2 import (
    WSSServerV2,
    WSSServerConfigV2,
    TransportEnvelope,
    SchemaFamily,
    Topic,
    TopicRouter,
    ConnectionManagerV2,
    WSSLoggerV2,
    create_server_v2,
    get_default_config_v2,
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
    return WSSServerConfigV2(
        host="localhost",
        port=8000,
        log_dir=temp_log_dir,
        log_format="jsonl",
        log_level="DEBUG",
        max_clients=10,
        heartbeat_interval=60.0,  # Long interval for tests
    )


@pytest.fixture
async def server(server_config):
    """Create and start test server."""
    srv = WSSServerV2(server_config)
    
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

class TestServerStartupV2:
    """Test server starts correctly on single port 8000."""
    
    @pytest.mark.asyncio
    async def test_server_creates_instance_v2(self, server_config):
        """Test server can be instantiated."""
        srv = WSSServerV2(server_config)
        assert srv is not None
        assert srv.config == server_config
        assert not srv._running
    
    @pytest.mark.asyncio
    async def test_default_config_v2(self):
        """Test default configuration."""
        config = get_default_config_v2()
        assert config.host == "localhost"
        assert config.port == 8000
    
    @pytest.mark.asyncio
    async def test_server_starts_on_port_8000(self, server_config):
        """Test server accepts connections on port 8000."""
        srv = WSSServerV2(server_config)
        server_task = asyncio.create_task(srv.start())
        
        # Wait for startup
        await asyncio.sleep(0.5)
        
        try:
            # Test single port
            uri = f"ws://{server_config.host}:8000"
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
    async def test_server_v2_only_uses_port_8000(self, server_config):
        """Test server only uses port 8000, not legacy ports."""
        srv = WSSServerV2(server_config)
        server_task = asyncio.create_task(srv.start())
        await asyncio.sleep(0.5)
        
        try:
            # Should work on 8000
            async with ws_connect("ws://localhost:8000") as ws:
                assert ws.open
            
            # Should NOT work on legacy ports
            for port in [8001, 8002, 8003, 8004, 8005]:
                with pytest.raises(Exception):
                    async with ws_connect(f"ws://localhost:{port}"):
                        pass
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

class TestClientConnectionsV2:
    """Test clients can connect and subscribe."""
    
    @pytest.mark.asyncio
    async def test_client_can_connect_v2(self, server_config):
        """Test basic client connection."""
        srv = WSSServerV2(server_config)
        server_task = asyncio.create_task(srv.start())
        await asyncio.sleep(0.5)
        
        try:
            async with ws_connect("ws://localhost:8000") as ws:
                assert ws.open
                
                # Send ping
                await ws.send(json.dumps({"type": "ping"}))
                response = await asyncio.wait_for(ws.recv(), timeout=2.0)
                data = json.loads(response)
                assert data["type"] == "pong"
        finally:
            await srv.stop()
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass
    
    @pytest.mark.asyncio
    async def test_multiple_clients_v2(self, server_config):
        """Test multiple clients can connect simultaneously."""
        srv = WSSServerV2(server_config)
        server_task = asyncio.create_task(srv.start())
        await asyncio.sleep(0.5)
        
        try:
            connections = []
            for _ in range(5):
                ws = await ws_connect("ws://localhost:8000")
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
    
    @pytest.mark.asyncio
    async def test_client_subscription_v2(self, server_config):
        """Test client can subscribe to topics."""
        srv = WSSServerV2(server_config)
        server_task = asyncio.create_task(srv.start())
        await asyncio.sleep(0.5)
        
        try:
            async with ws_connect("ws://localhost:8000") as ws:
                # Subscribe to topic
                await ws.send(json.dumps({
                    "type": "subscribe",
                    "topics": ["vision.detection.yolo"]
                }))
                
                response = await asyncio.wait_for(ws.recv(), timeout=2.0)
                data = json.loads(response)
                assert data["type"] == "subscribe_ack"
                assert "vision.detection.yolo" in data["topics"]
        finally:
            await srv.stop()
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass
    
    @pytest.mark.asyncio
    async def test_client_multiple_subscriptions_v2(self, server_config):
        """Test client can subscribe to multiple topics."""
        srv = WSSServerV2(server_config)
        server_task = asyncio.create_task(srv.start())
        await asyncio.sleep(0.5)
        
        try:
            async with ws_connect("ws://localhost:8000") as ws:
                topics = [
                    "vision.detection.yolo",
                    "vision.segmentation.sam",
                    "vision.classification.eagle"
                ]
                
                await ws.send(json.dumps({
                    "type": "subscribe",
                    "topics": topics
                }))
                
                response = await asyncio.wait_for(ws.recv(), timeout=2.0)
                data = json.loads(response)
                assert data["type"] == "subscribe_ack"
                assert data["subscribed_count"] == 3
        finally:
            await srv.stop()
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass
    
    @pytest.mark.asyncio
    async def test_client_unsubscribe_v2(self, server_config):
        """Test client can unsubscribe from topics."""
        srv = WSSServerV2(server_config)
        server_task = asyncio.create_task(srv.start())
        await asyncio.sleep(0.5)
        
        try:
            async with ws_connect("ws://localhost:8000") as ws:
                # Subscribe first
                await ws.send(json.dumps({
                    "type": "subscribe",
                    "topics": ["vision.detection.yolo"]
                }))
                await asyncio.wait_for(ws.recv(), timeout=2.0)
                
                # Then unsubscribe
                await ws.send(json.dumps({
                    "type": "unsubscribe",
                    "topics": ["vision.detection.yolo"]
                }))
                
                response = await asyncio.wait_for(ws.recv(), timeout=2.0)
                data = json.loads(response)
                assert data["type"] == "unsubscribe_ack"
        finally:
            await srv.stop()
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass


# =============================================================================
# Topic Routing Tests
# =============================================================================

class TestTopicRoutingV2:
    """Test topic-based message routing."""
    
    def test_topic_router_mappings(self):
        """Test topic router has correct mappings."""
        assert TopicRouter.get_topic_for_event("detection", "yolo") == Topic.VISION_DETECTION_YOLO
        assert TopicRouter.get_topic_for_event("segmentation", "sam") == Topic.VISION_SEGMENTATION_SAM
        assert TopicRouter.get_topic_for_event("classification", "eagle") == Topic.VISION_CLASSIFICATION_EAGLE
        assert TopicRouter.get_topic_for_event("analysis", "qwen") == Topic.VISION_ANALYSIS_QWEN
    
    def test_topic_router_by_source(self):
        """Test topic router falls back to source."""
        assert TopicRouter.get_topic_for_event("unknown", "yolo") == Topic.VISION_DETECTION_YOLO
        assert TopicRouter.get_topic_for_event("unknown", "sam") == Topic.VISION_SEGMENTATION_SAM
        assert TopicRouter.get_topic_for_event("unknown", "eagle") == Topic.VISION_CLASSIFICATION_EAGLE
    
    def test_schema_family_mapping(self):
        """Test schema family mappings."""
        assert TopicRouter.get_schema_family(Topic.VISION_DETECTION_YOLO) == SchemaFamily.DETECTION
        assert TopicRouter.get_schema_family(Topic.VISION_SEGMENTATION_SAM) == SchemaFamily.SEGMENTATION
        assert TopicRouter.get_schema_family(Topic.VISION_CLASSIFICATION_EAGLE) == SchemaFamily.CLASSIFICATION
        assert TopicRouter.get_schema_family(Topic.VISION_ANALYSIS_QWEN) == SchemaFamily.ANALYSIS
    
    @pytest.mark.asyncio
    async def test_publish_to_specific_topic_v2(self, server_config):
        """Test publishing to specific topic."""
        srv = WSSServerV2(server_config)
        server_task = asyncio.create_task(srv.start())
        await asyncio.sleep(0.5)
        
        try:
            # Connect publisher and subscriber
            async with ws_connect("ws://localhost:8000") as subscriber:
                # Subscribe to detection topic
                await subscriber.send(json.dumps({
                    "type": "subscribe",
                    "topics": ["vision.detection.yolo"]
                }))
                await asyncio.wait_for(subscriber.recv(), timeout=2.0)
                
                await asyncio.sleep(0.1)
                
                # Publish detection envelope
                envelope = TransportEnvelope(
                    event_type="detection",
                    schema_family=SchemaFamily.DETECTION,
                    source="yolo",
                    frame_ref="frame_001",
                    payload={"boxes": [{"x": 100, "y": 100, "w": 200, "h": 150}]}
                )
                
                sent = await srv.publish(envelope, "vision.detection.yolo")
                assert sent >= 1
                
                # Receive message
                received = await asyncio.wait_for(subscriber.recv(), timeout=2.0)
                data = json.loads(received)
                assert data["event_type"] == "detection"
                assert data["schema_family"] == "detection"
                assert data["source"] == "yolo"
        finally:
            await srv.stop()
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass
    
    @pytest.mark.asyncio
    async def test_topic_filtering_v2(self, server_config):
        """Test that subscribers only receive their subscribed topics."""
        srv = WSSServerV2(server_config)
        server_task = asyncio.create_task(srv.start())
        await asyncio.sleep(0.5)
        
        try:
            # Subscriber 1: detection only
            sub1 = await ws_connect("ws://localhost:8000")
            await sub1.send(json.dumps({
                "type": "subscribe",
                "topics": ["vision.detection.yolo"]
            }))
            await asyncio.wait_for(sub1.recv(), timeout=2.0)
            
            # Subscriber 2: classification only
            sub2 = await ws_connect("ws://localhost:8000")
            await sub2.send(json.dumps({
                "type": "subscribe",
                "topics": ["vision.classification.eagle"]
            }))
            await asyncio.wait_for(sub2.recv(), timeout=2.0)
            
            await asyncio.sleep(0.1)
            
            # Publish to detection topic
            detection_env = TransportEnvelope(
                event_type="detection",
                schema_family=SchemaFamily.DETECTION,
                source="yolo",
                payload={"boxes": []}
            )
            await srv.publish(detection_env, "vision.detection.yolo")
            
            # Only sub1 should receive
            received1 = await asyncio.wait_for(sub1.recv(), timeout=2.0)
            data1 = json.loads(received1)
            assert data1["event_type"] == "detection"
            
            # Publish to classification topic
            class_env = TransportEnvelope(
                event_type="classification",
                schema_family=SchemaFamily.CLASSIFICATION,
                source="eagle",
                payload={"label": "chart"}
            )
            await srv.publish(class_env, "vision.classification.eagle")
            
            # Only sub2 should receive
            received2 = await asyncio.wait_for(sub2.recv(), timeout=2.0)
            data2 = json.loads(received2)
            assert data2["event_type"] == "classification"
            
            await sub1.close()
            await sub2.close()
        finally:
            await srv.stop()
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass


# =============================================================================
# Transport Envelope Tests
# =============================================================================

class TestTransportEnvelopeV2:
    """Test transport envelope structure."""
    
    def test_envelope_creation(self):
        """Test envelope can be created."""
        envelope = TransportEnvelope(
            event_type="detection",
            schema_family=SchemaFamily.DETECTION,
            source="yolo",
            frame_ref="frame_001",
            trace_id=str(uuid.uuid4()),
            payload={"boxes": []}
        )
        
        assert envelope.event_type == "detection"
        assert envelope.schema_family == SchemaFamily.DETECTION
        assert envelope.source == "yolo"
        assert envelope.frame_ref == "frame_001"
        assert envelope.event_id is not None
        assert envelope.created_at is not None
    
    def test_envelope_auto_fields(self):
        """Test envelope auto-generates required fields."""
        envelope = TransportEnvelope(
            event_type="test",
            schema_family=SchemaFamily.SYSTEM,
            source="test"
        )
        
        # event_id should be auto-generated
        assert envelope.event_id
        assert len(envelope.event_id) > 0
        
        # created_at should be auto-generated
        assert envelope.created_at
        assert "T" in envelope.created_at  # ISO format
    
    def test_envelope_serialization(self):
        """Test envelope JSON serialization."""
        envelope = TransportEnvelope(
            event_type="classification",
            schema_family=SchemaFamily.CLASSIFICATION,
            source="eagle",
            payload={"label": "order_ticket", "confidence": 0.95}
        )
        
        json_str = envelope.model_dump_json()
        data = json.loads(json_str)
        
        assert data["event_type"] == "classification"
        assert data["schema_family"] == "classification"
        assert data["source"] == "eagle"
        assert data["payload"]["label"] == "order_ticket"
    
    def test_envelope_deserialization(self):
        """Test envelope JSON deserialization."""
        data = {
            "event_id": str(uuid.uuid4()),
            "event_type": "analysis",
            "schema_family": "analysis",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source": "qwen",
            "frame_ref": "frame_123",
            "trace_id": str(uuid.uuid4()),
            "payload": {"risk_level": "high", "recommendation": "pause"}
        }
        
        envelope = TransportEnvelope(**data)
        assert envelope.event_type == "analysis"
        assert envelope.schema_family == SchemaFamily.ANALYSIS
        assert envelope.payload["risk_level"] == "high"


# =============================================================================
# Durable Logging Tests
# =============================================================================

class TestDurableLoggingV2:
    """Test logging to events.jsonl and classifications.jsonl."""
    
    @pytest.mark.asyncio
    async def test_events_jsonl_logging(self, temp_log_dir):
        """Test events are logged to events.jsonl."""
        config = WSSServerConfigV2(log_dir=temp_log_dir, log_format="jsonl")
        logger = WSSLoggerV2(config)
        
        envelope = TransportEnvelope(
            event_type="detection",
            schema_family=SchemaFamily.DETECTION,
            source="yolo",
            payload={"boxes": []}
        )
        
        logger.log_event(envelope)
        
        # Check log file exists
        log_file = temp_log_dir / "events.jsonl"
        assert log_file.exists()
        
        content = log_file.read_text()
        assert "detection" in content
        assert "yolo" in content
    
    @pytest.mark.asyncio
    async def test_classifications_jsonl_logging(self, temp_log_dir):
        """Test classifications are logged to classifications.jsonl."""
        config = WSSServerConfigV2(log_dir=temp_log_dir, log_format="jsonl")
        logger = WSSLoggerV2(config)
        
        envelope = TransportEnvelope(
            event_type="classification",
            schema_family=SchemaFamily.CLASSIFICATION,
            source="eagle",
            payload={"label": "order_ticket"}
        )
        
        logger.log_event(envelope)
        logger.log_classification(envelope)
        
        # Check both log files exist
        events_file = temp_log_dir / "events.jsonl"
        class_file = temp_log_dir / "classifications.jsonl"
        
        assert events_file.exists()
        assert class_file.exists()
        
        # Classifications should be in both
        class_content = class_file.read_text()
        assert "order_ticket" in class_content
    
    @pytest.mark.asyncio
    async def test_logging_all_schema_families(self, temp_log_dir):
        """Test logging works for all schema families."""
        config = WSSServerConfigV2(log_dir=temp_log_dir, log_format="jsonl")
        logger = WSSLoggerV2(config)
        
        families = [
            (SchemaFamily.DETECTION, "yolo"),
            (SchemaFamily.SEGMENTATION, "sam"),
            (SchemaFamily.CLASSIFICATION, "eagle"),
            (SchemaFamily.ANALYSIS, "qwen"),
            (SchemaFamily.SYSTEM, "server"),
        ]
        
        for family, source in families:
            envelope = TransportEnvelope(
                event_type="test",
                schema_family=family,
                source=source,
                payload={"test": True}
            )
            logger.log_event(envelope)
        
        log_file = temp_log_dir / "events.jsonl"
        content = log_file.read_text()
        
        for _, source in families:
            assert source in content


# =============================================================================
# Connection Manager v2 Tests
# =============================================================================

class TestConnectionManagerV2:
    """Test connection manager functionality."""
    
    @pytest.mark.asyncio
    async def test_connection_tracking_v2(self):
        """Test connection manager tracks connections."""
        cm = ConnectionManagerV2(max_clients=5)
        
        # Mock websocket
        class MockWS:
            pass
        
        ws1 = MockWS()
        ws2 = MockWS()
        
        conn1 = await cm.connect(ws1)
        conn2 = await cm.connect(ws2)
        
        assert conn1 is not None
        assert conn2 is not None
        assert conn1.client_id != conn2.client_id
        
        stats = cm.get_stats()
        assert stats["current_connections"] == 2
        assert stats["total_connections"] == 2
    
    @pytest.mark.asyncio
    async def test_max_clients_limit_v2(self):
        """Test max clients limit is enforced."""
        cm = ConnectionManagerV2(max_clients=2)
        
        class MockWS:
            pass
        
        ws1, ws2, ws3 = MockWS(), MockWS(), MockWS()
        
        conn1 = await cm.connect(ws1)
        conn2 = await cm.connect(ws2)
        conn3 = await cm.connect(ws3)
        
        assert conn1 is not None
        assert conn2 is not None
        assert conn3 is None  # Should fail at limit
    
    @pytest.mark.asyncio
    async def test_topic_subscription_v2(self):
        """Test topic subscription tracking."""
        cm = ConnectionManagerV2()
        
        class MockWS:
            pass
        
        ws = MockWS()
        conn = await cm.connect(ws)
        
        # Subscribe to topics
        success = await cm.subscribe(conn.client_id, "vision.detection.yolo")
        assert success
        
        success = await cm.subscribe(conn.client_id, "vision.classification.eagle")
        assert success
        
        stats = cm.get_stats()
        assert stats["topic_subscriptions"]["vision.detection.yolo"] == 1
        assert stats["topic_subscriptions"]["vision.classification.eagle"] == 1
    
    @pytest.mark.asyncio
    async def test_unsubscribe_v2(self):
        """Test unsubscription."""
        cm = ConnectionManagerV2()
        
        class MockWS:
            pass
        
        ws = MockWS()
        conn = await cm.connect(ws)
        
        await cm.subscribe(conn.client_id, "vision.detection.yolo")
        await cm.unsubscribe(conn.client_id, "vision.detection.yolo")
        
        stats = cm.get_stats()
        assert stats["topic_subscriptions"].get("vision.detection.yolo", 0) == 0


# =============================================================================
# Authentication Tests
# =============================================================================

class TestAuthenticationV2:
    """Test authentication functionality."""
    
    @pytest.mark.asyncio
    async def test_auth_disabled_by_default(self, server_config):
        """Test that auth is disabled by default."""
        srv = WSSServerV2(server_config)
        assert not srv.config.auth_enabled
    
    @pytest.mark.asyncio
    async def test_auth_enabled_connection(self, temp_log_dir):
        """Test that auth is enforced when enabled."""
        config = WSSServerConfigV2(
            host="localhost",
            port=8000,
            log_dir=temp_log_dir,
            auth_enabled=True,
            auth_token="test_token_123"
        )
        
        srv = WSSServerV2(config)
        server_task = asyncio.create_task(srv.start())
        await asyncio.sleep(0.5)
        
        try:
            # Connect and try to interact without auth
            async with ws_connect("ws://localhost:8000") as ws:
                # Server should reject operations without auth
                # The first message after connect triggers auth check
                await ws.send(json.dumps({"type": "ping"}))
                response = await asyncio.wait_for(ws.recv(), timeout=2.0)
                data = json.loads(response)
                # Should receive auth_failed
                assert data["type"] == "auth_failed"
        finally:
            await srv.stop()
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass
    
    @pytest.mark.asyncio
    async def test_auth_token_set(self, temp_log_dir):
        """Test that auth token is properly configured."""
        config = WSSServerConfigV2(
            host="localhost",
            port=8000,
            log_dir=temp_log_dir,
            auth_enabled=True,
            auth_token="test_token_123"
        )
        
        assert config.auth_enabled is True
        assert config.auth_token == "test_token_123"


# =============================================================================
# Server Stats Tests
# =============================================================================

class TestServerStatsV2:
    """Test server statistics."""
    
    @pytest.mark.asyncio
    async def test_initial_stats_v2(self, server_config):
        """Test initial server stats."""
        srv = WSSServerV2(server_config)
        
        stats = srv.get_stats()
        assert stats["running"] is False
        assert stats["uptime_seconds"] == 0
    
    @pytest.mark.asyncio
    async def test_message_counting_v2(self, server_config):
        """Test message counts are tracked."""
        srv = WSSServerV2(server_config)
        server_task = asyncio.create_task(srv.start())
        await asyncio.sleep(0.5)
        
        try:
            # Publish some messages
            for i in range(5):
                envelope = TransportEnvelope(
                    event_type="detection",
                    schema_family=SchemaFamily.DETECTION,
                    source="yolo",
                    payload={"index": i}
                )
                await srv.publish(envelope, "vision.detection.yolo")
            
            stats = srv.get_stats()
            assert stats["message_counts"]["vision.detection.yolo"] == 5
        finally:
            await srv.stop()
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass
    
    @pytest.mark.asyncio
    async def test_stats_via_websocket(self, server_config):
        """Test getting stats via WebSocket."""
        srv = WSSServerV2(server_config)
        server_task = asyncio.create_task(srv.start())
        await asyncio.sleep(0.5)
        
        try:
            async with ws_connect("ws://localhost:8000") as ws:
                await ws.send(json.dumps({"type": "get_stats"}))
                
                response = await asyncio.wait_for(ws.recv(), timeout=2.0)
                data = json.loads(response)
                
                assert data["type"] == "stats"
                assert "data" in data
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

class TestFactoryFunctionsV2:
    """Test factory convenience functions."""
    
    @pytest.mark.asyncio
    async def test_create_server_v2(self, server_config):
        """Test create_server_v2 factory."""
        srv = await create_server_v2(server_config)
        assert isinstance(srv, WSSServerV2)
        assert srv.config == server_config


# =============================================================================
# Topic Constants Tests
# =============================================================================

class TestTopicConstants:
    """Test topic constants are correctly defined."""
    
    def test_detection_topic(self):
        """Test YOLO detection topic."""
        assert Topic.VISION_DETECTION_YOLO.value == "vision.detection.yolo"
    
    def test_segmentation_topic(self):
        """Test SAM segmentation topic."""
        assert Topic.VISION_SEGMENTATION_SAM.value == "vision.segmentation.sam"
    
    def test_classification_topic(self):
        """Test Eagle classification topic."""
        assert Topic.VISION_CLASSIFICATION_EAGLE.value == "vision.classification.eagle"
    
    def test_analysis_topic(self):
        """Test Qwen analysis topic."""
        assert Topic.VISION_ANALYSIS_QWEN.value == "vision.analysis.qwen"
    
    def test_system_topics(self):
        """Test system topics."""
        assert Topic.SYSTEM_HEARTBEAT.value == "system.heartbeat"
        assert Topic.SYSTEM_ERROR.value == "system.error"
        assert Topic.SYSTEM_METRICS.value == "system.metrics"


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegrationV2:
    """Integration tests for v2 architecture."""
    
    @pytest.mark.asyncio
    async def test_full_flow_v2(self, server_config):
        """Test full publish/subscribe flow."""
        srv = WSSServerV2(server_config)
        server_task = asyncio.create_task(srv.start())
        await asyncio.sleep(0.5)
        
        received_messages = []
        
        try:
            async with ws_connect("ws://localhost:8000") as subscriber:
                # Subscribe to all vision topics
                await subscriber.send(json.dumps({
                    "type": "subscribe",
                    "topics": VisionTopic.ALL_VISION
                }))
                await asyncio.wait_for(subscriber.recv(), timeout=2.0)
                
                await asyncio.sleep(0.1)
                
                # Publish from different sources
                topics_envelopes = [
                    ("vision.detection.yolo", TransportEnvelope(
                        event_type="detection",
                        schema_family=SchemaFamily.DETECTION,
                        source="yolo",
                        payload={"boxes": [{"x": 100, "y": 100, "w": 200, "h": 150}]}
                    )),
                    ("vision.segmentation.sam", TransportEnvelope(
                        event_type="segmentation",
                        schema_family=SchemaFamily.SEGMENTATION,
                        source="sam",
                        payload={"masks": [{"roi_id": "roi_001"}]}
                    )),
                    ("vision.classification.eagle", TransportEnvelope(
                        event_type="classification",
                        schema_family=SchemaFamily.CLASSIFICATION,
                        source="eagle",
                        payload={"label": "order_ticket", "confidence": 0.92}
                    )),
                    ("vision.analysis.qwen", TransportEnvelope(
                        event_type="analysis",
                        schema_family=SchemaFamily.ANALYSIS,
                        source="qwen",
                        payload={"risk_level": "medium", "recommendation": "continue"}
                    )),
                ]
                
                for topic, envelope in topics_envelopes:
                    await srv.publish(envelope, topic)
                
                # Receive all messages
                for _ in range(4):
                    received = await asyncio.wait_for(subscriber.recv(), timeout=2.0)
                    data = json.loads(received)
                    received_messages.append(data)
                
                # Verify all were received
                assert len(received_messages) == 4
                
                sources = {m["source"] for m in received_messages}
                assert sources == {"yolo", "sam", "eagle", "qwen"}
        finally:
            await srv.stop()
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass


# Re-export for use in tests
VisionTopic = None  # Will be imported from actual module

# Need to import here to avoid circular reference
from advanced_vision.wss_agent_subscriber_v2 import VisionTopic
