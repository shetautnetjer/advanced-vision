"""Trading-Watch Intelligence module for advanced-vision.

Track B implementation following Dad's architecture:
- B0: Domain framing (events.py) - Trading event taxonomy
- B1: Higher-precision visual review (detector.py, roi.py) - YOLO/SAM3/ROI
- B2: Local reviewer lane (reviewer.py) - Qwen reviewer, Kimi escalation

Model role map (per Dad's findings):
- YOLO: Tripwire/reflex lane - fast detection
- BoT-SORT: Tracking (built into Ultralytics)
- SAM3: Precision refinement - selective/heavy (gated)
- OmniParser: Structure extraction
- Eagle2-2B: Scout - fast classification
- Qwen3.5-2B/4B-NVFP4: Local reviewer - judgment
- Kimi: Overseer - cloud escalation/second opinion
- Governor: Policy layer - final decisions

Usage:
    from advanced_vision.trading import (
        TradingEvent,
        RiskLevel,
        YOLODetector,
        ROIExtractor,
        LocalReviewer,
    )
    
    # Create detection pipeline
    detector = create_detector(mode=DetectorMode.TRADING_WATCH)
    
    # Process frame
    result = detector.process_frame(screenshot, timestamp, dry_run=True)
    
    # Extract ROIs
    roi_extractor = ROIExtractor()
    rois = roi_extractor.extract_rois_for_event(screenshot, elements, ...)
    
    # Run reviewer
    reviewer = create_reviewer(dry_run=True)
    output = reviewer.review(reviewer_input)
"""

from __future__ import annotations

# Event taxonomy (B0)
from advanced_vision.trading.events import (
    ActionRecommendation,
    BoundingBox,
    DetectionSource,
    RiskLevel,
    ReviewerAssessment,
    ROI,
    TradingEvent,
    TradingEventType,
    TradingSession,
    UIElement,
    UIElementType,
    is_noise_event,
    is_trading_relevant,
    requires_reviewer,
    should_escalate_to_overseer,
)

# Detection (B1)
from advanced_vision.trading.detector import (
    CursorSuppressor,
    DetectionPipeline,
    DetectionResult,
    DetectorConfig,
    DetectorMode,
    MotionGate,
    MotionResult,
    YOLODetector,
    create_detector,
)

# ROI extraction (B1)
from advanced_vision.trading.roi import (
    ChartRegion,
    ChartRegionDetector,
    EvidenceBundle,
    EvidenceBundler,
    OrderField,
    OrderTicket,
    OrderTicketExtractor,
    ROIConfig,
    ROIExtractor,
    UIStructure,
    UIStructureExtractor,
)

# Reviewer (B2)
from advanced_vision.trading.reviewer import (
    EscalationPreparer,
    LocalReviewer,
    ReviewerConfig,
    ReviewerInput,
    ReviewerLane,
    ReviewerModel,
    ReviewerOutput,
    create_reviewer,
    create_reviewer_lane,
)

__all__ = [
    # Events (B0)
    "ActionRecommendation",
    "BoundingBox",
    "DetectionSource",
    "RiskLevel",
    "ReviewerAssessment",
    "ROI",
    "TradingEvent",
    "TradingEventType",
    "TradingSession",
    "UIElement",
    "UIElementType",
    "is_noise_event",
    "is_trading_relevant",
    "requires_reviewer",
    "should_escalate_to_overseer",
    
    # Detection (B1)
    "CursorSuppressor",
    "DetectionPipeline",
    "DetectionResult",
    "DetectorConfig",
    "DetectorMode",
    "MotionGate",
    "MotionResult",
    "YOLODetector",
    "create_detector",
    
    # ROI (B1)
    "ChartRegion",
    "ChartRegionDetector",
    "EvidenceBundle",
    "EvidenceBundler",
    "OrderField",
    "OrderTicket",
    "OrderTicketExtractor",
    "ROIConfig",
    "ROIExtractor",
    "UIStructure",
    "UIStructureExtractor",
    
    # Reviewer (B2)
    "EscalationPreparer",
    "LocalReviewer",
    "ReviewerConfig",
    "ReviewerInput",
    "ReviewerLane",
    "ReviewerModel",
    "ReviewerOutput",
    "create_reviewer",
    "create_reviewer_lane",
]
