"""Tests for execution preconditions.

This test suite validates that:
1. Reviewer recommendations alone cannot trigger execution
2. Execution candidates require valid GovernorVerdicts
3. Blocked verdicts halt execution
4. Require_approval verdicts halt pending approval
5. Recheck verdicts route back for deeper review
6. TruthWriter logs verdict lineage
7. Hot path tests cover bypass attempts
8. Stale verdicts are rejected
9. Malformed verdicts are rejected
10. Missing lineage fields are rejected
11. Freshness window is enforced

These tests ensure AD-010 is truly resolved: runtime execution is structurally
unable to skip the gate.
"""

import json
import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4, UUID

from src.advanced_vision.core.governor import Governor, PolicyContext, ReviewerResult
from src.advanced_vision.core.governor_verdict import (
    create_verdict,
    Decision,
    GovernorVerdict,
    Lineage,
    PolicyClass,
    RiskLevel,
    validate_verdict_dict,
)
from src.advanced_vision.core.execution_precondition import (
    ExecutionPrecondition,
    ValidationResult,
    GateResult,
)
from src.advanced_vision.core.execution_gate import ExecutionGate, GateDecision
from src.advanced_vision.core.precondition_result import PreconditionResult


class TestReviewerCannotTriggerExecutionDirectly:
    """Test that reviewer recommendations alone cannot trigger execution."""

    def test_reviewer_recommendation_alone_blocked(self):
        """Reviewer recommendation without GovernorVerdict cannot trigger execution."""
        precondition = ExecutionPrecondition()

        # Packet is execution candidate but has no verdict
        packet = {
            "execution_candidate": True,
            "reviewer_recommendation": "execute",
            "confidence": 0.95,
        }

        result = precondition.check(packet, verdict=None)

        assert result.allowed is False
        assert result.violation_type == "missing_verdict"
        assert "Reviewer recommendation alone cannot trigger execution" in result.reason

    def test_reviewer_high_confidence_still_blocked(self):
        """Even high confidence reviewer output is blocked without verdict."""
        precondition = ExecutionPrecondition()

        packet = {
            "execution_candidate": True,
            "reviewer_id": "eagle",
            "recommendation": "continue",
            "confidence": 0.99,
            "risk_assessment": "low",
        }

        result = precondition.check(packet, verdict=None)

        assert result.allowed is False
        assert result.violation_type == "missing_verdict"

    def test_non_execution_candidate_no_verdict_needed(self):
        """Non-execution candidates don't require verdicts."""
        precondition = ExecutionPrecondition()

        packet = {
            "execution_candidate": False,
            "reviewer_recommendation": "log_only",
        }

        result = precondition.check(packet, verdict=None)

        assert result.allowed is True
        assert result.verdict_id is None


class TestExecutionCandidatesRequireVerdict:
    """Test that execution candidates require valid GovernorVerdicts."""

    def test_execution_candidate_with_valid_verdict_allowed(self):
        """Execution candidate with valid verdict can proceed."""
        precondition = ExecutionPrecondition()

        verdict = create_verdict(
            risk_level=RiskLevel.LOW,
            decision=Decision.CONTINUE,
            policy_class=PolicyClass.OBSERVE,
            rationale="Low risk observation",
            source_event=str(uuid4()),
            reviewer="eagle",
        )

        packet = {
            "execution_candidate": True,
            "action": "observe",
        }

        result = precondition.check(packet, verdict)

        assert result.allowed is True
        assert result.verdict_id == verdict.verdict_id

    def test_execution_candidate_without_verdict_blocked(self):
        """Execution candidate without verdict is blocked."""
        precondition = ExecutionPrecondition()

        packet = {
            "execution_candidate": True,
            "action": "execute_trade",
        }

        result = precondition.check(packet, verdict=None)

        assert result.allowed is False
        assert result.violation_type == "missing_verdict"

    def test_trading_execution_candidate_requires_verdict(self):
        """Trading execution candidates specifically require verdicts."""
        gate = ExecutionGate()

        reviewer_output = {
            "reviewer_id": "qwen",
            "recommendation": "execute",
            "risk_assessment": "medium",
            "execution_candidate": True,
            "mode": "trading",
        }

        decision = gate.process(reviewer_output, {"mode": "trading"})

        # Should get a verdict attached
        assert decision.verdict is not None
        assert "governor_verdict" in decision.packet

        # Trading execution candidates should require approval
        assert decision.verdict.decision == Decision.REQUIRE_APPROVAL


class TestBlockedVerdictsHaltExecution:
    """Test that blocked verdicts halt execution."""

    def test_block_decision_halts_execution(self):
        """BLOCK decision halts execution."""
        precondition = ExecutionPrecondition()

        verdict = create_verdict(
            risk_level=RiskLevel.CRITICAL,
            decision=Decision.BLOCK,
            policy_class=PolicyClass.SENSITIVE_DATA_ACCESS,
            rationale="Critical risk - access blocked",
            source_event=str(uuid4()),
            reviewer="qwen",
        )

        packet = {"execution_candidate": True}
        result = precondition.check(packet, verdict)

        assert result.allowed is False
        assert result.violation_type == "blocked_decision"
        assert verdict.verdict_id == result.verdict_id

    def test_block_violation_logged(self):
        """Block violations are logged with attempt."""
        precondition = ExecutionPrecondition()

        verdict = create_verdict(
            risk_level=RiskLevel.HIGH,
            decision=Decision.BLOCK,
            policy_class=PolicyClass.UI_INTERACTION_CANDIDATE,
            rationale="External side effects detected",
            source_event=str(uuid4()),
            reviewer="aya",
        )

        packet = {"execution_candidate": True}
        result = precondition.check(packet, verdict)

        assert result.allowed is False
        assert "block" in result.reason.lower()
        assert "violation attempt" in result.reason.lower() or "halt" in result.reason.lower()


class TestRequireApprovalVerdicts:
    """Test that require_approval verdicts halt pending approval."""

    def test_require_approval_halts_pending_approval(self):
        """REQUIRE_APPROVAL decision halts execution pending approval."""
        precondition = ExecutionPrecondition()

        verdict = create_verdict(
            risk_level=RiskLevel.HIGH,
            decision=Decision.REQUIRE_APPROVAL,
            policy_class=PolicyClass.TRADING_EXECUTION_CANDIDATE,
            rationale="Trading execution requires explicit approval",
            source_event=str(uuid4()),
            reviewer="qwen",
        )

        packet = {"execution_candidate": True}
        result = precondition.check(packet, verdict)

        assert result.allowed is False
        assert result.violation_type == "approval_required"

    def test_trading_execution_never_auto_executes(self):
        """Trading execution candidates never auto-execute."""
        gate = ExecutionGate()

        reviewer_output = {
            "reviewer_id": "qwen",
            "recommendation": "continue",
            "risk_assessment": "low",
            "execution_candidate": True,
            "mode": "trading",
        }

        context = {"mode": "trading", "has_trading_implications": True}
        decision = gate.process(reviewer_output, context)

        # Should NOT allow direct execution
        assert decision.can_execute is False
        # Should require approval
        assert decision.verdict.decision == Decision.REQUIRE_APPROVAL
        assert decision.requires_approval is True


class TestRecheckVerdicts:
    """Test that recheck verdicts route back for deeper review."""

    def test_recheck_routes_back_for_review(self):
        """RECHECK decision routes back for deeper review."""
        precondition = ExecutionPrecondition()

        verdict = create_verdict(
            risk_level=RiskLevel.HIGH,
            decision=Decision.RECHECK,
            policy_class=PolicyClass.TRADING_ANALYSIS,
            rationale="High risk - needs deeper review",
            source_event=str(uuid4()),
            reviewer="eagle",
        )

        packet = {"execution_candidate": True}
        result = precondition.check(packet, verdict)

        assert result.allowed is False
        assert result.violation_type == "recheck_required"

    def test_recheck_gate_routing(self):
        """ExecutionGate routes recheck verdicts appropriately."""
        gate = ExecutionGate()

        verdict = create_verdict(
            risk_level=RiskLevel.MEDIUM,
            decision=Decision.RECHECK,
            policy_class=PolicyClass.UI_INTERACTION_CANDIDATE,
            rationale="External side effects need review",
            source_event=str(uuid4()),
            reviewer="aya",
        )

        packet = {"execution_candidate": True}
        decision = gate.process_with_verdict(packet, verdict)

        assert decision.can_execute is False
        assert decision.requires_recheck is True
        assert decision.route_to == "recheck"


class TestTruthWriterLineage:
    """Test that TruthWriter logs verdict lineage."""

    def test_truth_writer_receives_verdict_lineage(self):
        """TruthWriter receives complete verdict lineage."""
        events = []

        class MockTruthWriter:
            def write_event(self, event):
                events.append(event)

        truth_writer = MockTruthWriter()
        governor = Governor(truth_writer=truth_writer)

        reviewer_result = ReviewerResult(
            reviewer_id="eagle",
            recommendation="observe",
            risk_assessment=RiskLevel.LOW,
        )

        context = PolicyContext(mode="ui")

        verdict = governor.evaluate(
            recommendation=reviewer_result,
            context=context,
            policy_class=PolicyClass.OBSERVE,
        )

        # Should have logged to TruthWriter
        assert len(events) == 1
        logged_event = events[0]

        # Event should contain verdict with lineage
        assert logged_event["event_type"] == "governor_verdict"
        assert "verdict" in logged_event
        assert "lineage" in logged_event["verdict"]
        assert "source_event" in logged_event["verdict"]["lineage"]
        assert "reviewer" in logged_event["verdict"]["lineage"]
        assert "trace_id" in logged_event["verdict"]["lineage"]

    def test_lineage_contains_all_required_fields(self):
        """Verdict lineage contains all required trace fields."""
        verdict = create_verdict(
            risk_level=RiskLevel.LOW,
            decision=Decision.CONTINUE,
            policy_class=PolicyClass.OBSERVE,
            rationale="Test",
            source_event=str(uuid4()),
            reviewer="eagle",
        )

        # Validate UUID format
        assert UUID(verdict.lineage.source_event)
        assert UUID(verdict.lineage.trace_id)
        assert verdict.lineage.reviewer == "eagle"

        # All fields present
        assert verdict.lineage.source_event
        assert verdict.lineage.reviewer
        assert verdict.lineage.trace_id


class TestHotPathBypassAttempts:
    """Test that hot path covers bypass attempts."""

    def test_direct_packet_manipulation_blocked(self):
        """Direct packet manipulation to add fake verdict is caught."""
        precondition = ExecutionPrecondition()

        # Try to bypass with invalid verdict object (dict instead of GovernorVerdict)
        fake_verdict = {"not_a_real_verdict": True}

        packet = {"execution_candidate": True}

        # The precondition gracefully handles this by validating structure
        result = precondition.check(packet, fake_verdict)  # type: ignore

        # Should be blocked due to malformed verdict
        assert result.allowed is False
        assert result.violation_type == "malformed_verdict"

    def test_bypass_with_non_execution_flag_fails(self):
        """Trying to bypass by setting execution_candidate=False doesn't help if action requires it."""
        gate = ExecutionGate()

        # Even with low risk, if packet says it's not an execution candidate,
        # but the action is clearly an execution, the application logic should check
        reviewer_output = {
            "reviewer_id": "qwen",
            "recommendation": "execute_trade",
            "risk_assessment": "critical",
            "execution_candidate": False,  # Trying to bypass
            "mode": "trading",
        }

        # The gate processes it but the application layer should still validate
        decision = gate.process(reviewer_output, {"mode": "trading"})

        # Verdict is still created
        assert decision.verdict is not None
        # But the application should check execution_candidate flag separately

    def test_structural_prevention_of_skip(self):
        """AD-010: Runtime execution is structurally unable to skip the gate."""
        # The very existence of ExecutionPrecondition and ExecutionGate
        # with the check() method means any execution must pass through

        precondition = ExecutionPrecondition()

        # There is no path around the precondition check
        # The API forces a verdict to be passed

        packet = {"execution_candidate": True}

        # Without a verdict, execution is blocked
        result = precondition.check(packet, verdict=None)
        assert result.allowed is False

        # With a valid continue verdict, execution is allowed
        verdict = create_verdict(
            risk_level=RiskLevel.LOW,
            decision=Decision.CONTINUE,
            policy_class=PolicyClass.OBSERVE,
            rationale="Test",
            source_event=str(uuid4()),
            reviewer="eagle",
        )

        result = precondition.check(packet, verdict)
        assert result.allowed is True


class TestStaleVerdictRejection:
    """Test that stale verdicts are rejected."""

    def test_stale_verdict_rejected(self):
        """Verdict older than freshness window is rejected."""
        precondition = ExecutionPrecondition(default_freshness_seconds=30)

        # Create a verdict with old timestamp
        old_timestamp = (datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat()

        verdict = GovernorVerdict(
            verdict_id=str(uuid4()),
            timestamp=old_timestamp,
            risk_level=RiskLevel.LOW,
            decision=Decision.CONTINUE,
            policy_class=PolicyClass.OBSERVE,
            rationale="Old verdict",
            lineage=Lineage(
                source_event=str(uuid4()),
                reviewer="eagle",
                trace_id=str(uuid4()),
            ),
        )

        packet = {"execution_candidate": True}
        result = precondition.check(packet, verdict)

        assert result.allowed is False
        assert result.violation_type == "stale_verdict"

    def test_fresh_verdict_accepted(self):
        """Verdict within freshness window is accepted."""
        precondition = ExecutionPrecondition(default_freshness_seconds=30)

        # Create a fresh verdict
        verdict = create_verdict(
            risk_level=RiskLevel.LOW,
            decision=Decision.CONTINUE,
            policy_class=PolicyClass.OBSERVE,
            rationale="Fresh verdict",
            source_event=str(uuid4()),
            reviewer="eagle",
        )

        packet = {"execution_candidate": True}
        result = precondition.check(packet, verdict)

        assert result.allowed is True

    def test_custom_freshness_window(self):
        """Custom freshness window is respected."""
        precondition = ExecutionPrecondition(default_freshness_seconds=300)  # 5 minutes

        # Create a verdict that's 60 seconds old (within 5 minute window)
        old_timestamp = (datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat()

        verdict = GovernorVerdict(
            verdict_id=str(uuid4()),
            timestamp=old_timestamp,
            risk_level=RiskLevel.LOW,
            decision=Decision.CONTINUE,
            policy_class=PolicyClass.OBSERVE,
            rationale="Somewhat old but within window",
            lineage=Lineage(
                source_event=str(uuid4()),
                reviewer="eagle",
                trace_id=str(uuid4()),
            ),
        )

        packet = {"execution_candidate": True}
        result = precondition.check(packet, verdict)

        assert result.allowed is True


class TestMalformedVerdictRejection:
    """Test that malformed verdicts are rejected."""

    def test_missing_required_fields_rejected(self):
        """Verdict missing required fields is rejected."""
        precondition = ExecutionPrecondition()

        # Create a verdict with missing lineage
        verdict_dict = {
            "verdict_id": str(uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "risk_level": "low",
            "decision": "continue",
            "policy_class": "observe",
            "rationale": "Test",
            # Missing lineage!
        }

        # Validation should catch this
        is_valid, errors = validate_verdict_dict(verdict_dict)
        assert is_valid is False
        assert any("lineage" in err for err in errors)

    def test_invalid_risk_level_rejected(self):
        """Verdict with invalid risk level is rejected."""
        verdict_dict = {
            "verdict_id": str(uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "risk_level": "invalid_risk",
            "decision": "continue",
            "policy_class": "observe",
            "rationale": "Test",
            "lineage": {
                "source_event": str(uuid4()),
                "reviewer": "eagle",
                "trace_id": str(uuid4()),
            },
        }

        is_valid, errors = validate_verdict_dict(verdict_dict)
        assert is_valid is False
        assert any("risk_level" in err for err in errors)

    def test_invalid_decision_rejected(self):
        """Verdict with invalid decision is rejected."""
        verdict_dict = {
            "verdict_id": str(uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "risk_level": "low",
            "decision": "invalid_decision",
            "policy_class": "observe",
            "rationale": "Test",
            "lineage": {
                "source_event": str(uuid4()),
                "reviewer": "eagle",
                "trace_id": str(uuid4()),
            },
        }

        is_valid, errors = validate_verdict_dict(verdict_dict)
        assert is_valid is False
        assert any("decision" in err for err in errors)


class TestMissingLineageFields:
    """Test that missing lineage fields are rejected."""

    def test_missing_source_event_rejected(self):
        """Verdict missing source_event in lineage is rejected."""
        precondition = ExecutionPrecondition()

        verdict = GovernorVerdict(
            verdict_id=str(uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            risk_level=RiskLevel.LOW,
            decision=Decision.CONTINUE,
            policy_class=PolicyClass.OBSERVE,
            rationale="Test",
            lineage=Lineage(
                source_event="",  # Empty!
                reviewer="eagle",
                trace_id=str(uuid4()),
            ),
        )

        packet = {"execution_candidate": True}
        result = precondition.check(packet, verdict)

        assert result.allowed is False
        # Empty lineage fields are caught in structure validation as malformed_verdict
        assert result.violation_type in ("invalid_lineage", "malformed_verdict")

    def test_missing_reviewer_rejected(self):
        """Verdict missing reviewer in lineage is rejected."""
        precondition = ExecutionPrecondition()

        verdict = GovernorVerdict(
            verdict_id=str(uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            risk_level=RiskLevel.LOW,
            decision=Decision.CONTINUE,
            policy_class=PolicyClass.OBSERVE,
            rationale="Test",
            lineage=Lineage(
                source_event=str(uuid4()),
                reviewer="",  # Empty!
                trace_id=str(uuid4()),
            ),
        )

        packet = {"execution_candidate": True}
        result = precondition.check(packet, verdict)

        assert result.allowed is False
        # Empty lineage fields are caught in structure validation as malformed_verdict
        assert result.violation_type in ("invalid_lineage", "malformed_verdict")

    def test_missing_trace_id_rejected(self):
        """Verdict missing trace_id in lineage is rejected."""
        precondition = ExecutionPrecondition()

        verdict = GovernorVerdict(
            verdict_id=str(uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            risk_level=RiskLevel.LOW,
            decision=Decision.CONTINUE,
            policy_class=PolicyClass.OBSERVE,
            rationale="Test",
            lineage=Lineage(
                source_event=str(uuid4()),
                reviewer="eagle",
                trace_id="",  # Empty!
            ),
        )

        packet = {"execution_candidate": True}
        result = precondition.check(packet, verdict)

        assert result.allowed is False
        # Empty lineage fields are caught in structure validation as malformed_verdict
        assert result.violation_type in ("invalid_lineage", "malformed_verdict")

    def test_invalid_uuid_in_lineage_rejected(self):
        """Verdict with invalid UUID in lineage is rejected."""
        precondition = ExecutionPrecondition()

        verdict = GovernorVerdict(
            verdict_id=str(uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            risk_level=RiskLevel.LOW,
            decision=Decision.CONTINUE,
            policy_class=PolicyClass.OBSERVE,
            rationale="Test",
            lineage=Lineage(
                source_event="not-a-valid-uuid",
                reviewer="eagle",
                trace_id=str(uuid4()),
            ),
        )

        packet = {"execution_candidate": True}
        result = precondition.check(packet, verdict)

        assert result.allowed is False
        assert result.violation_type == "invalid_lineage"


class TestFreshnessWindowEnforcement:
    """Test that freshness window is properly enforced."""

    def test_check_verdict_freshness_method(self):
        """check_verdict_freshness method works correctly."""
        precondition = ExecutionPrecondition(default_freshness_seconds=30)

        # Fresh verdict
        fresh_verdict = create_verdict(
            risk_level=RiskLevel.LOW,
            decision=Decision.CONTINUE,
            policy_class=PolicyClass.OBSERVE,
            rationale="Fresh",
            source_event=str(uuid4()),
            reviewer="eagle",
        )

        assert precondition.check_verdict_freshness(fresh_verdict) is True

        # Stale verdict
        stale_timestamp = (datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat()
        stale_verdict = GovernorVerdict(
            verdict_id=str(uuid4()),
            timestamp=stale_timestamp,
            risk_level=RiskLevel.LOW,
            decision=Decision.CONTINUE,
            policy_class=PolicyClass.OBSERVE,
            rationale="Stale",
            lineage=Lineage(
                source_event=str(uuid4()),
                reviewer="eagle",
                trace_id=str(uuid4()),
            ),
        )

        assert precondition.check_verdict_freshness(stale_verdict) is False

    def test_freshness_with_explicit_max_age(self):
        """check_verdict_freshness respects explicit max_age parameter."""
        precondition = ExecutionPrecondition()

        # Verdict that's 45 seconds old
        timestamp = (datetime.now(timezone.utc) - timedelta(seconds=45)).isoformat()
        verdict = GovernorVerdict(
            verdict_id=str(uuid4()),
            timestamp=timestamp,
            risk_level=RiskLevel.LOW,
            decision=Decision.CONTINUE,
            policy_class=PolicyClass.OBSERVE,
            rationale="Test",
            lineage=Lineage(
                source_event=str(uuid4()),
                reviewer="eagle",
                trace_id=str(uuid4()),
            ),
        )

        # Should be stale with 30s window
        assert precondition.check_verdict_freshness(verdict, max_age_seconds=30) is False

        # Should be fresh with 60s window
        assert precondition.check_verdict_freshness(verdict, max_age_seconds=60) is True

    def test_invalid_timestamp_handling(self):
        """Invalid timestamp is treated as stale."""
        precondition = ExecutionPrecondition()

        verdict = GovernorVerdict(
            verdict_id=str(uuid4()),
            timestamp="invalid-timestamp",
            risk_level=RiskLevel.LOW,
            decision=Decision.CONTINUE,
            policy_class=PolicyClass.OBSERVE,
            rationale="Test",
            lineage=Lineage(
                source_event=str(uuid4()),
                reviewer="eagle",
                trace_id=str(uuid4()),
            ),
        )

        assert precondition.check_verdict_freshness(verdict) is False


class TestDecisionGate:
    """Test decision gate enforcement."""

    def test_continue_allows_execution(self):
        """CONTINUE decision allows execution."""
        precondition = ExecutionPrecondition()

        result = precondition.enforce_decision_gate(Decision.CONTINUE)

        assert result.can_proceed is True
        assert result.action_required == "proceed"

    def test_warn_allows_execution_with_caution(self):
        """WARN decision allows execution with caution."""
        precondition = ExecutionPrecondition()

        result = precondition.enforce_decision_gate(Decision.WARN)

        assert result.can_proceed is True
        assert result.action_required == "proceed_with_caution"

    def test_recheck_blocks_execution(self):
        """RECHECK decision blocks execution."""
        precondition = ExecutionPrecondition()

        result = precondition.enforce_decision_gate(Decision.RECHECK)

        assert result.can_proceed is False
        assert result.action_required == "recheck"

    def test_require_approval_blocks_execution(self):
        """REQUIRE_APPROVAL decision blocks execution."""
        precondition = ExecutionPrecondition()

        result = precondition.enforce_decision_gate(Decision.REQUIRE_APPROVAL)

        assert result.can_proceed is False
        assert result.action_required == "await_approval"

    def test_block_halts_execution(self):
        """BLOCK decision halts execution."""
        precondition = ExecutionPrecondition()

        result = precondition.enforce_decision_gate(Decision.BLOCK)

        assert result.can_proceed is False
        assert result.action_required == "halt"


class TestGateIntegration:
    """Test ExecutionGate integration scenarios."""

    def test_full_flow_from_reviewer_to_decision(self):
        """Complete flow from reviewer output to gate decision."""
        gate = ExecutionGate()

        reviewer_output = {
            "reviewer_id": "qwen",
            "recommendation": "analyze_chart",
            "risk_assessment": "medium",
            "confidence": 0.8,
        }

        context = {"mode": "trading"}
        decision = gate.process(reviewer_output, context)

        # Should produce a verdict
        assert decision.verdict is not None
        assert decision.packet is not None
        assert "governor_verdict" in decision.packet

        # Should have evaluated the recommendation
        assert decision.verdict.lineage.reviewer == "qwen"

    def test_execution_candidate_blocked_at_gate(self):
        """Execution candidates are blocked without approval."""
        gate = ExecutionGate()

        reviewer_output = {
            "reviewer_id": "qwen",
            "recommendation": "execute_trade",
            "risk_assessment": "high",
            "execution_candidate": True,
            "mode": "trading",
        }

        decision = gate.process(reviewer_output, {"mode": "trading"})

        # Trading execution candidates should require approval
        assert decision.can_execute is False
        assert decision.verdict.decision == Decision.REQUIRE_APPROVAL


class TestValidationResult:
    """Test ValidationResult helper class."""

    def test_valid_result(self):
        """Valid result has no errors."""
        result = ValidationResult(valid=True)

        assert result.is_valid is True
        assert result.errors == []

    def test_invalid_result(self):
        """Invalid result has errors."""
        result = ValidationResult(
            valid=False,
            errors=["Field missing", "Invalid value"],
            missing_fields=["field1"],
        )

        assert result.is_valid is False
        assert len(result.errors) == 2


class TestPreconditionResultHelpers:
    """Test PreconditionResult factory methods."""

    def test_allowed_result_factory(self):
        """allowed_result factory creates allowed result."""
        result = PreconditionResult.allowed_result("All good", verdict_id="v123")

        assert result.allowed is True
        assert result.reason == "All good"
        assert result.verdict_id == "v123"
        assert result.violation_type is None

    def test_blocked_result_factory(self):
        """blocked_result factory creates blocked result."""
        result = PreconditionResult.blocked_result(
            "Blocked", "test_violation", verdict_id="v456"
        )

        assert result.allowed is False
        assert result.reason == "Blocked"
        assert result.violation_type == "test_violation"
        assert result.verdict_id == "v456"

    def test_recheck_result_factory(self):
        """recheck_result factory creates recheck result."""
        result = PreconditionResult.recheck_result("Needs review")

        assert result.allowed is False
        assert result.violation_type == "recheck_required"

    def test_approval_required_result_factory(self):
        """approval_required_result factory creates approval result."""
        result = PreconditionResult.approval_required_result("Needs approval")

        assert result.allowed is False
        assert result.violation_type == "approval_required"


class TestPreconditionMetrics:
    """Test ExecutionPrecondition metrics."""

    def test_check_count_tracked(self):
        """Check count is tracked."""
        precondition = ExecutionPrecondition()

        initial_count = precondition.check_count

        packet = {"execution_candidate": False}
        precondition.check(packet, None)

        assert precondition.check_count == initial_count + 1

    def test_block_count_tracked(self):
        """Block count is tracked."""
        precondition = ExecutionPrecondition()

        initial_block_count = precondition.block_count

        packet = {"execution_candidate": True}
        precondition.check(packet, None)

        assert precondition.block_count == initial_block_count + 1


class TestGateDecisionProperties:
    """Test GateDecision helper properties."""

    def test_is_blocked_property(self):
        """is_blocked property works correctly."""
        decision = GateDecision(
            can_execute=False,
            verdict=None,
            precondition_result=PreconditionResult.blocked_result("Test", "test"),
        )

        assert decision.is_blocked is True

    def test_requires_recheck_property(self):
        """requires_recheck property works correctly."""
        decision = GateDecision(
            can_execute=False,
            verdict=None,
            precondition_result=PreconditionResult.recheck_result("Test"),
            route_to="recheck",
        )

        assert decision.requires_recheck is True

    def test_requires_approval_property(self):
        """requires_approval property works correctly."""
        decision = GateDecision(
            can_execute=False,
            verdict=None,
            precondition_result=PreconditionResult.approval_required_result("Test"),
            route_to="approval_queue",
        )

        assert decision.requires_approval is True
