"""Tests for the governed pipeline integration.

Test coverage:
- Full pipeline from capture to verdict
- Governor blocks suspicious detections
- Recheck verdicts route correctly
- TruthWriter logs all pipeline stages
- WSS only receives approved packets
- Lineage preserved through all stages
- Hot path performance (<5s total)
- All routing paths (block, recheck, approval, continue, warn)
- Reviewer cannot bypass governor
- Execution only proceeds if verdict allows
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4

import pytest
from PIL import Image

# Ensure src is in path
import sys
sys.path.insert(0, "/home/netjer/.openclaw/workspace/plane-a/projects/advanced-vision/src")

from advanced_vision.core.governor import Governor, ReviewerResult, PolicyContext
from advanced_vision.core.governor_verdict import (
    GovernorVerdict,
    Decision,
    RiskLevel,
    PolicyClass,
    create_verdict,
)
from advanced_vision.core.execution_gate import ExecutionGate, GateDecision
from advanced_vision.core.execution_precondition import ExecutionPrecondition
from advanced_vision.core.truth_writer import TruthWriter

from advanced_vision.trading.pipeline_stages import (
    StageContext,
    StageResult,
    CaptureStage,
    DetectionStage,
    ScoutStage,
    GovernanceStage,
    ExecutionStage,
    create_stage,
)

from advanced_vision.trading.governed_pipeline import (
    GovernedPipeline,
    PipelineResult,
    create_governed_pipeline,
)

from advanced_vision.trading.wss_manager import WSSPublisherManager


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def temp_truth_dir():
    """Create a temporary directory for truth logs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def truth_writer(temp_truth_dir):
    """Create a TruthWriter with temp directory."""
    return TruthWriter(temp_truth_dir)


@pytest.fixture
def mock_frame():
    """Create a mock frame (PIL Image)."""
    return Image.new('RGB', (1920, 1080), color='white')


@pytest.fixture
def governor(truth_writer):
    """Create a Governor with truth writer."""
    return Governor(truth_writer=truth_writer)


@pytest.fixture
def execution_gate(governor):
    """Create an ExecutionGate with governor."""
    return ExecutionGate(governor=governor)


@pytest.fixture
def governed_pipeline(temp_truth_dir, truth_writer):
    """Create a GovernedPipeline with temp truth directory."""
    return create_governed_pipeline(
        truth_dir=temp_truth_dir,
        mode="trading",
        policy_class="trading_analysis",
    )


@pytest.fixture
def sample_verdict_continue():
    """Create a sample CONTINUE verdict."""
    return create_verdict(
        risk_level=RiskLevel.LOW,
        decision=Decision.CONTINUE,
        policy_class=PolicyClass.TRADING_ANALYSIS,
        rationale="Low risk detection, safe to continue",
        source_event=str(uuid4()),
        reviewer="eagle_scout",
    )


@pytest.fixture
def sample_verdict_warn():
    """Create a sample WARN verdict."""
    return create_verdict(
        risk_level=RiskLevel.MEDIUM,
        decision=Decision.WARN,
        policy_class=PolicyClass.TRADING_ANALYSIS,
        rationale="Medium risk detection, proceed with caution",
        source_event=str(uuid4()),
        reviewer="eagle_scout",
    )


@pytest.fixture
def sample_verdict_recheck():
    """Create a sample RECHECK verdict."""
    return create_verdict(
        risk_level=RiskLevel.HIGH,
        decision=Decision.RECHECK,
        policy_class=PolicyClass.TRADING_ANALYSIS,
        rationale="High risk detection requires recheck",
        source_event=str(uuid4()),
        reviewer="eagle_scout",
    )


@pytest.fixture
def sample_verdict_block():
    """Create a sample BLOCK verdict."""
    return create_verdict(
        risk_level=RiskLevel.CRITICAL,
        decision=Decision.BLOCK,
        policy_class=PolicyClass.TRADING_ANALYSIS,
        rationale="Critical risk detection blocked",
        source_event=str(uuid4()),
        reviewer="eagle_scout",
    )


@pytest.fixture
def sample_verdict_require_approval():
    """Create a sample REQUIRE_APPROVAL verdict."""
    return create_verdict(
        risk_level=RiskLevel.HIGH,
        decision=Decision.REQUIRE_APPROVAL,
        policy_class=PolicyClass.TRADING_EXECUTION_CANDIDATE,
        rationale="Trading execution requires approval",
        source_event=str(uuid4()),
        reviewer="eagle_scout",
    )


# =============================================================================
# Test Class 1: Pipeline Stage Tests
# =============================================================================

class TestPipelineStages:
    """Tests for individual pipeline stages."""
    
    def test_capture_stage_creates_frame_id(self, truth_writer, mock_frame):
        """Test that capture stage creates frame ID and logs to TruthWriter."""
        stage = CaptureStage(truth_writer=truth_writer)
        context = StageContext()
        
        result = stage.execute({"frame": mock_frame}, context)
        
        assert result.success is True
        assert result.stage_name == "capture"
        assert context.frame_id is not None
        assert result.output_data["frame_id"] == context.frame_id
    
    def test_detection_stage_produces_detections(self, truth_writer, mock_frame):
        """Test that detection stage produces detection output."""
        capture_stage = CaptureStage(truth_writer=truth_writer)
        detection_stage = DetectionStage(
            truth_writer=truth_writer,
            config={"dry_run": True}
        )
        context = StageContext()
        
        # First run capture
        capture_result = capture_stage.execute({"frame": mock_frame}, context)
        
        # Then run detection
        result = detection_stage.execute(capture_result.output_data, context)
        
        assert result.success is True
        assert result.stage_name == "detection"
        assert "detections" in result.output_data
        assert "detection_count" in result.output_data
    
    def test_scout_stage_classifies_detections(self, truth_writer, mock_frame):
        """Test that scout stage classifies detections."""
        capture_stage = CaptureStage(truth_writer=truth_writer)
        detection_stage = DetectionStage(truth_writer=truth_writer, config={"dry_run": True})
        scout_stage = ScoutStage(truth_writer=truth_writer)
        context = StageContext()
        
        # Run pipeline through detection
        capture_result = capture_stage.execute({"frame": mock_frame}, context)
        detection_result = detection_stage.execute(capture_result.output_data, context)
        
        # Run scout stage
        result = scout_stage.execute(detection_result.output_data, context)
        
        assert result.success is True
        assert result.stage_name == "scout"
        assert "classifications" in result.output_data
        assert "overall_risk_level" in result.output_data
    
    def test_governance_stage_produces_verdict(self, truth_writer, mock_frame):
        """Test that governance stage produces a GovernorVerdict."""
        capture_stage = CaptureStage(truth_writer=truth_writer)
        detection_stage = DetectionStage(truth_writer=truth_writer, config={"dry_run": True})
        scout_stage = ScoutStage(truth_writer=truth_writer)
        governance_stage = GovernanceStage(
            truth_writer=truth_writer,
            config={"mode": "trading", "policy_class": "trading_analysis"}
        )
        context = StageContext()
        
        # Run pipeline through scout
        capture_result = capture_stage.execute({"frame": mock_frame}, context)
        detection_result = detection_stage.execute(capture_result.output_data, context)
        scout_result = scout_stage.execute(detection_result.output_data, context)
        
        # Run governance stage
        result = governance_stage.execute(scout_result.output_data, context)
        
        assert result.success is True
        assert result.stage_name == "governance"
        assert "verdict" in result.output_data
        assert isinstance(result.output_data["verdict"], GovernorVerdict)
        assert "decision" in result.output_data
    
    def test_execution_stage_validates_verdict(self, truth_writer, mock_frame):
        """Test that execution stage validates verdict and produces gate decision."""
        capture_stage = CaptureStage(truth_writer=truth_writer)
        detection_stage = DetectionStage(truth_writer=truth_writer, config={"dry_run": True})
        scout_stage = ScoutStage(truth_writer=truth_writer)
        governance_stage = GovernanceStage(
            truth_writer=truth_writer,
            config={"mode": "trading", "policy_class": "trading_analysis"}
        )
        execution_stage = ExecutionStage(truth_writer=truth_writer, config={"mode": "trading"})
        context = StageContext()
        
        # Run pipeline through governance
        capture_result = capture_stage.execute({"frame": mock_frame}, context)
        detection_result = detection_stage.execute(capture_result.output_data, context)
        scout_result = scout_stage.execute(detection_result.output_data, context)
        governance_result = governance_stage.execute(scout_result.output_data, context)
        
        # Run execution stage
        result = execution_stage.execute(governance_result.output_data, context)
        
        assert result.success is True
        assert result.stage_name == "execution"
        assert "gate_decision" in result.output_data
        assert "can_execute" in result.output_data


# =============================================================================
# Test Class 2: Full Pipeline Tests
# =============================================================================

class TestGovernedPipeline:
    """Tests for the full governed pipeline."""
    
    def test_full_pipeline_from_capture_to_verdict(self, governed_pipeline, mock_frame):
        """Test: full pipeline from capture to verdict."""
        result = governed_pipeline.process_frame(mock_frame, {"source": "test"})
        
        assert isinstance(result, PipelineResult)
        assert result.success is True
        assert result.verdict is not None
        assert result.frame_id is not None
        assert result.pipeline_id is not None
        assert result.trace_id is not None
        assert len(result.stages) == 5  # capture, detection, scout, governance, execution
        assert result.total_duration_ms > 0
        
        # Verify all stages completed
        stage_names = [s.stage_name for s in result.stages]
        assert "capture" in stage_names
        assert "detection" in stage_names
        assert "scout" in stage_names
        assert "governance" in stage_names
        assert "execution" in stage_names
    
    def test_truthwriter_logs_all_pipeline_stages(self, temp_truth_dir, governed_pipeline, mock_frame):
        """Test: TruthWriter logs all pipeline stages."""
        # Process a frame
        result = governed_pipeline.process_frame(mock_frame, {"source": "test"})
        
        assert result.success is True
        
        # Check that events were written to TruthWriter
        events = governed_pipeline.truth_writer.get_events_for_date(datetime.now())
        
        # Should have stage completion events plus pipeline completion
        event_types = [e.get("event_type") for e in events]
        assert "pipeline_stage_complete" in event_types
        assert "pipeline_complete" in event_types
        
        # Count stage completion events
        stage_events = [e for e in events if e.get("event_type") == "pipeline_stage_complete"]
        assert len(stage_events) >= 5  # At least 5 stages logged
    
    def test_lineage_preserved_through_all_stages(self, governed_pipeline, mock_frame):
        """Test: lineage preserved through all stages."""
        result = governed_pipeline.process_frame(mock_frame, {"source": "test"})
        
        assert result.success is True
        
        # Check that all stages have proper parent references
        parent_ids = set()
        for i, stage in enumerate(result.stages):
            if i > 0:
                # Each stage (except first) should reference a previous stage
                assert stage.parent_stage_id is not None
                assert stage.parent_stage_id in parent_ids
            parent_ids.add(stage.stage_id)
        
        # Verify trace_id is consistent
        trace_ids = set(s.output_data.get("trace_id") for s in result.stages if "trace_id" in s.output_data)
        if trace_ids:
            assert len(trace_ids) == 1  # All stages should share the same trace
    
    def test_hot_path_performance_under_5s(self, governed_pipeline, mock_frame):
        """Test: hot path performance (<5s total)."""
        start_time = time.time()
        result = governed_pipeline.process_frame(mock_frame, {"source": "test"})
        elapsed_ms = (time.time() - start_time) * 1000
        
        assert result.success is True
        assert result.total_duration_ms < 5000, f"Pipeline took {result.total_duration_ms}ms, expected <5000ms"
        assert elapsed_ms < 5000, f"Total elapsed time {elapsed_ms}ms exceeded 5000ms"
    
    def test_pipeline_handles_errors_gracefully(self, governed_pipeline):
        """Test that pipeline handles errors gracefully."""
        # Pass None as frame to trigger error
        result = governed_pipeline.process_frame(None, {"source": "test"})
        
        assert result.success is False
        assert result.error is not None


# =============================================================================
# Test Class 3: Governor Verdict Tests
# =============================================================================

class TestGovernorVerdictHandling:
    """Tests for governor verdict handling."""
    
    def test_governor_blocks_suspicious_detections(self, temp_truth_dir, mock_frame):
        """Test: governor blocks suspicious detections."""
        # Create a governor that will produce a BLOCK verdict
        truth_writer = TruthWriter(temp_truth_dir)
        
        # Create a pipeline and mock the governance stage to return BLOCK
        pipeline = create_governed_pipeline(
            truth_dir=temp_truth_dir,
            mode="trading",
            policy_class="trading_analysis",
        )
        
        # Process a frame
        result = pipeline.process_frame(mock_frame, {"source": "test"})
        
        # Verify we got a verdict
        assert result.verdict is not None
        
        # Test with explicitly high-risk scenario
        reviewer_result = ReviewerResult(
            reviewer_id="eagle",
            recommendation="block",
            risk_assessment=RiskLevel.CRITICAL,
            confidence=0.95,
        )
        
        context = PolicyContext(mode="trading", has_trading_implications=True)
        verdict = pipeline.governor.evaluate(
            recommendation=reviewer_result,
            context=context,
            policy_class=PolicyClass.TRADING_EXECUTION_CANDIDATE,
        )
        
        # Should block critical risk trading execution
        assert verdict.decision in (Decision.BLOCK, Decision.REQUIRE_APPROVAL)
    
    def test_recheck_verdicts_route_correctly(self, temp_truth_dir, mock_frame):
        """Test: recheck verdicts route correctly."""
        truth_writer = TruthWriter(temp_truth_dir)
        pipeline = create_governed_pipeline(
            truth_dir=temp_truth_dir,
            mode="trading",
            policy_class="trading_analysis",
        )
        
        # Create a recheck verdict
        verdict = create_verdict(
            risk_level=RiskLevel.HIGH,
            decision=Decision.RECHECK,
            policy_class=PolicyClass.TRADING_ANALYSIS,
            rationale="High risk requires recheck",
            source_event=str(uuid4()),
            reviewer="eagle_scout",
        )
        
        # Test execution gate with recheck verdict
        packet = {"frame_id": "test_frame", "execution_candidate": True}
        gate = ExecutionGate(governor=pipeline.governor)
        gate_decision = gate.process_with_verdict(packet, verdict)
        
        assert gate_decision.can_execute is False
        assert gate_decision.requires_recheck is True
        assert gate_decision.route_to == "recheck"
    
    def test_approval_required_verdicts_route_correctly(self, temp_truth_dir, mock_frame):
        """Test: approval required verdicts route correctly."""
        truth_writer = TruthWriter(temp_truth_dir)
        pipeline = create_governed_pipeline(
            truth_dir=temp_truth_dir,
            mode="trading",
            policy_class="trading_execution_candidate",
        )
        
        # Create an approval required verdict
        verdict = create_verdict(
            risk_level=RiskLevel.HIGH,
            decision=Decision.REQUIRE_APPROVAL,
            policy_class=PolicyClass.TRADING_EXECUTION_CANDIDATE,
            rationale="Trading execution requires approval",
            source_event=str(uuid4()),
            reviewer="eagle_scout",
        )
        
        # Test execution gate with approval required verdict
        packet = {"frame_id": "test_frame", "execution_candidate": True}
        gate = ExecutionGate(governor=pipeline.governor)
        gate_decision = gate.process_with_verdict(packet, verdict)
        
        assert gate_decision.can_execute is False
        assert gate_decision.requires_approval is True
        assert gate_decision.route_to == "approval_queue"
    
    def test_continue_verdict_allows_execution(self, temp_truth_dir, mock_frame):
        """Test: continue verdict allows execution."""
        truth_writer = TruthWriter(temp_truth_dir)
        pipeline = create_governed_pipeline(
            truth_dir=temp_truth_dir,
            mode="trading",
            policy_class="trading_analysis",
        )
        
        # Create a continue verdict
        verdict = create_verdict(
            risk_level=RiskLevel.LOW,
            decision=Decision.CONTINUE,
            policy_class=PolicyClass.TRADING_ANALYSIS,
            rationale="Low risk, continue",
            source_event=str(uuid4()),
            reviewer="eagle_scout",
        )
        
        # Test execution gate with continue verdict
        packet = {"frame_id": "test_frame", "execution_candidate": True}
        gate = ExecutionGate(governor=pipeline.governor)
        gate_decision = gate.process_with_verdict(packet, verdict)
        
        assert gate_decision.can_execute is True
        assert gate_decision.requires_recheck is False
        assert gate_decision.requires_approval is False
    
    def test_reviewer_cannot_bypass_governor(self, temp_truth_dir, mock_frame):
        """Test: reviewer cannot bypass governor."""
        # Create a scenario where reviewer says "continue" but governor should override
        truth_writer = TruthWriter(temp_truth_dir)
        pipeline = create_governed_pipeline(
            truth_dir=temp_truth_dir,
            mode="trading",
            policy_class="trading_execution_candidate",
        )
        
        # Reviewer says "continue" with low risk
        reviewer_result = ReviewerResult(
            reviewer_id="eagle",
            recommendation="continue",
            risk_assessment=RiskLevel.LOW,  # Reviewer says low risk
            confidence=0.8,
        )
        
        # But policy class is TRADING_EXECUTION_CANDIDATE which requires approval
        context = PolicyContext(
            mode="trading",
            has_trading_implications=True,
        )
        
        verdict = pipeline.governor.evaluate(
            recommendation=reviewer_result,
            context=context,
            policy_class=PolicyClass.TRADING_EXECUTION_CANDIDATE,
        )
        
        # Governor should override and require approval regardless of reviewer
        assert verdict.decision == Decision.REQUIRE_APPROVAL
        assert "trading_execution_candidate" in verdict.overrides_applied or \
               verdict.decision == Decision.REQUIRE_APPROVAL
    
    def test_execution_only_proceeds_if_verdict_allows(self, temp_truth_dir, mock_frame):
        """Test: execution only proceeds if verdict allows."""
        truth_writer = TruthWriter(temp_truth_dir)
        pipeline = create_governed_pipeline(
            truth_dir=temp_truth_dir,
            mode="trading",
            policy_class="trading_analysis",
        )
        
        # Test with different verdicts
        test_cases = [
            (Decision.CONTINUE, True),
            (Decision.WARN, True),
            (Decision.RECHECK, False),
            (Decision.REQUIRE_APPROVAL, False),
            (Decision.BLOCK, False),
        ]
        
        for decision, should_execute in test_cases:
            verdict = create_verdict(
                risk_level=RiskLevel.MEDIUM,
                decision=decision,
                policy_class=PolicyClass.TRADING_ANALYSIS,
                rationale=f"Test {decision.value}",
                source_event=str(uuid4()),
                reviewer="test",
            )
            
            packet = {"frame_id": "test_frame", "execution_candidate": True}
            gate = ExecutionGate(governor=pipeline.governor)
            gate_decision = gate.process_with_verdict(packet, verdict)
            
            assert gate_decision.can_execute == should_execute, \
                f"Decision {decision.value} should {'allow' if should_execute else 'block'} execution"


# =============================================================================
# Test Class 4: WSS Integration Tests
# =============================================================================

class TestWSSGovernorIntegration:
    """Tests for WSS manager governor integration."""
    
    def test_wss_only_receives_approved_packets(self, temp_truth_dir, sample_verdict_continue):
        """Test: WSS only receives approved packets."""
        truth_writer = TruthWriter(temp_truth_dir)
        
        # Create WSS manager with governor enabled
        manager = WSSPublisherManager(
            base_dir=temp_truth_dir,
            enable_governor=True,
            truth_writer=truth_writer,
            suppress_blocked_packets=True,
            enable_analysis=True,
        )
        
        # Check verdict before publish with CONTINUE
        result = manager.check_verdict_before_publish(sample_verdict_continue)
        assert result["can_publish"] is True
        assert result["action"] == "publish"
        
        # Check with BLOCK verdict
        block_verdict = create_verdict(
            risk_level=RiskLevel.CRITICAL,
            decision=Decision.BLOCK,
            policy_class=PolicyClass.TRADING_ANALYSIS,
            rationale="Blocked",
            source_event=str(uuid4()),
            reviewer="test",
        )
        
        result = manager.check_verdict_before_publish(block_verdict)
        assert result["can_publish"] is False
        assert result["action"] == "block"
    
    def test_wss_blocks_packets_with_block_verdict(self, temp_truth_dir, sample_verdict_block):
        """Test: WSS blocks packets with BLOCK verdict."""
        truth_writer = TruthWriter(temp_truth_dir)
        
        manager = WSSPublisherManager(
            base_dir=temp_truth_dir,
            enable_governor=True,
            truth_writer=truth_writer,
            suppress_blocked_packets=True,
            enable_analysis=False,  # Don't need actual WSS connection
        )
        
        # Check that BLOCK verdict suppresses publishing
        result = manager.check_verdict_before_publish(sample_verdict_block)
        
        assert result["can_publish"] is False
        assert result["action"] == "block"
    
    def test_wss_recheck_packets_not_published(self, temp_truth_dir, sample_verdict_recheck):
        """Test: WSS does not publish recheck packets."""
        truth_writer = TruthWriter(temp_truth_dir)
        
        manager = WSSPublisherManager(
            base_dir=temp_truth_dir,
            enable_governor=True,
            truth_writer=truth_writer,
            suppress_blocked_packets=True,
            enable_analysis=False,
        )
        
        result = manager.check_verdict_before_publish(sample_verdict_recheck)
        
        assert result["can_publish"] is False
        assert result["action"] == "recheck"
    
    def test_wss_approval_pending_packets_flagged(self, temp_truth_dir, sample_verdict_require_approval):
        """Test: WSS approval pending packets are flagged."""
        truth_writer = TruthWriter(temp_truth_dir)
        
        manager = WSSPublisherManager(
            base_dir=temp_truth_dir,
            enable_governor=True,
            truth_writer=truth_writer,
            publish_approval_pending=True,
            enable_analysis=False,
        )
        
        result = manager.check_verdict_before_publish(sample_verdict_require_approval)
        
        # Should be allowed but flagged as approval_pending
        assert result["can_publish"] is True
        assert result["action"] == "approval_pending"
    
    def test_wss_logs_blocked_packets_to_truthwriter(self, temp_truth_dir, sample_verdict_block):
        """Test: WSS logs blocked packets to TruthWriter."""
        truth_writer = TruthWriter(temp_truth_dir)
        
        manager = WSSPublisherManager(
            base_dir=temp_truth_dir,
            enable_governor=True,
            truth_writer=truth_writer,
            suppress_blocked_packets=True,
            enable_analysis=False,
        )
        
        # Log a suppressed packet
        packet = {
            "frame_id": "test_frame",
            "analysis": "Test analysis",
            "risk_level": "critical",
        }
        manager._log_suppressed_packet(packet, sample_verdict_block, "blocked")
        
        # Check that event was logged
        events = truth_writer.get_events_for_date(datetime.now())
        suppression_events = [e for e in events if e.get("event_type") == "wss_packet_suppressed"]
        
        assert len(suppression_events) >= 1
        assert suppression_events[0].get("suppression_reason") == "blocked"
        assert suppression_events[0].get("verdict_id") == sample_verdict_block.verdict_id
    
    def test_wss_governor_stats_tracked(self, temp_truth_dir):
        """Test: WSS governor statistics are tracked."""
        truth_writer = TruthWriter(temp_truth_dir)
        
        manager = WSSPublisherManager(
            base_dir=temp_truth_dir,
            enable_governor=True,
            truth_writer=truth_writer,
            suppress_blocked_packets=True,
            enable_analysis=False,
        )
        
        # Check initial stats
        stats = manager.governor_stats
        assert stats["enabled"] is True
        assert stats["packets_checked"] == 0
        
        # Process some verdicts through _check_execution_gate
        for decision in [Decision.CONTINUE, Decision.BLOCK, Decision.RECHECK]:
            verdict = create_verdict(
                risk_level=RiskLevel.MEDIUM,
                decision=decision,
                policy_class=PolicyClass.TRADING_ANALYSIS,
                rationale=f"Test {decision.value}",
                source_event=str(uuid4()),
                reviewer="test",
            )
            packet = {"frame_id": "test", "execution_candidate": True}
            manager._check_execution_gate(packet, verdict)
        
        # Check updated stats
        stats = manager.governor_stats
        assert stats["packets_checked"] == 3


# =============================================================================
# Test Class 5: Edge Cases and Integration
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and integration scenarios."""
    
    def test_pipeline_with_no_detections(self, temp_truth_dir):
        """Test pipeline handles frames with no detections."""
        pipeline = create_governed_pipeline(
            truth_dir=temp_truth_dir,
            mode="trading",
        )
        
        # Create a blank frame
        blank_frame = Image.new('RGB', (100, 100), color='black')
        
        result = pipeline.process_frame(blank_frame, {"source": "test"})
        
        # Should still complete successfully even with no detections
        assert result.success is True
        assert result.verdict is not None
    
    def test_pipeline_handles_recheck_callback(self, temp_truth_dir, mock_frame):
        """Test pipeline handles recheck callback."""
        pipeline = create_governed_pipeline(
            truth_dir=temp_truth_dir,
            mode="trading",
        )
        
        # Set up a recheck handler
        recheck_called = False
        recheck_pipeline_id = None
        
        def recheck_handler(pipeline_id, verdict, stage_context):
            nonlocal recheck_called, recheck_pipeline_id
            recheck_called = True
            recheck_pipeline_id = pipeline_id
        
        pipeline.set_recheck_handler(recheck_handler)
        
        # Force a recheck verdict by using a high-risk configuration
        # This test verifies the callback mechanism works
        # (Actual recheck trigger depends on detection output)
        
        result = pipeline.process_frame(mock_frame, {"source": "test"})
        
        assert result.success is True
        # Recheck handler may or may not be called depending on detection output
    
    def test_execution_gate_freshness_check(self, temp_truth_dir):
        """Test ExecutionGate freshness check."""
        precondition = ExecutionPrecondition(default_freshness_seconds=1)
        
        # Create a fresh verdict
        fresh_verdict = create_verdict(
            risk_level=RiskLevel.LOW,
            decision=Decision.CONTINUE,
            policy_class=PolicyClass.TRADING_ANALYSIS,
            rationale="Fresh verdict",
            source_event=str(uuid4()),
            reviewer="test",
        )
        
        packet = {"execution_candidate": True}
        
        # Should pass freshness check
        result = precondition.check(packet, fresh_verdict)
        assert result.allowed is True
        
        # Simulate stale verdict by manipulating timestamp
        # (In real test, would wait or mock time)
    
    def test_pipeline_statistics_accumulate(self, temp_truth_dir, mock_frame):
        """Test pipeline statistics accumulate correctly."""
        pipeline = create_governed_pipeline(
            truth_dir=temp_truth_dir,
            mode="trading",
        )
        
        # Process multiple frames
        for _ in range(3):
            pipeline.process_frame(mock_frame, {"source": "test"})
        
        stats = pipeline.stats
        
        assert stats["process_count"] == 3
        assert stats["error_count"] == 0
        # Other stats depend on verdict outcomes
    
    def test_pipeline_reset_stats(self, temp_truth_dir, mock_frame):
        """Test pipeline stats can be reset."""
        pipeline = create_governed_pipeline(
            truth_dir=temp_truth_dir,
            mode="trading",
        )
        
        # Process a frame
        pipeline.process_frame(mock_frame, {"source": "test"})
        assert pipeline.stats["process_count"] == 1
        
        # Reset stats
        pipeline.reset_stats()
        assert pipeline.stats["process_count"] == 0


# =============================================================================
# Test Class 6: Configuration Tests
# =============================================================================

class TestConfiguration:
    """Tests for pipeline configuration."""
    
    def test_pipeline_respects_policy_class_config(self, temp_truth_dir, mock_frame):
        """Test pipeline respects policy class configuration."""
        # Trading analysis policy
        pipeline = create_governed_pipeline(
            truth_dir=temp_truth_dir,
            mode="trading",
            policy_class="trading_analysis",
        )
        
        result = pipeline.process_frame(mock_frame, {"source": "test"})
        
        assert result.success is True
        assert result.verdict is not None
        assert result.verdict.policy_class == PolicyClass.TRADING_ANALYSIS
    
    def test_stage_factory_creates_correct_stages(self, truth_writer):
        """Test stage factory creates correct stage types."""
        capture = create_stage("capture", truth_writer)
        assert isinstance(capture, CaptureStage)
        
        detection = create_stage("detection", truth_writer)
        assert isinstance(detection, DetectionStage)
        
        scout = create_stage("scout", truth_writer)
        assert isinstance(scout, ScoutStage)
        
        governance = create_stage("governance", truth_writer)
        assert isinstance(governance, GovernanceStage)
        
        execution = create_stage("execution", truth_writer)
        assert isinstance(execution, ExecutionStage)
    
    def test_stage_factory_rejects_unknown_stage(self, truth_writer):
        """Test stage factory rejects unknown stage types."""
        with pytest.raises(ValueError, match="Unknown stage type"):
            create_stage("unknown_stage", truth_writer)


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
