"""Unified WSS Publisher Manager for vision pipeline.

Orchestrates all WebSocket publishers (YOLO, MobileSAM, Eagle, Analysis)
for coordinated real-time streaming of vision model outputs.

Uses WSS v2 architecture - single port (8000) with topic routing.

With Governor Integration (v2.1):
- Imports ExecutionGate for verdict validation
- Before publishing to WSS: runs ExecutionGate.check()
- Attaches verdict to packet envelope
- If verdict is block/recheck: doesn't publish, logs to TruthWriter
- If verdict is require_approval: publishes with approval_pending flag

Usage:
    manager = WSSPublisherManager()
    manager.start_all()
    
    # In detection loop:
    manager.publish_yolo_detection(result, frame_id)
    
    # When segmentation needed:
    manager.publish_sam_segmentation(roi_id, mask, bbox, frame_id)
    
    # After Eagle classification:
    manager.publish_eagle_classification(roi_id, frame_id, event_type, confidence)
    
    # After analysis with Governor:
    manager.publish_governed_analysis(
        frame_id=frame_id,
        analysis=analysis,
        risk_level=risk_level,
        recommendation=recommendation,
        verdict=verdict,  # GovernorVerdict required
    )
    
    manager.stop_all()
"""

from __future__ import annotations

import logging
import warnings
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

import numpy as np

from advanced_vision.trading.wss_yolo_publisher_v2 import YOLOWSSPublisherV2
from advanced_vision.trading.wss_sam_publisher_v2 import MobileSAMWSSPublisherV2
from advanced_vision.trading.wss_eagle_publisher_v2 import EagleWSSPublisherV2
from advanced_vision.trading.wss_analysis_publisher_v2 import AnalysisWSSPublisherV2
from advanced_vision.trading.detector import DetectionResult
from advanced_vision.trading.events import (
    BoundingBox,
    ROI,
    RiskLevel,
    ActionRecommendation,
    ReviewerAssessment,
    OverseerResponse,
    TradingEventType,
)

# Governor integration imports
from advanced_vision.core.execution_gate import ExecutionGate, GateDecision
from advanced_vision.core.execution_precondition import ExecutionPrecondition
from advanced_vision.core.governor_verdict import GovernorVerdict, Decision
from advanced_vision.core.truth_writer import TruthWriter

logger = logging.getLogger(__name__)


class WSSPublisherManager:
    """Manager for all vision model WebSocket publishers (v2).
    
    Coordinates four publishers on single port with topic routing:
    1. YOLO Detector (ws://localhost:8000, topic: vision.detection.yolo)
    2. MobileSAM (ws://localhost:8000, topic: vision.segmentation.sam)
    3. Eagle Vision (ws://localhost:8000, topic: vision.classification.eagle)
    4. Analysis (ws://localhost:8000, topic: vision.analysis.qwen)
    
    Governor Integration (v2.1):
    - ExecutionGate validates verdicts before WSS publishing
    - TruthWriter logs blocked/recheck packets before suppression
    - WSS only receives approved packets (or approval_pending flagged)
    - Maintains backward compatibility with v2 API
    
    Features:
    - Unified start/stop for all publishers
    - Per-publisher enable/disable
    - Shared frame storage directory
    - Unified statistics
    - Schema configuration ("ui" or "trading")
    - Distributed tracing support
    - Governor verdict validation (new in v2.1)
    """
    
    def __init__(
        self,
        base_dir: str | Path = "/tmp/advanced_vision",
        yolo_fps: int = 15,
        schema: str = "trading",
        enable_yolo: bool = True,
        enable_sam: bool = True,
        enable_eagle: bool = True,
        enable_analysis: bool = True,
        # Governor integration parameters (new in v2.1)
        enable_governor: bool = True,
        execution_gate: ExecutionGate | None = None,
        truth_writer: TruthWriter | None = None,
        suppress_blocked_packets: bool = True,
        publish_approval_pending: bool = True,
    ):
        self.base_dir = Path(base_dir)
        self.schema = schema
        
        # Create subdirectories
        self.frames_dir = self.base_dir / "frames"
        self.masks_dir = self.base_dir / "masks"
        self.frames_dir.mkdir(parents=True, exist_ok=True)
        self.masks_dir.mkdir(parents=True, exist_ok=True)
        
        # Publisher instances (v2)
        self._yolo: Optional[YOLOWSSPublisherV2] = None
        self._sam: Optional[MobileSAMWSSPublisherV2] = None
        self._eagle: Optional[EagleWSSPublisherV2] = None
        self._analysis: Optional[AnalysisWSSPublisherV2] = None
        
        # Enable flags
        self._enable_yolo = enable_yolo
        self._enable_sam = enable_sam
        self._enable_eagle = enable_eagle
        self._enable_analysis = enable_analysis
        
        # Config
        self._yolo_fps = yolo_fps
        
        # Governor integration (v2.1)
        self._enable_governor = enable_governor
        self._suppress_blocked_packets = suppress_blocked_packets
        self._publish_approval_pending = publish_approval_pending
        
        # ExecutionGate for verdict validation
        if execution_gate:
            self._execution_gate = execution_gate
        elif enable_governor:
            self._execution_gate = ExecutionGate()
        else:
            self._execution_gate = None
        
        # TruthWriter for logging blocked packets
        if truth_writer:
            self._truth_writer = truth_writer
        elif enable_governor:
            truth_dir = self.base_dir / "truth"
            truth_dir.mkdir(parents=True, exist_ok=True)
            self._truth_writer = TruthWriter(truth_dir)
        else:
            self._truth_writer = None
        
        # Statistics for governor integration
        self._governor_stats = {
            "packets_checked": 0,
            "packets_blocked": 0,
            "packets_recheck": 0,
            "packets_approval_pending": 0,
            "packets_allowed": 0,
        }
        
        self._started = False
    
    def start_all(self) -> None:
        """Start all enabled publishers."""
        if self._started:
            logger.warning("Publisher manager already started")
            return
        
        logger.info("Starting WSS v2 publishers...")
        
        if self._enable_yolo:
            self._yolo = YOLOWSSPublisherV2(
                fps=self._yolo_fps,
                frame_save_dir=self.frames_dir,
            )
            self._yolo.start()
            logger.info("  ✓ YOLO v2 publisher started (topic: vision.detection.yolo)")
        
        if self._enable_sam:
            self._sam = MobileSAMWSSPublisherV2(
                mask_save_dir=self.masks_dir,
            )
            self._sam.start()
            logger.info("  ✓ MobileSAM v2 publisher started (topic: vision.segmentation.sam)")
        
        if self._enable_eagle:
            self._eagle = EagleWSSPublisherV2()
            self._eagle.start()
            logger.info("  ✓ Eagle v2 publisher started (topic: vision.classification.eagle)")
        
        if self._enable_analysis:
            self._analysis = AnalysisWSSPublisherV2()
            self._analysis.start()
            logger.info("  ✓ Analysis v2 publisher started (topic: vision.analysis.qwen)")
        
        self._started = True
        logger.info("All WSS v2 publishers started on ws://localhost:8000")
    
    def stop_all(self) -> None:
        """Stop all publishers."""
        if not self._started:
            return
        
        logger.info("Stopping WSS v2 publishers...")
        
        if self._yolo:
            self._yolo.stop()
            self._yolo = None
            logger.info("  ✓ YOLO v2 publisher stopped")
        
        if self._sam:
            self._sam.stop()
            self._sam = None
            logger.info("  ✓ MobileSAM v2 publisher stopped")
        
        if self._eagle:
            self._eagle.stop()
            self._eagle = None
            logger.info("  ✓ Eagle v2 publisher stopped")
        
        if self._analysis:
            self._analysis.stop()
            self._analysis = None
            logger.info("  ✓ Analysis v2 publisher stopped")
        
        self._started = False
        logger.info("All WSS v2 publishers stopped")
    
    def publish_yolo_detection(
        self,
        result: DetectionResult,
        frame_id: str | None = None,
    ) -> None:
        """Publish YOLO detection result.
        
        Args:
            result: DetectionResult from YOLO
            frame_id: Optional frame identifier
        """
        if self._yolo and self._enable_yolo:
            # Convert DetectionResult to boxes format for v2
            boxes = []
            for elem in result.elements:
                box = {
                    "x": elem.bbox.x,
                    "y": elem.bbox.y,
                    "w": elem.bbox.width,
                    "h": elem.bbox.height,
                    "class": elem.element_type.value if hasattr(elem.element_type, 'value') else str(elem.element_type),
                    "confidence": round(elem.confidence, 4),
                    "element_id": elem.element_id,
                }
                boxes.append(box)
            
            self._yolo.publish_detection(
                boxes=boxes,
                frame_id=frame_id,
                inference_time_ms=result.inference_time_ms,
            )
    
    def publish_sam_segmentation(
        self,
        roi_id: str,
        mask: np.ndarray,
        bbox: BoundingBox,
        frame_id: str,
        confidence: float = 1.0,
    ) -> None:
        """Publish MobileSAM segmentation result.
        
        Args:
            roi_id: ROI identifier
            mask: Binary mask array
            bbox: Bounding box
            frame_id: Frame identifier
            confidence: Segmentation confidence
        """
        if self._sam and self._enable_sam:
            self._sam.publish_segmentation(
                roi_id=roi_id,
                mask=mask,
                bbox=bbox,
                frame_id=frame_id,
                confidence=confidence,
            )
    
    def publish_roi_segmentation(
        self,
        roi: ROI,
        frame_id: str,
    ) -> None:
        """Publish segmentation from ROI object.
        
        Args:
            roi: ROI with segmentation data
            frame_id: Frame identifier
        """
        if self._sam and self._enable_sam and roi.segmentation_mask is not None:
            self._sam.publish_segmentation(
                roi_id=roi.roi_id,
                mask=roi.segmentation_mask,
                bbox=roi.bbox,
                frame_id=frame_id,
                confidence=getattr(roi, 'confidence', 1.0),
            )
    
    def publish_eagle_classification(
        self,
        roi_id: str,
        frame_id: str,
        classification: str | TradingEventType,
        confidence: float,
        inference_time_ms: float | None = None,
        reasoning: str | None = None,
    ) -> bool:
        """Publish Eagle classification result.
        
        Args:
            roi_id: ROI identifier
            frame_id: Frame identifier
            classification: Event type classification
            confidence: Classification confidence
            inference_time_ms: Time taken for inference
            reasoning: Optional reasoning text
            
        Returns:
            True if published, False if cached
        """
        if self._eagle and self._enable_eagle:
            # Convert TradingEventType to string if needed
            if hasattr(classification, 'value'):
                classification = classification.value
            
            return self._eagle.publish_classification(
                roi_id=roi_id,
                frame_id=frame_id,
                classification=str(classification),
                confidence=confidence,
                inference_time_ms=inference_time_ms,
                reasoning=reasoning,
            )
        return False
    
    def publish_analysis(
        self,
        frame_id: str,
        analysis: str,
        risk_level: RiskLevel | str,
        recommendation: ActionRecommendation | str,
        confidence: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Publish generic analysis result.
        
        Args:
            frame_id: Frame identifier
            analysis: Analysis text
            risk_level: Risk assessment
            recommendation: Recommended action
            confidence: Optional confidence
            metadata: Optional metadata
        """
        if self._analysis and self._enable_analysis:
            self._analysis.publish_analysis(
                frame_id=frame_id,
                analysis=analysis,
                risk_level=risk_level,
                recommendation=recommendation,
                confidence=confidence,
                metadata=metadata,
            )
    
    def publish_reviewer_assessment(
        self,
        assessment: ReviewerAssessment,
        frame_id: str,
    ) -> None:
        """Publish local reviewer assessment.
        
        Args:
            assessment: ReviewerAssessment from local model
            frame_id: Frame identifier
        """
        if self._analysis and self._enable_analysis:
            metadata = {
                "assessment_id": getattr(assessment, 'assessment_id', None),
                "reviewer_type": getattr(assessment, 'reviewer_type', 'local'),
            }
            self._analysis.publish_analysis(
                frame_id=frame_id,
                analysis=assessment.analysis,
                risk_level=assessment.risk_level,
                recommendation=assessment.recommendation,
                confidence=getattr(assessment, 'confidence', None),
                metadata=metadata,
            )
    
    def publish_overseer_response(
        self,
        response: OverseerResponse,
        frame_id: str,
        escalated_from: ReviewerAssessment | None = None,
    ) -> None:
        """Publish overseer (Kimi) response.
        
        Args:
            response: OverseerResponse from cloud model
            frame_id: Frame identifier
            escalated_from: Original reviewer assessment if escalation
        """
        if self._analysis and self._enable_analysis:
            metadata = {
                "response_id": getattr(response, 'response_id', None),
                "overseer_type": getattr(response, 'overseer_type', 'cloud'),
                "escalated": escalated_from is not None,
            }
            self._analysis.publish_analysis(
                frame_id=frame_id,
                analysis=response.analysis,
                risk_level=response.risk_level,
                recommendation=response.recommendation,
                confidence=getattr(response, 'confidence', None),
                metadata=metadata,
            )
    
    def publish_trading_signal(
        self,
        frame_id: str,
        signal_type: str,
        symbol: str | None = None,
        direction: str | None = None,
        price: float | None = None,
        risk_level: RiskLevel = RiskLevel.MEDIUM,
        analysis: str = "",
    ) -> None:
        """Publish trading signal.
        
        Args:
            frame_id: Frame identifier
            signal_type: Type of signal
            symbol: Trading symbol
            direction: Signal direction
            price: Current/target price
            risk_level: Associated risk
            analysis: Signal analysis
        """
        if self._analysis and self._enable_analysis:
            self._analysis.publish_trading_signal(
                frame_id=frame_id,
                signal_type=signal_type,
                symbol=symbol,
                direction=direction,
                price=price,
                risk_level=risk_level,
                analysis=analysis,
            )
    
    # =========================================================================
    # Governor Integration Methods (v2.1)
    # =========================================================================
    
    def publish_governed_analysis(
        self,
        frame_id: str,
        analysis: str,
        risk_level: RiskLevel | str,
        recommendation: ActionRecommendation | str,
        verdict: GovernorVerdict | dict[str, Any],
        confidence: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Publish analysis result with Governor verdict validation.
        
        This method validates the verdict through ExecutionGate before publishing.
        It is the primary entry point for governed WSS publishing.
        
        Args:
            frame_id: Frame identifier
            analysis: Analysis text
            risk_level: Risk assessment
            recommendation: Recommended action
            verdict: GovernorVerdict (required) or dict representation
            confidence: Optional confidence
            metadata: Optional metadata
            
        Returns:
            Dict with publishing result:
            - published: Whether the packet was published to WSS
            - suppressed: Whether the packet was suppressed (blocked/recheck)
            - approval_pending: Whether published with approval_pending flag
            - reason: Human-readable reason for the decision
            - gate_decision: GateDecision from ExecutionGate
        """
        if not self._analysis or not self._enable_analysis:
            return {
                "published": False,
                "suppressed": True,
                "approval_pending": False,
                "reason": "Analysis publisher not enabled",
                "gate_decision": None,
            }
        
        # Convert dict to GovernorVerdict if needed
        if isinstance(verdict, dict):
            try:
                verdict = GovernorVerdict.from_dict(verdict)
            except Exception as e:
                logger.error(f"Failed to parse verdict dict: {e}")
                return {
                    "published": False,
                    "suppressed": True,
                    "approval_pending": False,
                    "reason": f"Invalid verdict format: {e}",
                    "gate_decision": None,
                }
        
        # Build packet for ExecutionGate
        packet = {
            "frame_id": frame_id,
            "analysis": analysis,
            "risk_level": risk_level.value if hasattr(risk_level, 'value') else risk_level,
            "recommendation": recommendation.value if hasattr(recommendation, 'value') else recommendation,
            "execution_candidate": True,
            "mode": self.schema,
            "governor_verdict": verdict.to_dict(),
        }
        
        if confidence is not None:
            packet["confidence"] = confidence
        
        if metadata:
            packet.update(metadata)
        
        # Run ExecutionGate validation
        gate_decision = self._check_execution_gate(packet, verdict)
        
        result = {
            "published": False,
            "suppressed": False,
            "approval_pending": False,
            "reason": "",
            "gate_decision": gate_decision,
        }
        
        # Handle verdict decision
        if verdict.decision == Decision.BLOCK:
            result["suppressed"] = True
            result["reason"] = f"Packet blocked by Governor: {verdict.rationale[:100]}..."
            
            if self._suppress_blocked_packets:
                # Log to TruthWriter instead of publishing
                self._log_suppressed_packet(packet, verdict, "blocked")
                logger.warning(
                    "WSS publish BLOCKED for frame %s: verdict=%s",
                    frame_id,
                    verdict.verdict_id[:8]
                )
                return result
        
        elif verdict.decision == Decision.RECHECK:
            result["suppressed"] = True
            result["reason"] = f"Packet routed to recheck: {verdict.rationale[:100]}..."
            
            if self._suppress_blocked_packets:
                # Log to TruthWriter instead of publishing
                self._log_suppressed_packet(packet, verdict, "recheck")
                logger.warning(
                    "WSS publish RECHECK for frame %s: verdict=%s",
                    frame_id,
                    verdict.verdict_id[:8]
                )
                return result
        
        elif verdict.decision == Decision.REQUIRE_APPROVAL:
            result["approval_pending"] = True
            result["reason"] = f"Packet requires approval: {verdict.rationale[:100]}..."
            
            if self._publish_approval_pending:
                # Publish with approval_pending flag
                enriched_metadata = metadata or {}
                enriched_metadata["governor_verdict"] = verdict.to_dict()
                enriched_metadata["approval_pending"] = True
                enriched_metadata["verdict_id"] = verdict.verdict_id
                
                self._analysis.publish_analysis(
                    frame_id=frame_id,
                    analysis=analysis,
                    risk_level=risk_level,
                    recommendation=recommendation,
                    confidence=confidence,
                    metadata=enriched_metadata,
                )
                result["published"] = True
                
                logger.info(
                    "WSS publish APPROVAL_PENDING for frame %s: verdict=%s",
                    frame_id,
                    verdict.verdict_id[:8]
                )
                return result
            else:
                # Don't publish approval-pending packets
                self._log_suppressed_packet(packet, verdict, "approval_pending")
                return result
        
        # Decision is CONTINUE or WARN - publish normally
        enriched_metadata = metadata or {}
        enriched_metadata["governor_verdict"] = verdict.to_dict()
        enriched_metadata["verdict_id"] = verdict.verdict_id
        enriched_metadata["decision"] = verdict.decision.value
        
        self._analysis.publish_analysis(
            frame_id=frame_id,
            analysis=analysis,
            risk_level=risk_level,
            recommendation=recommendation,
            confidence=confidence,
            metadata=enriched_metadata,
        )
        
        result["published"] = True
        result["reason"] = f"Published with verdict: {verdict.decision.value}"
        
        logger.debug(
            "WSS publish ALLOWED for frame %s: decision=%s verdict=%s",
            frame_id,
            verdict.decision.value,
            verdict.verdict_id[:8]
        )
        
        return result
    
    def _check_execution_gate(
        self,
        packet: dict[str, Any],
        verdict: GovernorVerdict,
    ) -> GateDecision | None:
        """Check packet through ExecutionGate.
        
        Args:
            packet: Packet to validate
            verdict: GovernorVerdict to validate
            
        Returns:
            GateDecision or None if governor not enabled
        """
        if not self._enable_governor or not self._execution_gate:
            return None
        
        self._governor_stats["packets_checked"] += 1
        
        gate_decision = self._execution_gate.process_with_verdict(packet, verdict)
        
        if gate_decision.can_execute:
            self._governor_stats["packets_allowed"] += 1
        elif gate_decision.requires_recheck:
            self._governor_stats["packets_recheck"] += 1
        elif gate_decision.requires_approval:
            self._governor_stats["packets_approval_pending"] += 1
        else:
            self._governor_stats["packets_blocked"] += 1
        
        return gate_decision
    
    def _log_suppressed_packet(
        self,
        packet: dict[str, Any],
        verdict: GovernorVerdict,
        suppression_reason: str,
    ) -> None:
        """Log suppressed packet to TruthWriter.
        
        Args:
            packet: The suppressed packet
            verdict: GovernorVerdict that caused suppression
            suppression_reason: Reason for suppression (blocked, recheck, etc.)
        """
        if not self._truth_writer:
            return
        
        event = {
            "event_type": "wss_packet_suppressed",
            "event_id": str(uuid4()),
            "frame_id": packet.get("frame_id"),
            "suppression_reason": suppression_reason,
            "verdict_id": verdict.verdict_id,
            "decision": verdict.decision.value,
            "policy_class": verdict.policy_class.value,
            "rationale": verdict.rationale,
            "packet_summary": {
                "analysis_preview": packet.get("analysis", "")[:200],
                "risk_level": packet.get("risk_level"),
                "recommendation": packet.get("recommendation"),
            },
        }
        
        try:
            self._truth_writer.write_event(event)
        except Exception as e:
            logger.error(f"Failed to log suppressed packet: {e}")
    
    def check_verdict_before_publish(
        self,
        verdict: GovernorVerdict | dict[str, Any],
        packet_type: str = "analysis",
    ) -> dict[str, Any]:
        """Check if a verdict allows WSS publishing without actually publishing.
        
        This is a dry-run method to check what would happen with a given verdict.
        
        Args:
            verdict: GovernorVerdict to check
            packet_type: Type of packet being checked
            
        Returns:
            Dict with check results:
            - can_publish: Whether publishing would be allowed
            - decision: The verdict decision
            - action: Recommended action (publish, suppress, approval_pending)
            - reason: Explanation
        """
        # Convert dict to GovernorVerdict if needed
        if isinstance(verdict, dict):
            try:
                verdict = GovernorVerdict.from_dict(verdict)
            except Exception as e:
                return {
                    "can_publish": False,
                    "decision": "invalid",
                    "action": "suppress",
                    "reason": f"Invalid verdict: {e}",
                }
        
        result = {
            "can_publish": False,
            "decision": verdict.decision.value,
            "action": "suppress",
            "reason": verdict.rationale,
        }
        
        if verdict.decision in (Decision.CONTINUE, Decision.WARN):
            result["can_publish"] = True
            result["action"] = "publish"
        elif verdict.decision == Decision.REQUIRE_APPROVAL:
            if self._publish_approval_pending:
                result["can_publish"] = True
                result["action"] = "approval_pending"
            else:
                result["action"] = "suppress"
        elif verdict.decision == Decision.RECHECK:
            result["action"] = "recheck"
        elif verdict.decision == Decision.BLOCK:
            result["action"] = "block"
        
        return result
    
    @property
    def governor_stats(self) -> dict[str, Any]:
        """Get governor integration statistics."""
        return {
            "enabled": self._enable_governor,
            "packets_checked": self._governor_stats["packets_checked"],
            "packets_allowed": self._governor_stats["packets_allowed"],
            "packets_blocked": self._governor_stats["packets_blocked"],
            "packets_recheck": self._governor_stats["packets_recheck"],
            "packets_approval_pending": self._governor_stats["packets_approval_pending"],
            "suppress_blocked": self._suppress_blocked_packets,
            "publish_approval_pending": self._publish_approval_pending,
        }
    
    def reset_governor_stats(self) -> None:
        """Reset governor integration statistics."""
        self._governor_stats = {
            "packets_checked": 0,
            "packets_blocked": 0,
            "packets_recheck": 0,
            "packets_approval_pending": 0,
            "packets_allowed": 0,
        }
    
    # =========================================================================
    # End Governor Integration Methods
    # =========================================================================
    
    def set_trace_id(self, trace_id: str) -> None:
        """Set trace ID for distributed tracing across all publishers."""
        if self._yolo:
            self._yolo.set_trace_id(trace_id)
        if self._sam:
            self._sam.set_trace_id(trace_id)
        if self._eagle:
            self._eagle.set_trace_id(trace_id)
        if self._analysis:
            self._analysis.set_trace_id(trace_id)
    
    def clear_trace_id(self) -> None:
        """Clear trace ID across all publishers."""
        if self._yolo:
            self._yolo.clear_trace_id()
        if self._sam:
            self._sam.clear_trace_id()
        if self._eagle:
            self._eagle.clear_trace_id()
        if self._analysis:
            self._analysis.clear_trace_id()
    
    @property
    def is_started(self) -> bool:
        """Check if manager is started."""
        return self._started
    
    @property
    def yolo_connected(self) -> bool:
        """Check YOLO publisher connection."""
        return self._yolo.is_connected if self._yolo else False
    
    @property
    def sam_connected(self) -> bool:
        """Check MobileSAM publisher connection."""
        return self._sam.is_connected if self._sam else False
    
    @property
    def eagle_connected(self) -> bool:
        """Check Eagle publisher connection."""
        return self._eagle.is_connected if self._eagle else False
    
    @property
    def analysis_connected(self) -> bool:
        """Check Analysis publisher connection."""
        return self._analysis.is_connected if self._analysis else False
    
    @property
    def all_connected(self) -> bool:
        """Check if all enabled publishers are connected."""
        connected = True
        if self._enable_yolo:
            connected = connected and self.yolo_connected
        if self._enable_sam:
            connected = connected and self.sam_connected
        if self._enable_eagle:
            connected = connected and self.eagle_connected
        if self._enable_analysis:
            connected = connected and self.analysis_connected
        return connected
    
    @property
    def stats(self) -> dict[str, Any]:
        """Get combined statistics from all publishers."""
        stats = {
            "started": self._started,
            "schema": self.schema,
            "version": "v2",
            "publishers": {},
        }
        
        if self._yolo:
            stats["publishers"]["yolo"] = self._yolo.stats
        if self._sam:
            stats["publishers"]["sam"] = self._sam.stats
        if self._eagle:
            stats["publishers"]["eagle"] = self._eagle.stats
        if self._analysis:
            stats["publishers"]["analysis"] = self._analysis.stats
        
        return stats
    
    def get_connection_status(self) -> dict[str, bool]:
        """Get connection status for all publishers."""
        return {
            "yolo": self.yolo_connected,
            "sam": self.sam_connected,
            "eagle": self.eagle_connected,
            "analysis": self.analysis_connected,
        }


# =============================================================================
# Convenience Functions
# =============================================================================

def create_wss_manager(
    base_dir: str = "/tmp/advanced_vision",
    yolo_fps: int = 15,
    schema: str = "trading",
) -> WSSPublisherManager:
    """Factory function to create WSS publisher manager (v2)."""
    return WSSPublisherManager(
        base_dir=base_dir,
        yolo_fps=yolo_fps,
        schema=schema,
    )


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    import time
    from datetime import datetime, timezone
    
    logging.basicConfig(level=logging.INFO)
    
    # Create and start manager
    manager = create_wss_manager(yolo_fps=10)
    manager.start_all()
    
    try:
        # Simulate pipeline outputs
        for i in range(20):
            frame_id = f"frame_{i:04d}"
            
            # 1. YOLO detection (every frame)
            from advanced_vision.trading.events import (
                UIElement, UIElementType, DetectionSource
            )
            
            elem = UIElement(
                element_id=f"elem_{i}",
                element_type=UIElementType.CHART_PANEL,
                bbox=BoundingBox(x=100, y=100, width=400, height=300),
                confidence=0.85,
                source=DetectionSource.TRIPWIRE,
            )
            detection = DetectionResult(
                elements=[elem],
                inference_time_ms=15.0,
                frame_timestamp=datetime.now(timezone.utc).isoformat(),
            )
            manager.publish_yolo_detection(detection, frame_id=frame_id)
            
            # 2. MobileSAM segmentation (every 5th frame)
            if i % 5 == 0:
                mask = np.random.rand(300, 400) > 0.5
                bbox = BoundingBox(x=100, y=100, width=400, height=300)
                manager.publish_sam_segmentation(
                    roi_id=f"roi_{i}",
                    mask=mask,
                    bbox=bbox,
                    frame_id=frame_id,
                    confidence=0.92,
                )
            
            # 3. Eagle classification (every 3rd frame, ~300-500ms)
            if i % 3 == 0:
                event_types = ["chart_update", "order_ticket", "price_change"]
                manager.publish_eagle_classification(
                    roi_id=f"roi_{i}",
                    frame_id=frame_id,
                    classification=event_types[i % 3],
                    confidence=0.85 + (i % 3) * 0.05,
                    inference_time_ms=350 + (i % 3) * 50,
                )
            
            # 4. Analysis (every 10th frame)
            if i % 10 == 0:
                risk_levels = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH]
                recommendations = [
                    ActionRecommendation.CONTINUE,
                    ActionRecommendation.NOTE,
                    ActionRecommendation.WARN,
                ]
                manager.publish_analysis(
                    frame_id=frame_id,
                    analysis=f"Frame {i} analysis complete",
                    risk_level=risk_levels[i % 3],
                    recommendation=recommendations[i % 3],
                    confidence=0.8,
                )
            
            print(f"Published frame {i} - Connections: {manager.get_connection_status()}")
            time.sleep(0.1)  # 10 FPS
            
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        manager.stop_all()
        print("\nFinal stats:")
        import json
        print(json.dumps(manager.stats, indent=2, default=str))
