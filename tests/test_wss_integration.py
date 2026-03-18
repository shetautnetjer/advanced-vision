"""Integration tests for WSS architecture.

Tests cover end-to-end flows:
- YOLO → WSS → Subscriber
- Eagle2 → WSS → Subscriber
- Schema routing (UI vs Trading)
- Logging (text + JSON)

These tests verify the complete pipeline works together.
"""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

import pytest
import pytest_asyncio

# Skip if websockets not available
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
)

# Import trading components for integration
from advanced_vision.trading.events import (
    TradingEvent,
    TradingEventType,
    RiskLevel,
    ActionRecommendation,
    DetectionSource,
    BoundingBox,
)
from advanced_vision.trading.detector import create_detector, DetectorMode


# =============================================================================
# Fixtures
# =============================================================================

@pytest_asyncio.fixture
def temp_log_dir():
    """Create temporary log directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest_asyncio.fixture
async def integration_config(temp_log_dir):
    """Create integration test configuration."""
    return WSSServerConfig(
        host="localhost",
        ports=[8001, 8002, 8003, 8004, 8005],
        log_dir=temp_log_dir,
        log_format="json",
        log_level="INFO",
        heartbeat_interval=300.0,  # Very long for integration tests
    )


@pytest_asyncio.fixture
async def running_server(integration_config):
    """Provide a running WSS server."""
    srv = WSSServer(integration_config)
    server_task = asyncio.create_task(srv.start())
    await asyncio.sleep(0.5)  # Wait for startup
    
    yield srv
    
    await srv.stop()
    server_task.cancel()
    try:
        await server_task
    except asyncio.CancelledError:
        pass


# =============================================================================
# YOLO → WSS → Subscriber Flow
# =============================================================================

class TestYOLOToWSSFlow:
    """Test YOLO detection results flow through WSS to subscribers."""
    
    @pytest.mark.asyncio
    async def test_yolo_detection_published_to_wss(self, running_server):
        """Test YOLO detection results are published to WSS port 8002."""
        # Connect subscriber to detection port
        async with ws_connect("ws://localhost:8002") as subscriber:
            await asyncio.sleep(0.1)
            
            # Simulate YOLO detection result
            detection_msg = DetectionMessage(
                timestamp=datetime.utcnow().isoformat(),
                source="yolo_detector",
                msg_type="detection",
                payload={
                    "frame_id": "frame_001",
                    "inference_time_ms": 12.5,
                    "detections": [
                        {
                            "element_id": "elem_001",
                            "element_type": "chart_panel",
                            "bbox": {"x": 100, "y": 100, "width": 400, "height": 300},
                            "confidence": 0.89,
                        },
                        {
                            "element_id": "elem_002",
                            "element_type": "order_ticket_panel",
                            "bbox": {"x": 600, "y": 150, "width": 250, "height": 400},
                            "confidence": 0.76,
                        },
                    ],
                    "model": "yolov8n",
                    "device": "cuda:0",
                }
            )
            
            # Publish to WSS
            sent = await running_server.publish(8002, detection_msg)
            assert sent >= 1
            
            # Subscriber receives the message
            received_raw = await asyncio.wait_for(subscriber.recv(), timeout=2.0)
            received = json.loads(received_raw)
            
            # Verify structure
            assert received["msg_type"] == "detection"
            assert received["source"] == "yolo_detector"
            assert received["payload"]["frame_id"] == "frame_001"
            assert len(received["payload"]["detections"]) == 2
            
            # Verify detection content
            first_detection = received["payload"]["detections"][0]
            assert first_detection["element_type"] == "chart_panel"
            assert first_detection["confidence"] == 0.89
    
    @pytest.mark.asyncio
    async def test_multiple_yolo_detections_sequence(self, running_server):
        """Test multiple sequential YOLO detections flow through WSS."""
        async with ws_connect("ws://localhost:8002") as subscriber:
            await asyncio.sleep(0.1)
            
            detections_received = []
            
            # Publish multiple detection frames
            for i in range(5):
                msg = DetectionMessage(
                    timestamp=datetime.utcnow().isoformat(),
                    source="yolo_detector",
                    msg_type="detection",
                    payload={
                        "frame_id": f"frame_{i:03d}",
                        "inference_time_ms": 10.0 + i,
                        "detections": [
                            {
                                "element_type": "chart_panel",
                                "confidence": 0.80 + (i * 0.02),
                            }
                        ],
                    }
                )
                await running_server.publish(8002, msg)
            
            # Receive all messages
            for i in range(5):
                received = await asyncio.wait_for(subscriber.recv(), timeout=2.0)
                data = json.loads(received)
                detections_received.append(data)
            
            # Verify sequence
            assert len(detections_received) == 5
            for i, det in enumerate(detections_received):
                assert det["payload"]["frame_id"] == f"frame_{i:03d}"
    
    @pytest.mark.asyncio
    async def test_yolo_with_empty_detections(self, running_server):
        """Test YOLO empty detection results are published correctly."""
        async with ws_connect("ws://localhost:8002") as subscriber:
            await asyncio.sleep(0.1)
            
            msg = DetectionMessage(
                timestamp=datetime.utcnow().isoformat(),
                source="yolo_detector",
                msg_type="detection",
                payload={
                    "frame_id": "frame_empty",
                    "inference_time_ms": 8.0,
                    "detections": [],
                    "model": "yolov8n",
                }
            )
            
            await running_server.publish(8002, msg)
            
            received = await asyncio.wait_for(subscriber.recv(), timeout=2.0)
            data = json.loads(received)
            
            assert data["payload"]["detections"] == []
            assert data["payload"]["frame_id"] == "frame_empty"


# =============================================================================
# Eagle2 → WSS → Subscriber Flow
# =============================================================================

class TestEagleToWSSFlow:
    """Test Eagle2 classification results flow through WSS to subscribers."""
    
    @pytest.mark.asyncio
    async def test_eagle_classification_published(self, running_server):
        """Test Eagle2 classification results are published to WSS port 8004."""
        async with ws_connect("ws://localhost:8004") as subscriber:
            await asyncio.sleep(0.1)
            
            # Simulate Eagle2 classification result
            classification_msg = ClassificationMessage(
                timestamp=datetime.utcnow().isoformat(),
                source="eagle2_scout",
                msg_type="classification",
                payload={
                    "frame_id": "frame_042",
                    "event_type": "CHART_UPDATE",
                    "confidence": 0.94,
                    "is_trading_relevant": True,
                    "inference_time_ms": 320,
                    "model": "eagle2-2b",
                    "raw_output": "Trading relevant: Chart showing price movement",
                }
            )
            
            await running_server.publish(8004, classification_msg)
            
            received = await asyncio.wait_for(subscriber.recv(), timeout=2.0)
            data = json.loads(received)
            
            assert data["msg_type"] == "classification"
            assert data["source"] == "eagle2_scout"
            assert data["payload"]["is_trading_relevant"] is True
            assert data["payload"]["event_type"] == "CHART_UPDATE"
    
    @pytest.mark.asyncio
    async def test_eagle_noise_classification(self, running_server):
        """Test Eagle2 noise classification is published correctly."""
        async with ws_connect("ws://localhost:8004") as subscriber:
            await asyncio.sleep(0.1)
            
            msg = ClassificationMessage(
                timestamp=datetime.utcnow().isoformat(),
                source="eagle2_scout",
                msg_type="classification",
                payload={
                    "frame_id": "frame_043",
                    "event_type": "NOISE",
                    "confidence": 0.88,
                    "is_trading_relevant": False,
                    "inference_time_ms": 280,
                    "model": "eagle2-2b",
                }
            )
            
            await running_server.publish(8004, msg)
            
            received = await asyncio.wait_for(subscriber.recv(), timeout=2.0)
            data = json.loads(received)
            
            assert data["payload"]["is_trading_relevant"] is False
            assert data["payload"]["event_type"] == "NOISE"
    
    @pytest.mark.asyncio
    async def test_eagle_high_confidence_alert(self, running_server):
        """Test Eagle2 high-confidence alert classification."""
        async with ws_connect("ws://localhost:8004") as subscriber:
            await asyncio.sleep(0.1)
            
            msg = ClassificationMessage(
                timestamp=datetime.utcnow().isoformat(),
                source="eagle2_scout",
                msg_type="classification",
                payload={
                    "frame_id": "frame_044",
                    "event_type": "WARNING_DIALOG",
                    "confidence": 0.97,
                    "is_trading_relevant": True,
                    "requires_reviewer": True,
                    "inference_time_ms": 350,
                    "model": "eagle2-2b",
                }
            )
            
            await running_server.publish(8004, msg)
            
            received = await asyncio.wait_for(subscriber.recv(), timeout=2.0)
            data = json.loads(received)
            
            assert data["payload"]["requires_reviewer"] is True
            assert data["payload"]["confidence"] > 0.95


# =============================================================================
# Schema Routing Tests (UI vs Trading)
# =============================================================================

class TestSchemaRouting:
    """Test schema-based message routing between UI and Trading ports."""
    
    @pytest.mark.asyncio
    async def test_ui_updates_routed_to_port_8001(self, running_server):
        """Test UI update messages are routed to port 8001."""
        async with ws_connect("ws://localhost:8001") as ui_subscriber:
            await asyncio.sleep(0.1)
            
            # UI update
            ui_msg = UIUpdateMessage(
                timestamp=datetime.utcnow().isoformat(),
                source="display_manager",
                msg_type="ui_update",
                payload={
                    "update_type": "screenshot_preview",
                    "data": {
                        "thumbnail_path": "/tmp/preview_001.jpg",
                        "resolution": "320x180",
                    }
                }
            )
            
            # Publish via routing
            sent = await running_server.publish_by_type("ui_update", ui_msg)
            assert sent >= 1
            
            # UI subscriber receives
            received = await asyncio.wait_for(ui_subscriber.recv(), timeout=2.0)
            data = json.loads(received)
            
            assert data["msg_type"] == "ui_update"
            assert data["payload"]["update_type"] == "screenshot_preview"
    
    @pytest.mark.asyncio
    async def test_trading_signals_routed_to_port_8005(self, running_server):
        """Test trading signal messages are routed to port 8005."""
        async with ws_connect("ws://localhost:8005") as trading_subscriber:
            await asyncio.sleep(0.1)
            
            # Trading signal
            signal_msg = TradingSignalMessage(
                timestamp=datetime.utcnow().isoformat(),
                source="qwen_reviewer",
                msg_type="trading_signal",
                payload={
                    "frame_id": "frame_100",
                    "signal_type": "PAUSE",
                    "risk_level": "HIGH",
                    "recommendation": "HOLD",
                    "confidence": 0.82,
                    "reasoning": "Warning dialog detected on order confirmation",
                    "action_required": True,
                }
            )
            
            # Publish via routing
            sent = await running_server.publish_by_type("trading_signal", signal_msg)
            assert sent >= 1
            
            # Trading subscriber receives
            received = await asyncio.wait_for(trading_subscriber.recv(), timeout=2.0)
            data = json.loads(received)
            
            assert data["msg_type"] == "trading_signal"
            assert data["payload"]["risk_level"] == "HIGH"
            assert data["payload"]["action_required"] is True
    
    @pytest.mark.asyncio
    async def test_messages_not_crossing_ports(self, running_server):
        """Test messages don't leak between different port subscribers."""
        async with ws_connect("ws://localhost:8001") as ui_sub:
            async with ws_connect("ws://localhost:8005") as trading_sub:
                await asyncio.sleep(0.1)
                
                # Send UI message
                ui_msg = UIUpdateMessage(
                    timestamp=datetime.utcnow().isoformat(),
                    source="display",
                    msg_type="ui_update",
                    payload={"data": "ui_data"}
                )
                await running_server.publish_by_type("ui_update", ui_msg)
                
                # UI subscriber gets it
                ui_received = await asyncio.wait_for(ui_sub.recv(), timeout=2.0)
                ui_data = json.loads(ui_received)
                assert ui_data["msg_type"] == "ui_update"
                
                # Trading subscriber should not receive UI message
                # (but we need to check if anything arrives with timeout)
                try:
                    trading_data = await asyncio.wait_for(trading_sub.recv(), timeout=0.5)
                    # If we get here, something crossed ports - that's bad
                    assert False, "Message crossed port boundary!"
                except asyncio.TimeoutError:
                    pass  # Expected - no message should arrive
    
    @pytest.mark.asyncio
    async def test_system_events_routed_to_port_8003(self, running_server):
        """Test system events are routed to port 8003."""
        async with ws_connect("ws://localhost:8003") as system_subscriber:
            await asyncio.sleep(0.1)
            
            # System event
            sys_msg = SystemEventMessage(
                timestamp=datetime.utcnow().isoformat(),
                source="system_monitor",
                msg_type="system_event",
                payload={
                    "event_type": "resource_warning",
                    "status": "warning",
                    "details": {
                        "vram_usage_gb": 14.2,
                        "vram_total_gb": 16.0,
                        "warning_threshold": 0.85,
                    }
                }
            )
            
            await running_server.publish_by_type("system_event", sys_msg)
            
            received = await asyncio.wait_for(system_subscriber.recv(), timeout=2.0)
            data = json.loads(received)
            
            assert data["msg_type"] == "system_event"
            assert data["payload"]["event_type"] == "resource_warning"


# =============================================================================
# Logging Integration Tests
# =============================================================================

class TestLoggingIntegration:
    """Test logging works correctly for all message types."""
    
    @pytest.mark.asyncio
    async def test_json_logging_format(self, integration_config, running_server):
        """Test JSON logs are written correctly."""
        # Publish a message
        msg = DetectionMessage(
            timestamp=datetime.utcnow().isoformat(),
            source="test",
            msg_type="detection",
            payload={"test": "data"}
        )
        await running_server.publish(8002, msg)
        
        # Give logger time to write
        await asyncio.sleep(0.1)
        
        # Check log file
        log_file = integration_config.log_dir / "port_8002.json.log"
        assert log_file.exists()
        
        content = log_file.read_text().strip()
        assert content
        
        # Parse JSON line
        log_entry = json.loads(content.split('\n')[0])
        assert log_entry["msg_type"] == "detection"
        assert log_entry["source"] == "test"
    
    @pytest.mark.asyncio
    async def test_all_ports_logged(self, integration_config, running_server):
        """Test all ports have log files created."""
        # Publish to all ports
        for port in [8001, 8002, 8003, 8004, 8005]:
            msg = WSSMessage(
                timestamp=datetime.utcnow().isoformat(),
                source="test",
                msg_type="test",
                payload={"port": port}
            )
            await running_server.publish(port, msg)
        
        await asyncio.sleep(0.1)
        
        # Check all log files exist
        for port in [8001, 8002, 8003, 8004, 8005]:
            log_file = integration_config.log_dir / f"port_{port}.json.log"
            assert log_file.exists(), f"Log file for port {port} not found"
    
    @pytest.mark.asyncio
    async def test_log_file_content_integrity(self, integration_config, running_server):
        """Test log file content is valid JSON with expected fields."""
        # Publish multiple messages
        for i in range(3):
            msg = TradingSignalMessage(
                timestamp=datetime.utcnow().isoformat(),
                source="trading_system",
                msg_type="trading_signal",
                payload={
                    "signal_id": f"sig_{i}",
                    "risk_level": "MEDIUM",
                }
            )
            await running_server.publish(8005, msg)
        
        await asyncio.sleep(0.1)
        
        # Verify log file
        log_file = integration_config.log_dir / "port_8005.json.log"
        content = log_file.read_text().strip()
        lines = content.split('\n')
        
        assert len(lines) == 3
        
        for i, line in enumerate(lines):
            entry = json.loads(line)
            assert entry["msg_type"] == "trading_signal"
            assert entry["source"] == "trading_system"
            assert entry["payload"]["signal_id"] == f"sig_{i}"
            assert "timestamp" in entry
            assert "schema_version" in entry


# =============================================================================
# End-to-End Pipeline Tests
# =============================================================================

class TestEndToEndPipeline:
    """Test complete pipeline flows."""
    
    @pytest.mark.asyncio
    async def test_full_detection_to_trading_flow(self, running_server):
        """Test full flow: Detection → Classification → Trading Signal."""
        
        # Subscribe to all relevant ports
        async with ws_connect("ws://localhost:8002") as detection_sub:
            async with ws_connect("ws://localhost:8004") as class_sub:
                async with ws_connect("ws://localhost:8005") as trading_sub:
                    await asyncio.sleep(0.1)
                    
                    # 1. YOLO Detection
                    detection_msg = DetectionMessage(
                        timestamp=datetime.utcnow().isoformat(),
                        source="yolo_detector",
                        msg_type="detection",
                        payload={
                            "frame_id": "e2e_001",
                            "detections": [
                                {"element_type": "warning_modal", "confidence": 0.91}
                            ],
                        }
                    )
                    await running_server.publish(8002, detection_msg)
                    
                    # 2. Eagle2 Classification
                    class_msg = ClassificationMessage(
                        timestamp=datetime.utcnow().isoformat(),
                        source="eagle2_scout",
                        msg_type="classification",
                        payload={
                            "frame_id": "e2e_001",
                            "event_type": "WARNING_DIALOG",
                            "is_trading_relevant": True,
                            "requires_reviewer": True,
                        }
                    )
                    await running_server.publish(8004, class_msg)
                    
                    # 3. Trading Signal
                    trading_msg = TradingSignalMessage(
                        timestamp=datetime.utcnow().isoformat(),
                        source="qwen_reviewer",
                        msg_type="trading_signal",
                        payload={
                            "frame_id": "e2e_001",
                            "signal_type": "HOLD",
                            "risk_level": "HIGH",
                            "recommendation": "PAUSE",
                        }
                    )
                    await running_server.publish(8005, trading_msg)
                    
                    # Collect all messages
                    detection_recv = await asyncio.wait_for(detection_sub.recv(), timeout=2.0)
                    class_recv = await asyncio.wait_for(class_sub.recv(), timeout=2.0)
                    trading_recv = await asyncio.wait_for(trading_sub.recv(), timeout=2.0)
                    
                    # Verify flow
                    det_data = json.loads(detection_recv)
                    class_data = json.loads(class_recv)
                    trade_data = json.loads(trading_recv)
                    
                    # All should reference same frame
                    assert det_data["payload"]["frame_id"] == "e2e_001"
                    assert class_data["payload"]["frame_id"] == "e2e_001"
                    assert trade_data["payload"]["frame_id"] == "e2e_001"
                    
                    # Verify progression
                    assert det_data["msg_type"] == "detection"
                    assert class_data["msg_type"] == "classification"
                    assert trade_data["msg_type"] == "trading_signal"
    
    @pytest.mark.asyncio
    async def test_multiple_subscribers_same_channel(self, running_server):
        """Test multiple subscribers can receive same trading signals."""
        
        # Connect multiple trading subscribers
        subscribers = []
        for _ in range(3):
            sub = await ws_connect("ws://localhost:8005")
            subscribers.append(sub)
        
        await asyncio.sleep(0.1)
        
        try:
            # Send one trading signal
            msg = TradingSignalMessage(
                timestamp=datetime.utcnow().isoformat(),
                source="reviewer",
                msg_type="trading_signal",
                payload={
                    "signal_type": "BUY",
                    "confidence": 0.88,
                }
            )
            sent = await running_server.publish(8005, msg)
            assert sent == 3
            
            # All subscribers should receive
            for sub in subscribers:
                received = await asyncio.wait_for(sub.recv(), timeout=2.0)
                data = json.loads(received)
                assert data["payload"]["signal_type"] == "BUY"
        finally:
            for sub in subscribers:
                await sub.close()


# =============================================================================
# Trading Integration Tests (with real trading components)
# =============================================================================

class TestTradingComponentIntegration:
    """Test integration with trading event components."""
    
    @pytest.mark.asyncio
    async def test_trading_event_serialization(self, running_server):
        """Test TradingEvent objects can be serialized and sent via WSS."""
        async with ws_connect("ws://localhost:8004") as subscriber:
            await asyncio.sleep(0.1)
            
            # Create a TradingEvent
            event = TradingEvent(
                event_id="evt_001",
                timestamp=datetime.utcnow().isoformat(),
                event_type=TradingEventType.WARNING_DIALOG,
                source=DetectionSource.TRIPWIRE,
                confidence=0.89,
                screen_width=1920,
                screen_height=1080,
                triggering_bbox=BoundingBox(x=400, y=300, width=500, height=400),
                summary="Warning dialog detected during order placement",
            )
            
            # Serialize and send as classification
            msg = ClassificationMessage(
                timestamp=event.timestamp,
                source="trading_pipeline",
                msg_type="classification",
                payload={
                    "event_id": event.event_id,
                    "event_type": event.event_type.value,
                    "confidence": event.confidence,
                    "source": event.source.value,
                    "bbox": event.triggering_bbox.model_dump() if event.triggering_bbox else None,
                    "summary": event.summary,
                }
            )
            
            await running_server.publish(8004, msg)
            
            received = await asyncio.wait_for(subscriber.recv(), timeout=2.0)
            data = json.loads(received)
            
            assert data["payload"]["event_id"] == "evt_001"
            assert data["payload"]["event_type"] == "warning_dialog"
            assert data["payload"]["source"] == "tripwire"
    
    def test_trading_event_types_available(self):
        """Test all trading event types are defined and usable."""
        # Verify event types exist
        assert TradingEventType.WARNING_DIALOG.value == "warning_dialog"
        assert TradingEventType.ERROR_DIALOG.value == "error_dialog"
        assert TradingEventType.CHART_UPDATE.value == "chart_update"
        assert TradingEventType.ORDER_TICKET.value == "order_ticket"
        
        # Verify risk levels
        assert RiskLevel.HIGH.value == "high"
        assert RiskLevel.CRITICAL.value == "critical"
        
        # Verify recommendations
        assert ActionRecommendation.HOLD.value == "hold"
        assert ActionRecommendation.PAUSE.value == "pause"


# =============================================================================
# Performance/Latency Tests
# =============================================================================

class TestPerformance:
    """Test performance characteristics."""
    
    @pytest.mark.asyncio
    async def test_message_latency(self, running_server):
        """Test message latency is within acceptable bounds."""
        async with ws_connect("ws://localhost:8002") as subscriber:
            await asyncio.sleep(0.1)
            
            latencies = []
            
            for _ in range(10):
                start_time = asyncio.get_event_loop().time()
                
                msg = DetectionMessage(
                    timestamp=datetime.utcnow().isoformat(),
                    source="perf_test",
                    msg_type="detection",
                    payload={"test": "data"}
                )
                
                await running_server.publish(8002, msg)
                
                # Wait for receipt
                await asyncio.wait_for(subscriber.recv(), timeout=2.0)
                
                end_time = asyncio.get_event_loop().time()
                latency = (end_time - start_time) * 1000  # ms
                latencies.append(latency)
            
            avg_latency = sum(latencies) / len(latencies)
            max_latency = max(latencies)
            
            # Should be under 100ms average, 200ms max
            assert avg_latency < 100, f"Average latency {avg_latency}ms too high"
            assert max_latency < 200, f"Max latency {max_latency}ms too high"
    
    @pytest.mark.asyncio
    async def test_high_frequency_messages(self, running_server):
        """Test server handles high-frequency message publishing."""
        async with ws_connect("ws://localhost:8001") as subscriber:
            await asyncio.sleep(0.1)
            
            # Send 100 messages rapidly
            for i in range(100):
                msg = UIUpdateMessage(
                    timestamp=datetime.utcnow().isoformat(),
                    source="stress_test",
                    msg_type="ui_update",
                    payload={"seq": i}
                )
                await running_server.publish(8001, msg)
            
            # Receive all messages
            received_count = 0
            try:
                while received_count < 100:
                    await asyncio.wait_for(subscriber.recv(), timeout=5.0)
                    received_count += 1
            except asyncio.TimeoutError:
                pass
            
            # Should receive at least 95% of messages
            assert received_count >= 95, f"Only received {received_count}/100 messages"