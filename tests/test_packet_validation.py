"""Tests for packet validation layer.

Tests valid/invalid packets for all 7 schemas:
- event_envelope
- ui_packet
- trading_packet
- scout_event
- external_review_request
- external_review_result
- artifact_manifest
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest

from advanced_vision.core import PacketValidator, PacketValidationError, TruthWriter


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def validator():
    """Provide a PacketValidator instance."""
    return PacketValidator()


@pytest.fixture
def truth_dir():
    """Provide a temporary truth directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def writer(truth_dir):
    """Provide a TruthWriter instance."""
    return TruthWriter(truth_dir)


# ============================================================================
# Valid Packet Examples
# ============================================================================

def make_valid_event_envelope():
    """Create a valid event envelope."""
    return {
        "event_id": str(uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "capture",
        "mode": "ui",
        "schema_version": "1.0.0",
        "payload": {"key": "value"},
        "payload_type": "ui_packet",
        "trace_id": str(uuid4()),
        "parent_event_id": str(uuid4()),
        "artifact_refs": [
            {
                "type": "frame",
                "path": "frames/001.png",
                "checksum": "a" * 64
            }
        ],
        "work_item_id": "work-123",
        "metadata": {"latency_ms": 100}
    }


def make_valid_ui_packet():
    """Create a valid UI packet."""
    return {
        "packet_id": str(uuid4()),
        "mode": "ui",
        "event_type": "ui_change",
        "summary": "Login form appeared",
        "frame_ref": "frames/screenshot_001.png",
        "previous_frame_ref": "frames/screenshot_000.png",
        "roi_refs": [
            {
                "id": "roi-1",
                "path": "rois/login_form.png",
                "bbox": [100, 200, 300, 400],
                "label": "modal",
                "confidence": 0.95
            }
        ],
        "targets": [
            {
                "id": "btn-login",
                "bbox": [150, 250, 100, 50],
                "label": "button",
                "confidence": 0.98,
                "click_point": [200, 275],
                "text_content": "Login"
            }
        ],
        "scout_note": "Login modal detected on screen",
        "risk_tags": ["requires_confirmation"],
        "needs_local_review": True,
        "needs_external_review": True,
        "latency_ms": {
            "capture_to_packet": 50,
            "scout_inference": 100,
            "total_pipeline": 150
        }
    }


def make_valid_trading_packet():
    """Create a valid trading packet."""
    return {
        "packet_id": str(uuid4()),
        "mode": "trading",
        "event_type": "price_movement",
        "summary": "EURUSD broke resistance at 1.0850",
        "frame_ref": "charts/eurusd_001.png",
        "previous_frame_ref": "charts/eurusd_000.png",
        "chart_regions": [
            {
                "id": "chart-1",
                "path": "rois/chart_main.png",
                "bbox": [0, 0, 1920, 1080],
                "instrument": "EURUSD",
                "timeframe": "M15",
                "price_snapshot": {
                    "bid": 1.0851,
                    "ask": 1.0853,
                    "spread_pips": 0.2
                }
            }
        ],
        "ticket_regions": [
            {
                "id": "ticket-1",
                "path": "rois/ticket.png",
                "bbox": [500, 500, 400, 300],
                "ticket_type": "market_order",
                "extracted_fields": {"volume": 0.1}
            }
        ],
        "indicators": [
            {
                "name": "RSI",
                "signal": "buy",
                "confidence": 0.75,
                "location": "bottom_panel"
            }
        ],
        "scout_note": "Strong bullish momentum detected",
        "risk_tags": ["high_volatility", "news_event"],
        "risk_level": "medium",
        "needs_local_review": True,
        "needs_external_review": True,
        "suggested_action": "review_details"
    }


def make_valid_scout_event():
    """Create a valid scout event."""
    return {
        "event_id": str(uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "scout_version": "eagle2-2b-v1.0",
        "inference_time_ms": 45,
        "classification": "meaningful_ui_change",
        "confidence": 0.92,
        "roi_count": 3,
        "motion_metrics": {
            "cursor_only": False,
            "motion_pixels": 15000,
            "motion_percentage": 7.5
        },
        "escalation_recommended": True,
        "escalation_reason": "high_confidence_change",
        "artifact_refs": {
            "input_frame": "frames/input_001.png",
            "output_rois": ["rois/roi_001.png", "rois/roi_002.png"]
        }
    }


def make_valid_external_review_request():
    """Create a valid external review request."""
    return {
        "request_id": str(uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "reviewer_target": {
            "agent_identity": "aya",
            "provider": "openclaw",
            "model": "kimi"
        },
        "packet_ref": "packets/ui_001.json",
        "packet_type": "ui_packet",
        "context": {
            "mode": "ui",
            "summary": "Modal dialog needs review",
            "image_refs": [
                {
                    "type": "full_frame",
                    "path": "frames/full.png",
                    "description": "Full screenshot"
                }
            ],
            "recent_history": [
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "event_type": "click",
                    "summary": "Clicked login button"
                }
            ],
            "scout_note": "Unexpected modal appeared",
            "risk_tags": ["requires_confirmation"]
        },
        "decision_options": ["continue", "click", "wait", "block"],
        "timeout_seconds": 30
    }


def make_valid_external_review_result():
    """Create a valid external review result."""
    return {
        "result_id": str(uuid4()),
        "request_id": str(uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "reviewer": {
            "agent_identity": "aya",
            "provider": "openclaw",
            "model": "kimi",
            "model_version": "k2.5"
        },
        "decision": "click",
        "reasoning": "This is a legitimate login dialog. Click the Login button.",
        "action_payload": {
            "click_target": {
                "target_id": "btn-login",
                "coordinates": [200, 275]
            }
        },
        "confidence": 0.95,
        "risk_assessment": {
            "risk_level": "low",
            "concerns": []
        },
        "latency_ms": 1200
    }


def make_valid_artifact_manifest():
    """Create a valid artifact manifest."""
    return {
        "manifest_id": str(uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "artifact_type": "frame",
        "path": "frames/screenshot_001.png",
        "checksum": "a" * 64,
        "size_bytes": 1024000,
        "related_event_id": str(uuid4()),
        "trace_id": str(uuid4()),
        "metadata": {
            "frame": {
                "width": 1920,
                "height": 1080,
                "format": "png"
            }
        },
        "retention_policy": "long_term",
        "access_log": [
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "accessor": "scout",
                "purpose": "inference"
            }
        ]
    }


# ============================================================================
# Schema Tests - Valid Packets
# ============================================================================

class TestValidPackets:
    """Test that valid packets pass validation."""
    
    def test_event_envelope_valid(self, validator):
        """Valid event envelope should pass."""
        packet = make_valid_event_envelope()
        assert validator.validate(packet, "event_envelope") is True
    
    def test_ui_packet_valid(self, validator):
        """Valid UI packet should pass."""
        packet = make_valid_ui_packet()
        assert validator.validate(packet, "ui_packet") is True
    
    def test_trading_packet_valid(self, validator):
        """Valid trading packet should pass."""
        packet = make_valid_trading_packet()
        assert validator.validate(packet, "trading_packet") is True
    
    def test_scout_event_valid(self, validator):
        """Valid scout event should pass."""
        packet = make_valid_scout_event()
        assert validator.validate(packet, "scout_event") is True
    
    def test_external_review_request_valid(self, validator):
        """Valid external review request should pass."""
        packet = make_valid_external_review_request()
        assert validator.validate(packet, "external_review_request") is True
    
    def test_external_review_result_valid(self, validator):
        """Valid external review result should pass."""
        packet = make_valid_external_review_result()
        assert validator.validate(packet, "external_review_result") is True
    
    def test_artifact_manifest_valid(self, validator):
        """Valid artifact manifest should pass."""
        packet = make_valid_artifact_manifest()
        assert validator.validate(packet, "artifact_manifest") is True


# ============================================================================
# Schema Tests - Invalid Packets
# ============================================================================

class TestInvalidPackets:
    """Test that invalid packets fail with clear errors."""
    
    def test_event_envelope_missing_required(self, validator):
        """Event envelope missing required fields should fail."""
        packet = {"event_id": str(uuid4())}  # Missing most required fields
        assert validator.validate(packet, "event_envelope") is False
        
        errors = validator.get_validation_errors(packet, "event_envelope")
        assert len(errors) > 0
        assert any("timestamp" in str(e) or "source" in str(e) for e in errors)
    
    def test_event_envelope_invalid_source(self, validator):
        """Event envelope with invalid source enum should fail."""
        packet = make_valid_event_envelope()
        packet["source"] = "invalid_source"
        assert validator.validate(packet, "event_envelope") is False
        
        errors = validator.get_validation_errors(packet, "event_envelope")
        assert any("source" in e["message"] for e in errors)
    
    def test_event_envelope_invalid_mode(self, validator):
        """Event envelope with invalid mode enum should fail."""
        packet = make_valid_event_envelope()
        packet["mode"] = "invalid_mode"
        assert validator.validate(packet, "event_envelope") is False
    
    def test_ui_packet_wrong_mode(self, validator):
        """UI packet with wrong mode should fail."""
        packet = make_valid_ui_packet()
        packet["mode"] = "trading"  # Must be 'ui'
        assert validator.validate(packet, "ui_packet") is False
    
    def test_ui_packet_invalid_event_type(self, validator):
        """UI packet with invalid event_type should fail."""
        packet = make_valid_ui_packet()
        packet["event_type"] = "invalid_type"
        assert validator.validate(packet, "ui_packet") is False
    
    def test_ui_packet_missing_required(self, validator):
        """UI packet missing required fields should fail."""
        packet = {"mode": "ui"}  # Missing packet_id, event_type, etc.
        assert validator.validate(packet, "ui_packet") is False
        
        errors = validator.get_validation_errors(packet, "ui_packet")
        assert len(errors) > 0
    
    def test_ui_packet_invalid_bbox(self, validator):
        """UI packet with invalid bbox should fail."""
        packet = make_valid_ui_packet()
        packet["roi_refs"][0]["bbox"] = [1, 2, 3]  # Need 4 items
        assert validator.validate(packet, "ui_packet") is False
    
    def test_trading_packet_wrong_mode(self, validator):
        """Trading packet with wrong mode should fail."""
        packet = make_valid_trading_packet()
        packet["mode"] = "ui"  # Must be 'trading'
        assert validator.validate(packet, "trading_packet") is False
    
    def test_trading_packet_invalid_risk_level(self, validator):
        """Trading packet with invalid risk_level should fail."""
        packet = make_valid_trading_packet()
        packet["risk_level"] = "extreme"  # Not in enum
        assert validator.validate(packet, "trading_packet") is False
    
    def test_scout_event_invalid_classification(self, validator):
        """Scout event with invalid classification should fail."""
        packet = make_valid_scout_event()
        packet["classification"] = "unknown_classification"
        assert validator.validate(packet, "scout_event") is False
    
    def test_scout_event_invalid_confidence_range(self, validator):
        """Scout event with confidence > 1 should fail."""
        packet = make_valid_scout_event()
        packet["confidence"] = 1.5
        assert validator.validate(packet, "scout_event") is False
    
    def test_review_request_invalid_mode(self, validator):
        """Review request with invalid context mode should fail."""
        packet = make_valid_external_review_request()
        packet["context"]["mode"] = "invalid"
        assert validator.validate(packet, "external_review_request") is False
    
    def test_review_result_invalid_decision(self, validator):
        """Review result with invalid decision should fail."""
        packet = make_valid_external_review_result()
        packet["decision"] = "invalid_decision"
        assert validator.validate(packet, "external_review_result") is False
    
    def test_artifact_manifest_invalid_type(self, validator):
        """Artifact manifest with invalid type should fail."""
        packet = make_valid_artifact_manifest()
        packet["artifact_type"] = "invalid_type"
        assert validator.validate(packet, "artifact_manifest") is False
    
    def test_artifact_manifest_invalid_checksum(self, validator):
        """Artifact manifest with non-hex checksum should fail."""
        packet = make_valid_artifact_manifest()
        packet["checksum"] = "not_a_valid_checksum"
        assert validator.validate(packet, "artifact_manifest") is False


# ============================================================================
# Validation Error Reporting Tests
# ============================================================================

class TestErrorReporting:
    """Test that validation errors are clear and detailed."""
    
    def test_validation_error_structure(self, validator):
        """Errors should have message, path, schema_path, validator fields."""
        packet = {"mode": "ui"}  # Missing required fields
        errors = validator.get_validation_errors(packet, "ui_packet")
        
        assert len(errors) > 0
        for error in errors:
            assert "message" in error
            assert "path" in error
            assert "schema_path" in error
            assert "validator" in error
    
    def test_validation_or_raise(self, validator):
        """validate_or_raise should raise PacketValidationError."""
        packet = {"mode": "ui"}  # Invalid
        
        with pytest.raises(PacketValidationError) as exc_info:
            validator.validate_or_raise(packet, "ui_packet")
        
        assert exc_info.value.schema_name == "ui_packet"
        assert len(exc_info.value.errors) > 0
    
    def test_multiple_errors_reported(self, validator):
        """Multiple validation errors should all be reported."""
        packet = {}  # Completely empty
        errors = validator.get_validation_errors(packet, "ui_packet")
        
        # Should report multiple missing required fields
        assert len(errors) >= 3  # packet_id, mode, event_type, etc.


# ============================================================================
# Fast Path Tests
# ============================================================================

class TestFastPath:
    """Test AV_SKIP_VALIDATION fast path."""
    
    def test_skip_validation_env_var(self, truth_dir, monkeypatch):
        """Setting AV_SKIP_VALIDATION=1 should skip validation."""
        monkeypatch.setenv("AV_SKIP_VALIDATION", "1")
        validator = PacketValidator()
        
        assert validator.is_validation_enabled() is False
        # Even invalid packets should pass
        assert validator.validate({"invalid": "data"}, "ui_packet") is True
    
    def test_validation_enabled_by_default(self):
        """Validation should be enabled by default."""
        validator = PacketValidator()
        assert validator.is_validation_enabled() is True


# ============================================================================
# Truth Writer Tests
# ============================================================================

class TestTruthWriter:
    """Test TruthWriter functionality."""
    
    def test_write_event_creates_file(self, writer, truth_dir):
        """Writing an event should create the daily log file."""
        event = {"event_id": "test-1", "data": "value"}
        log_file = writer.write_event(event)
        
        assert log_file.exists()
        assert log_file.parent == truth_dir / "events"
    
    def test_write_event_adds_ingestion_timestamp(self, writer, truth_dir):
        """write_event should add ingestion_timestamp if not present."""
        event = {"event_id": "test-1"}
        writer.write_event(event)
        
        events = writer.get_events_for_date(datetime.now())
        assert len(events) == 1
        assert "ingestion_timestamp" in events[0]
    
    def test_write_event_preserves_existing_ingestion_timestamp(self, writer, truth_dir):
        """write_event should not overwrite existing ingestion_timestamp."""
        custom_ts = "2024-01-01T00:00:00+00:00"
        event = {"event_id": "test-1", "ingestion_timestamp": custom_ts}
        writer.write_event(event)
        
        events = writer.get_events_for_date(datetime.now())
        assert events[0]["ingestion_timestamp"] == custom_ts
    
    def test_write_artifact_creates_manifest(self, writer, truth_dir):
        """Writing an artifact should add to manifest."""
        manifest = {
            "artifact_type": "frame",
            "path": "frames/test.png"
        }
        manifest_path = writer.write_artifact(manifest)
        
        assert manifest_path.exists()
        
        manifests = writer.get_all_manifests()
        assert len(manifests) == 1
        assert manifests[0]["artifact_type"] == "frame"
    
    def test_write_artifact_generates_ids(self, writer, truth_dir):
        """write_artifact should generate manifest_id and timestamp if missing."""
        manifest = {"artifact_type": "frame", "path": "test.png"}
        writer.write_artifact(manifest)
        
        manifests = writer.get_all_manifests()
        assert "manifest_id" in manifests[0]
        assert "timestamp" in manifests[0]
    
    def test_atomic_write_artifact(self, writer, truth_dir):
        """write_artifact_atomic should write file and manifest."""
        manifest = {"artifact_type": "frame"}
        artifact_path, manifest_path = writer.write_artifact_atomic(
            manifest,
            b"fake image data",
            "frames/test.png"
        )
        
        assert artifact_path.exists()
        assert (truth_dir / "frames" / "test.png").exists()
        
        manifests = writer.get_all_manifests()
        assert len(manifests) == 1
        assert manifests[0]["path"] == "frames/test.png"
    
    def test_get_events_by_date(self, writer, truth_dir):
        """get_events_for_date should return events for specific date."""
        event1 = {"event_id": "test-1"}
        writer.write_event(event1)
        
        today = datetime.now().strftime("%Y-%m-%d")
        events = writer.get_events_for_date(today)
        assert len(events) == 1
        
        # Non-existent date
        events = writer.get_events_for_date("1999-01-01")
        assert len(events) == 0
    
    def test_multiple_events_append(self, writer, truth_dir):
        """Multiple events should be appended to same file."""
        for i in range(5):
            writer.write_event({"event_id": f"test-{i}"})
        
        events = writer.get_events_for_date(datetime.now())
        assert len(events) == 5
        
        # Verify order preserved
        event_ids = [e["event_id"] for e in events]
        assert event_ids == [f"test-{i}" for i in range(5)]


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests showing the truth-first pattern."""
    
    def test_truth_first_pattern(self, validator, writer):
        """Demonstrate the truth-first, then validate, then fanout pattern."""
        # 1. Create a valid UI packet
        packet = make_valid_ui_packet()
        
        # 2. Create corresponding event envelope
        event = make_valid_event_envelope()
        event["payload"] = packet
        event["payload_type"] = "ui_packet"
        
        # 3. TRUTH-FIRST: Write event before any validation/fanout
        writer.write_event(event)
        
        # 4. Validate the packet
        is_valid = validator.validate(packet, "ui_packet")
        assert is_valid is True
        
        # 5. Only then would we fan out (simulated)
        # wss_publisher.publish(packet)
        
        # Verify event was written
        events = writer.get_events_for_date(datetime.now())
        assert len(events) == 1
        assert events[0]["payload_type"] == "ui_packet"
    
    def test_invalid_packet_still_logged(self, validator, writer):
        """Invalid packets should still be logged to truth before rejection."""
        packet = make_valid_ui_packet()
        packet["mode"] = "invalid"  # Make it invalid
        
        # Log first (truth-first)
        event = make_valid_event_envelope()
        event["payload"] = packet
        event["payload_type"] = "ui_packet"
        writer.write_event(event)
        
        # Then validate (should fail)
        is_valid = validator.validate(packet, "ui_packet")
        assert is_valid is False
        
        # But event was still logged
        events = writer.get_events_for_date(datetime.now())
        assert len(events) == 1


# ============================================================================
# Schema Loading Tests
# ============================================================================

class TestSchemaLoading:
    """Test schema loading functionality."""
    
    def test_all_schemas_loaded(self, validator):
        """All 7 schemas should be loaded."""
        schemas = validator.list_schemas()
        expected = [
            "event_envelope",
            "ui_packet",
            "trading_packet",
            "scout_event",
            "external_review_request",
            "external_review_result",
            "artifact_manifest",
        ]
        assert set(schemas) == set(expected)
    
    def test_unknown_schema_returns_false(self, validator):
        """Validating against unknown schema should return False."""
        assert validator.validate({"test": "data"}, "unknown_schema") is False
    
    def test_unknown_schema_raises_on_validate_or_raise(self, validator):
        """validate_or_raise with unknown schema should raise ValueError."""
        with pytest.raises(ValueError, match="Unknown schema"):
            validator.validate_or_raise({"test": "data"}, "unknown_schema")


# ============================================================================
# Edge Cases
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_empty_packet(self, validator):
        """Empty packet should fail validation."""
        assert validator.validate({}, "ui_packet") is False
    
    def test_none_packet(self, validator):
        """None packet should fail gracefully."""
        # jsonschema will handle this
        try:
            result = validator.validate(None, "ui_packet")  # type: ignore
            assert result is False
        except Exception:
            pass  # Also acceptable
    
    def test_extra_fields_allowed(self, validator):
        """Extra fields should be allowed (additionalProperties: true by default)."""
        packet = make_valid_ui_packet()
        packet["extra_field"] = "extra_value"
        packet["another_extra"] = {"nested": "data"}
        
        assert validator.validate(packet, "ui_packet") is True
    
    def test_nested_validation_errors(self, validator):
        """Errors in nested objects should be reported."""
        packet = make_valid_ui_packet()
        packet["roi_refs"][0]["confidence"] = "not_a_number"
        
        errors = validator.get_validation_errors(packet, "ui_packet")
        assert any("confidence" in str(e) for e in errors)
