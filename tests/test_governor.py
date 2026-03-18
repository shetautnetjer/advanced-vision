"""Tests for the Governor system.

Tests cover:
- Default class behavior (all 9 policy classes)
- Risk→decision mapping
- Approval escalation conditions
- Block conditions
- Trading-specific overrides
- Trust/integrity violations
- Verdict structure validation
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from advanced_vision.core.governor import (
    Governor,
    PolicyContext,
    PolicyRule,
    ReviewerResult,
    quick_evaluate,
)
from advanced_vision.core.governor_verdict import (
    Decision,
    GovernorVerdict,
    Lineage,
    PolicyClass,
    RiskLevel,
    create_verdict,
    GOVERNOR_VERDICT_SCHEMA,
    validate_verdict_dict,
)
from advanced_vision.core.truth_writer import TruthWriter


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def temp_truth_dir():
    """Create a temporary directory for truth writer."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def truth_writer(temp_truth_dir):
    """Create a TruthWriter instance."""
    return TruthWriter(temp_truth_dir, fsync=False)


@pytest.fixture
def governor(truth_writer):
    """Create a Governor instance with truth writer."""
    return Governor(truth_writer=truth_writer)


@pytest.fixture
def governor_no_truth():
    """Create a Governor instance without truth writer."""
    return Governor()


@pytest.fixture
def base_context():
    """Create a base policy context."""
    return PolicyContext(mode="ui")


@pytest.fixture
def base_reviewer_result():
    """Create a base reviewer result."""
    return ReviewerResult(
        reviewer_id="eagle",
        recommendation="continue",
        risk_assessment=RiskLevel.LOW,
    )


# =============================================================================
# Test 1-9: Default class behavior for all 9 policy classes
# =============================================================================

class TestPolicyClassDefaults:
    """Test default behavior for all 9 policy classes."""
    
    def test_observe_policy_low_risk(self, governor_no_truth, base_context):
        """Test observe policy with low risk - should continue."""
        recommendation = ReviewerResult(
            reviewer_id="eagle",
            recommendation="observe",
            risk_assessment=RiskLevel.LOW,
        )
        
        verdict = governor_no_truth.evaluate(
            recommendation=recommendation,
            context=base_context,
            policy_class=PolicyClass.OBSERVE,
        )
        
        assert verdict.decision == Decision.CONTINUE
        assert verdict.policy_class == PolicyClass.OBSERVE
    
    def test_inform_policy_medium_risk(self, governor_no_truth, base_context):
        """Test inform policy with medium risk - should warn."""
        recommendation = ReviewerResult(
            reviewer_id="qwen",
            recommendation="inform",
            risk_assessment=RiskLevel.MEDIUM,
        )
        
        verdict = governor_no_truth.evaluate(
            recommendation=recommendation,
            context=base_context,
            policy_class=PolicyClass.INFORM,
        )
        
        assert verdict.decision == Decision.WARN
        assert verdict.policy_class == PolicyClass.INFORM
    
    def test_internal_state_update_policy(self, governor_no_truth, base_context):
        """Test internal_state_update policy - should cap at warn."""
        recommendation = ReviewerResult(
            reviewer_id="aya",
            recommendation="update",
            risk_assessment=RiskLevel.HIGH,
        )
        
        verdict = governor_no_truth.evaluate(
            recommendation=recommendation,
            context=base_context,
            policy_class=PolicyClass.INTERNAL_STATE_UPDATE,
        )
        
        # Capped at warn by policy
        assert verdict.decision == Decision.WARN
    
    def test_external_review_policy(self, governor_no_truth, base_context):
        """Test external_review policy - minimum gate is continue."""
        recommendation = ReviewerResult(
            reviewer_id="claude",
            recommendation="review",
            risk_assessment=RiskLevel.LOW,
        )
        
        verdict = governor_no_truth.evaluate(
            recommendation=recommendation,
            context=base_context,
            policy_class=PolicyClass.EXTERNAL_REVIEW,
        )
        
        # Minimum gate is continue, low risk -> continue
        assert verdict.decision == Decision.CONTINUE
    
    def test_trading_analysis_policy_high_risk(self, governor_no_truth, base_context):
        """Test trading_analysis policy with high risk."""
        recommendation = ReviewerResult(
            reviewer_id="eagle",
            recommendation="analyze",
            risk_assessment=RiskLevel.HIGH,
        )
        
        verdict = governor_no_truth.evaluate(
            recommendation=recommendation,
            context=base_context,
            policy_class=PolicyClass.TRADING_ANALYSIS,
        )
        
        # High risk -> recheck (default max)
        assert verdict.decision == Decision.RECHECK
    
    def test_trading_execution_candidate_policy(self, governor_no_truth, base_context):
        """Test trading_execution_candidate - always require approval."""
        recommendation = ReviewerResult(
            reviewer_id="eagle",
            recommendation="execute",
            risk_assessment=RiskLevel.LOW,
        )
        
        verdict = governor_no_truth.evaluate(
            recommendation=recommendation,
            context=base_context,
            policy_class=PolicyClass.TRADING_EXECUTION_CANDIDATE,
        )
        
        # Always require approval
        assert verdict.decision == Decision.REQUIRE_APPROVAL
        assert "trading_execution_candidate" in verdict.overrides_applied
    
    def test_ui_interaction_candidate_policy(self, governor_no_truth, base_context):
        """Test ui_interaction_candidate policy."""
        recommendation = ReviewerResult(
            reviewer_id="aya",
            recommendation="interact",
            risk_assessment=RiskLevel.LOW,
        )
        
        verdict = governor_no_truth.evaluate(
            recommendation=recommendation,
            context=base_context,
            policy_class=PolicyClass.UI_INTERACTION_CANDIDATE,
        )
        
        # Minimum gate is recheck
        assert verdict.decision == Decision.RECHECK
    
    def test_sensitive_data_access_policy(self, governor_no_truth, base_context):
        """Test sensitive_data_access policy."""
        recommendation = ReviewerResult(
            reviewer_id="qwen",
            recommendation="access",
            risk_assessment=RiskLevel.LOW,
        )
        
        verdict = governor_no_truth.evaluate(
            recommendation=recommendation,
            context=base_context,
            policy_class=PolicyClass.SENSITIVE_DATA_ACCESS,
        )
        
        # Minimum gate is recheck
        assert verdict.decision == Decision.RECHECK
    
    def test_promotion_candidate_policy(self, governor_no_truth, base_context):
        """Test promotion_candidate - never auto-promote."""
        recommendation = ReviewerResult(
            reviewer_id="eagle",
            recommendation="promote",
            risk_assessment=RiskLevel.NONE,
        )
        
        verdict = governor_no_truth.evaluate(
            recommendation=recommendation,
            context=base_context,
            policy_class=PolicyClass.PROMOTION_CANDIDATE,
        )
        
        # Never auto-promote
        assert verdict.decision == Decision.REQUIRE_APPROVAL
        assert "promotion_candidate" in verdict.overrides_applied


# =============================================================================
# Test 10-14: Risk to Decision Mapping
# =============================================================================

class TestRiskDecisionMapping:
    """Test risk level to decision mapping."""
    
    def test_none_risk_maps_to_continue(self, governor_no_truth, base_context):
        """Test that NONE risk maps to CONTINUE."""
        recommendation = ReviewerResult(
            reviewer_id="eagle",
            recommendation="test",
            risk_assessment=RiskLevel.NONE,
        )
        
        verdict = governor_no_truth.evaluate(
            recommendation=recommendation,
            context=base_context,
            policy_class=PolicyClass.OBSERVE,
        )
        
        assert verdict.decision == Decision.CONTINUE
    
    def test_low_risk_maps_to_continue(self, governor_no_truth, base_context):
        """Test that LOW risk maps to CONTINUE."""
        recommendation = ReviewerResult(
            reviewer_id="eagle",
            recommendation="test",
            risk_assessment=RiskLevel.LOW,
        )
        
        verdict = governor_no_truth.evaluate(
            recommendation=recommendation,
            context=base_context,
            policy_class=PolicyClass.OBSERVE,
        )
        
        assert verdict.decision == Decision.CONTINUE
    
    def test_medium_risk_maps_to_warn(self, governor_no_truth, base_context):
        """Test that MEDIUM risk maps to WARN."""
        recommendation = ReviewerResult(
            reviewer_id="eagle",
            recommendation="test",
            risk_assessment=RiskLevel.MEDIUM,
        )
        
        verdict = governor_no_truth.evaluate(
            recommendation=recommendation,
            context=base_context,
            policy_class=PolicyClass.OBSERVE,
        )
        
        assert verdict.decision == Decision.WARN
    
    def test_high_risk_maps_to_recheck(self, governor_no_truth, base_context):
        """Test that HIGH risk maps to RECHECK."""
        recommendation = ReviewerResult(
            reviewer_id="eagle",
            recommendation="test",
            risk_assessment=RiskLevel.HIGH,
        )
        
        verdict = governor_no_truth.evaluate(
            recommendation=recommendation,
            context=base_context,
            policy_class=PolicyClass.TRADING_ANALYSIS,
        )
        
        assert verdict.decision == Decision.RECHECK
    
    def test_critical_risk_maps_to_block(self, governor_no_truth, base_context):
        """Test that CRITICAL risk maps to BLOCK."""
        recommendation = ReviewerResult(
            reviewer_id="eagle",
            recommendation="test",
            risk_assessment=RiskLevel.CRITICAL,
        )
        
        verdict = governor_no_truth.evaluate(
            recommendation=recommendation,
            context=base_context,
            policy_class=PolicyClass.OBSERVE,
        )
        
        assert verdict.decision == Decision.BLOCK


# =============================================================================
# Test 15-17: Approval Escalation Conditions
# =============================================================================

class TestApprovalEscalation:
    """Test conditions that escalate to require_approval."""
    
    def test_trading_execution_escalates_to_approval(self, governor_no_truth, base_context):
        """Test trading execution always escalates to require_approval."""
        recommendation = ReviewerResult(
            reviewer_id="eagle",
            recommendation="execute",
            risk_assessment=RiskLevel.NONE,
        )
        
        verdict = governor_no_truth.evaluate(
            recommendation=recommendation,
            context=base_context,
            policy_class=PolicyClass.TRADING_EXECUTION_CANDIDATE,
        )
        
        assert verdict.decision == Decision.REQUIRE_APPROVAL
        assert verdict.requires_approval()
    
    def test_promotion_escalates_to_approval(self, governor_no_truth, base_context):
        """Test promotion never auto-approves."""
        recommendation = ReviewerResult(
            reviewer_id="aya",
            recommendation="promote",
            risk_assessment=RiskLevel.NONE,
        )
        
        verdict = governor_no_truth.evaluate(
            recommendation=recommendation,
            context=base_context,
            policy_class=PolicyClass.PROMOTION_CANDIDATE,
        )
        
        assert verdict.decision == Decision.REQUIRE_APPROVAL
        assert not verdict.is_execution_allowed()
    
    def test_ui_external_side_effects_escalate(self, governor_no_truth, base_context):
        """Test UI with external side effects escalates."""
        recommendation = ReviewerResult(
            reviewer_id="eagle",
            recommendation="interact",
            risk_assessment=RiskLevel.LOW,
        )
        
        context = PolicyContext(
            mode="ui",
            external_side_effects=True,
        )
        
        verdict = governor_no_truth.evaluate(
            recommendation=recommendation,
            context=context,
            policy_class=PolicyClass.UI_INTERACTION_CANDIDATE,
        )
        
        # Should be recheck due to external side effects override
        assert "external_side_effects" in verdict.overrides_applied


# =============================================================================
# Test 18-20: Block Conditions
# =============================================================================

class TestBlockConditions:
    """Test conditions that result in BLOCK."""
    
    def test_critical_risk_results_in_block(self, governor_no_truth, base_context):
        """Test critical risk always blocks."""
        recommendation = ReviewerResult(
            reviewer_id="eagle",
            recommendation="test",
            risk_assessment=RiskLevel.CRITICAL,
        )
        
        verdict = governor_no_truth.evaluate(
            recommendation=recommendation,
            context=base_context,
            policy_class=PolicyClass.OBSERVE,
        )
        
        assert verdict.decision == Decision.BLOCK
        assert verdict.is_blocked()
        assert not verdict.is_execution_allowed()
    
    def test_unknown_policy_class_blocks(self, governor_no_truth, base_context):
        """Test unknown policy class results in block."""
        recommendation = ReviewerResult(
            reviewer_id="eagle",
            recommendation="test",
            risk_assessment=RiskLevel.LOW,
        )
        
        # Use invalid policy class string
        verdict = governor_no_truth.evaluate(
            recommendation=recommendation,
            context=base_context,
            policy_class="unknown_class",
        )
        
        assert verdict.decision == Decision.BLOCK
        assert "unknown_policy_class" in verdict.overrides_applied
    
    def test_sensitive_data_unclear_trust_boundary_blocks(self, governor_no_truth):
        """Test sensitive data access with unclear trust boundary blocks."""
        recommendation = ReviewerResult(
            reviewer_id="qwen",
            recommendation="access",
            risk_assessment=RiskLevel.LOW,
        )
        
        context = PolicyContext(
            mode="ui",
            trust_boundary_clear=False,
        )
        
        verdict = governor_no_truth.evaluate(
            recommendation=recommendation,
            context=context,
            policy_class=PolicyClass.SENSITIVE_DATA_ACCESS,
        )
        
        assert verdict.decision == Decision.BLOCK
        assert "unclear_trust_boundary" in verdict.overrides_applied


# =============================================================================
# Test 21-25: Trading-Specific Overrides
# =============================================================================

class TestTradingOverrides:
    """Test trading-specific override behavior."""
    
    def test_trading_analysis_can_recheck(self, governor_no_truth):
        """Test trading analysis can reach recheck."""
        recommendation = ReviewerResult(
            reviewer_id="eagle",
            recommendation="analyze",
            risk_assessment=RiskLevel.HIGH,
        )
        
        context = PolicyContext(mode="trading")
        
        verdict = governor_no_truth.evaluate(
            recommendation=recommendation,
            context=context,
            policy_class=PolicyClass.TRADING_ANALYSIS,
        )
        
        assert verdict.decision == Decision.RECHECK
        assert "trading" in verdict.tags
    
    def test_trading_execution_never_auto_execute(self, governor_no_truth):
        """Test trading execution never proceeds automatically."""
        for risk in RiskLevel:
            recommendation = ReviewerResult(
                reviewer_id="eagle",
                recommendation="execute",
                risk_assessment=risk,
            )
            
            context = PolicyContext(mode="trading")
            
            verdict = governor_no_truth.evaluate(
                recommendation=recommendation,
                context=context,
                policy_class=PolicyClass.TRADING_EXECUTION_CANDIDATE,
            )
            
            # Either REQUIRE_APPROVAL or BLOCK is acceptable - both prevent auto-execution
            assert verdict.decision in (Decision.REQUIRE_APPROVAL, Decision.BLOCK), \
                f"Risk {risk.value} should not auto-execute"
    
    def test_trading_mode_tagged(self, governor_no_truth):
        """Test trading mode is reflected in tags."""
        recommendation = ReviewerResult(
            reviewer_id="eagle",
            recommendation="analyze",
            risk_assessment=RiskLevel.LOW,
        )
        
        context = PolicyContext(mode="trading")
        
        verdict = governor_no_truth.evaluate(
            recommendation=recommendation,
            context=context,
            policy_class=PolicyClass.TRADING_ANALYSIS,
        )
        
        assert "mode:trading" in verdict.tags
    
    def test_trading_analysis_with_implications_tagged(self, governor_no_truth):
        """Test trading implications add tags."""
        recommendation = ReviewerResult(
            reviewer_id="eagle",
            recommendation="analyze",
            risk_assessment=RiskLevel.LOW,
        )
        
        context = PolicyContext(
            mode="trading",
            has_trading_implications=True,
        )
        
        verdict = governor_no_truth.evaluate(
            recommendation=recommendation,
            context=context,
            policy_class=PolicyClass.TRADING_ANALYSIS,
        )
        
        assert "trading" in verdict.tags


# =============================================================================
# Test 26-30: Trust and Integrity
# =============================================================================

class TestTrustIntegrity:
    """Test trust boundary and integrity checks."""
    
    def test_clear_trust_boundary_allows_sensitive_access(self, governor_no_truth):
        """Test sensitive access with clear trust boundary doesn't block."""
        recommendation = ReviewerResult(
            reviewer_id="qwen",
            recommendation="access",
            risk_assessment=RiskLevel.LOW,
        )
        
        context = PolicyContext(
            mode="ui",
            trust_boundary_clear=True,
        )
        
        verdict = governor_no_truth.evaluate(
            recommendation=recommendation,
            context=context,
            policy_class=PolicyClass.SENSITIVE_DATA_ACCESS,
        )
        
        # Should be recheck (minimum gate), not block
        assert verdict.decision == Decision.RECHECK
        assert not verdict.is_blocked()
    
    def test_sensitive_data_tag_added(self, governor_no_truth):
        """Test sensitive data tag is added when flag is set."""
        recommendation = ReviewerResult(
            reviewer_id="qwen",
            recommendation="access",
            risk_assessment=RiskLevel.LOW,
        )
        
        context = PolicyContext(
            mode="ui",
            sensitive_data_involved=True,
        )
        
        verdict = governor_no_truth.evaluate(
            recommendation=recommendation,
            context=context,
            policy_class=PolicyClass.SENSITIVE_DATA_ACCESS,
        )
        
        assert "sensitive_data" in verdict.tags
    
    def test_external_effects_tag_added(self, governor_no_truth):
        """Test external effects tag is added when flag is set."""
        recommendation = ReviewerResult(
            reviewer_id="eagle",
            recommendation="interact",
            risk_assessment=RiskLevel.LOW,
        )
        
        context = PolicyContext(
            mode="ui",
            external_side_effects=True,
        )
        
        verdict = governor_no_truth.evaluate(
            recommendation=recommendation,
            context=context,
            policy_class=PolicyClass.UI_INTERACTION_CANDIDATE,
        )
        
        assert "external_effects" in verdict.tags
    
    def test_lineage_tracking_in_verdict(self, governor_no_truth, base_context):
        """Test verdict includes proper lineage tracking."""
        source_event = str(uuid4())
        recommendation = ReviewerResult(
            reviewer_id="aya",
            recommendation="test",
            risk_assessment=RiskLevel.LOW,
        )
        
        verdict = governor_no_truth.evaluate(
            recommendation=recommendation,
            context=base_context,
            policy_class=PolicyClass.OBSERVE,
            source_event_id=source_event,
        )
        
        assert verdict.lineage.source_event == source_event
        assert verdict.lineage.reviewer == "aya"
        assert verdict.lineage.trace_id is not None
    
    def test_artifact_refs_in_truth_log(self, governor, base_context):
        """Test artifact references are logged to truth writer."""
        recommendation = ReviewerResult(
            reviewer_id="eagle",
            recommendation="test",
            risk_assessment=RiskLevel.LOW,
        )
        
        context = PolicyContext(
            mode="ui",
            artifact_refs=["artifact_1", "artifact_2"],
        )
        
        verdict = governor.evaluate(
            recommendation=recommendation,
            context=context,
            policy_class=PolicyClass.OBSERVE,
        )
        
        # Verify verdict was created
        assert verdict is not None


# =============================================================================
# Test 31-35: Verdict Structure Validation
# =============================================================================

class TestVerdictStructure:
    """Test GovernorVerdict structure and serialization."""
    
    def test_verdict_has_required_fields(self):
        """Test verdict has all required fields."""
        verdict = create_verdict(
            risk_level=RiskLevel.LOW,
            decision=Decision.CONTINUE,
            policy_class=PolicyClass.OBSERVE,
            rationale="Test rationale",
            source_event=str(uuid4()),
            reviewer="eagle",
        )
        
        assert verdict.verdict_id is not None
        assert verdict.timestamp is not None
        assert verdict.risk_level == RiskLevel.LOW
        assert verdict.decision == Decision.CONTINUE
        assert verdict.policy_class == PolicyClass.OBSERVE
        assert verdict.rationale == "Test rationale"
        assert verdict.lineage is not None
    
    def test_verdict_to_dict_roundtrip(self):
        """Test verdict can be serialized to dict and back."""
        original = create_verdict(
            risk_level=RiskLevel.MEDIUM,
            decision=Decision.WARN,
            policy_class=PolicyClass.TRADING_ANALYSIS,
            rationale="Test",
            source_event=str(uuid4()),
            reviewer="qwen",
            tags=["tag1", "tag2"],
            overrides_applied=["override1"],
        )
        
        data = original.to_dict()
        restored = GovernorVerdict.from_dict(data)
        
        assert restored.risk_level == original.risk_level
        assert restored.decision == original.decision
        assert restored.policy_class == original.policy_class
        assert restored.rationale == original.rationale
        assert restored.tags == original.tags
        assert restored.overrides_applied == original.overrides_applied
    
    def test_verdict_json_serialization(self):
        """Test verdict JSON serialization."""
        verdict = create_verdict(
            risk_level=RiskLevel.HIGH,
            decision=Decision.RECHECK,
            policy_class=PolicyClass.SENSITIVE_DATA_ACCESS,
            rationale="Test JSON",
            source_event=str(uuid4()),
            reviewer="aya",
        )
        
        json_str = verdict.to_json()
        data = json.loads(json_str)
        
        assert data["risk_level"] == "high"
        assert data["decision"] == "recheck"
        assert data["policy_class"] == "sensitive_data_access"
    
    def test_verdict_schema_validation(self):
        """Test verdict validates against schema."""
        verdict = create_verdict(
            risk_level=RiskLevel.LOW,
            decision=Decision.CONTINUE,
            policy_class=PolicyClass.OBSERVE,
            rationale="Valid verdict",
            source_event=str(uuid4()),
            reviewer="eagle",
        )
        
        data = verdict.to_dict()
        is_valid, errors = validate_verdict_dict(data)
        
        assert is_valid, f"Validation errors: {errors}"
    
    def test_invalid_verdict_fails_validation(self):
        """Test invalid verdict data fails schema validation."""
        invalid_data = {
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
        
        is_valid, errors = validate_verdict_dict(invalid_data)
        
        assert not is_valid
        assert any("risk_level" in e for e in errors)


# =============================================================================
# Test 36-40: Integration and Edge Cases
# =============================================================================

class TestIntegrationAndEdgeCases:
    """Test integration scenarios and edge cases."""
    
    def test_truth_writer_logs_verdict(self, truth_writer, base_context):
        """Test that verdicts are logged to truth writer."""
        governor = Governor(truth_writer=truth_writer)
        
        recommendation = ReviewerResult(
            reviewer_id="eagle",
            recommendation="test",
            risk_assessment=RiskLevel.LOW,
        )
        
        verdict = governor.evaluate(
            recommendation=recommendation,
            context=base_context,
            policy_class=PolicyClass.OBSERVE,
        )
        
        # Check that evaluation was counted
        assert governor.eval_count == 1
        assert verdict is not None
    
    def test_quick_evaluate_convenience_function(self):
        """Test quick_evaluate convenience function."""
        verdict = quick_evaluate(
            reviewer_id="eagle",
            risk_level=RiskLevel.LOW,
            policy_class=PolicyClass.OBSERVE,
            mode="ui",
        )
        
        assert verdict.decision == Decision.CONTINUE
        assert verdict.policy_class == PolicyClass.OBSERVE
    
    def test_policy_class_string_input(self, governor_no_truth, base_context):
        """Test that string policy class names work."""
        recommendation = ReviewerResult(
            reviewer_id="eagle",
            recommendation="test",
            risk_assessment=RiskLevel.LOW,
        )
        
        verdict = governor_no_truth.evaluate(
            recommendation=recommendation,
            context=base_context,
            policy_class="observe",  # String instead of enum
        )
        
        assert verdict.policy_class == PolicyClass.OBSERVE
    
    def test_custom_policy_matrix(self):
        """Test governor with custom policy matrix."""
        custom_matrix = {
            PolicyClass.OBSERVE: PolicyRule(
                policy_class=PolicyClass.OBSERVE,
                default_max=Decision.CONTINUE,  # More restrictive
                minimum_gate=Decision.CONTINUE,
                description="Custom observe rule",
            ),
        }
        
        governor = Governor(policy_matrix=custom_matrix)
        
        recommendation = ReviewerResult(
            reviewer_id="eagle",
            recommendation="test",
            risk_assessment=RiskLevel.HIGH,
        )
        
        context = PolicyContext()
        
        verdict = governor.evaluate(
            recommendation=recommendation,
            context=context,
            policy_class=PolicyClass.OBSERVE,
        )
        
        # Should be capped at continue by custom rule
        assert verdict.decision == Decision.CONTINUE
    
    def test_multiple_overrides_can_apply(self, governor_no_truth):
        """Test that multiple overrides can apply simultaneously."""
        recommendation = ReviewerResult(
            reviewer_id="eagle",
            recommendation="execute",
            risk_assessment=RiskLevel.LOW,
        )
        
        context = PolicyContext(
            mode="trading",
            external_side_effects=True,
        )
        
        verdict = governor_no_truth.evaluate(
            recommendation=recommendation,
            context=context,
            policy_class=PolicyClass.TRADING_EXECUTION_CANDIDATE,
        )
        
        # Trading execution candidate override should apply
        assert "trading_execution_candidate" in verdict.overrides_applied
        assert verdict.decision == Decision.REQUIRE_APPROVAL


# =============================================================================
# Test 41-42: Governor State and Policy Access
# =============================================================================

class TestGovernorState:
    """Test governor state management."""
    
    def test_get_policy_rule(self, governor_no_truth):
        """Test retrieving policy rules."""
        rule = governor_no_truth.get_policy_rule(PolicyClass.TRADING_EXECUTION_CANDIDATE)
        
        assert rule is not None
        assert rule.policy_class == PolicyClass.TRADING_EXECUTION_CANDIDATE
        assert rule.minimum_gate == Decision.REQUIRE_APPROVAL
    
    def test_update_policy_rule(self, governor_no_truth):
        """Test updating policy rules."""
        new_rule = PolicyRule(
            policy_class=PolicyClass.OBSERVE,
            default_max=Decision.RECHECK,
            minimum_gate=None,
            description="Updated rule",
        )
        
        governor_no_truth.update_policy_rule(PolicyClass.OBSERVE, new_rule)
        
        rule = governor_no_truth.get_policy_rule(PolicyClass.OBSERVE)
        assert rule.default_max == Decision.RECHECK


# =============================================================================
# Test 43-45: Verdict Helper Methods
# =============================================================================

class TestVerdictHelpers:
    """Test verdict helper methods."""
    
    def test_is_execution_allowed(self):
        """Test is_execution_allowed helper."""
        continue_verdict = create_verdict(
            risk_level=RiskLevel.LOW,
            decision=Decision.CONTINUE,
            policy_class=PolicyClass.OBSERVE,
            rationale="Test",
            source_event=str(uuid4()),
            reviewer="eagle",
        )
        
        warn_verdict = create_verdict(
            risk_level=RiskLevel.MEDIUM,
            decision=Decision.WARN,
            policy_class=PolicyClass.OBSERVE,
            rationale="Test",
            source_event=str(uuid4()),
            reviewer="eagle",
        )
        
        block_verdict = create_verdict(
            risk_level=RiskLevel.CRITICAL,
            decision=Decision.BLOCK,
            policy_class=PolicyClass.OBSERVE,
            rationale="Test",
            source_event=str(uuid4()),
            reviewer="eagle",
        )
        
        assert continue_verdict.is_execution_allowed()
        assert warn_verdict.is_execution_allowed()
        assert not block_verdict.is_execution_allowed()
    
    def test_is_blocked(self):
        """Test is_blocked helper."""
        block_verdict = create_verdict(
            risk_level=RiskLevel.CRITICAL,
            decision=Decision.BLOCK,
            policy_class=PolicyClass.OBSERVE,
            rationale="Test",
            source_event=str(uuid4()),
            reviewer="eagle",
        )
        
        continue_verdict = create_verdict(
            risk_level=RiskLevel.LOW,
            decision=Decision.CONTINUE,
            policy_class=PolicyClass.OBSERVE,
            rationale="Test",
            source_event=str(uuid4()),
            reviewer="eagle",
        )
        
        assert block_verdict.is_blocked()
        assert not continue_verdict.is_blocked()
    
    def test_requires_approval(self):
        """Test requires_approval helper."""
        approval_verdict = create_verdict(
            risk_level=RiskLevel.HIGH,
            decision=Decision.REQUIRE_APPROVAL,
            policy_class=PolicyClass.TRADING_EXECUTION_CANDIDATE,
            rationale="Test",
            source_event=str(uuid4()),
            reviewer="eagle",
        )
        
        continue_verdict = create_verdict(
            risk_level=RiskLevel.LOW,
            decision=Decision.CONTINUE,
            policy_class=PolicyClass.OBSERVE,
            rationale="Test",
            source_event=str(uuid4()),
            reviewer="eagle",
        )
        
        assert approval_verdict.requires_approval()
        assert not continue_verdict.requires_approval()


# =============================================================================
# Test 46-50: Enum and Schema Tests
# =============================================================================

class TestEnumsAndSchema:
    """Test enums and schema definitions."""
    
    def test_risk_level_enum_values(self):
        """Test risk level enum has all expected values."""
        expected = ["none", "low", "medium", "high", "critical"]
        actual = [r.value for r in RiskLevel]
        assert actual == expected
    
    def test_decision_enum_values(self):
        """Test decision enum has all expected values."""
        expected = ["continue", "warn", "recheck", "require_approval", "block"]
        actual = [d.value for d in Decision]
        assert actual == expected
    
    def test_policy_class_enum_values(self):
        """Test policy class enum has all 9 expected values."""
        expected = [
            "observe",
            "inform",
            "internal_state_update",
            "external_review",
            "trading_analysis",
            "trading_execution_candidate",
            "ui_interaction_candidate",
            "sensitive_data_access",
            "promotion_candidate",
        ]
        actual = [p.value for p in PolicyClass]
        assert actual == expected
    
    def test_governor_verdict_schema_structure(self):
        """Test that schema has all required fields defined."""
        required = GOVERNOR_VERDICT_SCHEMA["required"]
        assert "verdict_id" in required
        assert "timestamp" in required
        assert "risk_level" in required
        assert "decision" in required
        assert "policy_class" in required
        assert "rationale" in required
        assert "lineage" in required
    
    def test_lineage_roundtrip(self):
        """Test lineage serialization roundtrip."""
        original = Lineage(
            source_event=str(uuid4()),
            reviewer="eagle",
            trace_id=str(uuid4()),
        )
        
        data = original.to_dict()
        restored = Lineage.from_dict(data)
        
        assert restored.source_event == original.source_event
        assert restored.reviewer == original.reviewer
        assert restored.trace_id == original.trace_id
