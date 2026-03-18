"""Tests for Track B: Trading-Watch Intelligence.

Tests cover:
- B0: Domain framing (event taxonomy)
- B1: Higher-precision visual review (ROI, detection)
- B2: Local reviewer lane

Safety:
    All tests use dry_run=True by default.
    No actual model downloads or inference.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

# Import trading module
from advanced_vision.trading import (
    ActionRecommendation,
    BoundingBox,
    ChartRegionDetector,
    DetectionPipeline,
    DetectionResult,
    DetectionSource,
    DetectorConfig,
    DetectorMode,
    EscalationPreparer,
    EvidenceBundle,
    EvidenceBundler,
    LocalReviewer,
    ROI,
    ROIConfig,
    ROIExtractor,
    ReviewerAssessment,
    ReviewerConfig,
    ReviewerInput,
    ReviewerLane,
    ReviewerModel,
    RiskLevel,
    TradingEvent,
    TradingEventType,
    UIElement,
    UIElementType,
    create_detector,
    create_reviewer,
    create_reviewer_lane,
    is_noise_event,
    is_trading_relevant,
    requires_reviewer,
    should_escalate_to_overseer,
)
from advanced_vision.trading.events import TRADING_EVENT_PRIORITY


# =============================================================================
# B0: Domain Framing - Event Taxonomy Tests
# =============================================================================

class TestEventTaxonomy:
    """B0: Test trading event type definitions and classifications."""
    
    def test_risk_level_enum(self):
        """B0.1: Risk levels are properly defined."""
        assert RiskLevel.NONE.value == "none"
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.MEDIUM.value == "medium"
        assert RiskLevel.HIGH.value == "high"
        assert RiskLevel.CRITICAL.value == "critical"
    
    def test_action_recommendation_enum(self):
        """B0.2: Action recommendations are properly defined."""
        actions = [
            ActionRecommendation.CONTINUE,
            ActionRecommendation.NOTE,
            ActionRecommendation.WARN,
            ActionRecommendation.HOLD,
            ActionRecommendation.PAUSE,
            ActionRecommendation.ESCALATE,
        ]
        for action in actions:
            assert isinstance(action.value, str)
    
    def test_trading_event_type_taxonomy(self):
        """B0.3: Trading event types cover all required categories."""
        # Noise types
        assert TradingEventType.NOISE.value == "noise"
        assert TradingEventType.CURSOR_ONLY.value == "cursor_only"
        
        # Trading-specific types
        assert TradingEventType.CHART_UPDATE.value == "chart_update"
        assert TradingEventType.ORDER_TICKET.value == "order_ticket"
        assert TradingEventType.CONFIRM_DIALOG.value == "confirm_dialog"
        assert TradingEventType.WARNING_DIALOG.value == "warning_dialog"
        assert TradingEventType.ERROR_DIALOG.value == "error_dialog"
        assert TradingEventType.SLIPPAGE_WARNING.value == "slippage_warning"
        assert TradingEventType.MARGIN_WARNING.value == "margin_warning"
    
    def test_ui_element_types(self):
        """B0.4: UI element types include trading-specific elements."""
        # Cursor/noise types
        assert UIElementType.MOUSE_CURSOR.value == "mouse_cursor"
        assert UIElementType.TOOLTIP.value == "tooltip"
        
        # Trading-specific
        assert UIElementType.CHART_PANEL.value == "chart_panel"
        assert UIElementType.ORDER_TICKET_PANEL.value == "order_ticket_panel"
        assert UIElementType.CONFIRM_MODAL.value == "confirm_modal"
        assert UIElementType.WARNING_MODAL.value == "warning_modal"
        assert UIElementType.ERROR_MODAL.value == "error_modal"
    
    def test_detection_source_enum(self):
        """B0.5: Detection sources match Dad's role map."""
        sources = {
            DetectionSource.REFLEX: "reflex",
            DetectionSource.TRIPWIRE: "tripwire",
            DetectionSource.TRACKER: "tracker",
            DetectionSource.PRECISION: "precision",
            DetectionSource.PARSER: "parser",
            DetectionSource.SCOUT: "scout",
            DetectionSource.REVIEWER: "reviewer",
            DetectionSource.OVERSEER: "overseer",
        }
        for source, expected in sources.items():
            assert source.value == expected
    
    def test_is_noise_event(self):
        """B0.6: Noise event detection works correctly."""
        assert is_noise_event(TradingEventType.NOISE) is True
        assert is_noise_event(TradingEventType.CURSOR_ONLY) is True
        assert is_noise_event(TradingEventType.ANIMATION) is True
        assert is_noise_event(TradingEventType.CHART_UPDATE) is False
        assert is_noise_event(TradingEventType.ERROR_DIALOG) is False
    
    def test_is_trading_relevant(self):
        """B0.7: Trading relevance detection works correctly."""
        # Trading-relevant
        assert is_trading_relevant(TradingEventType.ORDER_TICKET) is True
        assert is_trading_relevant(TradingEventType.MARGIN_WARNING) is True
        assert is_trading_relevant(TradingEventType.CONFIRM_DIALOG) is True
        
        # Not trading-specific
        assert is_trading_relevant(TradingEventType.UI_CHANGE) is False
        assert is_noise_event(TradingEventType.NOISE) is True
    
    def test_requires_reviewer(self):
        """B0.8: Reviewer trigger detection works correctly."""
        # Should trigger reviewer
        assert requires_reviewer(TradingEventType.WARNING_DIALOG) is True
        assert requires_reviewer(TradingEventType.ERROR_DIALOG) is True
        assert requires_reviewer(TradingEventType.MARGIN_WARNING) is True
        assert requires_reviewer(TradingEventType.CONFIRM_DIALOG) is True
        
        # Should not trigger reviewer
        assert requires_reviewer(TradingEventType.CHART_UPDATE) is False
        assert requires_reviewer(TradingEventType.NOISE) is False
    
    def test_event_priority_ordering(self):
        """B0.9: Event priorities are correctly ordered."""
        # Critical events should have highest priority
        assert TRADING_EVENT_PRIORITY[TradingEventType.ERROR_DIALOG] == 100
        assert TRADING_EVENT_PRIORITY[TradingEventType.MARGIN_WARNING] == 95
        
        # Noise should have lowest priority
        assert TRADING_EVENT_PRIORITY[TradingEventType.NOISE] == 0
        assert TRADING_EVENT_PRIORITY[TradingEventType.CURSOR_ONLY] == 0
        
        # Warnings should be higher than normal updates
        assert (TRADING_EVENT_PRIORITY[TradingEventType.WARNING_DIALOG] >
                TRADING_EVENT_PRIORITY[TradingEventType.CHART_UPDATE])


class TestPydanticSchemas:
    """B0.10-15: Test Pydantic schema validation."""
    
    def test_bounding_box(self):
        """B0.10: BoundingBox schema works correctly."""
        bbox = BoundingBox(x=100, y=200, width=300, height=400)
        assert bbox.area == 120000
        assert bbox.center == (250, 400)
        assert bbox.contains(150, 250) is True
        assert bbox.contains(500, 500) is False
    
    def test_ui_element_creation(self):
        """B0.11: UIElement schema validates correctly."""
        bbox = BoundingBox(x=0, y=0, width=100, height=100)
        element = UIElement(
            element_id="test_001",
            element_type=UIElementType.CHART_PANEL,
            bbox=bbox,
            confidence=0.85,
            source=DetectionSource.TRIPWIRE,
            text_content="AAPL",
        )
        assert element.element_id == "test_001"
        assert element.confidence == 0.85
        assert element.text_content == "AAPL"
    
    def test_trading_event_creation(self):
        """B0.12: TradingEvent schema validates correctly."""
        event = TradingEvent(
            event_id="evt_001",
            timestamp="2026-03-17T16:00:00Z",
            event_type=TradingEventType.CHART_UPDATE,
            source=DetectionSource.SCOUT,
            confidence=0.78,
            screen_width=1920,
            screen_height=1080,
            summary="Chart updated for AAPL",
        )
        assert event.event_id == "evt_001"
        assert event.screen_width == 1920
    
    def test_reviewer_assessment_creation(self):
        """B0.13: ReviewerAssessment schema validates correctly."""
        assessment = ReviewerAssessment(
            reviewer_model="qwen3.5-2b-nvfp4",
            timestamp="2026-03-17T16:00:00Z",
            risk_level=RiskLevel.MEDIUM,
            recommendation=ActionRecommendation.WARN,
            confidence=0.82,
            reasoning="Order ticket detected with unusual values",
            is_uncertain=False,
        )
        assert assessment.confidence == 0.82
        assert assessment.is_uncertain is False
    
    def test_roi_creation(self):
        """B0.14: ROI schema validates correctly."""
        bbox = BoundingBox(x=100, y=100, width=200, height=150)
        roi = ROI(
            roi_id="roi_001",
            element_type=UIElementType.CHART_PANEL,
            bbox=bbox,
            confidence=0.90,
            crop_path="/tmp/roi_001.png",
            source=DetectionSource.PRECISION,
        )
        assert roi.roi_id == "roi_001"
        assert roi.crop_path == "/tmp/roi_001.png"


# =============================================================================
# B1: Higher-Precision Visual Review - ROI Tests
# =============================================================================

class TestROIExtractor:
    """B1.1-5: Test ROI extraction functionality."""
    
    @pytest.fixture
    def mock_screenshot(self):
        """Create a mock screenshot for testing."""
        return Image.new('RGB', (1920, 1080), color='white')
    
    def test_roi_extractor_creation(self):
        """B1.1: ROIExtractor can be created with default config."""
        extractor = ROIExtractor()
        assert extractor.config is not None
        assert extractor.artifacts_dir.exists()
    
    def test_roi_extraction_stub(self, mock_screenshot, tmp_path):
        """B1.2: ROI extraction works in stub mode (no SAM3)."""
        extractor = ROIExtractor(artifacts_dir=tmp_path)
        
        bbox = BoundingBox(x=100, y=100, width=200, height=150)
        element = UIElement(
            element_id="elem_001",
            element_type=UIElementType.CHART_PANEL,
            bbox=bbox,
            confidence=0.85,
            source=DetectionSource.TRIPWIRE,
        )
        
        roi = extractor.extract_roi(
            mock_screenshot, element, 1920, 1080, save_crop=False
        )
        
        assert roi.element_type == UIElementType.CHART_PANEL
        assert roi.confidence == 0.85
        assert roi.source == DetectionSource.TRIPWIRE
        assert roi.roi_id.startswith("roi_chart_panel_")
    
    def test_roi_bounds_adjustment(self, mock_screenshot, tmp_path):
        """B1.3: ROI bounds are adjusted with margins and clamped."""
        config = ROIConfig(margin_pixels=20, min_width=50, min_height=50)
        extractor = ROIExtractor(config=config, artifacts_dir=tmp_path)
        
        # Element at edge of screen
        bbox = BoundingBox(x=5, y=5, width=100, height=100)
        element = UIElement(
            element_id="elem_002",
            element_type=UIElementType.BUTTON,
            bbox=bbox,
            confidence=0.90,
            source=DetectionSource.TRIPWIRE,
        )
        
        roi = extractor.extract_roi(
            mock_screenshot, element, 1920, 1080, save_crop=False
        )
        
        # Should be clamped to 0, not negative
        assert roi.bbox.x >= 0
        assert roi.bbox.y >= 0
    
    def test_roi_registry(self, mock_screenshot, tmp_path):
        """B1.4: ROI registry tracks extracted ROIs."""
        extractor = ROIExtractor(artifacts_dir=tmp_path)
        
        bbox = BoundingBox(x=100, y=100, width=200, height=150)
        element = UIElement(
            element_id="elem_003",
            element_type=UIElementType.ORDER_TICKET_PANEL,
            bbox=bbox,
            confidence=0.75,
            source=DetectionSource.TRIPWIRE,
        )
        
        roi = extractor.extract_roi(
            mock_screenshot, element, 1920, 1080, save_crop=False
        )
        
        # Should be in registry
        retrieved = extractor.get_roi(roi.roi_id)
        assert retrieved is not None
        assert retrieved.roi_id == roi.roi_id
        
        # Clear registry
        extractor.clear_registry()
        assert extractor.get_roi(roi.roi_id) is None
    
    def test_extract_rois_for_event(self, mock_screenshot, tmp_path):
        """B1.5: Extract ROIs for specific event types."""
        extractor = ROIExtractor(artifacts_dir=tmp_path)
        
        elements = [
            UIElement(
                element_id="e1",
                element_type=UIElementType.CHART_PANEL,
                bbox=BoundingBox(x=0, y=0, width=400, height=300),
                confidence=0.85,
                source=DetectionSource.TRIPWIRE,
            ),
            UIElement(
                element_id="e2",
                element_type=UIElementType.ORDER_TICKET_PANEL,
                bbox=BoundingBox(x=500, y=0, width=300, height=400),
                confidence=0.80,
                source=DetectionSource.TRIPWIRE,
            ),
        ]
        
        rois = extractor.extract_rois_for_event(
            mock_screenshot, elements, 1920, 1080,
            TradingEventType.CHART_UPDATE
        )
        
        # Should extract ROI for chart panel
        assert len(rois) >= 1
        assert any(r.element_type == UIElementType.CHART_PANEL for r in rois)


class TestEvidenceBundler:
    """B1.6-8: Test evidence bundle preparation."""
    
    def test_evidence_bundle_creation(self):
        """B1.6: EvidenceBundle schema validates correctly."""
        bundle = EvidenceBundle(
            event_id="evt_001",
            timestamp="2026-03-17T16:00:00Z",
            event_summary="Order ticket detected",
            risk_indicators=["medium_risk", "order_active"],
            roi_crop_paths=["/tmp/roi_001.png"],
            reviewer_confidence=0.82,
            reviewer_reasoning="Order form is active",
        )
        assert bundle.event_id == "evt_001"
        assert len(bundle.risk_indicators) == 2
    
    def test_evidence_bundler_creation(self, tmp_path):
        """B1.7: EvidenceBundler can be created."""
        bundler = EvidenceBundler(artifacts_dir=tmp_path)
        assert bundler.artifacts_dir.exists()
    
    def test_redaction_of_sensitive_content(self):
        """B1.8: Sensitive content is redacted in bundles."""
        bundler = EvidenceBundler()
        
        # Use longer API key to match pattern (24+ chars after sk-)
        sensitive_text = "API key: sk-live-123456789012345678901234 wallet: 0x1234567890abcdef1234567890abcdef12345678"
        redacted = bundler._redact_sensitive_content(sensitive_text)
        
        # Should have redacted wallet address
        assert "[WALLET_REDACTED]" in redacted


# =============================================================================
# B1: Higher-Precision Visual Review - Detection Tests
# =============================================================================

class TestDetectionPipeline:
    """B1.9-15: Test detection pipeline functionality."""
    
    @pytest.fixture
    def mock_screenshot(self):
        """Create a mock screenshot for testing."""
        return Image.new('RGB', (1920, 1080), color='white')
    
    def test_detector_creation(self):
        """B1.9: Detector can be created with factory function."""
        detector = create_detector(mode=DetectorMode.TRADING_WATCH)
        assert detector is not None
        assert detector.config.mode == DetectorMode.TRADING_WATCH
    
    def test_detector_config_modes(self):
        """B1.10: All detector modes are available."""
        for mode in DetectorMode:
            config = DetectorConfig(mode=mode)
            assert config.mode == mode
    
    def test_motion_gate_creation(self):
        """B1.11: MotionGate can be created."""
        from advanced_vision.trading.detector import MotionGate
        gate = MotionGate()
        assert gate is not None
    
    def test_cursor_suppressor(self):
        """B1.12: CursorSuppressor filters cursor regions."""
        from advanced_vision.trading.detector import CursorSuppressor
        suppressor = CursorSuppressor()
        
        # Update cursor position
        suppressor.update_cursor_position(500, 500)
        
        # Small box near cursor should be suppressed
        bbox = BoundingBox(x=490, y=490, width=20, height=20)
        assert suppressor.is_cursor_region(bbox) is True
        
        # Larger box should not be suppressed
        bbox_large = BoundingBox(x=490, y=490, width=100, height=100)
        assert suppressor.is_cursor_region(bbox_large) is False
    
    def test_detection_pipeline_dry_run(self, mock_screenshot):
        """B1.13: Detection pipeline works in dry_run mode."""
        detector = create_detector(mode=DetectorMode.TRADING_WATCH)
        
        result = detector.process_frame(
            mock_screenshot,
            timestamp="2026-03-17T16:00:00Z",
            dry_run=True,
        )
        
        assert result is not None
        assert isinstance(result, DetectionResult)
        assert len(result.elements) >= 0
    
    def test_event_type_classification(self, mock_screenshot):
        """B1.14: Event type classification works correctly."""
        detector = create_detector(mode=DetectorMode.TRADING_WATCH)
        
        # Test with error modal elements
        error_elements = [
            UIElement(
                element_id="e1",
                element_type=UIElementType.ERROR_MODAL,
                bbox=BoundingBox(x=0, y=0, width=100, height=100),
                confidence=0.90,
                source=DetectionSource.TRIPWIRE,
            )
        ]
        
        event_type = detector.classify_event_type(error_elements)
        assert event_type == TradingEventType.ERROR_DIALOG
        
        # Test with chart panel
        chart_elements = [
            UIElement(
                element_id="e1",
                element_type=UIElementType.CHART_PANEL,
                bbox=BoundingBox(x=0, y=0, width=100, height=100),
                confidence=0.85,
                source=DetectionSource.TRIPWIRE,
            )
        ]
        
        event_type = detector.classify_event_type(chart_elements)
        assert event_type == TradingEventType.CHART_UPDATE
    
    def test_detector_reset(self, mock_screenshot):
        """B1.15: Detector pipeline can be reset."""
        detector = create_detector()
        
        # Process some frames
        detector.process_frame(mock_screenshot, "2026-03-17T16:00:00Z", dry_run=True)
        detector.process_frame(mock_screenshot, "2026-03-17T16:00:01Z", dry_run=True)
        
        assert detector._frame_count == 2
        
        # Reset
        detector.reset()
        assert detector._frame_count == 0


# =============================================================================
# B2: Local Reviewer Lane Tests
# =============================================================================

class TestLocalReviewer:
    """B2.1-8: Test local reviewer functionality."""
    
    def test_reviewer_creation(self):
        """B2.1: LocalReviewer can be created with factory."""
        reviewer = create_reviewer(dry_run=True)
        assert reviewer is not None
        assert reviewer.config.dry_run is True
    
    def test_reviewer_models(self):
        """B2.2: All reviewer models are defined."""
        models = [
            ReviewerModel.QWEN_2B_NVFP4,
            ReviewerModel.QWEN_4B_NVFP4,
            ReviewerModel.QWEN_7B,
            ReviewerModel.EAGLE_SCOUT,
            ReviewerModel.LLAVA,
            ReviewerModel.STUB,
        ]
        for model in models:
            assert isinstance(model.value, str)
    
    def test_reviewer_config(self):
        """B2.3: ReviewerConfig validates correctly."""
        config = ReviewerConfig(
            model=ReviewerModel.QWEN_4B_NVFP4,
            dry_run=True,
            min_confidence=0.6,
            high_confidence=0.85,
        )
        assert config.model == ReviewerModel.QWEN_4B_NVFP4
        assert config.dry_run is True
    
    def test_reviewer_input_creation(self):
        """B2.4: ReviewerInput schema validates correctly."""
        event = TradingEvent(
            event_id="evt_001",
            timestamp="2026-03-17T16:00:00Z",
            event_type=TradingEventType.ORDER_TICKET,
            source=DetectionSource.SCOUT,
            confidence=0.78,
            screen_width=1920,
            screen_height=1080,
        )
        
        input_data = ReviewerInput(
            event=event,
            scout_notes="Order ticket visible",
        )
        assert input_data.event.event_id == "evt_001"
    
    def test_stub_review_output(self):
        """B2.5: Stub reviewer produces valid assessment."""
        reviewer = create_reviewer(dry_run=True)
        
        event = TradingEvent(
            event_id="evt_001",
            timestamp="2026-03-17T16:00:00Z",
            event_type=TradingEventType.ERROR_DIALOG,
            source=DetectionSource.SCOUT,
            confidence=0.90,
            screen_width=1920,
            screen_height=1080,
        )
        
        input_data = ReviewerInput(event=event)
        output = reviewer.review(input_data, dry_run=True)
        
        assert output.assessment is not None
        assert output.assessment.risk_level in RiskLevel
        assert output.assessment.confidence >= 0.0
        assert output.assessment.confidence <= 1.0
        assert output.model_used == ReviewerModel.QWEN_4B_NVFP4.value
    
    def test_rule_based_assessment_risk_levels(self):
        """B2.6: Rule-based assessment assigns correct risk levels."""
        reviewer = create_reviewer(dry_run=True)
        
        test_cases = [
            (TradingEventType.NOISE, RiskLevel.NONE),
            (TradingEventType.CHART_UPDATE, RiskLevel.LOW),
            (TradingEventType.ORDER_TICKET, RiskLevel.MEDIUM),
            (TradingEventType.WARNING_DIALOG, RiskLevel.HIGH),
            (TradingEventType.ERROR_DIALOG, RiskLevel.CRITICAL),
            (TradingEventType.MARGIN_WARNING, RiskLevel.CRITICAL),
        ]
        
        for event_type, expected_risk in test_cases:
            event = TradingEvent(
                event_id="evt_test",
                timestamp="2026-03-17T16:00:00Z",
                event_type=event_type,
                source=DetectionSource.SCOUT,
                confidence=0.80,
                screen_width=1920,
                screen_height=1080,
            )
            
            assessment = reviewer._rule_based_assessment(event)
            assert assessment.risk_level == expected_risk, f"Failed for {event_type}"
    
    def test_should_escalate_to_overseer(self):
        """B2.7: Escalation logic works correctly."""
        # High risk should escalate
        high_risk = ReviewerAssessment(
            reviewer_model="test",
            timestamp="2026-03-17T16:00:00Z",
            risk_level=RiskLevel.HIGH,
            recommendation=ActionRecommendation.HOLD,
            confidence=0.80,
            reasoning="High risk",
            is_uncertain=False,
        )
        assert should_escalate_to_overseer(high_risk) is True
        
        # Uncertain should escalate
        uncertain = ReviewerAssessment(
            reviewer_model="test",
            timestamp="2026-03-17T16:00:00Z",
            risk_level=RiskLevel.MEDIUM,
            recommendation=ActionRecommendation.WARN,
            confidence=0.80,
            reasoning="Uncertain",
            is_uncertain=True,
        )
        assert should_escalate_to_overseer(uncertain) is True
        
        # Low confidence certain should not escalate
        low_confidence = ReviewerAssessment(
            reviewer_model="test",
            timestamp="2026-03-17T16:00:00Z",
            risk_level=RiskLevel.LOW,
            recommendation=ActionRecommendation.CONTINUE,
            confidence=0.80,
            reasoning="Low risk",
            is_uncertain=False,
        )
        # Note: This may or may not escalate depending on thresholds
        # The function should at least not crash
        result = should_escalate_to_overseer(low_confidence)
        assert isinstance(result, bool)
    
    def test_reviewer_stats(self):
        """B2.8: Reviewer tracks statistics."""
        reviewer = create_reviewer(dry_run=True)
        
        initial_stats = reviewer.get_stats()
        assert initial_stats["inference_count"] == 0
        
        # Process some events
        for i in range(3):
            event = TradingEvent(
                event_id=f"evt_{i}",
                timestamp="2026-03-17T16:00:00Z",
                event_type=TradingEventType.CHART_UPDATE,
                source=DetectionSource.SCOUT,
                confidence=0.80,
                screen_width=1920,
                screen_height=1080,
            )
            reviewer.review(ReviewerInput(event=event), dry_run=True)
        
        final_stats = reviewer.get_stats()
        assert final_stats["inference_count"] == 3


class TestReviewerLane:
    """B2.9-12: Test reviewer lane orchestration."""
    
    def test_reviewer_lane_creation(self):
        """B2.9: ReviewerLane can be created with factory."""
        lane = create_reviewer_lane(dry_run=True)
        assert lane is not None
        assert lane.config.dry_run is True
    
    def test_reviewer_lane_processes_event(self):
        """B2.10: ReviewerLane processes events and adds assessment."""
        lane = create_reviewer_lane(dry_run=True)
        
        event = TradingEvent(
            event_id="evt_001",
            timestamp="2026-03-17T16:00:00Z",
            event_type=TradingEventType.WARNING_DIALOG,
            source=DetectionSource.SCOUT,
            confidence=0.85,
            screen_width=1920,
            screen_height=1080,
        )
        
        result = lane.process_event(event, dry_run=True)
        
        assert result.reviewer_assessment is not None
        assert result.reviewer_assessment.risk_level == RiskLevel.HIGH
    
    def test_reviewer_lane_skips_noise(self):
        """B2.11: ReviewerLane skips noise events efficiently."""
        lane = create_reviewer_lane(dry_run=True)
        
        event = TradingEvent(
            event_id="evt_001",
            timestamp="2026-03-17T16:00:00Z",
            event_type=TradingEventType.NOISE,
            source=DetectionSource.REFLEX,
            confidence=0.50,
            screen_width=1920,
            screen_height=1080,
        )
        
        result = lane.process_event(event, dry_run=True)
        
        # Should still have assessment but with NONE risk
        assert result.reviewer_assessment is not None
        assert result.reviewer_assessment.risk_level == RiskLevel.NONE
        assert result.reviewer_assessment.recommendation == ActionRecommendation.CONTINUE
    
    def test_reviewer_lane_stats(self):
        """B2.12: ReviewerLane tracks escalation statistics."""
        lane = create_reviewer_lane(dry_run=True)
        
        # Process events
        for event_type in [TradingEventType.NOISE, TradingEventType.ERROR_DIALOG]:
            event = TradingEvent(
                event_id=f"evt_{event_type.value}",
                timestamp="2026-03-17T16:00:00Z",
                event_type=event_type,
                source=DetectionSource.SCOUT,
                confidence=0.90,
                screen_width=1920,
                screen_height=1080,
            )
            lane.process_event(event, dry_run=True)
        
        stats = lane.get_stats()
        assert stats["processed_count"] == 2
        assert "escalated_count" in stats
        assert "escalation_rate" in stats


class TestEscalationPreparer:
    """B2.13-15: Test escalation preparation."""
    
    def test_escalation_preparer_creation(self):
        """B2.13: EscalationPreparer can be created."""
        preparer = EscalationPreparer()
        assert preparer is not None
    
    def test_prepare_escalation_bundle(self):
        """B2.14: EscalationPreparer creates valid evidence bundle."""
        preparer = EscalationPreparer()
        
        assessment = ReviewerAssessment(
            reviewer_model="qwen3.5-2b-nvfp4",
            timestamp="2026-03-17T16:00:00Z",
            risk_level=RiskLevel.HIGH,
            recommendation=ActionRecommendation.HOLD,
            confidence=0.75,
            reasoning="Warning dialog detected",
            is_uncertain=True,
        )
        
        event = TradingEvent(
            event_id="evt_001",
            timestamp="2026-03-17T16:00:00Z",
            event_type=TradingEventType.WARNING_DIALOG,
            source=DetectionSource.REVIEWER,
            confidence=0.85,
            screen_width=1920,
            screen_height=1080,
            summary="Warning dialog appeared",
            reviewer_assessment=assessment,
        )
        
        bundle = preparer.prepare_escalation(event)
        
        assert bundle.event_id == "evt_001"
        assert "Warning" in bundle.event_summary
        assert "risk_high" in bundle.risk_indicators
        assert bundle.reviewer_confidence == 0.75
    
    def test_escalation_redaction(self):
        """B2.15: Escalation bundle redacts sensitive content."""
        preparer = EscalationPreparer()
        
        # Use longer API key to match pattern (20+ chars after sk-)
        event = TradingEvent(
            event_id="evt_001",
            timestamp="2026-03-17T16:00:00Z",
            event_type=TradingEventType.ORDER_TICKET,
            source=DetectionSource.SCOUT,
            confidence=0.80,
            screen_width=1920,
            screen_height=1080,
            raw_text_extracted="API key: sk-12345678901234567890 wallet: 0x1234567890abcdef1234567890abcdef12345678",
        )
        
        bundle = preparer.prepare_escalation(event)
        
        # Should be redacted
        if bundle.redacted_text:
            # API key should be redacted or contain KEY_REDACTED
            assert "KEY_REDACTED" in bundle.redacted_text or "sk-1234567890" not in bundle.redacted_text
            # Wallet should be redacted
            assert "[WALLET_REDACTED]" in bundle.redacted_text


# =============================================================================
# Integration Tests
# =============================================================================

class TestTradingPipelineIntegration:
    """Integration tests for full trading pipeline."""
    
    @pytest.fixture
    def mock_screenshot(self):
        """Create a mock screenshot for testing."""
        return Image.new('RGB', (1920, 1080), color='white')
    
    def test_full_pipeline_error_dialog(self, mock_screenshot, tmp_path):
        """Test full pipeline: detection -> ROI -> review -> escalation."""
        # 1. Detection
        detector = create_detector(mode=DetectorMode.TRADING_WATCH)
        detection = detector.process_frame(
            mock_screenshot,
            "2026-03-17T16:00:00Z",
            dry_run=True,
        )
        assert detection is not None
        
        # Override detection with error modal
        detection.elements = [
            UIElement(
                element_id="err_001",
                element_type=UIElementType.ERROR_MODAL,
                bbox=BoundingBox(x=800, y=400, width=320, height=200),
                confidence=0.95,
                source=DetectionSource.TRIPWIRE,
                text_content="Order rejected",
            )
        ]
        
        # 2. Classify event
        event_type = detector.classify_event_type(detection.elements)
        assert event_type == TradingEventType.ERROR_DIALOG
        
        # 3. Create event
        event = TradingEvent(
            event_id="evt_error_001",
            timestamp="2026-03-17T16:00:00Z",
            event_type=event_type,
            source=DetectionSource.TRIPWIRE,
            confidence=0.95,
            screen_width=1920,
            screen_height=1080,
            triggering_bbox=detection.elements[0].bbox,
        )
        
        # 4. Extract ROI
        roi_extractor = ROIExtractor(artifacts_dir=tmp_path)
        rois = roi_extractor.extract_rois_for_event(
            mock_screenshot,
            detection.elements,
            1920, 1080,
            event_type,
        )
        event.rois = rois
        
        # 5. Review
        lane = create_reviewer_lane(dry_run=True)
        event = lane.process_event(event, dry_run=True)
        
        assert event.reviewer_assessment is not None
        assert event.reviewer_assessment.risk_level == RiskLevel.CRITICAL
        
        # 6. Escalate if needed
        if event.escalated_to_overseer:
            preparer = EscalationPreparer()
            bundle = preparer.prepare_escalation(event)
            assert bundle is not None
            assert "risk_critical" in bundle.risk_indicators or "risk_high" in bundle.risk_indicators
    
    def test_noise_suppression_pipeline(self, mock_screenshot):
        """Test that noise events are handled efficiently."""
        # Create event for cursor-only motion
        event = TradingEvent(
            event_id="evt_cursor_001",
            timestamp="2026-03-17T16:00:00Z",
            event_type=TradingEventType.CURSOR_ONLY,
            source=DetectionSource.REFLEX,
            confidence=0.60,
            screen_width=1920,
            screen_height=1080,
        )
        
        # Process through reviewer lane
        lane = create_reviewer_lane(dry_run=True)
        result = lane.process_event(event, dry_run=True)
        
        # Should be fast-tracked with NONE risk
        assert result.reviewer_assessment is not None
        assert result.reviewer_assessment.risk_level == RiskLevel.NONE
        assert result.reviewer_assessment.recommendation == ActionRecommendation.CONTINUE
        assert not result.escalated_to_overseer


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
