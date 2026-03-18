"""Object detection module for Track B: Trading-Watch Intelligence.

This module implements the tripwire/reflex lane:
- YOLO-based UI element detection
- BoT-SORT tracking integration (via Ultralytics)
- Motion gating / frame differencing
- Cursor suppression

Per Dad's findings:
- YOLO is the "tripwire" - fast, cheap, always-on
- BoT-SORT is built into Ultralytics track mode
- SAM3 is gated/optional for precision refinement
- Models produce evidence, governor decides
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from PIL.Image import Image

from advanced_vision.trading.events import (
    BoundingBox,
    DetectionSource,
    TradingEventType,
    UIElement,
    UIElementType,
)


# =============================================================================
# Detection Configuration
# =============================================================================

class DetectorMode(str, Enum):
    """Detection sensitivity modes."""
    DESKTOP_SCOUT = "desktop_scout"   # Ignore more, lower sensitivity
    TRADING_WATCH = "trading_watch"   # Higher sensitivity for trading
    DEEP_REVIEW = "deep_review"       # Maximum detection for forensic review


class DetectorConfig(BaseModel):
    """Configuration for detection behavior."""
    
    # Mode
    mode: DetectorMode = DetectorMode.TRADING_WATCH
    
    # YOLO settings (stub - model not downloaded)
    yolo_model_name: str = "yolov8n.pt"  # Nano = smallest/fastest
    yolo_model_path: str | None = None   # Custom model path
    confidence_threshold: float = 0.35
    iou_threshold: float = 0.45
    
    # Detection classes to enable
    enabled_classes: list[UIElementType] = Field(default_factory=lambda: [
        UIElementType.CHART_PANEL,
        UIElementType.ORDER_TICKET_PANEL,
        UIElementType.CONFIRM_MODAL,
        UIElementType.WARNING_MODAL,
        UIElementType.ERROR_MODAL,
        UIElementType.POSITION_PANEL,
        UIElementType.PNL_WIDGET,
        UIElementType.BUTTON,
    ])
    
    # Classes to ignore (cursor suppression)
    ignored_classes: list[UIElementType] = Field(default_factory=lambda: [
        UIElementType.MOUSE_CURSOR,
        UIElementType.TOOLTIP,
        UIElementType.CURSOR_HIGHLIGHT,
    ])
    
    # Motion gating
    motion_gating_enabled: bool = True
    motion_threshold: float = 0.02  # 2% of pixels changed
    
    # Frame differencing
    frame_diff_enabled: bool = True
    min_pixel_change: int = 1000
    
    # Tracking (BoT-SORT via Ultralytics)
    tracking_enabled: bool = True
    track_persist: bool = True
    track_buffer: int = 30  # Frames to keep lost tracks
    
    # Performance
    inference_device: str = "auto"  # "cpu", "cuda", "auto"
    half_precision: bool = True


# =============================================================================
# Motion Detection (Reflex Lane)
# =============================================================================

class MotionResult(BaseModel):
    """Result of motion detection between frames."""
    motion_detected: bool
    change_ratio: float  # 0.0 to 1.0
    changed_pixels: int
    total_pixels: int
    motion_bbox: BoundingBox | None = None  # Bounding box of changed region


class MotionGate:
    """Fast motion detection for gating expensive inference.
    
    This is the reflex lane - cheap, always-on, filters noise.
    """
    
    def __init__(self, config: DetectorConfig | None = None):
        self.config = config or DetectorConfig()
        self._last_frame: "Image" | None = None
    
    def check_motion(
        self,
        current_frame: "Image",
        previous_frame: "Image" | None = None,
    ) -> MotionResult:
        """Check for meaningful motion between frames.
        
        Uses simple pixel differencing for speed.
        More sophisticated methods (optical flow) can be added later.
        """
        prev = previous_frame or self._last_frame
        
        if prev is None:
            self._last_frame = current_frame.copy()
            return MotionResult(
                motion_detected=True,  # First frame always triggers
                change_ratio=1.0,
                changed_pixels=current_frame.width * current_frame.height,
                total_pixels=current_frame.width * current_frame.height,
            )
        
        # Ensure same size
        if current_frame.size != prev.size:
            prev = prev.resize(current_frame.size)
        
        # Convert to grayscale for comparison
        current_gray = current_frame.convert("L")
        prev_gray = prev.convert("L")
        
        # Calculate difference
        diff = current_gray.point(lambda p: 255 if abs(p - prev_gray.getpixel(
            (0, 0) if False else (0, 0)  # Placeholder for proper pixel access
        )) > 20 else 0)
        
        # Simple count-based detection (production would use numpy for speed)
        # This is a stub implementation
        total_pixels = current_frame.width * current_frame.height
        
        # Store current frame for next comparison
        self._last_frame = current_frame.copy()
        
        # Stub: assume motion detected for now
        # Production would implement proper pixel differencing
        return MotionResult(
            motion_detected=True,
            change_ratio=0.1,
            changed_pixels=total_pixels // 10,
            total_pixels=total_pixels,
        )
    
    def reset(self) -> None:
        """Reset motion history."""
        self._last_frame = None


# =============================================================================
# Cursor Suppression
# =============================================================================

class CursorSuppressor:
    """Suppress detections caused by mouse cursor movement.
    
    Per PRD: aggressively ignore pointer-only motion.
    """
    
    def __init__(self):
        self._cursor_positions: list[tuple[int, int]] = []
        self._max_history = 10
    
    def update_cursor_position(self, x: int, y: int) -> None:
        """Update tracked cursor position."""
        self._cursor_positions.append((x, y))
        if len(self._cursor_positions) > self._max_history:
            self._cursor_positions.pop(0)
    
    def is_cursor_region(self, bbox: BoundingBox) -> bool:
        """Check if bounding box likely contains only cursor."""
        # Cursor regions are typically small (< 50x50)
        if bbox.width > 50 or bbox.height > 50:
            return False
        
        # Check if near recent cursor positions
        cx, cy = bbox.center
        for px, py in self._cursor_positions:
            if abs(cx - px) < 30 and abs(cy - py) < 30:
                return True
        
        return False
    
    def suppress_cursor_detections(self, elements: list[UIElement]) -> list[UIElement]:
        """Filter out elements that are likely just cursor."""
        return [
            e for e in elements
            if not self.is_cursor_region(e.bbox)
            and e.element_type not in {
                UIElementType.MOUSE_CURSOR,
                UIElementType.TOOLTIP,
                UIElementType.CURSOR_HIGHLIGHT,
            }
        ]


# =============================================================================
# YOLO Detector (Tripwire Lane)
# =============================================================================

class DetectionResult(BaseModel):
    """Result of YOLO detection pass."""
    elements: list[UIElement]
    inference_time_ms: float
    frame_timestamp: str
    source: DetectionSource = DetectionSource.TRIPWIRE


class YOLODetector:
    """YOLO-based UI element detection.
    
    Tripwire lane: fast detection of UI elements.
    This is a stub - actual YOLO model not downloaded per constraints.
    """
    
    def __init__(self, config: DetectorConfig | None = None):
        self.config = config or DetectorConfig()
        self._model: Any | None = None
        self._model_loaded = False
    
    def _load_model(self) -> bool:
        """Load YOLO model. Stub - returns False (model not downloaded)."""
        if self._model_loaded:
            return True
        
        # Stub: Model not downloaded per constraints
        # Production would:
        # from ultralytics import YOLO
        # self._model = YOLO(self.config.yolo_model_name)
        # self._model_loaded = True
        
        return False
    
    def detect(
        self,
        screenshot: "Image",
        timestamp: str,
        dry_run: bool = True,
    ) -> DetectionResult:
        """Run YOLO detection on screenshot.
        
        Args:
            screenshot: PIL Image to analyze
            timestamp: ISO timestamp for result
            dry_run: If True, return stub results (safe mode)
            
        Returns:
            DetectionResult with detected elements
        """
        if dry_run or not self._load_model():
            # Return stub results for safe testing
            return self._stub_detection(screenshot, timestamp)
        
        # Production implementation would:
        # results = self._model(screenshot, conf=self.config.confidence_threshold)
        # elements = self._parse_yolo_results(results)
        # return DetectionResult(...)
        
        return self._stub_detection(screenshot, timestamp)
    
    def _stub_detection(self, screenshot: "Image", timestamp: str) -> DetectionResult:
        """Generate stub detection results for testing."""
        width, height = screenshot.size
        
        # Create mock elements based on mode
        elements: list[UIElement] = []
        
        if self.config.mode == DetectorMode.TRADING_WATCH:
            # Mock chart panel
            elements.append(UIElement(
                element_id="elem_chart_001",
                element_type=UIElementType.CHART_PANEL,
                bbox=BoundingBox(
                    x=width // 4,
                    y=height // 4,
                    width=width // 2,
                    height=height // 2,
                ),
                confidence=0.85,
                source=DetectionSource.TRIPWIRE,
                text_content="AAPL 1D",
            ))
            
            # Mock order panel
            elements.append(UIElement(
                element_id="elem_order_001",
                element_type=UIElementType.ORDER_TICKET_PANEL,
                bbox=BoundingBox(
                    x=width * 3 // 4,
                    y=height // 4,
                    width=width // 5,
                    height=height // 3,
                ),
                confidence=0.78,
                source=DetectionSource.TRIPWIRE,
            ))
        
        return DetectionResult(
            elements=elements,
            inference_time_ms=15.0,  # Simulated fast inference
            frame_timestamp=timestamp,
        )
    
    def detect_with_tracking(
        self,
        screenshot: "Image",
        timestamp: str,
        track_id: str | None = None,
        dry_run: bool = True,
    ) -> DetectionResult:
        """Run YOLO detection with BoT-SORT tracking.
        
        BoT-SORT is built into Ultralytics track mode per Dad's findings.
        """
        if dry_run or not self._load_model():
            result = self._stub_detection(screenshot, timestamp)
            # Add tracking IDs to stub results
            for i, elem in enumerate(result.elements):
                elem.metadata["track_id"] = f"track_{i}"
            return result
        
        # Production would use:
        # results = self._model.track(
        #     screenshot,
        #     persist=self.config.track_persist,
        #     tracker="botsort.yaml",
        # )
        
        return self._stub_detection(screenshot, timestamp)


# =============================================================================
# Multi-Lane Detection Pipeline
# =============================================================================

class DetectionPipeline:
    """Orchestrates the full detection pipeline across lanes.
    
    Flow per Dad's architecture:
    1. Reflex (motion gate) - cheap always-on
    2. Tripwire (YOLO) - detection
    3. Tracker (BoT-SORT) - persistence
    4. Precision (SAM3) - refinement (gated)
    5. Parser - structure extraction
    """
    
    def __init__(self, config: DetectorConfig | None = None):
        self.config = config or DetectorConfig()
        self.motion_gate = MotionGate(config)
        self.cursor_suppressor = CursorSuppressor()
        self.yolo_detector = YOLODetector(config)
        self._frame_count = 0
    
    def process_frame(
        self,
        screenshot: "Image",
        timestamp: str,
        cursor_position: tuple[int, int] | None = None,
        force_detect: bool = False,
        dry_run: bool = True,
    ) -> DetectionResult | None:
        """Process a single frame through the detection pipeline.
        
        Args:
            screenshot: PIL Image to analyze
            timestamp: ISO timestamp
            cursor_position: Current mouse position for suppression
            force_detect: Bypass motion gate
            dry_run: Safe mode (no actual model inference)
            
        Returns:
            DetectionResult or None if no meaningful detection
        """
        self._frame_count += 1
        
        # Update cursor tracking
        if cursor_position:
            self.cursor_suppressor.update_cursor_position(*cursor_position)
        
        # 1. Motion gate (reflex lane)
        if not force_detect and self.config.motion_gating_enabled:
            motion_result = self.motion_gate.check_motion(screenshot)
            if not motion_result.motion_detected:
                return None  # Skip expensive inference
        
        # 2. YOLO detection (tripwire lane)
        detection = self.yolo_detector.detect(screenshot, timestamp, dry_run)
        
        # 3. Cursor suppression
        filtered_elements = self.cursor_suppressor.suppress_cursor_detections(
            detection.elements
        )
        
        # 4. Apply class filtering
        filtered_elements = [
            e for e in filtered_elements
            if e.element_type in self.config.enabled_classes
            or not self.config.enabled_classes  # All enabled if empty
        ]
        
        return DetectionResult(
            elements=filtered_elements,
            inference_time_ms=detection.inference_time_ms,
            frame_timestamp=timestamp,
        )
    
    def classify_event_type(
        self,
        elements: list[UIElement],
        previous_elements: list[UIElement] | None = None,
    ) -> TradingEventType:
        """Classify trading event type from detected elements.
        
        Simple rule-based classifier before scout model.
        """
        element_types = {e.element_type for e in elements}
        
        # Check for modals/dialogs (highest priority)
        if UIElementType.ERROR_MODAL in element_types:
            return TradingEventType.ERROR_DIALOG
        if UIElementType.WARNING_MODAL in element_types:
            return TradingEventType.WARNING_DIALOG
        if UIElementType.CONFIRM_MODAL in element_types:
            return TradingEventType.CONFIRM_DIALOG
        
        # Check for trading-specific UI
        if UIElementType.ORDER_TICKET_PANEL in element_types:
            return TradingEventType.ORDER_TICKET
        if UIElementType.CHART_PANEL in element_types:
            return TradingEventType.CHART_UPDATE
        if UIElementType.POSITION_PANEL in element_types:
            return TradingEventType.POSITION_CHANGE
        if UIElementType.PNL_WIDGET in element_types:
            return TradingEventType.PNL_UPDATE
        
        # Check for changes
        if previous_elements:
            prev_types = {e.element_type for e in previous_elements}
            new_elements = element_types - prev_types
            if new_elements:
                return TradingEventType.UI_CHANGE
        
        return TradingEventType.UNKNOWN
    
    def reset(self) -> None:
        """Reset pipeline state."""
        self.motion_gate.reset()
        self._frame_count = 0


# =============================================================================
# Utility Functions
# =============================================================================

def create_detector(
    mode: DetectorMode = DetectorMode.TRADING_WATCH,
    motion_gating: bool = True,
    tracking: bool = True,
) -> DetectionPipeline:
    """Factory function to create configured detection pipeline."""
    config = DetectorConfig(
        mode=mode,
        motion_gating_enabled=motion_gating,
        tracking_enabled=tracking,
    )
    return DetectionPipeline(config)
