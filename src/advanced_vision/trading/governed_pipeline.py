"""Governed Pipeline - Integrated vision pipeline with Governor enforcement.

This module provides the GovernedPipeline class which:
1. Integrates capture → YOLO → Eagle → Governor → ExecutionGate
2. Provides process_frame() method for frame processing
3. Returns pipeline result with verdict attached
4. Handles recheck routing internally
5. Logs all stages to TruthWriter

Target hot path:
    Capture → YOLO → Eagle Scout
                  ↓
             Governor.evaluate(policy_class="trading_analysis")
                  ↓
             ExecutionGate.process()
                  ↓
        ┌─────────┴─────────┐
        ↓                   ↓
    TruthWriter      WSS SchemaAdapter
        ↓                   ↓
    Event Log       Subscribers
        ↓
    Execution (if verdict allows)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from advanced_vision.core.truth_writer import TruthWriter
from advanced_vision.core.governor import Governor, ReviewerResult, PolicyContext
from advanced_vision.core.governor_verdict import GovernorVerdict, Decision, RiskLevel, PolicyClass
from advanced_vision.core.execution_gate import ExecutionGate, GateDecision
from advanced_vision.core.execution_precondition import ExecutionPrecondition

from advanced_vision.trading.pipeline_stages import (
    StageContext,
    StageResult,
    CaptureStage,
    DetectionStage,
    ScoutStage,
    GovernanceStage,
    ExecutionStage,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Pipeline Result
# =============================================================================

@dataclass
class PipelineResult:
    """Result from the governed pipeline.
    
    Attributes:
        success: Whether pipeline completed successfully
        frame_id: Identifier for the processed frame
        pipeline_id: Unique identifier for this pipeline execution
        trace_id: Distributed trace ID
        verdict: GovernorVerdict from governance stage (if reached)
        gate_decision: GateDecision from execution stage (if reached)
        stages: List of all stage results
        total_duration_ms: Total pipeline execution time
        can_execute: Whether execution is allowed based on verdict
        route_to: Routing destination if blocked (recheck, approval_queue)
        error: Error message if pipeline failed
        metadata: Additional metadata
    """
    success: bool
    frame_id: str | None = None
    pipeline_id: str = field(default_factory=lambda: str(uuid4()))
    trace_id: str = field(default_factory=lambda: str(uuid4()))
    verdict: GovernorVerdict | None = None
    gate_decision: GateDecision | None = None
    stages: list[StageResult] = field(default_factory=list)
    total_duration_ms: float = 0.0
    can_execute: bool = False
    route_to: str | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_blocked(self) -> bool:
        """Check if execution is blocked."""
        return not self.can_execute
    
    @property
    def requires_recheck(self) -> bool:
        """Check if this result requires recheck routing."""
        return self.route_to == "recheck"
    
    @property
    def requires_approval(self) -> bool:
        """Check if this result requires approval."""
        return self.route_to == "approval_queue"
    
    @property
    def final_decision(self) -> str:
        """Get the final decision string."""
        if self.verdict:
            return self.verdict.decision.value
        return "unknown"
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "success": self.success,
            "frame_id": self.frame_id,
            "pipeline_id": self.pipeline_id,
            "trace_id": self.trace_id,
            "verdict": self.verdict.to_dict() if self.verdict else None,
            "gate_decision": {
                "can_execute": self.gate_decision.can_execute if self.gate_decision else None,
                "route_to": self.gate_decision.route_to if self.gate_decision else None,
            } if self.gate_decision else None,
            "stage_count": len(self.stages),
            "total_duration_ms": self.total_duration_ms,
            "can_execute": self.can_execute,
            "route_to": self.route_to,
            "final_decision": self.final_decision,
            "error": self.error,
        }


# =============================================================================
# Governed Pipeline
# =============================================================================

class GovernedPipeline:
    """Integrated vision pipeline with Governor enforcement.
    
    This class orchestrates the full pipeline from capture to execution gate,
    ensuring Governor verdicts are produced and validated before any execution.
    
    Usage:
        pipeline = GovernedPipeline(
            truth_writer=truth_writer,
            config={"mode": "trading", "policy_class": "trading_analysis"}
        )
        
        result = pipeline.process_frame(frame, context={"source": "screen_capture"})
        
        if result.can_execute:
            execute_action(result)
        elif result.requires_recheck:
            route_to_recheck(result)
        elif result.requires_approval:
            send_to_approval_queue(result)
    """
    
    def __init__(
        self,
        truth_writer: TruthWriter | None = None,
        governor: Governor | None = None,
        execution_gate: ExecutionGate | None = None,
        config: dict[str, Any] | None = None,
    ):
        """Initialize the governed pipeline.
        
        Args:
            truth_writer: TruthWriter for event logging (required)
            governor: Governor instance (created if not provided)
            execution_gate: ExecutionGate instance (created if not provided)
            config: Pipeline configuration
        """
        self.truth_writer = truth_writer or TruthWriter("/tmp/advanced_vision/truth")
        self.config = config or {}
        
        # Create or use provided governor and execution gate
        self.governor = governor or Governor(truth_writer=self.truth_writer)
        self.execution_gate = execution_gate or ExecutionGate(
            governor=self.governor,
        )
        
        # Create stages
        stage_config = self.config.get("stages", {})
        
        self._capture_stage = CaptureStage(
            truth_writer=self.truth_writer,
            config=stage_config.get("capture", {}),
        )
        
        self._detection_stage = DetectionStage(
            truth_writer=self.truth_writer,
            config=stage_config.get("detection", {}),
        )
        
        self._scout_stage = ScoutStage(
            truth_writer=self.truth_writer,
            config=stage_config.get("scout", {}),
        )
        
        self._governance_stage = GovernanceStage(
            governor=self.governor,
            truth_writer=self.truth_writer,
            config=stage_config.get("governance", self.config),
        )
        
        self._execution_stage = ExecutionStage(
            execution_gate=self.execution_gate,
            truth_writer=self.truth_writer,
            config=stage_config.get("execution", self.config),
        )
        
        # Recheck handler
        self._recheck_handler: callable | None = None
        
        # Statistics
        self._process_count = 0
        self._blocked_count = 0
        self._recheck_count = 0
        self._approval_count = 0
        self._error_count = 0
        
        logger.info("GovernedPipeline initialized with mode=%s", self.config.get("mode", "trading"))
    
    def process_frame(
        self,
        frame: Any,
        context: dict[str, Any] | None = None,
    ) -> PipelineResult:
        """Process a frame through the full governed pipeline.
        
        This is the main entry point for frame processing. It runs the frame
        through all stages: capture → detection → scout → governance → execution.
        
        Args:
            frame: The frame to process (numpy array or PIL Image)
            context: Optional context dictionary with metadata
            
        Returns:
            PipelineResult with verdict and execution decision
        """
        self._process_count += 1
        start_time = time.time()
        context = context or {}
        
        # Create pipeline context for lineage tracking
        pipeline_id = str(uuid4())
        trace_id = context.get("trace_id") or str(uuid4())
        frame_id = context.get("frame_id") or f"frame_{uuid4().hex[:8]}"
        
        stage_context = StageContext(
            trace_id=trace_id,
            pipeline_id=pipeline_id,
            frame_id=frame_id,
            metadata=context,
        )
        
        try:
            # Stage 1: Capture
            capture_input = {
                "frame": frame,
                "frame_id": frame_id,
                "frame_path": context.get("frame_path"),
            }
            capture_result = self._capture_stage.execute(capture_input, stage_context)
            
            if capture_result.failed:
                return self._create_error_result(
                    stage_context,
                    start_time,
                    capture_result,
                    "Capture stage failed",
                )
            
            # Stage 2: Detection (YOLO)
            detection_result = self._detection_stage.execute(
                capture_result.output_data,
                stage_context,
            )
            
            if detection_result.failed:
                return self._create_error_result(
                    stage_context,
                    start_time,
                    detection_result,
                    "Detection stage failed",
                )
            
            # Stage 3: Scout (Eagle)
            scout_result = self._scout_stage.execute(
                detection_result.output_data,
                stage_context,
            )
            
            if scout_result.failed:
                return self._create_error_result(
                    stage_context,
                    start_time,
                    scout_result,
                    "Scout stage failed",
                )
            
            # Stage 4: Governance (Governor evaluation)
            governance_result = self._governance_stage.execute(
                scout_result.output_data,
                stage_context,
            )
            
            if governance_result.failed:
                return self._create_error_result(
                    stage_context,
                    start_time,
                    governance_result,
                    "Governance stage failed",
                )
            
            # Extract verdict from governance result
            verdict = governance_result.output_data.get("verdict")
            
            # Stage 5: Execution Gate
            execution_result = self._execution_stage.execute(
                governance_result.output_data,
                stage_context,
            )
            
            if execution_result.failed:
                return self._create_error_result(
                    stage_context,
                    start_time,
                    execution_result,
                    "Execution stage failed",
                )
            
            # Extract gate decision
            gate_decision = execution_result.output_data.get("gate_decision")
            
            # Determine final routing
            can_execute = execution_result.output_data.get("can_execute", False)
            route_to = execution_result.output_data.get("route_to")
            
            # Update statistics
            if not can_execute:
                self._blocked_count += 1
            if route_to == "recheck":
                self._recheck_count += 1
                self._handle_recheck(pipeline_id, verdict, stage_context)
            if route_to == "approval_queue":
                self._approval_count += 1
            
            # Log pipeline completion
            total_duration_ms = (time.time() - start_time) * 1000
            self._log_pipeline_completion(
                pipeline_id=pipeline_id,
                frame_id=frame_id,
                trace_id=trace_id,
                verdict=verdict,
                can_execute=can_execute,
                route_to=route_to,
                duration_ms=total_duration_ms,
                stages=stage_context.stage_results,
            )
            
            logger.info(
                "Pipeline %s completed in %.2fms: decision=%s can_execute=%s",
                pipeline_id[:8],
                total_duration_ms,
                verdict.decision.value if verdict else "none",
                can_execute,
            )
            
            return PipelineResult(
                success=True,
                frame_id=frame_id,
                pipeline_id=pipeline_id,
                trace_id=trace_id,
                verdict=verdict,
                gate_decision=gate_decision,
                stages=stage_context.stage_results,
                total_duration_ms=total_duration_ms,
                can_execute=can_execute,
                route_to=route_to,
            )
            
        except Exception as e:
            self._error_count += 1
            total_duration_ms = (time.time() - start_time) * 1000
            
            logger.exception("Pipeline %s failed: %s", pipeline_id[:8], e)
            
            # Log error
            self._log_pipeline_error(
                pipeline_id=pipeline_id,
                frame_id=frame_id,
                trace_id=trace_id,
                error=str(e),
                duration_ms=total_duration_ms,
            )
            
            return PipelineResult(
                success=False,
                frame_id=frame_id,
                pipeline_id=pipeline_id,
                trace_id=trace_id,
                stages=stage_context.stage_results,
                total_duration_ms=total_duration_ms,
                error=str(e),
            )
    
    def _create_error_result(
        self,
        stage_context: StageContext,
        start_time: float,
        failed_stage: StageResult,
        message: str,
    ) -> PipelineResult:
        """Create an error result from a failed stage.
        
        Args:
            stage_context: Pipeline context with stage results
            start_time: Pipeline start time
            failed_stage: The stage that failed
            message: Error message
            
        Returns:
            PipelineResult with error information
        """
        total_duration_ms = (time.time() - start_time) * 1000
        error_msg = f"{message}: {failed_stage.error}"
        
        self._error_count += 1
        
        logger.error(
            "Pipeline %s failed at stage %s: %s",
            stage_context.pipeline_id[:8],
            failed_stage.stage_name,
            error_msg,
        )
        
        return PipelineResult(
            success=False,
            frame_id=stage_context.frame_id,
            pipeline_id=stage_context.pipeline_id,
            trace_id=stage_context.trace_id,
            stages=stage_context.stage_results,
            total_duration_ms=total_duration_ms,
            error=error_msg,
        )
    
    def _handle_recheck(
        self,
        pipeline_id: str,
        verdict: GovernorVerdict | None,
        stage_context: StageContext,
    ) -> None:
        """Handle recheck routing.
        
        Args:
            pipeline_id: Pipeline ID
            verdict: Governor verdict that triggered recheck
            stage_context: Pipeline context
        """
        if self._recheck_handler:
            try:
                self._recheck_handler(
                    pipeline_id=pipeline_id,
                    verdict=verdict,
                    stage_context=stage_context,
                )
            except Exception as e:
                logger.error("Recheck handler failed: %s", e)
        
        # Log recheck event
        if self.truth_writer:
            self.truth_writer.write_event({
                "event_type": "pipeline_recheck",
                "event_id": str(uuid4()),
                "pipeline_id": pipeline_id,
                "trace_id": stage_context.trace_id,
                "frame_id": stage_context.frame_id,
                "verdict_id": verdict.verdict_id if verdict else None,
                "reason": verdict.rationale if verdict else "recheck_required",
            })
    
    def set_recheck_handler(self, handler: callable) -> None:
        """Set a handler for recheck routing.
        
        Args:
            handler: Callable that accepts (pipeline_id, verdict, stage_context)
        """
        self._recheck_handler = handler
    
    def _log_pipeline_completion(
        self,
        pipeline_id: str,
        frame_id: str,
        trace_id: str,
        verdict: GovernorVerdict | None,
        can_execute: bool,
        route_to: str | None,
        duration_ms: float,
        stages: list[StageResult],
    ) -> None:
        """Log pipeline completion to TruthWriter.
        
        Args:
            pipeline_id: Pipeline ID
            frame_id: Frame ID
            trace_id: Trace ID
            verdict: Governor verdict
            can_execute: Whether execution is allowed
            route_to: Routing destination
            duration_ms: Pipeline duration
            stages: List of stage results
        """
        if self.truth_writer is None:
            return
        
        event = {
            "event_type": "pipeline_complete",
            "event_id": str(uuid4()),
            "pipeline_id": pipeline_id,
            "trace_id": trace_id,
            "frame_id": frame_id,
            "verdict_id": verdict.verdict_id if verdict else None,
            "decision": verdict.decision.value if verdict else None,
            "can_execute": can_execute,
            "route_to": route_to,
            "duration_ms": duration_ms,
            "stage_summary": [
                {
                    "stage_name": s.stage_name,
                    "stage_id": s.stage_id,
                    "duration_ms": s.duration_ms,
                    "success": s.success,
                }
                for s in stages
            ],
        }
        
        try:
            self.truth_writer.write_event(event)
        except Exception as e:
            logger.error("Failed to log pipeline completion: %s", e)
    
    def _log_pipeline_error(
        self,
        pipeline_id: str,
        frame_id: str,
        trace_id: str,
        error: str,
        duration_ms: float,
    ) -> None:
        """Log pipeline error to TruthWriter.
        
        Args:
            pipeline_id: Pipeline ID
            frame_id: Frame ID
            trace_id: Trace ID
            error: Error message
            duration_ms: Pipeline duration
        """
        if self.truth_writer is None:
            return
        
        event = {
            "event_type": "pipeline_error",
            "event_id": str(uuid4()),
            "pipeline_id": pipeline_id,
            "trace_id": trace_id,
            "frame_id": frame_id,
            "error": error,
            "duration_ms": duration_ms,
        }
        
        try:
            self.truth_writer.write_event(event)
        except Exception as e:
            logger.error("Failed to log pipeline error: %s", e)
    
    @property
    def stats(self) -> dict[str, Any]:
        """Get pipeline statistics."""
        return {
            "process_count": self._process_count,
            "blocked_count": self._blocked_count,
            "recheck_count": self._recheck_count,
            "approval_count": self._approval_count,
            "error_count": self._error_count,
            "block_rate": self._blocked_count / max(1, self._process_count),
            "recheck_rate": self._recheck_count / max(1, self._process_count),
        }
    
    def reset_stats(self) -> None:
        """Reset pipeline statistics."""
        self._process_count = 0
        self._blocked_count = 0
        self._recheck_count = 0
        self._approval_count = 0
        self._error_count = 0


# =============================================================================
# Convenience Functions
# =============================================================================

def create_governed_pipeline(
    truth_dir: str = "/tmp/advanced_vision/truth",
    mode: str = "trading",
    policy_class: str = "trading_analysis",
    **config: Any,
) -> GovernedPipeline:
    """Factory function to create a governed pipeline.
    
    Args:
        truth_dir: Directory for truth logs
        mode: Operating mode ("trading" or "ui")
        policy_class: Default policy class for governor
        **config: Additional configuration
        
    Returns:
        Configured GovernedPipeline instance
    """
    truth_writer = TruthWriter(truth_dir)
    
    pipeline_config = {
        "mode": mode,
        "policy_class": policy_class,
        "external_side_effects": config.get("external_side_effects", False),
        "user_present": config.get("user_present", False),
        "trust_boundary_clear": config.get("trust_boundary_clear", True),
    }
    
    return GovernedPipeline(
        truth_writer=truth_writer,
        config=pipeline_config,
    )
