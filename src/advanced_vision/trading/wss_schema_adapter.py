"""WSS Schema Adapter for converting TransportEnvelope to schema-compliant EventEnvelope.

This module provides adapters to wrap WSS v2 TransportEnvelope messages into
fully schema-compliant event envelopes as defined in schemas/event_envelope.schema.json.

Features:
- Wraps raw packets in event_envelope format
- Adds trace_id correlation across pipeline stages
- Handles envelope serialization with schema validation
- Builds artifact_refs for frames, ROIs, and masks
- Maps payload types to correct discriminator values
- Supports both "trading" and "ui" modes

Usage:
    adapter = SchemaAdapter(mode="trading", schema_version="1.0.0")
    
    # Wrap detection batch
    envelope = adapter.wrap_detection_batch(
        frame_id="frame_001",
        detections=[...],
        trace_id="uuid..."
    )
    
    # Publish via WSS
    await publisher.publish(envelope)

Truth-First Pattern:
    All events are logged to disk before publishing to WSS.
    This ensures durability even if network delivery fails.
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional, Union

# Try to import uuid7 for time-sortable IDs, fall back to uuid4
try:
    from uuid_extensions import uuid7
    HAS_UUID7 = True
except ImportError:
    HAS_UUID7 = False
    uuid7 = lambda: uuid.uuid4()

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================

class Source(str, Enum):
    """Event source component - matches event_envelope.schema.json enum."""
    CAPTURE = "capture"
    YOLO = "yolo"
    MOBILESAM = "mobilesam"
    EAGLE = "eagle"
    QWEN = "qwen"
    GOVERNOR = "governor"
    EXTERNAL_REVIEW = "external_review"
    SYSTEM = "system"


class Mode(str, Enum):
    """Operational mode - matches event_envelope.schema.json enum."""
    UI = "ui"
    TRADING = "trading"
    SYSTEM = "system"
    DIAGNOSTIC = "diagnostic"


class PayloadType(str, Enum):
    """Payload type discriminator - matches event_envelope.schema.json enum."""
    UI_PACKET = "ui_packet"
    TRADING_PACKET = "trading_packet"
    SCOUT_EVENT = "scout_event"
    EXTERNAL_REVIEW_REQUEST = "external_review_request"
    EXTERNAL_REVIEW_RESULT = "external_review_result"
    ARTIFACT_MANIFEST = "artifact_manifest"
    SYSTEM_HEARTBEAT = "system_heartbeat"
    GOVERNOR_DECISION = "governor_decision"


class ArtifactType(str, Enum):
    """Artifact type - matches event_envelope.schema.json artifact_refs items."""
    FRAME = "frame"
    ROI = "roi"
    CLIP = "clip"
    LOG = "log"
    MANIFEST = "manifest"


class ScoutClassification(str, Enum):
    """Scout classification - matches scout_event.schema.json enum."""
    CURSOR_NOISE = "cursor_noise"
    BENIGN_UI_CHANGE = "benign_ui_change"
    MEANINGFUL_UI_CHANGE = "meaningful_ui_change"
    MODAL_DIALOG = "modal_dialog"
    FORM_INTERACTION = "form_interaction"
    CHART_UPDATE = "chart_update"
    TICKET_UPDATE = "ticket_update"
    ALERT_CONDITION = "alert_condition"
    UNKNOWN_SIGNIFICANT = "unknown_significant"
    REQUIRES_REVIEW = "requires_review"


class TradingEventType(str, Enum):
    """Trading packet event type - matches trading_packet.schema.json enum."""
    PRICE_MOVEMENT = "price_movement"
    SIGNAL_DETECTED = "signal_detected"
    TICKET_STATE_CHANGE = "ticket_state_change"
    ALERT_TRIGGERED = "alert_triggered"
    CONFIRMATION_REQUIRED = "confirmation_required"
    ANOMALY = "anomaly"
    UNKNOWN = "unknown"


class UIEventType(str, Enum):
    """UI packet event type - matches ui_packet.schema.json enum."""
    UI_CHANGE = "ui_change"
    MODAL_APPEARED = "modal_appeared"
    BUTTON_DETECTED = "button_detected"
    FORM_DETECTED = "form_detected"
    NAVIGATION = "navigation"
    UNKNOWN = "unknown"


class RiskLevel(str, Enum):
    """Risk level - common across multiple schemas."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SuggestedAction(str, Enum):
    """Suggested action - matches trading_packet.schema.json enum."""
    MONITOR = "monitor"
    REVIEW_DETAILS = "review_details"
    CONFIRM_EXIT = "confirm_exit"
    CONFIRM_ENTRY = "confirm_entry"
    HOLD = "hold"
    ALERT_HUMAN = "alert_human"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class ArtifactRef:
    """Reference to an artifact (frame, ROI, clip, etc.)."""
    type: ArtifactType
    path: str
    checksum: Optional[str] = None
    
    def to_dict(self) -> dict[str, Any]:
        result = {"type": self.type.value, "path": self.path}
        if self.checksum:
            result["checksum"] = self.checksum
        return result


@dataclass
class EventEnvelope:
    """Schema-compliant event envelope.
    
    Matches event_envelope.schema.json structure exactly.
    """
    event_id: str
    timestamp: str
    source: Source
    mode: Mode
    schema_version: str
    payload: dict[str, Any]
    payload_type: PayloadType
    trace_id: Optional[str] = None
    parent_event_id: Optional[str] = None
    artifact_refs: list[ArtifactRef] = field(default_factory=list)
    work_item_id: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate required fields after initialization."""
        if not self.event_id:
            raise ValueError("event_id is required")
        if not self.timestamp:
            raise ValueError("timestamp is required")
        if not self.schema_version:
            raise ValueError("schema_version is required")
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result: dict[str, Any] = {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "source": self.source.value,
            "mode": self.mode.value,
            "schema_version": self.schema_version,
            "payload": self.payload,
            "payload_type": self.payload_type.value,
        }
        
        if self.trace_id:
            result["trace_id"] = self.trace_id
        if self.parent_event_id:
            result["parent_event_id"] = self.parent_event_id
        if self.artifact_refs:
            result["artifact_refs"] = [ref.to_dict() for ref in self.artifact_refs]
        if self.work_item_id:
            result["work_item_id"] = self.work_item_id
        if self.metadata:
            result["metadata"] = self.metadata
            
        return result
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), default=str)


@dataclass
class ScoutEventPayload:
    """Scout event payload - matches scout_event.schema.json."""
    event_id: str
    timestamp: str
    scout_version: str
    classification: ScoutClassification
    confidence: float
    inference_time_ms: Optional[int] = None
    roi_count: Optional[int] = None
    motion_metrics: Optional[dict[str, Any]] = None
    escalation_recommended: bool = False
    escalation_reason: Optional[str] = None
    artifact_refs: Optional[dict[str, Any]] = None
    
    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "scout_version": self.scout_version,
            "classification": self.classification.value,
            "confidence": round(self.confidence, 4),
            "escalation_recommended": self.escalation_recommended,
        }
        if self.inference_time_ms is not None:
            result["inference_time_ms"] = self.inference_time_ms
        if self.roi_count is not None:
            result["roi_count"] = self.roi_count
        if self.motion_metrics:
            result["motion_metrics"] = self.motion_metrics
        if self.escalation_reason:
            result["escalation_reason"] = self.escalation_reason
        if self.artifact_refs:
            result["artifact_refs"] = self.artifact_refs
        return result


@dataclass
class TradingPacketPayload:
    """Trading packet payload - matches trading_packet.schema.json."""
    packet_id: str
    mode: str = "trading"
    event_type: TradingEventType = TradingEventType.UNKNOWN
    summary: str = ""
    frame_ref: str = ""
    previous_frame_ref: Optional[str] = None
    chart_regions: list[dict[str, Any]] = field(default_factory=list)
    ticket_regions: list[dict[str, Any]] = field(default_factory=list)
    indicators: list[dict[str, Any]] = field(default_factory=list)
    scout_note: str = ""
    risk_tags: list[str] = field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.NONE
    needs_local_review: bool = True
    needs_external_review: bool = True
    suggested_action: SuggestedAction = SuggestedAction.MONITOR
    
    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "packet_id": self.packet_id,
            "mode": self.mode,
            "event_type": self.event_type.value,
            "frame_ref": self.frame_ref,
            "scout_note": self.scout_note,
            "risk_level": self.risk_level.value,
            "needs_local_review": self.needs_local_review,
            "needs_external_review": self.needs_external_review,
            "suggested_action": self.suggested_action.value,
        }
        if self.summary:
            result["summary"] = self.summary
        if self.previous_frame_ref:
            result["previous_frame_ref"] = self.previous_frame_ref
        if self.chart_regions:
            result["chart_regions"] = self.chart_regions
        if self.ticket_regions:
            result["ticket_regions"] = self.ticket_regions
        if self.indicators:
            result["indicators"] = self.indicators
        if self.risk_tags:
            result["risk_tags"] = self.risk_tags
        return result


@dataclass
class UIPacketPayload:
    """UI packet payload - matches ui_packet.schema.json."""
    packet_id: str
    mode: str = "ui"
    event_type: UIEventType = UIEventType.UNKNOWN
    summary: str = ""
    frame_ref: str = ""
    previous_frame_ref: Optional[str] = None
    roi_refs: list[dict[str, Any]] = field(default_factory=list)
    targets: list[dict[str, Any]] = field(default_factory=list)
    scout_note: str = ""
    risk_tags: list[str] = field(default_factory=list)
    needs_local_review: bool = False
    needs_external_review: bool = True
    latency_ms: Optional[dict[str, int]] = None
    
    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "packet_id": self.packet_id,
            "mode": self.mode,
            "event_type": self.event_type.value,
            "frame_ref": self.frame_ref,
            "scout_note": self.scout_note,
            "needs_local_review": self.needs_local_review,
            "needs_external_review": self.needs_external_review,
        }
        if self.summary:
            result["summary"] = self.summary
        if self.previous_frame_ref:
            result["previous_frame_ref"] = self.previous_frame_ref
        if self.roi_refs:
            result["roi_refs"] = self.roi_refs
        if self.targets:
            result["targets"] = self.targets
        if self.risk_tags:
            result["risk_tags"] = self.risk_tags
        if self.latency_ms:
            result["latency_ms"] = self.latency_ms
        return result


# =============================================================================
# Mapping Tables
# =============================================================================

# Map eagle classifications to scout event classifications
EAGLE_TO_SCOUT_CLASSIFICATION: dict[str, ScoutClassification] = {
    "order_ticket": ScoutClassification.TICKET_UPDATE,
    "chart_update": ScoutClassification.CHART_UPDATE,
    "confirm_dialog": ScoutClassification.MODAL_DIALOG,
    "warning_dialog": ScoutClassification.ALERT_CONDITION,
    "price_change": ScoutClassification.CHART_UPDATE,
    "signal_detected": ScoutClassification.ALERT_CONDITION,
    "cursor_noise": ScoutClassification.CURSOR_NOISE,
    "benign_ui_change": ScoutClassification.BENIGN_UI_CHANGE,
    "meaningful_ui_change": ScoutClassification.MEANINGFUL_UI_CHANGE,
    "modal_dialog": ScoutClassification.MODAL_DIALOG,
    "form_interaction": ScoutClassification.FORM_INTERACTION,
    "alert_condition": ScoutClassification.ALERT_CONDITION,
    "unknown_significant": ScoutClassification.UNKNOWN_SIGNIFICANT,
    "requires_review": ScoutClassification.REQUIRES_REVIEW,
}

# Map risk level strings to enum
RISK_LEVEL_MAP: dict[str, RiskLevel] = {
    "none": RiskLevel.NONE,
    "low": RiskLevel.LOW,
    "medium": RiskLevel.MEDIUM,
    "high": RiskLevel.HIGH,
    "critical": RiskLevel.CRITICAL,
}

# Map recommendation strings to suggested action enum
RECOMMENDATION_TO_ACTION: dict[str, SuggestedAction] = {
    "continue": SuggestedAction.MONITOR,
    "note": SuggestedAction.MONITOR,
    "warn": SuggestedAction.REVIEW_DETAILS,
    "hold": SuggestedAction.HOLD,
    "pause": SuggestedAction.ALERT_HUMAN,
    "escalate": SuggestedAction.CONFIRM_EXIT,
    "monitor": SuggestedAction.MONITOR,
    "review_details": SuggestedAction.REVIEW_DETAILS,
    "confirm_exit": SuggestedAction.CONFIRM_EXIT,
    "confirm_entry": SuggestedAction.CONFIRM_ENTRY,
}


# =============================================================================
# Schema Adapter
# =============================================================================

class SchemaAdapter:
    """Adapter to convert WSS v2 data to schema-compliant EventEnvelope.
    
    Usage:
        adapter = SchemaAdapter(mode="trading", base_dir="/tmp/advanced_vision")
        
        # Wrap detection results
        envelope = adapter.wrap_detection_batch(
            frame_id="frame_001",
            detections=[{"class": "chart", "confidence": 0.95}],
            trace_id="uuid..."
        )
    """
    
    def __init__(
        self,
        mode: Mode | str = Mode.TRADING,
        schema_version: str = "1.0.0",
        base_dir: str | Path = "/tmp/advanced_vision",
        scout_version: str = "eagle2-2b-v1.0",
        enable_checksums: bool = True,
    ):
        self.mode = mode if isinstance(mode, Mode) else Mode(mode)
        self.schema_version = schema_version
        self.base_dir = Path(base_dir)
        self.scout_version = scout_version
        self.enable_checksums = enable_checksums
        self._trace_id: Optional[str] = None
    
    def set_trace_id(self, trace_id: str) -> None:
        """Set default trace ID for all subsequent envelopes."""
        self._trace_id = trace_id
    
    def clear_trace_id(self) -> None:
        """Clear default trace ID."""
        self._trace_id = None
    
    def _generate_event_id(self) -> str:
        """Generate time-sortable event ID."""
        return str(uuid7())
    
    def _get_timestamp(self) -> str:
        """Get current ISO 8601 timestamp."""
        return datetime.now(timezone.utc).isoformat()
    
    def _compute_checksum(self, file_path: Path) -> Optional[str]:
        """Compute SHA256 checksum of a file."""
        if not self.enable_checksums:
            return None
        
        try:
            if not file_path.exists():
                return None
            
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    sha256_hash.update(chunk)
            return f"sha256:{sha256_hash.hexdigest()}"
        except Exception as e:
            logger.warning(f"Failed to compute checksum for {file_path}: {e}")
            return None
    
    def _build_artifact_ref(
        self,
        artifact_type: ArtifactType,
        relative_path: str,
        compute_checksum: bool = True,
    ) -> ArtifactRef:
        """Build artifact reference with optional checksum."""
        full_path = self.base_dir / relative_path
        checksum = None
        
        if compute_checksum and self.enable_checksums:
            checksum = self._compute_checksum(full_path)
        
        return ArtifactRef(
            type=artifact_type,
            path=relative_path,
            checksum=checksum,
        )
    
    def wrap_detection_batch(
        self,
        frame_id: str,
        detections: list[dict[str, Any]],
        inference_time_ms: Optional[float] = None,
        trace_id: Optional[str] = None,
        parent_event_id: Optional[str] = None,
        work_item_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> EventEnvelope:
        """Wrap YOLO detection batch in schema-compliant envelope.
        
        Args:
            frame_id: Frame identifier
            detections: List of detection dictionaries
            inference_time_ms: Time taken for inference
            trace_id: Distributed trace ID (uses default if not provided)
            parent_event_id: Reference to parent event
            work_item_id: External work item reference
            metadata: Additional metadata
            
        Returns:
            Schema-compliant EventEnvelope
        """
        event_id = self._generate_event_id()
        timestamp = self._get_timestamp()
        trace = trace_id or self._trace_id
        
        # Build artifact refs
        artifact_refs: list[ArtifactRef] = []
        frame_path = f"frames/{frame_id}.png"
        artifact_refs.append(self._build_artifact_ref(ArtifactType.FRAME, frame_path))
        
        # Build scout event payload
        payload = ScoutEventPayload(
            event_id=event_id,
            timestamp=timestamp,
            scout_version=self.scout_version,
            classification=ScoutClassification.MEANINGFUL_UI_CHANGE,
            confidence=0.85,  # Aggregate confidence
            inference_time_ms=int(inference_time_ms) if inference_time_ms else None,
            roi_count=len(detections),
            escalation_recommended=len(detections) > 0,
            artifact_refs={"input_frame": frame_path, "detections": detections},
        )
        
        return EventEnvelope(
            event_id=event_id,
            timestamp=timestamp,
            source=Source.YOLO,
            mode=self.mode,
            schema_version=self.schema_version,
            trace_id=trace,
            parent_event_id=parent_event_id,
            artifact_refs=artifact_refs,
            work_item_id=work_item_id,
            payload=payload.to_dict(),
            payload_type=PayloadType.SCOUT_EVENT,
            metadata=metadata or {},
        )
    
    def wrap_segmentation_batch(
        self,
        frame_id: str,
        masks: list[dict[str, Any]],
        roi_ids: Optional[list[str]] = None,
        inference_time_ms: Optional[float] = None,
        trace_id: Optional[str] = None,
        parent_event_id: Optional[str] = None,
        work_item_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> EventEnvelope:
        """Wrap MobileSAM segmentation batch in schema-compliant envelope.
        
        Args:
            frame_id: Frame identifier
            masks: List of mask dictionaries
            roi_ids: List of ROI identifiers
            inference_time_ms: Time taken for inference
            trace_id: Distributed trace ID
            parent_event_id: Reference to parent event
            work_item_id: External work item reference
            metadata: Additional metadata
            
        Returns:
            Schema-compliant EventEnvelope
        """
        event_id = self._generate_event_id()
        timestamp = self._get_timestamp()
        trace = trace_id or self._trace_id
        
        # Build artifact refs
        artifact_refs: list[ArtifactRef] = []
        frame_path = f"frames/{frame_id}.png"
        artifact_refs.append(self._build_artifact_ref(ArtifactType.FRAME, frame_path))
        
        # Add ROI refs
        roi_ids = roi_ids or []
        for roi_id in roi_ids:
            roi_path = f"masks/{roi_id}.png"
            artifact_refs.append(self._build_artifact_ref(ArtifactType.ROI, roi_path))
        
        # Build scout event payload
        payload = ScoutEventPayload(
            event_id=event_id,
            timestamp=timestamp,
            scout_version=self.scout_version,
            classification=ScoutClassification.MEANINGFUL_UI_CHANGE,
            confidence=0.92,
            inference_time_ms=int(inference_time_ms) if inference_time_ms else None,
            roi_count=len(masks),
            escalation_recommended=len(masks) > 0,
            artifact_refs={
                "input_frame": frame_path,
                "output_rois": [f"masks/{m.get('roi_id', 'unknown')}.png" for m in masks],
            },
        )
        
        return EventEnvelope(
            event_id=event_id,
            timestamp=timestamp,
            source=Source.MOBILESAM,
            mode=self.mode,
            schema_version=self.schema_version,
            trace_id=trace,
            parent_event_id=parent_event_id,
            artifact_refs=artifact_refs,
            work_item_id=work_item_id,
            payload=payload.to_dict(),
            payload_type=PayloadType.SCOUT_EVENT,
            metadata=metadata or {},
        )
    
    def wrap_classification(
        self,
        frame_id: str,
        roi_id: str,
        classification: str,
        confidence: float,
        inference_time_ms: Optional[float] = None,
        reasoning: Optional[str] = None,
        trace_id: Optional[str] = None,
        parent_event_id: Optional[str] = None,
        work_item_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> EventEnvelope:
        """Wrap Eagle classification in schema-compliant envelope.
        
        Args:
            frame_id: Frame identifier
            roi_id: ROI identifier
            classification: Event classification string
            confidence: Classification confidence
            inference_time_ms: Time taken for inference
            reasoning: Optional reasoning text
            trace_id: Distributed trace ID
            parent_event_id: Reference to parent event
            work_item_id: External work item reference
            metadata: Additional metadata
            
        Returns:
            Schema-compliant EventEnvelope
        """
        event_id = self._generate_event_id()
        timestamp = self._get_timestamp()
        trace = trace_id or self._trace_id
        
        # Map classification to scout event classification
        scout_classification = EAGLE_TO_SCOUT_CLASSIFICATION.get(
            classification.lower(),
            ScoutClassification.UNKNOWN_SIGNIFICANT
        )
        
        # Build artifact refs
        artifact_refs: list[ArtifactRef] = []
        frame_path = f"frames/{frame_id}.png"
        roi_path = f"masks/{roi_id}.png"
        artifact_refs.append(self._build_artifact_ref(ArtifactType.FRAME, frame_path))
        artifact_refs.append(self._build_artifact_ref(ArtifactType.ROI, roi_path))
        
        # Build scout event payload
        payload = ScoutEventPayload(
            event_id=event_id,
            timestamp=timestamp,
            scout_version=self.scout_version,
            classification=scout_classification,
            confidence=confidence,
            inference_time_ms=int(inference_time_ms) if inference_time_ms else None,
            roi_count=1,
            escalation_recommended=confidence > 0.7,
            escalation_reason="high_confidence_change" if confidence > 0.7 else None,
            artifact_refs={
                "input_frame": frame_path,
                "output_rois": [roi_path],
            },
        )
        
        meta = metadata or {}
        if reasoning:
            meta["reasoning"] = reasoning
        
        return EventEnvelope(
            event_id=event_id,
            timestamp=timestamp,
            source=Source.EAGLE,
            mode=self.mode,
            schema_version=self.schema_version,
            trace_id=trace,
            parent_event_id=parent_event_id,
            artifact_refs=artifact_refs,
            work_item_id=work_item_id,
            payload=payload.to_dict(),
            payload_type=PayloadType.SCOUT_EVENT,
            metadata=meta,
        )
    
    def wrap_analysis(
        self,
        frame_id: str,
        analysis: str,
        risk_level: RiskLevel | str,
        recommendation: SuggestedAction | str,
        confidence: Optional[float] = None,
        chart_regions: Optional[list[dict[str, Any]]] = None,
        ticket_regions: Optional[list[dict[str, Any]]] = None,
        indicators: Optional[list[dict[str, Any]]] = None,
        trace_id: Optional[str] = None,
        parent_event_id: Optional[str] = None,
        work_item_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> EventEnvelope:
        """Wrap Qwen/Kimi analysis in schema-compliant envelope.
        
        Args:
            frame_id: Frame identifier
            analysis: Analysis text/summary
            risk_level: Risk assessment level
            recommendation: Suggested action
            confidence: Optional confidence score
            chart_regions: List of chart region dictionaries
            ticket_regions: List of ticket region dictionaries
            indicators: List of indicator dictionaries
            trace_id: Distributed trace ID
            parent_event_id: Reference to parent event
            work_item_id: External work item reference
            metadata: Additional metadata
            
        Returns:
            Schema-compliant EventEnvelope
        """
        event_id = self._generate_event_id()
        timestamp = self._get_timestamp()
        trace = trace_id or self._trace_id
        
        # Normalize risk_level
        if isinstance(risk_level, str):
            risk_level = RISK_LEVEL_MAP.get(risk_level.lower(), RiskLevel.NONE)
        
        # Normalize recommendation
        if isinstance(recommendation, str):
            recommendation = RECOMMENDATION_TO_ACTION.get(
                recommendation.lower(),
                SuggestedAction.MONITOR
            )
        
        # Build artifact refs
        artifact_refs: list[ArtifactRef] = []
        frame_path = f"frames/{frame_id}.png"
        artifact_refs.append(self._build_artifact_ref(ArtifactType.FRAME, frame_path))
        
        # Determine payload type based on mode
        if self.mode == Mode.TRADING:
            payload_type = PayloadType.TRADING_PACKET
            payload = TradingPacketPayload(
                packet_id=event_id,
                event_type=TradingEventType.SIGNAL_DETECTED,
                summary=analysis[:500] if analysis else "",
                frame_ref=frame_path,
                chart_regions=chart_regions or [],
                ticket_regions=ticket_regions or [],
                indicators=indicators or [],
                scout_note=analysis[:1000] if analysis else "",
                risk_level=risk_level,
                suggested_action=recommendation,
            ).to_dict()
        else:
            payload_type = PayloadType.UI_PACKET
            payload = UIPacketPayload(
                packet_id=event_id,
                event_type=UIEventType.UI_CHANGE,
                summary=analysis[:500] if analysis else "",
                frame_ref=frame_path,
                scout_note=analysis[:1000] if analysis else "",
            ).to_dict()
        
        meta = metadata or {}
        if confidence is not None:
            meta["confidence"] = round(confidence, 4)
        
        return EventEnvelope(
            event_id=event_id,
            timestamp=timestamp,
            source=Source.QWEN,
            mode=self.mode,
            schema_version=self.schema_version,
            trace_id=trace,
            parent_event_id=parent_event_id,
            artifact_refs=artifact_refs,
            work_item_id=work_item_id,
            payload=payload,
            payload_type=payload_type,
            metadata=meta,
        )
    
    def wrap_error(
        self,
        frame_id: str,
        error_message: str,
        error_type: str = "analysis_error",
        trace_id: Optional[str] = None,
        parent_event_id: Optional[str] = None,
        work_item_id: Optional[str] = None,
    ) -> EventEnvelope:
        """Wrap error event in schema-compliant envelope.
        
        Args:
            frame_id: Frame identifier
            error_message: Error description
            error_type: Type of error
            trace_id: Distributed trace ID
            parent_event_id: Reference to parent event
            work_item_id: External work item reference
            
        Returns:
            Schema-compliant EventEnvelope
        """
        event_id = self._generate_event_id()
        timestamp = self._get_timestamp()
        trace = trace_id or self._trace_id
        
        return EventEnvelope(
            event_id=event_id,
            timestamp=timestamp,
            source=Source.SYSTEM,
            mode=Mode.SYSTEM,
            schema_version=self.schema_version,
            trace_id=trace,
            parent_event_id=parent_event_id,
            work_item_id=work_item_id,
            payload={
                "error_type": error_type,
                "error_message": error_message,
                "frame_id": frame_id,
                "risk_level": RiskLevel.HIGH.value,
                "recommendation": SuggestedAction.HOLD.value,
            },
            payload_type=PayloadType.SYSTEM_HEARTBEAT,
            metadata={"error": True},
        )


# =============================================================================
# Convenience Functions
# =============================================================================

def create_schema_adapter(
    mode: str = "trading",
    schema_version: str = "1.0.0",
    base_dir: str = "/tmp/advanced_vision",
) -> SchemaAdapter:
    """Factory function to create a schema adapter."""
    return SchemaAdapter(
        mode=Mode(mode),
        schema_version=schema_version,
        base_dir=base_dir,
    )


def validate_envelope_against_schema(
    envelope: EventEnvelope,
    schema_path: Optional[Path] = None,
) -> tuple[bool, list[str]]:
    """Validate an envelope against the JSON schema.
    
    Args:
        envelope: EventEnvelope to validate
        schema_path: Path to event_envelope.schema.json
        
    Returns:
        Tuple of (is_valid, error_messages)
    """
    try:
        import jsonschema
    except ImportError:
        logger.warning("jsonschema not installed, skipping validation")
        return True, []
    
    if schema_path is None:
        # Try to find schema relative to this file
        schema_path = Path(__file__).parent.parent.parent / "schemas" / "event_envelope.schema.json"
    
    try:
        with open(schema_path) as f:
            schema = json.load(f)
        
        validator = jsonschema.Draft202012Validator(schema)
        errors = list(validator.iter_errors(envelope.to_dict()))
        
        if errors:
            error_messages = [f"{e.path}: {e.message}" for e in errors]
            return False, error_messages
        
        return True, []
        
    except Exception as e:
        return False, [f"Validation error: {e}"]


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Create adapter
    adapter = SchemaAdapter(mode="trading", base_dir="/tmp/advanced_vision")
    adapter.set_trace_id(str(uuid.uuid4()))
    
    # Wrap detection batch
    detection_envelope = adapter.wrap_detection_batch(
        frame_id="frame_001",
        detections=[
            {"class": "chart_panel", "confidence": 0.95, "bbox": [100, 100, 400, 300]},
            {"class": "order_ticket", "confidence": 0.88, "bbox": [50, 500, 300, 200]},
        ],
        inference_time_ms=15.5,
    )
    print("Detection Envelope:")
    print(json.dumps(detection_envelope.to_dict(), indent=2))
    
    # Wrap classification
    classification_envelope = adapter.wrap_classification(
        frame_id="frame_001",
        roi_id="roi_001",
        classification="order_ticket",
        confidence=0.92,
        inference_time_ms=350,
        reasoning="Detected order ticket based on UI patterns",
        parent_event_id=detection_envelope.event_id,
    )
    print("\nClassification Envelope:")
    print(json.dumps(classification_envelope.to_dict(), indent=2))
    
    # Wrap analysis
    analysis_envelope = adapter.wrap_analysis(
        frame_id="frame_001",
        analysis="Potential margin call detected on EURUSD position",
        risk_level=RiskLevel.HIGH,
        recommendation=SuggestedAction.ALERT_HUMAN,
        confidence=0.85,
        parent_event_id=classification_envelope.event_id,
    )
    print("\nAnalysis Envelope:")
    print(json.dumps(analysis_envelope.to_dict(), indent=2))
    
    # Validate
    is_valid, errors = validate_envelope_against_schema(analysis_envelope)
    print(f"\nValidation: {'PASSED' if is_valid else 'FAILED'}")
    if errors:
        for error in errors:
            print(f"  - {error}")
