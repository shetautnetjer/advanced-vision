"""ROI (Region of Interest) extraction for Track B: Trading-Watch Intelligence.

This module implements:
- ROI extraction from detected UI elements
- ROI crop generation for focused analysis
- UI structure extraction patterns (OmniParser-like)
- Chart region detection
- Order ticket/modal isolation

Per Dad's findings:
- SAM3 is the "precision knife" - used selectively, not always-on
- ROIs feed the scout (Eagle) and reviewer (Qwen) lanes
- Minimal evidence bundles for cloud escalation
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from PIL.Image import Image

from advanced_vision.trading.events import (
    BoundingBox,
    DetectionSource,
    ROI,
    TradingEventType,
    UIElement,
    UIElementType,
)


# =============================================================================
# ROI Configuration
# =============================================================================

class ROIConfig(BaseModel):
    """Configuration for ROI extraction behavior."""
    
    # Margin to add around detected elements (pixels)
    margin_pixels: int = 10
    
    # Minimum ROI size (ignore smaller)
    min_width: int = 50
    min_height: int = 30
    
    # Maximum ROI size (avoid full-screen captures)
    max_width: int = 800
    max_height: int = 600
    
    # Whether to use SAM3 for segmentation (if available)
    use_sam3: bool = False
    
    # SAM3 model path (stub - don't download actual model)
    sam3_model_path: str | None = None
    
    # Crop output settings
    crop_format: str = "PNG"
    crop_quality: int = 95
    
    # Padding for context around elements
    context_padding: int = 20


# =============================================================================
# ROI Extractor
# =============================================================================

class ROIExtractor:
    """Extract and manage Regions of Interest from screen captures.
    
    This is the precision refinement lane per Dad's architecture:
    - Takes detected elements from YOLO tripwire
    - Extracts focused crops for scout/reviewer analysis
    - Optionally uses SAM3 for precise segmentation
    - Maintains ROI registry for tracking across frames
    """
    
    def __init__(self, config: ROIConfig | None = None, artifacts_dir: Path | None = None):
        self.config = config or ROIConfig()
        self.artifacts_dir = artifacts_dir or Path("artifacts/trading")
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        
        # ROI registry for tracking across frames
        self._roi_registry: dict[str, ROI] = {}
        self._roi_counter = 0
        
        # SAM3 stub (not loaded until explicitly requested)
        self._sam3_model: Any | None = None
    
    def _generate_roi_id(self, element_type: UIElementType, bbox: BoundingBox) -> str:
        """Generate unique ROI ID."""
        self._roi_counter += 1
        data = f"{element_type.value}_{bbox.x}_{bbox.y}_{self._roi_counter}"
        hash_part = hashlib.md5(data.encode()).hexdigest()[:8]
        return f"roi_{element_type.value}_{hash_part}"
    
    def _adjust_bbox(self, bbox: BoundingBox, screen_width: int, screen_height: int) -> BoundingBox:
        """Adjust bounding box with margins and bounds checking."""
        # Add margin
        x = max(0, bbox.x - self.config.margin_pixels)
        y = max(0, bbox.y - self.config.margin_pixels)
        width = min(
            screen_width - x,
            bbox.width + (self.config.margin_pixels * 2)
        )
        height = min(
            screen_height - y,
            bbox.height + (self.config.margin_pixels * 2)
        )
        
        # Apply min/max constraints
        if width < self.config.min_width or height < self.config.min_height:
            return bbox  # Return original if too small after margin
        
        width = min(width, self.config.max_width)
        height = min(height, self.config.max_height)
        
        return BoundingBox(x=x, y=y, width=width, height=height)
    
    def extract_roi(
        self,
        screenshot: "Image",
        element: UIElement,
        screen_width: int,
        screen_height: int,
        save_crop: bool = True,
    ) -> ROI:
        """Extract ROI from screenshot based on detected element.
        
        Args:
            screenshot: PIL Image of full screen
            element: Detected UI element
            screen_width: Screen width in pixels
            screen_height: Screen height in pixels
            save_crop: Whether to save cropped image to disk
            
        Returns:
            ROI object with metadata and optional crop path
        """
        # Adjust bounding box
        adjusted_bbox = self._adjust_bbox(
            element.bbox, screen_width, screen_height
        )
        
        # Generate ROI ID
        roi_id = self._generate_roi_id(element.element_type, adjusted_bbox)
        
        # Extract crop path
        crop_path: str | None = None
        if save_crop:
            crop_path = self._save_crop(screenshot, adjusted_bbox, roi_id)
        
        # Create ROI
        roi = ROI(
            roi_id=roi_id,
            element_type=element.element_type,
            bbox=adjusted_bbox,
            confidence=element.confidence,
            crop_path=crop_path,
            source=DetectionSource.PRECISION if self.config.use_sam3 else DetectionSource.TRIPWIRE,
        )
        
        # Register for tracking
        self._roi_registry[roi_id] = roi
        
        return roi
    
    def _save_crop(
        self,
        screenshot: "Image",
        bbox: BoundingBox,
        roi_id: str,
    ) -> str:
        """Save ROI crop to disk."""
        crop = screenshot.crop((
            bbox.x,
            bbox.y,
            bbox.x + bbox.width,
            bbox.y + bbox.height,
        ))
        
        crop_path = self.artifacts_dir / f"{roi_id}.png"
        crop.save(crop_path, format=self.config.crop_format)
        
        return str(crop_path)
    
    def extract_rois_for_event(
        self,
        screenshot: "Image",
        elements: list[UIElement],
        screen_width: int,
        screen_height: int,
        event_type: TradingEventType,
    ) -> list[ROI]:
        """Extract ROIs for all elements relevant to a trading event.
        
        Args:
            screenshot: Full screen capture
            elements: List of detected UI elements
            screen_width: Screen dimensions
            screen_height: Screen dimensions
            event_type: Type of trading event
            
        Returns:
            List of extracted ROIs
        """
        rois = []
        
        # Filter elements relevant to event type
        relevant_types = self._get_relevant_element_types(event_type)
        
        for element in elements:
            if element.element_type in relevant_types:
                roi = self.extract_roi(
                    screenshot, element, screen_width, screen_height
                )
                rois.append(roi)
        
        # Also extract primary ROI if no specific matches
        if not rois and elements:
            # Use highest confidence element
            primary = max(elements, key=lambda e: e.confidence)
            roi = self.extract_roi(
                screenshot, primary, screen_width, screen_height
            )
            rois.append(roi)
        
        return rois
    
    def _get_relevant_element_types(
        self, event_type: TradingEventType
    ) -> set[UIElementType]:
        """Get UI element types relevant to a trading event type."""
        mapping: dict[TradingEventType, set[UIElementType]] = {
            TradingEventType.CHART_UPDATE: {
                UIElementType.CHART_PANEL,
                UIElementType.CHART_TOOLBAR,
            },
            TradingEventType.PRICE_CHANGE: {
                UIElementType.PRICE_DISPLAY,
                UIElementType.CHART_PANEL,
            },
            TradingEventType.ORDER_TICKET: {
                UIElementType.ORDER_TICKET_PANEL,
                UIElementType.TEXT_FIELD,
                UIElementType.BUTTON,
            },
            TradingEventType.CONFIRM_DIALOG: {
                UIElementType.CONFIRM_MODAL,
                UIElementType.BUTTON,
            },
            TradingEventType.WARNING_DIALOG: {
                UIElementType.WARNING_MODAL,
                UIElementType.BUTTON,
            },
            TradingEventType.ERROR_DIALOG: {
                UIElementType.ERROR_MODAL,
                UIElementType.BUTTON,
            },
            TradingEventType.PNL_UPDATE: {
                UIElementType.PNL_WIDGET,
                UIElementType.POSITION_PANEL,
            },
            TradingEventType.POSITION_CHANGE: {
                UIElementType.POSITION_PANEL,
            },
        }
        return mapping.get(event_type, set())
    
    def get_roi(self, roi_id: str) -> ROI | None:
        """Get ROI from registry by ID."""
        return self._roi_registry.get(roi_id)
    
    def clear_registry(self) -> None:
        """Clear ROI registry (e.g., between sessions)."""
        self._roi_registry.clear()
        self._roi_counter = 0


# =============================================================================
# UI Structure Extraction (OmniParser-like)
# =============================================================================

class UIElementNode(BaseModel):
    """Tree node for UI structure extraction."""
    element: UIElement
    children: list["UIElementNode"] = Field(default_factory=list)
    depth: int = 0


class UIStructure(BaseModel):
    """Extracted UI structure from parser lane."""
    root_elements: list[UIElementNode]
    all_elements: list[UIElement]
    screen_width: int
    screen_height: int
    extraction_timestamp: str
    
    def find_by_type(self, element_type: UIElementType) -> list[UIElement]:
        """Find all elements of given type."""
        return [e for e in self.all_elements if e.element_type == element_type]
    
    def find_by_text(self, text: str) -> list[UIElement]:
        """Find elements containing text (case-insensitive)."""
        text_lower = text.lower()
        return [
            e for e in self.all_elements
            if e.text_content and text_lower in e.text_content.lower()
        ]
    
    def get_modals(self) -> list[UIElement]:
        """Get all modal/dialog elements."""
        modal_types = {
            UIElementType.CONFIRM_MODAL,
            UIElementType.WARNING_MODAL,
            UIElementType.ERROR_MODAL,
        }
        return [e for e in self.all_elements if e.element_type in modal_types]


class UIStructureExtractor:
    """Extract structured UI hierarchy from detections.
    
    OmniParser-like functionality for UI structure extraction.
    Provides semantic understanding of UI layout without requiring
    the actual OmniParser model (stub implementation).
    """
    
    def __init__(self):
        self._element_tree: list[UIElementNode] = []
    
    def extract_structure(
        self,
        elements: list[UIElement],
        screen_width: int,
        screen_height: int,
    ) -> UIStructure:
        """Extract hierarchical UI structure from flat element list.
        
        This is a simplified implementation that groups elements
        by spatial proximity and containment.
        """
        # Sort by area (largest first) for parent detection
        sorted_elements = sorted(
            elements,
            key=lambda e: e.bbox.area,
            reverse=True
        )
        
        # Build parent-child relationships
        element_nodes: dict[str, UIElementNode] = {}
        root_nodes: list[UIElementNode] = []
        
        for element in sorted_elements:
            node = UIElementNode(element=element, children=[], depth=0)
            element_nodes[element.element_id] = node
            
            # Find parent (smallest containing element)
            parent: UIElementNode | None = None
            for other_id, other_node in element_nodes.items():
                if other_id == element.element_id:
                    continue
                if self._is_contained_in(element.bbox, other_node.element.bbox):
                    if parent is None or other_node.element.bbox.area < parent.element.bbox.area:
                        parent = other_node
            
            if parent:
                node.depth = parent.depth + 1
                parent.children.append(node)
            else:
                root_nodes.append(node)
        
        return UIStructure(
            root_elements=root_nodes,
            all_elements=elements,
            screen_width=screen_width,
            screen_height=screen_height,
            extraction_timestamp="",  # To be set by caller
        )
    
    def _is_contained_in(self, inner: BoundingBox, outer: BoundingBox) -> bool:
        """Check if inner box is contained within outer box."""
        return (
            inner.x >= outer.x and
            inner.y >= outer.y and
            inner.x + inner.width <= outer.x + outer.width and
            inner.y + inner.height <= outer.y + outer.height
        )


# =============================================================================
# Chart Region Detection
# =============================================================================

class ChartRegion(BaseModel):
    """Detected chart region with metadata."""
    roi: ROI
    chart_type: str | None = None  # "candlestick", "line", "volume", etc.
    symbol: str | None = None
    timeframe: str | None = None
    indicators: list[str] = Field(default_factory=list)


class ChartRegionDetector:
    """Detect and classify chart regions in trading interfaces."""
    
    def __init__(self, roi_extractor: ROIExtractor | None = None):
        self.roi_extractor = roi_extractor or ROIExtractor()
    
    def detect_chart_regions(
        self,
        screenshot: "Image",
        elements: list[UIElement],
        screen_width: int,
        screen_height: int,
    ) -> list[ChartRegion]:
        """Detect chart panels from UI elements."""
        chart_regions = []
        
        for element in elements:
            if element.element_type == UIElementType.CHART_PANEL:
                roi = self.roi_extractor.extract_roi(
                    screenshot, element, screen_width, screen_height
                )
                
                chart_region = ChartRegion(
                    roi=roi,
                    chart_type=None,  # Would require image analysis
                    symbol=self._extract_symbol(element),
                    timeframe=None,  # Would require OCR/text analysis
                )
                chart_regions.append(chart_region)
        
        return chart_regions
    
    def _extract_symbol(self, element: UIElement) -> str | None:
        """Attempt to extract trading symbol from element text."""
        if not element.text_content:
            return None
        
        # Simple pattern matching for common symbol formats
        text = element.text_content.upper()
        
        # Look for patterns like AAPL, BTCUSD, EUR/USD
        import re
        symbol_pattern = r'\b([A-Z]{2,5}|\b[A-Z]{3}/[A-Z]{3})\b'
        matches = re.findall(symbol_pattern, text)
        
        return matches[0] if matches else None


# =============================================================================
# Order Ticket Extraction
# =============================================================================

class OrderField(BaseModel):
    """Field within an order ticket."""
    field_name: str
    field_type: str  # "text", "dropdown", "checkbox", etc.
    value: str | None = None
    bbox: BoundingBox


class OrderTicket(BaseModel):
    """Extracted order ticket structure."""
    roi: ROI
    fields: list[OrderField]
    action: str | None = None  # "buy", "sell", etc.
    symbol: str | None = None
    quantity: float | None = None
    order_type: str | None = None  # "market", "limit", "stop", etc.
    price: float | None = None
    
    def is_valid(self) -> bool:
        """Check if ticket has minimum required fields."""
        return bool(self.symbol and self.action and self.quantity)


class OrderTicketExtractor:
    """Extract structured order ticket information."""
    
    def __init__(self, roi_extractor: ROIExtractor | None = None):
        self.roi_extractor = roi_extractor or ROIExtractor()
    
    def extract_order_ticket(
        self,
        screenshot: "Image",
        ticket_element: UIElement,
        child_elements: list[UIElement],
        screen_width: int,
        screen_height: int,
    ) -> OrderTicket | None:
        """Extract order ticket from UI elements."""
        roi = self.roi_extractor.extract_roi(
            screenshot, ticket_element, screen_width, screen_height
        )
        
        # Extract fields from child elements
        fields = []
        for child in child_elements:
            field = OrderField(
                field_name=child.element_type.value,
                field_type="text" if child.element_type == UIElementType.TEXT_FIELD else "other",
                value=child.text_content,
                bbox=child.bbox,
            )
            fields.append(field)
        
        return OrderTicket(
            roi=roi,
            fields=fields,
        )


# =============================================================================
# Evidence Bundle Preparation
# =============================================================================

class EvidenceBundle(BaseModel):
    """Minimal evidence bundle for cloud escalation.
    
    Per Dad's findings: escalate only minimal, sanitized evidence to Kimi.
    """
    event_id: str
    timestamp: str
    
    # Redacted/sanitized content
    event_summary: str
    risk_indicators: list[str]
    
    # ROI references (paths, not full images)
    roi_crop_paths: list[str]
    
    # Reviewer assessment (if available)
    reviewer_confidence: float | None = None
    reviewer_reasoning: str | None = None
    
    # Optional redacted OCR text
    redacted_text: str | None = None
    
    # No raw screenshots or sensitive data


class EvidenceBundler:
    """Prepare minimal, sanitized evidence bundles for cloud escalation."""
    
    def __init__(self, artifacts_dir: Path | None = None):
        self.artifacts_dir = artifacts_dir or Path("artifacts/trading/bundles")
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
    
    def create_bundle(
        self,
        event: "TradingEvent",  # Forward reference
        redact_sensitive: bool = True,
    ) -> EvidenceBundle:
        """Create minimal evidence bundle for overseer escalation."""
        # Collect ROI paths
        roi_paths = [
            roi.crop_path for roi in event.rois
            if roi.crop_path
        ]
        
        # Extract risk indicators
        risk_indicators = []
        if event.reviewer_assessment:
            if event.reviewer_assessment.is_uncertain:
                risk_indicators.append("reviewer_uncertain")
            risk_indicators.append(f"risk_{event.reviewer_assessment.risk_level.value}")
        
        # Sanitize text content
        redacted_text = None
        if event.raw_text_extracted and redact_sensitive:
            redacted_text = self._redact_sensitive_content(event.raw_text_extracted)
        
        return EvidenceBundle(
            event_id=event.event_id,
            timestamp=event.timestamp,
            event_summary=event.summary or "No summary available",
            risk_indicators=risk_indicators,
            roi_crop_paths=roi_paths,
            reviewer_confidence=event.reviewer_assessment.confidence if event.reviewer_assessment else None,
            reviewer_reasoning=event.reviewer_assessment.reasoning if event.reviewer_assessment else None,
            redacted_text=redacted_text,
        )
    
    def _redact_sensitive_content(self, text: str) -> str:
        """Redact potentially sensitive information.
        
        Removes/redacts:
        - API keys
        - Wallet addresses
        - Account numbers
        - Specific dollar amounts (keep patterns)
        """
        import re
        
        redacted = text
        
        # Redact API keys (patterns like key_xxx, sk-xxx, etc.)
        redacted = re.sub(r'\b(key_[a-zA-Z0-9]{16,}|sk-[a-zA-Z0-9]{24,})\b', '[API_KEY_REDACTED]', redacted)
        
        # Redact crypto wallet addresses
        redacted = re.sub(r'\b(0x[a-fA-F0-9]{40})\b', '[WALLET_REDACTED]', redacted)
        
        # Redact account numbers (keep last 4 digits)
        def redact_acct(match):
            full = match.group(1)
            return '[ACCT-XXXX' + full[-4:] + ']'
        redacted = re.sub(r'\b(\d{8,})\b', redact_acct, redacted)
        
        return redacted
