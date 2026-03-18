"""End-to-End Integration Test Fixtures for Advanced Vision Pipeline.

Provides shared fixtures for e2e tests:
- Mock screenshot generation (with realistic UI patterns)
- Performance timing utilities
- Log verification helpers
- Model initialization helpers

All fixtures support both live and dry-run modes.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from PIL import Image, ImageDraw, ImageFont

if TYPE_CHECKING:
    from collections.abc import Generator

# Import project modules
from advanced_vision.models.model_manager import ModelManager, ModelState
from advanced_vision.trading import (
    BoundingBox,
    DetectionPipeline,
    DetectorConfig,
    DetectorMode,
    LocalReviewer,
    ReviewerConfig,
    ReviewerInput,
    ReviewerLane,
    ReviewerModel,
    ROI,
    ROIExtractor,
    TradingEvent,
    TradingEventType,
    UIElement,
    UIElementType,
)
from advanced_vision.trading.detector import DetectionResult
from advanced_vision.trading.events import DetectionSource, RiskLevel


# =============================================================================
# Performance Timing
# =============================================================================

@dataclass
class StageTiming:
    """Timing data for a pipeline stage."""
    stage_name: str
    start_time: float
    end_time: float | None = None
    latency_ms: float = 0.0
    passed: bool = False
    error: str | None = None
    
    def complete(self, passed: bool = True, error: str | None = None) -> None:
        """Mark stage as complete."""
        self.end_time = time.perf_counter()
        self.latency_ms = (self.end_time - self.start_time) * 1000
        self.passed = passed
        self.error = error


@dataclass
class PipelineTiming:
    """Complete timing data for a pipeline run."""
    run_id: str
    start_time: float = field(default_factory=time.perf_counter)
    stages: dict[str, StageTiming] = field(default_factory=dict)
    end_time: float | None = None
    total_latency_ms: float = 0.0
    
    def start_stage(self, stage_name: str) -> StageTiming:
        """Start timing a new stage."""
        timing = StageTiming(
            stage_name=stage_name,
            start_time=time.perf_counter(),
        )
        self.stages[stage_name] = timing
        return timing
    
    def complete(self) -> None:
        """Mark pipeline run as complete."""
        self.end_time = time.perf_counter()
        self.total_latency_ms = (self.end_time - self.start_time) * 1000
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "run_id": self.run_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "total_latency_ms": round(self.total_latency_ms, 2),
            "stages": {
                name: {
                    "latency_ms": round(t.latency_ms, 2),
                    "passed": t.passed,
                    "error": t.error,
                }
                for name, t in self.stages.items()
            },
        }


# =============================================================================
# Mock Screenshot Generator
# =============================================================================

class MockScreenshotGenerator:
    """Generate realistic mock screenshots for testing.
    
    Creates synthetic UI screenshots with:
    - Charts (candlestick patterns)
    - Buttons and UI elements
    - Trading interfaces
    - Modal dialogs
    """
    
    def __init__(self, width: int = 1920, height: int = 1080):
        self.width = width
        self.height = height
        self._temp_dir = Path(tempfile.mkdtemp(prefix="e2e_test_"))
    
    def create_base_screen(self, bg_color: tuple[int, int, int] = (30, 30, 35)) -> Image.Image:
        """Create base screenshot with background."""
        return Image.new("RGB", (self.width, self.height), bg_color)
    
    def draw_chart_panel(
        self,
        img: Image.Image,
        x: int = 100,
        y: int = 100,
        width: int = 800,
        height: int = 600,
        symbol: str = "AAPL",
    ) -> BoundingBox:
        """Draw a trading chart panel on the image."""
        draw = ImageDraw.Draw(img)
        
        # Panel background
        draw.rectangle([x, y, x + width, y + height], fill=(25, 25, 30), outline=(60, 60, 70), width=2)
        
        # Title bar
        draw.rectangle([x, y, x + width, y + 30], fill=(40, 40, 50))
        
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
        except:
            font = ImageFont.load_default()
        
        # Symbol label
        draw.text((x + 10, y + 7), f"{symbol} 1D", fill=(200, 200, 200), font=font)
        
        # Draw candlestick-like bars
        chart_top = y + 40
        chart_bottom = y + height - 40
        chart_left = x + 20
        chart_right = x + width - 20
        
        colors = [(0, 200, 100), (200, 50, 50)]  # Green/Red
        bar_width = 8
        gap = 4
        
        for i in range((chart_right - chart_left) // (bar_width + gap)):
            bar_x = chart_left + i * (bar_width + gap)
            if bar_x + bar_width > chart_right:
                break
            
            # Random height for variety
            import random
            bar_height = random.randint(50, 200)
            bar_y = chart_top + (chart_bottom - chart_top - bar_height) // 2
            
            color = colors[i % 2]
            draw.rectangle([bar_x, bar_y, bar_x + bar_width, bar_y + bar_height], fill=color)
        
        # Grid lines
        for i in range(5):
            y_pos = chart_top + i * (chart_bottom - chart_top) // 4
            draw.line([(chart_left, y_pos), (chart_right, y_pos)], fill=(50, 50, 55), width=1)
        
        return BoundingBox(x=x, y=y, width=width, height=height)
    
    def draw_order_ticket(
        self,
        img: Image.Image,
        x: int = 1000,
        y: int = 100,
        width: int = 300,
        height: int = 400,
    ) -> BoundingBox:
        """Draw an order ticket panel."""
        draw = ImageDraw.Draw(img)
        
        # Panel background
        draw.rectangle([x, y, x + width, y + height], fill=(35, 35, 40), outline=(80, 80, 90), width=2)
        
        # Title bar
        draw.rectangle([x, y, x + width, y + 35], fill=(50, 50, 60))
        
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
        except:
            font = ImageFont.load_default()
            font_small = font
        
        draw.text((x + 10, y + 10), "Order Ticket", fill=(220, 220, 220), font=font)
        
        # Form fields
        fields = ["Symbol:", "Quantity:", "Price:", "Type:"]
        field_y = y + 50
        for field in fields:
            draw.rectangle([x + 10, field_y, x + width - 10, field_y + 30], fill=(45, 45, 50), outline=(70, 70, 75))
            draw.text((x + 15, field_y + 7), field, fill=(180, 180, 180), font=font_small)
            field_y += 45
        
        # Submit button
        btn_y = y + height - 50
        draw.rectangle([x + 20, btn_y, x + width - 20, btn_y + 35], fill=(0, 150, 80), outline=(0, 180, 100))
        draw.text((x + width // 2 - 25, btn_y + 10), "Submit", fill=(255, 255, 255), font=font_small)
        
        return BoundingBox(x=x, y=y, width=width, height=height)
    
    def draw_modal(
        self,
        img: Image.Image,
        modal_type: str = "confirm",
        x: int | None = None,
        y: int | None = None,
        width: int = 400,
        height: int = 200,
    ) -> BoundingBox:
        """Draw a modal dialog."""
        if x is None:
            x = (self.width - width) // 2
        if y is None:
            y = (self.height - height) // 2
        
        draw = ImageDraw.Draw(img)
        
        # Semi-transparent overlay effect (simulated with darker rect)
        overlay = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 128))
        img_rgba = img.convert("RGBA")
        img_rgba = Image.alpha_composite(img_rgba, overlay)
        img.paste(img_rgba.convert("RGB"))
        
        # Modal background
        colors = {
            "confirm": (45, 55, 65),
            "warning": (65, 55, 35),
            "error": (65, 35, 35),
        }
        bg_color = colors.get(modal_type, colors["confirm"])
        
        draw.rectangle([x, y, x + width, y + height], fill=bg_color, outline=(100, 100, 110), width=2)
        
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
        except:
            font = ImageFont.load_default()
            font_small = font
        
        # Title
        titles = {
            "confirm": "Confirm Order",
            "warning": "Warning",
            "error": "Error",
        }
        draw.text((x + 20, y + 20), titles.get(modal_type, "Dialog"), fill=(220, 220, 220), font=font)
        
        # Message
        messages = {
            "confirm": "Please confirm your order details before submitting.",
            "warning": "High volatility detected. Proceed with caution.",
            "error": "Insufficient funds for this order.",
        }
        draw.text((x + 20, y + 60), messages.get(modal_type, ""), fill=(180, 180, 180), font=font_small)
        
        # Buttons
        btn_y = y + height - 50
        if modal_type == "confirm":
            draw.rectangle([x + 30, btn_y, x + 150, btn_y + 35], fill=(100, 100, 110), outline=(120, 120, 130))
            draw.text((x + 60, btn_y + 10), "Cancel", fill=(200, 200, 200), font=font_small)
            draw.rectangle([x + width - 150, btn_y, x + width - 30, btn_y + 35], fill=(0, 150, 80), outline=(0, 180, 100))
            draw.text((x + width - 110, btn_y + 10), "Confirm", fill=(255, 255, 255), font=font_small)
        else:
            draw.rectangle([x + width // 2 - 60, btn_y, x + width // 2 + 60, btn_y + 35], fill=(80, 80, 90), outline=(100, 100, 110))
            draw.text((x + width // 2 - 20, btn_y + 10), "OK", fill=(200, 200, 200), font=font_small)
        
        return BoundingBox(x=x, y=y, width=width, height=height)
    
    def draw_cursor(self, img: Image.Image, x: int = 500, y: int = 500) -> BoundingBox:
        """Draw a mouse cursor."""
        draw = ImageDraw.Draw(img)
        
        # Simple arrow cursor
        cursor_points = [
            (x, y),
            (x, y + 20),
            (x + 5, y + 15),
            (x + 10, y + 25),
            (x + 13, y + 22),
            (x + 8, y + 12),
            (x + 15, y + 12),
        ]
        draw.polygon(cursor_points, fill=(255, 255, 255), outline=(0, 0, 0))
        
        return BoundingBox(x=x, y=y, width=15, height=25)
    
    def draw_button(
        self,
        img: Image.Image,
        x: int,
        y: int,
        width: int = 120,
        height: int = 40,
        label: str = "Button",
        style: str = "primary",
    ) -> BoundingBox:
        """Draw a UI button."""
        draw = ImageDraw.Draw(img)
        
        colors = {
            "primary": (0, 120, 200),
            "secondary": (80, 80, 90),
            "danger": (200, 50, 50),
        }
        bg_color = colors.get(style, colors["primary"])
        
        draw.rectangle([x, y, x + width, y + height], fill=bg_color, outline=(bg_color[0] + 30, bg_color[1] + 30, bg_color[2] + 30))
        
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
        except:
            font = ImageFont.load_default()
        
        # Center text
        text_bbox = draw.textbbox((0, 0), label, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_x = x + (width - text_width) // 2
        text_y = y + (height - 14) // 2
        
        draw.text((text_x, text_y), label, fill=(255, 255, 255), font=font)
        
        return BoundingBox(x=x, y=y, width=width, height=height)
    
    def generate_chart_screenshot(self, filename: str | None = None) -> Path:
        """Generate a screenshot with a chart panel."""
        img = self.create_base_screen()
        self.draw_chart_panel(img, symbol="AAPL")
        self.draw_order_ticket(img)
        
        if filename is None:
            filename = f"chart_{uuid.uuid4().hex[:8]}.png"
        path = self._temp_dir / filename
        img.save(path, "PNG")
        return path
    
    def generate_ui_screenshot(self, filename: str | None = None) -> Path:
        """Generate a screenshot with UI elements (buttons)."""
        img = self.create_base_screen()
        
        # Draw several buttons
        self.draw_button(img, 100, 100, label="Buy", style="primary")
        self.draw_button(img, 250, 100, label="Sell", style="danger")
        self.draw_button(img, 400, 100, label="Settings", style="secondary")
        self.draw_button(img, 100, 200, label="Refresh", style="secondary")
        
        if filename is None:
            filename = f"ui_{uuid.uuid4().hex[:8]}.png"
        path = self._temp_dir / filename
        img.save(path, "PNG")
        return path
    
    def generate_pattern_screenshot(
        self,
        pattern_type: str = "support",
        filename: str | None = None,
    ) -> Path:
        """Generate a screenshot with a trading pattern ROI."""
        img = self.create_base_screen()
        
        # Draw chart with pattern
        chart_bbox = self.draw_chart_panel(img, symbol="TSLA")
        
        # Draw pattern annotation (simulated support/resistance line)
        draw = ImageDraw.Draw(img)
        line_y = chart_bbox.y + chart_bbox.height // 2
        draw.line(
            [(chart_bbox.x + 50, line_y), (chart_bbox.x + chart_bbox.width - 50, line_y)],
            fill=(255, 200, 0),
            width=3,
        )
        
        if filename is None:
            filename = f"pattern_{pattern_type}_{uuid.uuid4().hex[:8]}.png"
        path = self._temp_dir / filename
        img.save(path, "PNG")
        return path
    
    def generate_noise_screenshot(self, filename: str | None = None) -> Path:
        """Generate a screenshot with only cursor (noise)."""
        img = self.create_base_screen()
        self.draw_cursor(img, x=500, y=500)
        
        if filename is None:
            filename = f"noise_{uuid.uuid4().hex[:8]}.png"
        path = self._temp_dir / filename
        img.save(path, "PNG")
        return path
    
    def generate_modal_screenshot(self, modal_type: str = "confirm") -> Path:
        """Generate a screenshot with a modal dialog."""
        img = self.create_base_screen()
        self.draw_chart_panel(img)
        self.draw_modal(img, modal_type=modal_type)
        
        filename = f"modal_{modal_type}_{uuid.uuid4().hex[:8]}.png"
        path = self._temp_dir / filename
        img.save(path, "PNG")
        return path
    
    def cleanup(self) -> None:
        """Clean up temporary files."""
        import shutil
        if self._temp_dir.exists():
            shutil.rmtree(self._temp_dir)


# =============================================================================
# Log Verification Helpers
# =============================================================================

class LogVerifier:
    """Verify pipeline logs are written correctly to JSONL."""
    
    def __init__(self, log_dir: Path | None = None):
        self.log_dir = log_dir or Path("logs/e2e")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._log_file = self.log_dir / f"e2e_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
        self._entries: list[dict] = []
    
    def write_entry(self, entry: dict[str, Any]) -> None:
        """Write a log entry to the JSONL file."""
        entry["_log_timestamp"] = datetime.now().isoformat()
        self._entries.append(entry)
        
        with open(self._log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
    
    def verify_entry_exists(self, **filters) -> bool:
        """Verify an entry with given filters exists in the log."""
        for entry in self._entries:
            if all(entry.get(k) == v for k, v in filters.items()):
                return True
        return False
    
    def get_entries(self, **filters) -> list[dict]:
        """Get entries matching filters."""
        return [
            entry for entry in self._entries
            if all(entry.get(k) == v for k, v in filters.items())
        ]
    
    def get_last_entry(self) -> dict | None:
        """Get the last log entry."""
        return self._entries[-1] if self._entries else None
    
    def verify_schema(self, entry: dict, schema_type: str) -> tuple[bool, list[str]]:
        """Verify an entry matches expected schema."""
        errors = []
        
        if schema_type == "ui":
            required = ["event_id", "timestamp", "event_type", "source", "confidence"]
        elif schema_type == "trading":
            required = ["event_id", "timestamp", "event_type", "source", "confidence", "risk_level"]
        else:
            return False, [f"Unknown schema type: {schema_type}"]
        
        for field in required:
            if field not in entry:
                errors.append(f"Missing required field: {field}")
        
        return len(errors) == 0, errors
    
    @property
    def log_file_path(self) -> Path:
        """Get the path to the log file."""
        return self._log_file


# =============================================================================
# Pytest Fixtures
# =============================================================================

@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Provide a temporary directory for test artifacts."""
    import tempfile
    import shutil
    
    temp = Path(tempfile.mkdtemp(prefix="e2e_test_"))
    yield temp
    shutil.rmtree(temp, ignore_errors=True)


@pytest.fixture
def screenshot_generator() -> Generator[MockScreenshotGenerator, None, None]:
    """Provide a mock screenshot generator."""
    generator = MockScreenshotGenerator()
    yield generator
    generator.cleanup()


@pytest.fixture
def log_verifier() -> Generator[LogVerifier, None, None]:
    """Provide a log verifier."""
    verifier = LogVerifier()
    yield verifier


@pytest.fixture
def model_manager() -> Generator[ModelManager, None, None]:
    """Provide a model manager (dry-run by default for safety)."""
    manager = ModelManager(dry_run=True)
    yield manager
    manager.cleanup()


@pytest.fixture
def detection_pipeline() -> Generator[DetectionPipeline, None, None]:
    """Provide a detection pipeline."""
    config = DetectorConfig(mode=DetectorMode.TRADING_WATCH)
    pipeline = DetectionPipeline(config)
    yield pipeline
    pipeline.reset()


@pytest.fixture
def reviewer_lane() -> Generator[ReviewerLane, None, None]:
    """Provide a reviewer lane."""
    config = ReviewerConfig(
        model=ReviewerModel.STUB,
        dry_run=True,
    )
    lane = ReviewerLane(config)
    yield lane


@pytest.fixture
def roi_extractor(temp_dir: Path) -> Generator[ROIExtractor, None, None]:
    """Provide an ROI extractor."""
    extractor = ROIExtractor(artifacts_dir=temp_dir / "rois")
    yield extractor


@pytest.fixture
def pipeline_timing() -> Generator[PipelineTiming, None, None]:
    """Provide a pipeline timing tracker."""
    timing = PipelineTiming(run_id=uuid.uuid4().hex[:12])
    yield timing
    timing.complete()


# =============================================================================
# Performance Target Constants
# =============================================================================

PERFORMANCE_TARGETS = {
    "yolo_ms": 50,           # YOLO detection: < 50ms
    "eagle_ms": 1000,        # Eagle classification: < 1s
    "qwen_ms": 3000,         # Qwen analysis: < 3s
    "total_pipeline_ms": 5000,  # Total pipeline: < 5s
}


# =============================================================================
# Helper Functions
# =============================================================================

def create_test_event(
    event_type: TradingEventType,
    confidence: float = 0.85,
    screenshot_path: str | None = None,
) -> TradingEvent:
    """Create a test trading event."""
    return TradingEvent(
        event_id=f"test_{uuid.uuid4().hex[:12]}",
        timestamp=datetime.now().isoformat(),
        event_type=event_type,
        source=DetectionSource.TRIPWIRE,
        confidence=confidence,
        screen_width=1920,
        screen_height=1080,
        screenshot_path=screenshot_path,
    )


def assert_performance(
    timing: PipelineTiming,
    stage_name: str,
    target_ms: float,
) -> None:
    """Assert a stage meets its performance target."""
    stage = timing.stages.get(stage_name)
    if not stage:
        pytest.fail(f"Stage {stage_name} not found in timing data")
    
    if stage.latency_ms > target_ms:
        pytest.fail(
            f"Stage {stage_name} exceeded performance target: "
            f"{stage.latency_ms:.2f}ms > {target_ms}ms"
        )


def create_mock_ui_element(
    element_type: UIElementType,
    x: int = 100,
    y: int = 100,
    width: int = 200,
    height: int = 100,
    confidence: float = 0.85,
) -> UIElement:
    """Create a mock UI element."""
    return UIElement(
        element_id=f"elem_{uuid.uuid4().hex[:8]}",
        element_type=element_type,
        bbox=BoundingBox(x=x, y=y, width=width, height=height),
        confidence=confidence,
        source=DetectionSource.TRIPWIRE,
    )
