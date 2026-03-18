"""ExecutionGate - Gate between reviewers and execution.

This module provides the ExecutionGate class which:
1. Processes reviewer outputs through the Governor
2. Attaches verdicts to packets
3. Blocks execution if preconditions fail
4. Routes recheck verdicts appropriately

Core doctrine: No direct reviewer → execution paths exist.
All execution candidates must pass through the ExecutionGate.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional
from uuid import uuid4

from .governor import Governor, PolicyContext, ReviewerResult
from .governor_verdict import (
    Decision,
    GovernorVerdict,
    PolicyClass,
    RiskLevel,
)
from .execution_precondition import ExecutionPrecondition
from .precondition_result import PreconditionResult

logger = logging.getLogger(__name__)


@dataclass
class GateDecision:
    """Decision from the ExecutionGate.
    
    This encapsulates the complete result of processing a reviewer output
    through the ExecutionGate, including the verdict and routing decision.
    
    Attributes:
        can_execute: Whether execution is allowed
        verdict: The GovernorVerdict that was produced/evaluated
        precondition_result: Result of precondition checks
        route_to: Where to route if not executing (e.g., 'recheck', 'approval_queue')
        packet: The packet (with verdict attached) for downstream processing
        context: Additional context for routing decisions
    """
    can_execute: bool
    verdict: Optional[GovernorVerdict]
    precondition_result: PreconditionResult
    route_to: Optional[str] = None
    packet: Optional[dict[str, Any]] = None
    context: dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_blocked(self) -> bool:
        """Check if execution is blocked."""
        return not self.can_execute
    
    @property
    def requires_recheck(self) -> bool:
        """Check if this decision requires routing back for recheck."""
        return self.route_to == "recheck"
    
    @property
    def requires_approval(self) -> bool:
        """Check if this decision requires approval."""
        return self.route_to == "approval_queue"


class ExecutionGate:
    """Gate between reviewers and execution.
    
    The ExecutionGate ensures that:
    1. All reviewer outputs are evaluated by the Governor
    2. GovernorVerdicts are attached to packets
    3. Execution preconditions are validated
    4. Execution candidates are blocked without valid verdicts
    5. Recheck verdicts are routed appropriately
    
    Usage:
        gate = ExecutionGate(governor=governor)
        
        # Process reviewer output
        decision = gate.process(reviewer_output, context)
        
        if decision.can_execute:
            execute_action(decision.packet)
        elif decision.requires_recheck:
            route_to_recheck(decision.packet)
        elif decision.requires_approval:
            send_to_approval_queue(decision.packet)
    """
    
    def __init__(
        self,
        governor: Optional[Governor] = None,
        precondition: Optional[ExecutionPrecondition] = None,
        default_policy_class: PolicyClass = PolicyClass.OBSERVE,
    ):
        """Initialize ExecutionGate.
        
        Args:
            governor: Governor instance for evaluating recommendations
            precondition: ExecutionPrecondition instance (created if not provided)
            default_policy_class: Default policy class for evaluations
        """
        self.governor = governor or Governor()
        self.precondition = precondition or ExecutionPrecondition()
        self.default_policy_class = default_policy_class
        self._process_count = 0
        self._blocked_count = 0
        
        logger.info("ExecutionGate initialized")
    
    def process(
        self,
        reviewer_output: dict[str, Any],
        context: Optional[dict[str, Any]] = None,
    ) -> GateDecision:
        """Process a reviewer output through the gate.
        
        This is the main entry point. It:
        1. Evaluates the reviewer output through the Governor
        2. Creates/attaches a GovernorVerdict
        3. Validates execution preconditions
        4. Returns a GateDecision with routing information
        
        Args:
            reviewer_output: The reviewer's output to process
            context: Optional context for the evaluation
            
        Returns:
            GateDecision with verdict and routing information
        """
        self._process_count += 1
        context = context or {}
        
        # Step 1: Extract or create reviewer result
        reviewer_result = self._extract_reviewer_result(reviewer_output)
        
        # Step 2: Determine policy class
        policy_class = self._determine_policy_class(reviewer_output, context)
        
        # Step 3: Create policy context
        policy_context = self._create_policy_context(context)
        
        # Step 4: Evaluate through Governor
        try:
            verdict = self.governor.evaluate(
                recommendation=reviewer_result,
                context=policy_context,
                policy_class=policy_class,
                source_event_id=context.get("source_event_id"),
            )
            logger.debug(
                "Governor evaluation complete: %s -> %s",
                policy_class.value,
                verdict.decision.value
            )
        except Exception as e:
            logger.error("Governor evaluation failed: %s", e)
            # Create a block verdict on error
            verdict = self._create_error_block_verdict(
                reviewer_result=reviewer_result,
                error=str(e),
                source_event_id=context.get("source_event_id"),
            )
        
        # Step 5: Create packet with verdict attached
        packet = self._attach_verdict_to_packet(reviewer_output, verdict)
        
        # Step 6: Check execution preconditions
        precondition_result = self.precondition.check(packet, verdict)
        
        # Step 7: Determine routing based on verdict and preconditions
        if not precondition_result.allowed:
            self._blocked_count += 1
            route_to = self._determine_route(precondition_result, verdict)
            
            logger.warning(
                "ExecutionGate BLOCKED: verdict=%s reason=%s route_to=%s",
                verdict.verdict_id if verdict else None,
                precondition_result.reason,
                route_to
            )
            
            return GateDecision(
                can_execute=False,
                verdict=verdict,
                precondition_result=precondition_result,
                route_to=route_to,
                packet=packet,
                context={"violation_type": precondition_result.violation_type},
            )
        
        # Step 8: Execution allowed
        logger.debug(
            "ExecutionGate ALLOWED: verdict=%s decision=%s",
            verdict.verdict_id,
            verdict.decision.value
        )
        
        return GateDecision(
            can_execute=True,
            verdict=verdict,
            precondition_result=precondition_result,
            route_to=None,
            packet=packet,
            context={},
        )
    
    def process_with_verdict(
        self,
        packet: dict[str, Any],
        verdict: GovernorVerdict,
    ) -> GateDecision:
        """Process a packet that already has a verdict attached.
        
        This is used when a verdict was previously generated and we need to
        validate preconditions before execution.
        
        Args:
            packet: The packet with execution_candidate flag
            verdict: The GovernorVerdict to validate
            
        Returns:
            GateDecision with routing information
        """
        self._process_count += 1
        
        # Check preconditions with the provided verdict
        precondition_result = self.precondition.check(packet, verdict)
        
        # Attach verdict to packet
        packet = self._attach_verdict_to_packet(packet, verdict)
        
        if not precondition_result.allowed:
            self._blocked_count += 1
            route_to = self._determine_route(precondition_result, verdict)
            
            logger.warning(
                "ExecutionGate BLOCKED (existing verdict): verdict=%s reason=%s",
                verdict.verdict_id,
                precondition_result.reason
            )
            
            return GateDecision(
                can_execute=False,
                verdict=verdict,
                precondition_result=precondition_result,
                route_to=route_to,
                packet=packet,
                context={"violation_type": precondition_result.violation_type},
            )
        
        logger.debug(
            "ExecutionGate ALLOWED (existing verdict): verdict=%s",
            verdict.verdict_id
        )
        
        return GateDecision(
            can_execute=True,
            verdict=verdict,
            precondition_result=precondition_result,
            route_to=None,
            packet=packet,
            context={},
        )
    
    def _extract_reviewer_result(self, reviewer_output: dict[str, Any]) -> ReviewerResult:
        """Extract or create a ReviewerResult from reviewer output.
        
        Args:
            reviewer_output: Raw reviewer output
            
        Returns:
            ReviewerResult for Governor evaluation
        """
        # If already a ReviewerResult-like dict, extract fields
        if isinstance(reviewer_output, dict):
            return ReviewerResult(
                reviewer_id=reviewer_output.get("reviewer_id", "unknown"),
                recommendation=reviewer_output.get("recommendation", "unknown"),
                risk_assessment=RiskLevel(
                    reviewer_output.get("risk_assessment", "medium")
                ),
                evidence=reviewer_output.get("evidence", []),
                confidence=reviewer_output.get("confidence", 0.5),
                metadata=reviewer_output.get("metadata", {}),
            )
        
        # Default fallback
        return ReviewerResult(
            reviewer_id="unknown",
            recommendation="unknown",
            risk_assessment=RiskLevel.MEDIUM,
        )
    
    def _determine_policy_class(
        self,
        reviewer_output: dict[str, Any],
        context: dict[str, Any],
    ) -> PolicyClass:
        """Determine the policy class for this evaluation.
        
        Args:
            reviewer_output: Reviewer output to analyze
            context: Context with hints
            
        Returns:
            PolicyClass for Governor evaluation
        """
        # Check context for explicit policy class
        if "policy_class" in context:
            policy_class_str = context["policy_class"]
            if isinstance(policy_class_str, str):
                try:
                    return PolicyClass(policy_class_str)
                except ValueError:
                    pass
            elif isinstance(policy_class_str, PolicyClass):
                return policy_class_str
        
        # Check if this is an execution candidate
        if reviewer_output.get("execution_candidate", False):
            # Check for trading execution
            if reviewer_output.get("mode") == "trading" or context.get("mode") == "trading":
                return PolicyClass.TRADING_EXECUTION_CANDIDATE
            # UI interaction candidate
            if reviewer_output.get("ui_interaction", False):
                return PolicyClass.UI_INTERACTION_CANDIDATE
            # Default execution candidate
            return PolicyClass.PROMOTION_CANDIDATE
        
        # Check for trading analysis
        if reviewer_output.get("mode") == "trading" or context.get("mode") == "trading":
            return PolicyClass.TRADING_ANALYSIS
        
        # Check for sensitive data
        if reviewer_output.get("sensitive_data", False) or context.get("sensitive_data"):
            return PolicyClass.SENSITIVE_DATA_ACCESS
        
        # Default
        return self.default_policy_class
    
    def _create_policy_context(self, context: dict[str, Any]) -> PolicyContext:
        """Create PolicyContext from dict context.
        
        Args:
            context: Context dictionary
            
        Returns:
            PolicyContext for Governor
        """
        return PolicyContext(
            mode=context.get("mode", "ui"),
            trust_boundary_clear=context.get("trust_boundary_clear", True),
            external_side_effects=context.get("external_side_effects", False),
            has_trading_implications=context.get("has_trading_implications", False),
            sensitive_data_involved=context.get("sensitive_data_involved", False),
            user_present=context.get("user_present", False),
            artifact_refs=context.get("artifact_refs", []),
        )
    
    def _attach_verdict_to_packet(
        self,
        packet: dict[str, Any],
        verdict: GovernorVerdict,
    ) -> dict[str, Any]:
        """Attach a GovernorVerdict to a packet.
        
        Args:
            packet: Original packet
            verdict: GovernorVerdict to attach
            
        Returns:
            Packet with verdict attached
        """
        # Create a copy to avoid mutating original
        packet_copy = dict(packet)
        packet_copy["governor_verdict"] = verdict.to_dict()
        return packet_copy
    
    def _determine_route(
        self,
        precondition_result: PreconditionResult,
        verdict: Optional[GovernorVerdict],
    ) -> Optional[str]:
        """Determine routing for blocked execution.
        
        Args:
            precondition_result: Result of precondition checks
            verdict: The verdict that was evaluated
            
        Returns:
            Route destination or None if not routing
        """
        violation_type = precondition_result.violation_type
        
        if violation_type == "recheck_required":
            return "recheck"
        elif violation_type == "approval_required":
            return "approval_queue"
        elif violation_type == "missing_verdict":
            return "recheck"  # Missing verdict needs review
        elif violation_type == "stale_verdict":
            return "recheck"  # Stale verdict needs re-evaluation
        elif verdict and verdict.decision == Decision.RECHECK:
            return "recheck"
        elif verdict and verdict.decision == Decision.REQUIRE_APPROVAL:
            return "approval_queue"
        
        # Default: blocked without routing
        return None
    
    def _create_error_block_verdict(
        self,
        reviewer_result: ReviewerResult,
        error: str,
        source_event_id: Optional[str] = None,
    ) -> GovernorVerdict:
        """Create a block verdict when Governor evaluation fails.
        
        Args:
            reviewer_result: The reviewer result that failed
            error: Error message
            source_event_id: Source event ID
            
        Returns:
            Block GovernorVerdict
        """
        from .governor_verdict import create_verdict
        
        return create_verdict(
            risk_level=RiskLevel.CRITICAL,
            decision=Decision.BLOCK,
            policy_class=PolicyClass.OBSERVE,
            rationale=f"Governor evaluation error: {error}",
            source_event=source_event_id or str(uuid4()),
            reviewer=reviewer_result.reviewer_id,
            trace_id=str(uuid4()),
            tags=["error", "governor_failure"],
            overrides_applied=["governor_error"],
        )
    
    @property
    def process_count(self) -> int:
        """Total number of packets processed through the gate."""
        return self._process_count
    
    @property
    def blocked_count(self) -> int:
        """Total number of executions blocked."""
        return self._blocked_count
