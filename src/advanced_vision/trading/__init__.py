"""Trading-Watch Intelligence module for advanced-vision.

Track B implementation following Dad's architecture:
- B0: Domain framing (events.py) - Trading event taxonomy
- B1: Higher-precision visual review (detector.py, roi.py) - YOLO/SAM3/ROI
- B2: Local reviewer lane (reviewer.py) - Qwen reviewer, Kimi escalation
- B3: Real-time WebSocket feeds (wss_*.py) - Live streaming to UI/trading systems

Model role map (per Dad's findings):
- YOLO: Tripwire/reflex lane - fast detection
- BoT-SORT: Tracking (built into Ultralytics)
- SAM3: Precision refinement - selective/heavy (gated)
- OmniParser: Structure extraction
- Eagle2-2B: Scout - fast classification
- Qwen3.5-2B/4B-NVFP4: Local reviewer - judgment
- Kimi: Overseer - cloud escalation/second opinion
- Governor: Policy layer - final decisions

WebSocket Publishers (Real-time feeds):
- YOLO Detector: ws://localhost:8002 (10-30 FPS detection feed)
- MobileSAM: ws://localhost:8003 (on-demand segmentation feed)
- Eagle Vision: ws://localhost:8004 (classification feed ~300-500ms)
- Analysis: ws://localhost:8005 (Chronos/Kimi analysis results)

Usage:
    from advanced_vision.trading import (
        TradingEvent,
        RiskLevel,
        YOLODetector,
        ROIExtractor,
        LocalReviewer,
        WSSPublisherManager,  # Unified manager for all feeds
    )
    
    # Create detection pipeline
    detector = create_detector(mode=DetectorMode.TRADING_WATCH)
    
    # Create WSS manager for real-time feeds
    wss = create_wss_manager(yolo_fps=15)
    wss.start_all()
    
    # Process frame and publish
    result = detector.process_frame(screenshot, timestamp, dry_run=True)
    wss.publish_yolo_detection(result, screenshot, frame_id)
    
    # Run reviewer and publish analysis
    reviewer = create_reviewer(dry_run=True)
    output = reviewer.review(reviewer_input)
    wss.publish_reviewer_assessment(output.assessment, frame_id)
    
    wss.stop_all()
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

# WSS Publishers (Real-time feeds)
from advanced_vision.trading.wss_yolo_publisher import (
    YOLOWSSPublisher,
    create_yolo_publisher,
)
from advanced_vision.trading.wss_sam_publisher import (
    MobileSAMWSSPublisher,
    create_sam_publisher,
)
from advanced_vision.trading.wss_eagle_publisher import (
    EagleWSSPublisher,
    create_eagle_publisher,
)
from advanced_vision.trading.wss_analysis_publisher import (
    AnalysisWSSPublisher,
    create_analysis_publisher,
)
from advanced_vision.trading.wss_manager import (
    WSSPublisherManager,
    create_wss_manager,
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
    
    # WSS Publishers (Real-time feeds)
    "YOLOWSSPublisher",
    "create_yolo_publisher",
    "MobileSAMWSSPublisher",
    "create_sam_publisher",
    "EagleWSSPublisher",
    "create_eagle_publisher",
    "AnalysisWSSPublisher",
    "create_analysis_publisher",
    "WSSPublisherManager",
    "create_wss_manager",
]
