"""Governor - Constitutional gate between reviewers and execution.

The Governor evaluates reviewer recommendations and emits authoritative decisions.
No execution candidate proceeds without a structured GovernorVerdict.

Core doctrine: Reviewer outputs are advisory evidence, not executable authority.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Protocol
from uuid import uuid4

from .governor_verdict import (
    create_verdict,
    Decision,
    GovernorVerdict,
    Lineage,
    PolicyClass,
    RiskLevel,
)

logger = logging.getLogger(__name__)


@dataclass
class ReviewerResult:
    """Input from a reviewer to be evaluated by the Governor.
    
    Attributes:
        reviewer_id: Identifier for the reviewer (e.g., "eagle", "qwen", "aya")
        recommendation: The reviewer's recommendation (continue, block, etc.)
        risk_assessment: Reviewer's assessed risk level
        evidence: List of artifact references supporting the recommendation
        confidence: Reviewer's confidence score (0.0-1.0)
        metadata: Additional context from the reviewer
    """
    reviewer_id: str
    recommendation: str
    risk_assessment: RiskLevel
    evidence: list[str] = field(default_factory=list)
    confidence: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PolicyContext:
    """Context for policy evaluation.
    
    Attributes:
        mode: Operating mode ("trading" or "ui")
        trust_boundary_clear: Whether the trust boundary is well-defined
        external_side_effects: Whether this action has external side effects
        has_trading_implications: Whether this affects trading positions
        sensitive_data_involved: Whether sensitive data is accessed
        user_present: Whether a user is present for approval
        artifact_refs: References to source evidence artifacts
    """
    mode: str = "ui"  # "trading" or "ui"
    trust_boundary_clear: bool = True
    external_side_effects: bool = False
    has_trading_implications: bool = False
    sensitive_data_involved: bool = False
    user_present: bool = False
    artifact_refs: list[str] = field(default_factory=list)


@dataclass
class PolicyRule:
    """A policy rule defining max and minimum gates for a policy class.
    
    Attributes:
        policy_class: The policy class this rule applies to
        default_max: Default maximum decision allowed (without overrides)
        minimum_gate: Minimum decision required (escalates lower decisions)
        description: Human-readable description of this policy
    """
    policy_class: PolicyClass
    default_max: Decision
    minimum_gate: Decision | None
    description: str


class TruthWriterProtocol(Protocol):
    """Protocol for TruthWriter integration.
    
    This allows the Governor to work with any truth writer that supports
    the write_event method.
    """
    
    def write_event(self, event: dict[str, Any]) -> Any:
        """Write an event to the truth log."""
        ...


class Governor:
    """Constitutional gate for reviewer recommendations.
    
    The Governor evaluates reviewer outputs and emits structured verdicts.
    Every path returns a GovernorVerdict - no execution without a verdict.
    
    Usage:
        governor = Governor(truth_writer=truth_writer)
        
        verdict = governor.evaluate(
            recommendation=reviewer_result,
            context=policy_context,
            policy_class=PolicyClass.TRADING_ANALYSIS
        )
        
        if verdict.is_execution_allowed():
            execute_action()
    """
    
    # Policy class matrix - default max and minimum gates per class
    DEFAULT_POLICY_MATRIX: dict[PolicyClass, PolicyRule] = {
        PolicyClass.OBSERVE: PolicyRule(
            policy_class=PolicyClass.OBSERVE,
            default_max=Decision.WARN,
            minimum_gate=None,
            description="Passive monitoring - notifications only",
        ),
        PolicyClass.INFORM: PolicyRule(
            policy_class=PolicyClass.INFORM,
            default_max=Decision.WARN,
            minimum_gate=None,
            description="Informational notifications",
        ),
        PolicyClass.INTERNAL_STATE_UPDATE: PolicyRule(
            policy_class=PolicyClass.INTERNAL_STATE_UPDATE,
            default_max=Decision.WARN,
            minimum_gate=None,
            description="Local state changes only",
        ),
        PolicyClass.EXTERNAL_REVIEW: PolicyRule(
            policy_class=PolicyClass.EXTERNAL_REVIEW,
            default_max=Decision.WARN,
            minimum_gate=Decision.CONTINUE,
            description="Aya/Claude review - allow continuation",
        ),
        PolicyClass.TRADING_ANALYSIS: PolicyRule(
            policy_class=PolicyClass.TRADING_ANALYSIS,
            default_max=Decision.RECHECK,
            minimum_gate=None,
            description="Chart/ticket analysis - no execution",
        ),
        PolicyClass.TRADING_EXECUTION_CANDIDATE: PolicyRule(
            policy_class=PolicyClass.TRADING_EXECUTION_CANDIDATE,
            default_max=Decision.REQUIRE_APPROVAL,
            minimum_gate=Decision.REQUIRE_APPROVAL,
            description="Trading execution - NEVER auto-execute",
        ),
        PolicyClass.UI_INTERACTION_CANDIDATE: PolicyRule(
            policy_class=PolicyClass.UI_INTERACTION_CANDIDATE,
            default_max=Decision.RECHECK,
            minimum_gate=Decision.RECHECK,
            description="UI interaction - escalate if side effects",
        ),
        PolicyClass.SENSITIVE_DATA_ACCESS: PolicyRule(
            policy_class=PolicyClass.SENSITIVE_DATA_ACCESS,
            default_max=Decision.RECHECK,
            minimum_gate=Decision.RECHECK,
            description="Sensitive data - block if trust boundary unclear",
        ),
        PolicyClass.PROMOTION_CANDIDATE: PolicyRule(
            policy_class=PolicyClass.PROMOTION_CANDIDATE,
            default_max=Decision.REQUIRE_APPROVAL,
            minimum_gate=Decision.REQUIRE_APPROVAL,
            description="Promotion - NEVER auto-promote",
        ),
    }
    
    # Risk level to default decision mapping
    RISK_DECISION_MAP: dict[RiskLevel, Decision] = {
        RiskLevel.NONE: Decision.CONTINUE,
        RiskLevel.LOW: Decision.CONTINUE,
        RiskLevel.MEDIUM: Decision.WARN,
        RiskLevel.HIGH: Decision.RECHECK,
        RiskLevel.CRITICAL: Decision.BLOCK,
    }
    
    def __init__(
        self,
        truth_writer: TruthWriterProtocol | None = None,
        policy_matrix: dict[PolicyClass, PolicyRule] | None = None,
    ):
        """Initialize the Governor.
        
        Args:
            truth_writer: Optional TruthWriter for logging verdicts
            policy_matrix: Optional custom policy matrix (uses defaults if not provided)
        """
        self.truth_writer = truth_writer
        self.policy_matrix = policy_matrix or self.DEFAULT_POLICY_MATRIX.copy()
        self._eval_count = 0
        
        logger.info("Governor initialized with %d policy classes", len(self.policy_matrix))
    
    def evaluate(
        self,
        recommendation: ReviewerResult,
        context: PolicyContext,
        policy_class: PolicyClass | str,
        source_event_id: str | None = None,
    ) -> GovernorVerdict:
        """Evaluate a reviewer recommendation and emit a verdict.
        
        This is the core entry point for the Governor. Every evaluation
        returns a structured GovernorVerdict - no exceptions.
        
        Args:
            recommendation: The reviewer's result to evaluate
            context: Policy context for this evaluation
            policy_class: The policy class to apply
            source_event_id: Optional source event UUID (generated if not provided)
            
        Returns:
            GovernorVerdict with decision and rationale
        """
        self._eval_count += 1
        
        # Normalize policy_class to enum
        if isinstance(policy_class, str):
            try:
                policy_class = PolicyClass(policy_class)
            except ValueError:
                # Unknown policy class - block for safety
                trace_id = str(uuid4())
                event_id = source_event_id or str(uuid4())
                logger.error(f"Unknown policy class: {policy_class}")
                verdict = self._create_block_verdict(
                    policy_class=PolicyClass.OBSERVE,  # Use a valid enum value
                    rationale=f"Unknown policy class: {policy_class}",
                    source_event=event_id,
                    reviewer=recommendation.reviewer_id,
                    trace_id=trace_id,
                    risk_level=RiskLevel.CRITICAL,
                    overrides_applied=["unknown_policy_class"],
                )
                self._log_verdict(verdict, context)
                return verdict
        
        # Generate trace and event IDs
        trace_id = str(uuid4())
        event_id = source_event_id or str(uuid4())
        
        # Get policy rule for this class
        policy_rule = self.policy_matrix.get(policy_class)
        if policy_rule is None:
            logger.error(f"Unknown policy class: {policy_class}")
            # Unknown policy class - block for safety
            verdict = self._create_block_verdict(
                policy_class=policy_class,
                rationale=f"Unknown policy class: {policy_class.value}",
                source_event=event_id,
                reviewer=recommendation.reviewer_id,
                trace_id=trace_id,
                risk_level=RiskLevel.CRITICAL,
                overrides_applied=["unknown_policy_class"],
            )
            self._log_verdict(verdict, context)
            return verdict
        
        # Step 1: Determine base decision from risk level
        base_decision = self._risk_to_decision(recommendation.risk_assessment)
        
        # Step 2: Apply policy class constraints (default max)
        # Note: BLOCK is never capped as it's a safety override
        constrained_decision = self._apply_policy_constraints(
            base_decision, policy_rule
        )
        
        # Step 3: Apply minimum gate and track as override if escalated
        gated_decision, min_gate_overrides = self._apply_minimum_gate(
            constrained_decision, policy_rule, policy_class, context
        )
        
        # Step 4: Apply override conditions
        final_decision, overrides = self._apply_overrides(
            gated_decision, policy_class, context
        )
        
        # Combine overrides from minimum gate and other overrides
        overrides = min_gate_overrides + overrides
        
        # Step 5: Build rationale
        rationale = self._build_rationale(
            recommendation=recommendation,
            base_decision=base_decision,
            final_decision=final_decision,
            policy_rule=policy_rule,
            overrides=overrides,
        )
        
        # Step 6: Generate tags
        tags = self._generate_tags(
            risk_level=recommendation.risk_assessment,
            decision=final_decision,
            policy_class=policy_class,
            context=context,
        )
        
        # Step 7: Create verdict
        verdict = create_verdict(
            risk_level=recommendation.risk_assessment,
            decision=final_decision,
            policy_class=policy_class,
            rationale=rationale,
            source_event=event_id,
            reviewer=recommendation.reviewer_id,
            trace_id=trace_id,
            tags=tags,
            overrides_applied=overrides,
        )
        
        # Step 8: Log to TruthWriter
        self._log_verdict(verdict, context)
        
        logger.debug(
            f"Governor evaluation {self._eval_count}: {policy_class.value} -> "
            f"{final_decision.value} (risk: {recommendation.risk_assessment.value})"
        )
        
        return verdict
    
    def _risk_to_decision(self, risk_level: RiskLevel) -> Decision:
        """Map risk level to default decision.
        
        Args:
            risk_level: The assessed risk level
            
        Returns:
            Default decision for this risk level
        """
        return self.RISK_DECISION_MAP.get(risk_level, Decision.RECHECK)
    
    def _apply_policy_constraints(
        self,
        decision: Decision,
        policy_rule: PolicyRule,
    ) -> Decision:
        """Apply policy class default maximum constraints.
        
        Args:
            decision: The current decision
            policy_rule: The policy rule to apply
            
        Returns:
            Constrained decision (capped at policy default_max)
            Note: BLOCK is never capped as it's a safety override
        """
        # BLOCK is never constrained - it's a safety decision
        if decision == Decision.BLOCK:
            return Decision.BLOCK
        
        # Decision enum values are ordered by severity
        decision_order = [
            Decision.CONTINUE,
            Decision.WARN,
            Decision.RECHECK,
            Decision.REQUIRE_APPROVAL,
            Decision.BLOCK,
        ]
        
        decision_idx = decision_order.index(decision)
        max_idx = decision_order.index(policy_rule.default_max)
        
        if decision_idx > max_idx:
            # Decision exceeds policy max - cap it
            return policy_rule.default_max
        
        return decision
    
    def _apply_minimum_gate(
        self,
        decision: Decision,
        policy_rule: PolicyRule,
        policy_class: PolicyClass,
        context: PolicyContext,
    ) -> tuple[Decision, list[str]]:
        """Apply minimum gate constraint.
        
        Args:
            decision: The current decision
            policy_rule: The policy rule with minimum_gate
            policy_class: The policy class being evaluated
            
        Returns:
            Tuple of (decision escalated to minimum if needed, list of overrides)
        """
        overrides = []
        
        if policy_rule.minimum_gate is None:
            return decision, overrides
        
        decision_order = [
            Decision.CONTINUE,
            Decision.WARN,
            Decision.RECHECK,
            Decision.REQUIRE_APPROVAL,
            Decision.BLOCK,
        ]
        
        decision_idx = decision_order.index(decision)
        min_idx = decision_order.index(policy_rule.minimum_gate)
        
        if decision_idx < min_idx:
            # Decision below minimum gate - escalate and track override
            if policy_class == PolicyClass.TRADING_EXECUTION_CANDIDATE:
                overrides.append("trading_execution_candidate")
            elif policy_class == PolicyClass.PROMOTION_CANDIDATE:
                overrides.append("promotion_candidate")
            elif policy_class == PolicyClass.UI_INTERACTION_CANDIDATE and context.external_side_effects:
                overrides.append("external_side_effects")
            return policy_rule.minimum_gate, overrides
        
        return decision, overrides
    
    def _apply_overrides(
        self,
        decision: Decision,
        policy_class: PolicyClass,
        context: PolicyContext,
    ) -> tuple[Decision, list[str]]:
        """Apply override conditions.
        
        Escalates decisions based on context flags.
        
        Args:
            decision: The current decision
            policy_class: The policy class being evaluated
            context: Policy context with flags
            
        Returns:
            Tuple of (final decision, list of overrides applied)
        """
        overrides = []
        final_decision = decision
        
        # Override 1: External side effects detected
        if context.external_side_effects:
            if final_decision in (Decision.CONTINUE, Decision.WARN):
                final_decision = Decision.RECHECK
                overrides.append("external_side_effects")
        
        # Override 2: Trading execution candidate
        if policy_class == PolicyClass.TRADING_EXECUTION_CANDIDATE:
            # Never auto-execute trading
            if final_decision in (Decision.CONTINUE, Decision.WARN, Decision.RECHECK):
                final_decision = Decision.REQUIRE_APPROVAL
                overrides.append("trading_execution_candidate")
        
        # Override 3: Sensitive data access with unclear trust boundary
        if policy_class == PolicyClass.SENSITIVE_DATA_ACCESS:
            if not context.trust_boundary_clear:
                final_decision = Decision.BLOCK
                overrides.append("unclear_trust_boundary")
        
        # Override 4: Promotion candidate
        if policy_class == PolicyClass.PROMOTION_CANDIDATE:
            # Never auto-promote
            if final_decision in (Decision.CONTINUE, Decision.WARN, Decision.RECHECK):
                final_decision = Decision.REQUIRE_APPROVAL
                overrides.append("promotion_candidate")
        
        # Override 5: Critical risk in trading mode always requires approval
        if context.mode == "trading" and policy_class in (
            PolicyClass.TRADING_ANALYSIS,
            PolicyClass.TRADING_EXECUTION_CANDIDATE,
        ):
            # Already handled by policy class minimum, but ensure trading safety
            pass
        
        return final_decision, overrides
    
    def _build_rationale(
        self,
        recommendation: ReviewerResult,
        base_decision: Decision,
        final_decision: Decision,
        policy_rule: PolicyRule,
        overrides: list[str],
    ) -> str:
        """Build human-readable rationale for the verdict.
        
        Args:
            recommendation: The reviewer recommendation
            base_decision: Initial decision from risk mapping
            final_decision: Final decision after overrides
            policy_rule: The policy rule applied
            overrides: List of overrides triggered
            
        Returns:
            Human-readable rationale string
        """
        parts = []
        
        # Base decision explanation
        parts.append(
            f"Risk assessment '{recommendation.risk_assessment.value}' maps to "
            f"'{base_decision.value}'"
        )
        
        # Policy constraint
        parts.append(
            f"Policy class '{policy_rule.policy_class.value}' applied: "
            f"{policy_rule.description}"
        )
        
        # Overrides
        if overrides:
            parts.append(f"Overrides triggered: {', '.join(overrides)}")
        
        # Final decision
        if base_decision != final_decision:
            parts.append(f"Final decision escalated to '{final_decision.value}'")
        else:
            parts.append(f"Final decision: '{final_decision.value}'")
        
        return "; ".join(parts)
    
    def _generate_tags(
        self,
        risk_level: RiskLevel,
        decision: Decision,
        policy_class: PolicyClass,
        context: PolicyContext,
    ) -> list[str]:
        """Generate derived tags for the verdict.
        
        Tags are secondary to structured fields but useful for filtering.
        
        Args:
            risk_level: The assessed risk level
            decision: The final decision
            policy_class: The policy class applied
            context: Policy context
            
        Returns:
            List of tags
        """
        tags = [
            f"risk:{risk_level.value}",
            f"action:{decision.value}",
            f"policy_class:{policy_class.value}",
            f"mode:{context.mode}",
        ]
        
        # Add context-specific tags
        if context.external_side_effects:
            tags.append("external_effects")
        if context.mode == "trading" or context.has_trading_implications:
            tags.append("trading")
        if context.sensitive_data_involved:
            tags.append("sensitive_data")
        
        return tags
    
    def _create_block_verdict(
        self,
        policy_class: PolicyClass,
        rationale: str,
        source_event: str,
        reviewer: str,
        trace_id: str,
        risk_level: RiskLevel = RiskLevel.CRITICAL,
        overrides_applied: list[str] | None = None,
    ) -> GovernorVerdict:
        """Create a block verdict for error conditions.
        
        Args:
            policy_class: The policy class (may be unknown)
            rationale: Explanation for the block
            source_event: Source event UUID
            reviewer: Reviewer ID
            trace_id: Trace ID
            risk_level: Risk level for the block
            overrides_applied: Overrides that led to block
            
        Returns:
            GovernorVerdict with BLOCK decision
        """
        return create_verdict(
            risk_level=risk_level,
            decision=Decision.BLOCK,
            policy_class=policy_class,
            rationale=rationale,
            source_event=source_event,
            reviewer=reviewer,
            trace_id=trace_id,
            tags=["error", f"risk:{risk_level.value}", "action:block"],
            overrides_applied=overrides_applied or [],
        )
    
    def _log_verdict(
        self,
        verdict: GovernorVerdict,
        context: PolicyContext,
    ) -> None:
        """Log the verdict to TruthWriter.
        
        Args:
            verdict: The verdict to log
            context: Policy context with artifact references
        """
        if self.truth_writer is None:
            return
        
        # Build event for truth writer
        event = {
            "event_type": "governor_verdict",
            "event_id": str(uuid4()),
            "verdict": verdict.to_dict(),
            "artifact_refs": context.artifact_refs.copy(),
        }
        
        try:
            self.truth_writer.write_event(event)
            logger.debug(f"Verdict logged: {verdict.verdict_id}")
        except Exception as e:
            # Log error but don't fail - verdict is still returned
            logger.error(f"Failed to log verdict to TruthWriter: {e}")
    
    def get_policy_rule(self, policy_class: PolicyClass | str) -> PolicyRule | None:
        """Get the policy rule for a given class.
        
        Args:
            policy_class: The policy class to look up
            
        Returns:
            PolicyRule or None if not found
        """
        if isinstance(policy_class, str):
            try:
                policy_class = PolicyClass(policy_class)
            except ValueError:
                return None
        return self.policy_matrix.get(policy_class)
    
    def update_policy_rule(self, policy_class: PolicyClass, rule: PolicyRule) -> None:
        """Update a policy rule (for testing or dynamic configuration).
        
        Args:
            policy_class: The policy class to update
            rule: The new policy rule
        """
        self.policy_matrix[policy_class] = rule
        logger.info(f"Updated policy rule for {policy_class.value}")
    
    @property
    def eval_count(self) -> int:
        """Number of evaluations performed by this Governor instance."""
        return self._eval_count


def quick_evaluate(
    reviewer_id: str,
    risk_level: RiskLevel,
    policy_class: PolicyClass | str,
    mode: str = "ui",
) -> GovernorVerdict:
    """Quick evaluation without full context setup.
    
    Convenience function for simple evaluations where full context
    is not needed.
    
    Args:
        reviewer_id: ID of the reviewer
        risk_level: Assessed risk level
        policy_class: Policy class to apply
        mode: Operating mode ("ui" or "trading")
        
    Returns:
        GovernorVerdict
    """
    governor = Governor()
    
    recommendation = ReviewerResult(
        reviewer_id=reviewer_id,
        recommendation="evaluate",
        risk_assessment=risk_level,
    )
    
    context = PolicyContext(mode=mode)
    
    return governor.evaluate(
        recommendation=recommendation,
        context=context,
        policy_class=policy_class,
    )
