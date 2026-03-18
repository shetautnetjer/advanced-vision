"""Pipeline stages for governed vision pipeline.

Stage definitions: CaptureStage, DetectionStage, ScoutStage, GovernanceStage
Each stage logs to TruthWriter on completion with lineage tracking.
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol
from uuid import uuid4

from advanced_vision.core.truth_writer import TruthWriter
from advanced_vision.core.governor_verdict import GovernorVerdict, RiskLevel

logger = logging.getLogger(__name__)


# =============================================================================
# Stage Result Types
# =============================================================================

@dataclass
class StageResult:
    """Result from a pipeline stage execution.
    
    Attributes:
        success: Whether the stage completed successfully
        stage_name: Name of the stage
        stage_id: Unique identifier for this stage execution
        parent_stage_id: Parent stage ID for lineage
        timestamp: ISO timestamp when stage completed
        duration_ms: Time taken for stage execution
        output_data: Output data from the stage
        error: Error message if stage failed
        artifact_refs: References to generated artifacts
    """
    success: bool
    stage_name: str
    stage_id: str = field(default_factory=lambda: str(uuid4()))
    parent_stage_id: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    duration_ms: float = 0.0
    output_data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    artifact_refs: list[str] = field(default_factory=list)
    
    @property
    def failed(self) -> bool:
        """Check if stage failed."""
        return not self.success
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "stage_id": self.stage_id,
            "stage_name": self.stage_name,
            "parent_stage_id": self.parent_stage_id,
            "timestamp": self.timestamp,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "error": self.error,
            "artifact_refs": self.artifact_refs,
        }


# =============================================================================
# Stage Context
# =============================================================================

@dataclass
class StageContext:
    """Context passed through pipeline stages.
    
    Maintains lineage and trace information across all stages.
    """
    trace_id: str = field(default_factory=lambda: str(uuid4()))
    pipeline_id: str = field(default_factory=lambda: str(uuid4()))
    frame_id: str | None = None
    start_time: float = field(default_factory=time.time)
    stage_results: list[StageResult] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def get_last_stage_id(self) -> str | None:
        """Get the ID of the most recent completed stage."""
        if self.stage_results:
            return self.stage_results[-1].stage_id
        return None
    
    def add_stage_result(self, result: StageResult) -> None:
        """Add a stage result to the context."""
        self.stage_results.append(result)
    
    def total_duration_ms(self) -> float:
        """Get total pipeline duration so far."""
        return (time.time() - self.start_time) * 1000


# =============================================================================
# Base Stage
# =============================================================================

class PipelineStage(ABC):
    """Base class for pipeline stages.
    
    All stages must:
    1. Log to TruthWriter on completion
    2. Track lineage via parent_stage_id
    3. Return a StageResult
    """
    
    def __init__(
        self,
        stage_name: str,
        truth_writer: TruthWriter | None = None,
        config: dict[str, Any] | None = None,
    ):
        self.stage_name = stage_name
        self.truth_writer = truth_writer
        self.config = config or {}
        self._execution_count = 0
    
    def execute(
        self,
        input_data: dict[str, Any],
        context: StageContext,
    ) -> StageResult:
        """Execute the stage with logging.
        
        Args:
            input_data: Input data for the stage
            context: Pipeline context for lineage tracking
            
        Returns:
            StageResult with output data and metadata
        """
        self._execution_count += 1
        start_time = time.time()
        stage_id = str(uuid4())
        parent_stage_id = context.get_last_stage_id()
        
        try:
            # Run the stage-specific logic
            output_data = self._run(input_data, context)
            
            duration_ms = (time.time() - start_time) * 1000
            
            result = StageResult(
                success=True,
                stage_name=self.stage_name,
                stage_id=stage_id,
                parent_stage_id=parent_stage_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                duration_ms=duration_ms,
                output_data=output_data,
                artifact_refs=output_data.get("artifact_refs", []),
            )
            
            self._log_stage_completion(result, context)
            context.add_stage_result(result)
            
            logger.debug(
                "Stage %s completed in %.2fms",
                self.stage_name,
                duration_ms
            )
            
            return result
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            
            result = StageResult(
                success=False,
                stage_name=self.stage_name,
                stage_id=stage_id,
                parent_stage_id=parent_stage_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                duration_ms=duration_ms,
                error=str(e),
            )
            
            self._log_stage_completion(result, context)
            context.add_stage_result(result)
            
            logger.error(
                "Stage %s failed after %.2fms: %s",
                self.stage_name,
                duration_ms,
                e
            )
            
            return result
    
    @abstractmethod
    def _run(
        self,
        input_data: dict[str, Any],
        context: StageContext,
    ) -> dict[str, Any]:
        """Run the stage-specific logic.
        
        Args:
            input_data: Input data for the stage
            context: Pipeline context
            
        Returns:
            Output data dictionary
        """
        pass
    
    def _log_stage_completion(
        self,
        result: StageResult,
        context: StageContext,
    ) -> None:
        """Log stage completion to TruthWriter.
        
        Args:
            result: Stage execution result
            context: Pipeline context
        """
        if self.truth_writer is None:
            return
        
        event = {
            "event_type": "pipeline_stage_complete",
            "event_id": str(uuid4()),
            "pipeline_id": context.pipeline_id,
            "trace_id": context.trace_id,
            "stage": result.to_dict(),
            "frame_id": context.frame_id,
        }
        
        try:
            self.truth_writer.write_event(event)
        except Exception as e:
            logger.error(f"Failed to log stage completion: {e}")
    
    @property
    def execution_count(self) -> int:
        """Number of times this stage has been executed."""
        return self._execution_count


# =============================================================================
# Concrete Stage Implementations
# =============================================================================

class CaptureStage(PipelineStage):
    """Stage 1: Frame capture from screen/video.
    
    Captures raw frame and initializes pipeline lineage.
    """
    
    def __init__(
        self,
        truth_writer: TruthWriter | None = None,
        config: dict[str, Any] | None = None,
    ):
        super().__init__("capture", truth_writer, config)
    
    def _run(
        self,
        input_data: dict[str, Any],
        context: StageContext,
    ) -> dict[str, Any]:
        """Capture frame and initialize lineage.
        
        Args:
            input_data: Must contain 'frame' (numpy array or PIL Image)
            context: Pipeline context
            
        Returns:
            Dict with frame reference and metadata
        """
        frame = input_data.get("frame")
        frame_id = input_data.get("frame_id") or f"frame_{uuid4().hex[:8]}"
        
        # Update context with frame_id
        context.frame_id = frame_id
        
        # Store frame path if provided
        frame_path = input_data.get("frame_path")
        
        return {
            "frame_id": frame_id,
            "frame": frame,
            "frame_path": frame_path,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "artifact_refs": [frame_path] if frame_path else [],
        }


class DetectionStage(PipelineStage):
    """Stage 2: YOLO object detection.
    
    Runs YOLO detection and produces detection results.
    """
    
    def __init__(
        self,
        detector: Any | None = None,
        truth_writer: TruthWriter | None = None,
        config: dict[str, Any] | None = None,
    ):
        super().__init__("detection", truth_writer, config)
        self.detector = detector
    
    def _run(
        self,
        input_data: dict[str, Any],
        context: StageContext,
    ) -> dict[str, Any]:
        """Run YOLO detection on the captured frame.
        
        Args:
            input_data: Must contain 'frame' from previous stage
            context: Pipeline context
            
        Returns:
            Dict with detections and metadata
        """
        from advanced_vision.trading.detector import YOLODetector
        
        frame = input_data.get("frame")
        if frame is None:
            raise ValueError("No frame provided for detection")
        
        # Use provided detector or create one
        detector = self.detector
        if detector is None:
            detector = YOLODetector()
        
        # Run detection (dry_run=True for safety if not configured otherwise)
        dry_run = self.config.get("dry_run", True)
        timestamp = input_data.get("timestamp") or datetime.now(timezone.utc).isoformat()
        
        result = detector.detect(frame, timestamp, dry_run=dry_run)
        
        # Convert elements to serializable format
        detections = []
        for elem in result.elements:
            detections.append({
                "element_id": elem.element_id,
                "element_type": elem.element_type.value if hasattr(elem.element_type, 'value') else str(elem.element_type),
                "bbox": elem.bbox.to_tuple() if hasattr(elem.bbox, 'to_tuple') else elem.bbox,
                "confidence": elem.confidence,
                "source": elem.source.value if hasattr(elem.source, 'value') else str(elem.source),
            })
        
        return {
            "frame_id": context.frame_id,
            "detections": detections,
            "inference_time_ms": result.inference_time_ms,
            "timestamp": timestamp,
            "detection_count": len(detections),
        }


class ScoutStage(PipelineStage):
    """Stage 3: Eagle Scout classification.
    
    Classifies detected regions and produces scout events.
    """
    
    def __init__(
        self,
        scout: Any | None = None,
        truth_writer: TruthWriter | None = None,
        config: dict[str, Any] | None = None,
    ):
        super().__init__("scout", truth_writer, config)
        self.scout = scout
    
    def _run(
        self,
        input_data: dict[str, Any],
        context: StageContext,
    ) -> dict[str, Any]:
        """Run Eagle Scout classification on detections.
        
        Args:
            input_data: Must contain 'detections' from previous stage
            context: Pipeline context
            
        Returns:
            Dict with classifications and metadata
        """
        detections = input_data.get("detections", [])
        frame_id = context.frame_id
        
        # Classify each detection
        classifications = []
        for detection in detections:
            # Simple classification based on element type
            element_type = detection.get("element_type", "unknown")
            confidence = detection.get("confidence", 0.5)
            
            # Map element types to scout classifications
            classification = self._classify_element(element_type, confidence)
            classifications.append({
                "detection": detection,
                "classification": classification["type"],
                "confidence": classification["confidence"],
                "risk_level": classification["risk_level"],
            })
        
        # Determine overall risk level
        risk_levels = [c["risk_level"] for c in classifications]
        overall_risk = self._aggregate_risk(risk_levels)
        
        # Determine if escalation is recommended
        escalation_recommended = overall_risk in (RiskLevel.HIGH, RiskLevel.CRITICAL)
        
        return {
            "frame_id": frame_id,
            "classifications": classifications,
            "classification_count": len(classifications),
            "overall_risk_level": overall_risk.value,
            "escalation_recommended": escalation_recommended,
            "scout_version": self.config.get("scout_version", "eagle2-2b-v1.0"),
        }
    
    def _classify_element(self, element_type: str, confidence: float) -> dict[str, Any]:
        """Classify a single element type.
        
        Args:
            element_type: Type of UI element
            confidence: Detection confidence
            
        Returns:
            Classification result with type, confidence, and risk level
        """
        # Trading-relevant elements get higher risk assessment
        high_risk_elements = {
            "error_modal", "warning_modal", "confirm_modal",
            "order_ticket_panel", "position_panel"
        }
        medium_risk_elements = {
            "chart_panel", "pnl_widget", "order_book"
        }
        
        if element_type.lower() in high_risk_elements:
            return {
                "type": "alert_condition" if "modal" in element_type else "ticket_update",
                "confidence": confidence,
                "risk_level": RiskLevel.HIGH if "error" in element_type else RiskLevel.MEDIUM,
            }
        elif element_type.lower() in medium_risk_elements:
            return {
                "type": "chart_update" if "chart" in element_type else "price_change",
                "confidence": confidence,
                "risk_level": RiskLevel.LOW,
            }
        else:
            return {
                "type": "benign_ui_change",
                "confidence": confidence,
                "risk_level": RiskLevel.NONE,
            }
    
    def _aggregate_risk(self, risk_levels: list[RiskLevel]) -> RiskLevel:
        """Aggregate multiple risk levels into overall risk.
        
        Args:
            risk_levels: List of risk levels
            
        Returns:
            Highest risk level from the list
        """
        if not risk_levels:
            return RiskLevel.NONE
        
        risk_order = [RiskLevel.NONE, RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
        max_index = 0
        for risk in risk_levels:
            try:
                idx = risk_order.index(risk)
                max_index = max(max_index, idx)
            except ValueError:
                pass
        
        return risk_order[max_index]


class GovernanceStage(PipelineStage):
    """Stage 4: Governor evaluation.
    
    Evaluates scout output through Governor and produces verdict.
    """
    
    def __init__(
        self,
        governor: Any | None = None,
        truth_writer: TruthWriter | None = None,
        config: dict[str, Any] | None = None,
    ):
        super().__init__("governance", truth_writer, config)
        self.governor = governor
    
    def _run(
        self,
        input_data: dict[str, Any],
        context: StageContext,
    ) -> dict[str, Any]:
        """Run Governor evaluation on scout output.
        
        Args:
            input_data: Must contain 'classifications' and 'overall_risk_level'
            context: Pipeline context
            
        Returns:
            Dict with GovernorVerdict and metadata
        """
        from advanced_vision.core.governor import Governor, ReviewerResult, PolicyContext
        from advanced_vision.core.governor_verdict import RiskLevel, PolicyClass
        
        # Use provided governor or create one
        governor = self.governor
        if governor is None:
            governor = Governor(truth_writer=self.truth_writer)
        
        # Extract risk level from input
        risk_level_str = input_data.get("overall_risk_level", "none")
        try:
            risk_level = RiskLevel(risk_level_str)
        except ValueError:
            risk_level = RiskLevel.MEDIUM
        
        # Create reviewer result from scout output
        reviewer_result = ReviewerResult(
            reviewer_id="eagle_scout",
            recommendation="evaluate",
            risk_assessment=risk_level,
            evidence=[c["detection"]["element_id"] for c in input_data.get("classifications", [])],
            confidence=input_data.get("classifications", [{}])[0].get("confidence", 0.5) if input_data.get("classifications") else 0.5,
            metadata={
                "classification_count": input_data.get("classification_count", 0),
                "escalation_recommended": input_data.get("escalation_recommended", False),
                "scout_version": input_data.get("scout_version", "unknown"),
            }
        )
        
        # Create policy context
        mode = self.config.get("mode", "trading")
        policy_context = PolicyContext(
            mode=mode,
            trust_boundary_clear=self.config.get("trust_boundary_clear", True),
            external_side_effects=self.config.get("external_side_effects", False),
            has_trading_implications=mode == "trading",
            sensitive_data_involved=self.config.get("sensitive_data_involved", False),
            user_present=self.config.get("user_present", False),
            artifact_refs=[context.frame_id] if context.frame_id else [],
        )
        
        # Determine policy class
        policy_class_str = self.config.get("policy_class", "trading_analysis")
        policy_class = PolicyClass(policy_class_str)
        
        # Run governor evaluation
        verdict = governor.evaluate(
            recommendation=reviewer_result,
            context=policy_context,
            policy_class=policy_class,
            source_event_id=context.pipeline_id,
        )
        
        return {
            "frame_id": context.frame_id,
            "verdict": verdict,
            "verdict_dict": verdict.to_dict(),
            "decision": verdict.decision.value,
            "risk_level": verdict.risk_level.value,
            "policy_class": verdict.policy_class.value,
            "trace_id": verdict.lineage.trace_id,
        }


class ExecutionStage(PipelineStage):
    """Stage 5: Execution gate validation.
    
    Validates preconditions before allowing execution.
    """
    
    def __init__(
        self,
        execution_gate: Any | None = None,
        truth_writer: TruthWriter | None = None,
        config: dict[str, Any] | None = None,
    ):
        super().__init__("execution", truth_writer, config)
        self.execution_gate = execution_gate
    
    def _run(
        self,
        input_data: dict[str, Any],
        context: StageContext,
    ) -> dict[str, Any]:
        """Run execution gate validation.
        
        Args:
            input_data: Must contain 'verdict' from previous stage
            context: Pipeline context
            
        Returns:
            Dict with GateDecision and metadata
        """
        from advanced_vision.core.execution_gate import ExecutionGate
        
        # Use provided execution_gate or create one
        execution_gate = self.execution_gate
        if execution_gate is None:
            execution_gate = ExecutionGate()
        
        # Get verdict from previous stage
        verdict = input_data.get("verdict")
        if verdict is None:
            raise ValueError("No verdict provided for execution gate validation")
        
        # Create packet for execution gate
        packet = {
            "frame_id": context.frame_id,
            "execution_candidate": True,
            "mode": self.config.get("mode", "trading"),
            "governor_verdict": verdict.to_dict(),
            "pipeline_id": context.pipeline_id,
            "trace_id": input_data.get("trace_id"),
        }
        
        # Run execution gate validation
        gate_decision = execution_gate.process_with_verdict(packet, verdict)
        
        return {
            "frame_id": context.frame_id,
            "gate_decision": gate_decision,
            "can_execute": gate_decision.can_execute,
            "is_blocked": gate_decision.is_blocked,
            "requires_recheck": gate_decision.requires_recheck,
            "requires_approval": gate_decision.requires_approval,
            "route_to": gate_decision.route_to,
            "verdict": verdict,
            "packet": gate_decision.packet,
        }


# =============================================================================
# Stage Factory
# =============================================================================

def create_stage(
    stage_type: str,
    truth_writer: TruthWriter | None = None,
    config: dict[str, Any] | None = None,
    **kwargs: Any,
) -> PipelineStage:
    """Factory function to create pipeline stages.
    
    Args:
        stage_type: Type of stage ('capture', 'detection', 'scout', 'governance', 'execution')
        truth_writer: TruthWriter for logging
        config: Stage configuration
        **kwargs: Additional stage-specific arguments
        
    Returns:
        PipelineStage instance
    """
    stages = {
        "capture": CaptureStage,
        "detection": DetectionStage,
        "scout": ScoutStage,
        "governance": GovernanceStage,
        "execution": ExecutionStage,
    }
    
    stage_class = stages.get(stage_type)
    if stage_class is None:
        raise ValueError(f"Unknown stage type: {stage_type}")
    
    return stage_class(truth_writer=truth_writer, config=config, **kwargs)
