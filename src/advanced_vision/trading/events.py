"""Trading event taxonomy for Track B: Trading-Watch Intelligence.

This module defines the event types, risk levels, and UI element classifications
used in trading-watch mode. Based on the PRD/SDD architecture and Dad's role map:
- YOLO: tripwire/reflex lane
- SAM3: precision refinement lane (selective/heavy)
- OmniParser: structure/parsing lane
- Eagle2-2B: scout lane
- Qwen: local reviewer lane
- Kimi: overseer lane (cloud escalation)
- Governor: policy layer
"""

from __future__ import annotations

from enum import Enum, auto
from typing import Any

from pydantic import BaseModel, Field


# =============================================================================
# Risk Classification (Governor Layer Input)
# =============================================================================

class RiskLevel(str, Enum):
    """Risk levels for trading events.
    
    Used by the governor layer to determine appropriate action.
    Models produce recommendations; governor decides.
    """
    NONE = "none"           # No risk, safe to continue
    LOW = "low"             # Minor note, no action needed
    MEDIUM = "medium"       # Worth watching, possible warning
    HIGH = "high"           # Significant concern, recommend pause
    CRITICAL = "critical"   # Immediate attention required


class ActionRecommendation(str, Enum):
    """Recommended actions from reviewer models.
    
    These are advisory only - final decision is governor/policy layer.
    """
    CONTINUE = "continue"           # No action needed
    NOTE = "note"                   # Log but continue
    WARN = "warn"                   # Alert user but allow
    HOLD = "hold"                   # Pause for review
    PAUSE = "pause"                 # Stop and wait
    ESCALATE = "escalate"           # Send to Kimi overseer


# =============================================================================
# Trading Event Types (Scout Classification)
# =============================================================================

class TradingEventType(str, Enum):
    """Taxonomy of trading-relevant UI events.
    
    These are classifications the scout (Eagle) can assign to detected changes.
    """
    # Noise / Non-events
    NOISE = "noise"                     # Non-meaningful change
    CURSOR_ONLY = "cursor_only"         # Just pointer movement
    ANIMATION = "animation"             # Visual effect, not state change
    
    # UI Changes (generic)
    UI_CHANGE = "ui_change"             # General UI element appeared/changed
    MODAL_APPEARED = "modal_appeared"   # Dialog/modal popup
    NOTIFICATION = "notification"       # System/app notification
    
    # Trading-Specific Events
    CHART_UPDATE = "chart_update"       # Chart panel changed
    PRICE_CHANGE = "price_change"       # Price display updated
    SPREAD_CHANGE = "spread_change"     # Bid/ask spread changed
    ORDER_TICKET = "order_ticket"       # Order entry form visible
    CONFIRM_DIALOG = "confirm_dialog"   # Confirmation dialog appeared
    WARNING_DIALOG = "warning_dialog"   # Warning/alert dialog
    ERROR_DIALOG = "error_dialog"       # Error dialog
    PNL_UPDATE = "pnl_update"           # P&L display changed
    POSITION_CHANGE = "position_change" # Position status changed
    FILL_NOTIFICATION = "fill_notification"  # Order filled
    SLIPPAGE_WARNING = "slippage_warning"    # Slippage detected
    MARGIN_WARNING = "margin_warning"        # Margin/call warning
    ROUTE_WARNING = "route_warning"          # Order routing warning
    SYMBOL_MISMATCH = "symbol_mismatch"      # Wrong symbol detected
    UNKNOWN = "unknown"                      # Unclassified change


# =============================================================================
# UI Element Types (Detection/Tracking Targets)
# =============================================================================

class UIElementType(str, Enum):
    """Classifiable UI elements for YOLO tripwire detection.
    
    These are the target classes for the detection layer.
    """
    # Pointer/Noise (to suppress)
    MOUSE_CURSOR = "mouse_cursor"
    TOOLTIP = "tooltip"
    CURSOR_HIGHLIGHT = "cursor_highlight"
    
    # Generic UI
    BUTTON = "button"
    TEXT_FIELD = "text_field"
    DROPDOWN = "dropdown"
    CHECKBOX = "checkbox"
    TAB = "tab"
    SCROLLBAR = "scrollbar"
    
    # Trading-Specific UI
    CHART_PANEL = "chart_panel"
    CHART_TOOLBAR = "chart_toolbar"
    PRICE_DISPLAY = "price_display"
    ORDER_BOOK = "order_book"
    ORDER_TICKET_PANEL = "order_ticket_panel"
    POSITION_PANEL = "position_panel"
    PNL_WIDGET = "pnl_widget"
    WATCHLIST = "watchlist"
    NEWS_PANEL = "news_panel"
    TIME_SALES = "time_sales"
    CONFIRM_MODAL = "confirm_modal"
    WARNING_MODAL = "warning_modal"
    ERROR_MODAL = "error_modal"


# =============================================================================
# Detection Confidence & Tracking
# =============================================================================

class DetectionSource(str, Enum):
    """Which lane produced the detection."""
    REFLEX = "reflex"           # Frame diff / motion gate
    TRIPWIRE = "tripwire"       # YOLO detection
    TRACKER = "tracker"         # BoT-SORT tracking
    PRECISION = "precision"     # SAM3 segmentation
    PARSER = "parser"           # OmniParser structure
    SCOUT = "scout"             # Eagle classification
    REVIEWER = "reviewer"       # Qwen judgment
    OVERSEER = "overseer"       # Kimi escalation


# =============================================================================
# Pydantic Schemas
# =============================================================================

class BoundingBox(BaseModel):
    """2D bounding box for UI elements."""
    x: int = Field(..., ge=0, description="Left coordinate")
    y: int = Field(..., ge=0, description="Top coordinate")
    width: int = Field(..., ge=0, description="Box width")
    height: int = Field(..., ge=0, description="Box height")
    
    @property
    def area(self) -> int:
        return self.width * self.height
    
    @property
    def center(self) -> tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)
    
    def contains(self, px: int, py: int) -> bool:
        """Check if point is inside box."""
        return (self.x <= px < self.x + self.width and 
                self.y <= py < self.y + self.height)
    
    def to_tuple(self) -> tuple[int, int, int, int]:
        """Return as (x, y, width, height) tuple."""
        return (self.x, self.y, self.width, self.height)


class UIElement(BaseModel):
    """Detected UI element from tripwire/parser lanes."""
    element_id: str = Field(..., description="Unique element identifier")
    element_type: UIElementType
    bbox: BoundingBox
    confidence: float = Field(..., ge=0.0, le=1.0)
    source: DetectionSource
    text_content: str | None = None
    parent_id: str | None = None
    children_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ROI(BaseModel):
    """Region of Interest for focused analysis.
    
    Produced by SAM3 precision lane or parsed from UI structure.
    """
    roi_id: str
    element_type: UIElementType
    bbox: BoundingBox
    # SAM3 can produce segmentation mask (optional)
    segmentation_mask: list[tuple[int, int]] | None = None
    confidence: float = Field(..., ge=0.0, le=1.0)
    crop_path: str | None = None  # Path to extracted ROI image
    source: DetectionSource


class TradingEvent(BaseModel):
    """Structured trading event - append-only record.
    
    This is the core event type for the trading-watch mode.
    Produced by the scout (Eagle) and enhanced by reviewer (Qwen).
    """
    event_id: str
    timestamp: str  # ISO 8601
    event_type: TradingEventType
    
    # Detection context
    source: DetectionSource
    confidence: float = Field(..., ge=0.0, le=1.0)
    
    # Spatial context
    screen_width: int
    screen_height: int
    triggering_bbox: BoundingBox | None = None
    rois: list[ROI] = Field(default_factory=list)
    
    # Semantic content
    summary: str | None = None
    raw_text_extracted: str | None = None
    structured_data: dict[str, Any] = Field(default_factory=dict)
    
    # Reviewer judgment (if applicable)
    reviewer_assessment: ReviewerAssessment | None = None
    
    # Escalation tracking
    escalated_to_overseer: bool = False
    overseer_response: OverseerResponse | None = None
    
    # Evidence links
    screenshot_path: str | None = None
    video_clip_path: str | None = None
    
    class Config:
        extra = "allow"  # Allow extension for future fields


class ReviewerAssessment(BaseModel):
    """Local reviewer (Qwen) judgment on a trading event."""
    reviewer_model: str = "qwen3.5-4b-nvfp4"  # Deep reviewer model
    timestamp: str
    
    # Judgment
    risk_level: RiskLevel
    recommendation: ActionRecommendation
    confidence: float = Field(..., ge=0.0, le=1.0)
    
    # Explanation
    reasoning: str
    evidence_links: list[str] = Field(default_factory=list)
    
    # Uncertainty flag (triggers escalation if True)
    is_uncertain: bool = False
    uncertainty_reason: str | None = None


class OverseerResponse(BaseModel):
    """Cloud overseer (Kimi) second opinion."""
    model: str = "kimi-k2.5"
    timestamp: str
    request_id: str
    
    # Second opinion
    agrees_with_reviewer: bool | None = None
    risk_level: RiskLevel
    recommendation: ActionRecommendation
    confidence: float = Field(..., ge=0.0, le=1.0)
    
    # Analysis
    reasoning: str
    additional_observations: str | None = None


class TradingSession(BaseModel):
    """Trading session container for grouped events."""
    session_id: str
    start_time: str
    end_time: str | None = None
    platform: str | None = None  # "tradingview", "thinkorswim", etc.
    mode: str = "watch"  # "scout", "watch", "review"
    events: list[TradingEvent] = Field(default_factory=list)
    
    # Session-level risk tracking
    max_risk_encountered: RiskLevel = RiskLevel.NONE
    escalation_count: int = 0
    
    # Evidence bundle paths
    evidence_dir: str | None = None


# =============================================================================
# Utility Functions
# =============================================================================

def is_noise_event(event_type: TradingEventType) -> bool:
    """Check if event type is considered noise."""
    return event_type in {
        TradingEventType.NOISE,
        TradingEventType.CURSOR_ONLY,
        TradingEventType.ANIMATION,
    }


def is_trading_relevant(event_type: TradingEventType) -> bool:
    """Check if event type is trading-specific."""
    trading_types = {
        TradingEventType.CHART_UPDATE,
        TradingEventType.PRICE_CHANGE,
        TradingEventType.SPREAD_CHANGE,
        TradingEventType.ORDER_TICKET,
        TradingEventType.CONFIRM_DIALOG,
        TradingEventType.WARNING_DIALOG,
        TradingEventType.ERROR_DIALOG,
        TradingEventType.PNL_UPDATE,
        TradingEventType.POSITION_CHANGE,
        TradingEventType.FILL_NOTIFICATION,
        TradingEventType.SLIPPAGE_WARNING,
        TradingEventType.MARGIN_WARNING,
        TradingEventType.ROUTE_WARNING,
        TradingEventType.SYMBOL_MISMATCH,
    }
    return event_type in trading_types


def requires_reviewer(event_type: TradingEventType) -> bool:
    """Check if event type should trigger local reviewer."""
    reviewer_triggers = {
        TradingEventType.WARNING_DIALOG,
        TradingEventType.ERROR_DIALOG,
        TradingEventType.SLIPPAGE_WARNING,
        TradingEventType.MARGIN_WARNING,
        TradingEventType.ROUTE_WARNING,
        TradingEventType.SYMBOL_MISMATCH,
        TradingEventType.CONFIRM_DIALOG,
        TradingEventType.ORDER_TICKET,
    }
    return event_type in reviewer_triggers


def should_escalate_to_overseer(assessment: ReviewerAssessment) -> bool:
    """Determine if reviewer assessment warrants Kimi escalation.
    
    Per Dad's findings: escalate on uncertainty or high risk.
    """
    if assessment.is_uncertain:
        return True
    if assessment.risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL}:
        return True
    if assessment.recommendation in {ActionRecommendation.PAUSE, ActionRecommendation.HOLD}:
        return True
    return False


# =============================================================================
# Event Classification Helpers
# =============================================================================

TRADING_EVENT_PRIORITY = {
    # Highest priority (critical)
    TradingEventType.ERROR_DIALOG: 100,
    TradingEventType.MARGIN_WARNING: 95,
    TradingEventType.SYMBOL_MISMATCH: 90,
    
    # High priority
    TradingEventType.WARNING_DIALOG: 80,
    TradingEventType.SLIPPAGE_WARNING: 75,
    TradingEventType.ROUTE_WARNING: 70,
    TradingEventType.CONFIRM_DIALOG: 65,
    
    # Medium priority
    TradingEventType.ORDER_TICKET: 50,
    TradingEventType.FILL_NOTIFICATION: 45,
    TradingEventType.POSITION_CHANGE: 40,
    TradingEventType.PNL_UPDATE: 35,
    
    # Low priority
    TradingEventType.PRICE_CHANGE: 30,
    TradingEventType.SPREAD_CHANGE: 25,
    TradingEventType.CHART_UPDATE: 20,
    
    # Background
    TradingEventType.NOTIFICATION: 10,
    TradingEventType.MODAL_APPEARED: 10,
    TradingEventType.UI_CHANGE: 5,
    
    # Noise (ignore)
    TradingEventType.NOISE: 0,
    TradingEventType.CURSOR_ONLY: 0,
    TradingEventType.ANIMATION: 0,
    TradingEventType.UNKNOWN: 1,
}


def get_event_priority(event_type: TradingEventType) -> int:
    """Get priority score for event type (higher = more important)."""
    return TRADING_EVENT_PRIORITY.get(event_type, 1)
