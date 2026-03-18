# Architecture - Advanced Vision Trading System

**Last Verified:** 2026-03-17  
**Hardware:** NVIDIA RTX 5070 Ti 16GB  
**Status:** ✅ Architecture Confirmed & Operational

---

## System Overview

The Advanced Vision Trading System is a local-first computer-use pipeline optimized for real-time trading interface analysis. It combines vision-language models with traditional computer vision for screen understanding and UI interaction.

---

## Pipeline Architecture

### Data Flow (Confirmed Working)

```
┌─────────────────────────────────────────────────────────────────┐
│  1. SCREEN CAPTURE                                              │
│     └─→ advanced_vision.tools.screenshot_full()                 │
│         ~100ms, 1920x1080 PNG                                   │
└──────────────────────────┬──────────────────────────────────────┘
                           ↓
┌──────────────────────────▼──────────────────────────────────────┐
│  2. YOLO DETECTION (YOLOv8n)                                    │
│     └─→ Detects: chart panels, buttons, modals, text inputs     │
│         ~10ms, 0.4GB VRAM                                       │
└──────────────────────────┬──────────────────────────────────────┘
                           ↓
┌──────────────────────────▼──────────────────────────────────────┐
│  3. EAGLE2 SCOUT (Eagle2-2B)                                    │
│     └─→ "Is this trading-relevant?"                             │
│         • noise → discard                                       │
│         • trading-relevant → send to Qwen                       │
│         ~300-500ms, ~4GB VRAM                                   │
└──────────────────────────┬──────────────────────────────────────┘
                           ↓
┌──────────────────────────▼──────────────────────────────────────┐
│  4. QWEN REVIEWER (Qwen3.5-4B)                                  │
│     └─→ Deep analysis: pattern type, risk level, recommendation │
│         • confident → action                                    │
│         • uncertain → escalate to Kimi                          │
│         ~1-2s, 8.4GB VRAM                                       │
└─────────────────────────────────────────────────────────────────┘
```

**Total Pipeline Latency:** ~2-4 seconds for full analysis

---

## Model Roles

| Role | Model | Speed | VRAM | Job |
|------|-------|-------|------|-----|
| **Detect** | YOLOv8n | ~10ms | 0.4GB | UI element detection |
| **Segment** | MobileSAM | ~12ms | 0.5GB | Precise ROI extraction |
| **Scout** | Eagle2-2B | ~300-500ms | ~4GB | Fast classify: noise vs trading-relevant |
| **Reviewer** | Qwen3.5-4B | ~1-2s | 8.4GB | Deep analysis: patterns, risk, actions |
| **Scout (alt)** | Qwen3.5-2B | ~500ms-1s | 3.8GB | Alternative scout (smaller/faster) |

---

## Directory Structure

```
advanced-vision/
├── src/advanced_vision/
│   ├── models/
│   │   ├── model_manager.py      # VRAM-aware model loading
│   │   └── __init__.py
│   ├── trading/
│   │   ├── detector.py           # YOLO detection pipeline
│   │   ├── reviewer.py           # Qwen reviewer lane
│   │   ├── events.py             # Trading event taxonomy
│   │   ├── roi.py                # ROI extraction logic
│   │   └── __init__.py
│   ├── tools/
│   │   └── screenshot.py         # Screen capture tools
│   ├── schemas.py                # Data models
│   └── server.py                 # MCP server
├── models/                       # Model weights (NOT in git)
│   ├── Qwen3.5-4B/              # 8.1GB on disk
│   ├── Qwen3.5-2B/              # 4.1GB on disk
│   ├── Eagle2-2B/               # 4.2GB on disk
│   ├── MobileSAM/               # 39MB on disk
│   ├── yolov8n.pt               # 6.3MB
│   └── yolov8s.pt               # 22MB
├── config/
│   └── model_registry.json       # Model metadata
├── docs/                         # Documentation
└── artifacts/
    └── screens/                  # Screenshot storage
```

---

## VRAM Budget (Verified)

### Resident Models (Always Loaded)

```
Component                    VRAM Usage
────────────────────────────────────────
YOLOv8n (detection)          0.4 GB
MobileSAM (segmentation)     0.5 GB
Eagle2-2B (scout)            4.0 GB
Qwen3.5-4B (reviewer)        8.4 GB
────────────────────────────────────────
Subtotal:                   13.3 GB
Cache/Overhead:              0.5 GB
────────────────────────────────────────
Total Resident:             13.8 GB
Headroom:                    2.2 GB / 16 GB ✅
```

### Alternative: 2B Scout Configuration

```
YOLOv8n                      0.4 GB
MobileSAM                    0.5 GB
Qwen3.5-2B (scout)           3.8 GB
Qwen3.5-4B (reviewer)        8.4 GB
────────────────────────────────────────
Total:                      13.1 GB ✅
More headroom for batching
```

---

## Module Descriptions

### 1. Model Manager (`models/model_manager.py`)

Central VRAM-aware model loading system.

**Key Classes:**
- `ModelManager` - Main orchestrator
- `ModelConfig` - Per-model configuration
- `VRAMStats` - VRAM tracking

**Features:**
- Sequential loading to prevent fragmentation
- Automatic model swapping when VRAM constrained
- Dry-run mode for testing
- vLLM/Transformers dual support

**Usage:**
```python
from advanced_vision.models import ModelManager

manager = ModelManager()
manager.load_model('qwen3.5-4b')  # Auto-detects BF16
manager.print_status()
```

---

### 2. Trading Detector (`trading/detector.py`)

YOLO-based UI element detection.

**Key Classes:**
- `DetectionPipeline` - Main detection orchestrator
- `UIElement` - Detected element structure

**Detects:**
- Chart panels
- Order buttons
- Text inputs
- Modal dialogs
- Price displays

---

### 3. Trading Reviewer (`trading/reviewer.py`)

Local reviewer lane for event assessment.

**Key Classes:**
- `LocalReviewer` - Model-based assessment
- `ReviewerLane` - Pipeline orchestration
- `ReviewerConfig` - Configuration

**Output:**
- Risk level (none/low/medium/high/critical)
- Recommendation (continue/note/warn/hold/pause/escalate)
- Confidence score
- Escalation flag

---

### 4. Trading Events (`trading/events.py`)

Event taxonomy and risk classification.

**Key Enums:**
- `TradingEventType` - Event categories
- `RiskLevel` - Risk classification
- `ActionRecommendation` - System response

**Event Types:**
- NOISE, CURSOR_ONLY, ANIMATION
- CHART_UPDATE, PRICE_CHANGE
- ORDER_TICKET, CONFIRM_DIALOG
- WARNING_DIALOG, ERROR_DIALOG
- SLIPPAGE_WARNING, MARGIN_WARNING

---

### 5. ROI Extraction (`trading/roi.py`)

Region-of-interest handling and evidence bundling.

**Key Classes:**
- `ROI` - Region of interest
- `EvidenceBundle` - Aggregated evidence
- `UIStructure` - Parsed UI hierarchy

---

## Data Flow Details

### Screenshot → Analysis Pipeline

```python
# 1. Capture
from advanced_vision.tools import screenshot_full
screenshot = screenshot_full()  # Returns ScreenshotArtifact

# 2. Detect UI elements
from advanced_vision.trading.detector import DetectionPipeline
detector = DetectionPipeline()
elements = detector.detect(screenshot.path)  # List[UIElement]

# 3. Extract ROIs
from advanced_vision.trading.roi import extract_rois
rois = extract_rois(screenshot.path, elements)  # List[ROI]

# 4. Scout classification
from advanced_vision.models import ModelManager
manager = ModelManager()
manager.load_model('eagle2-2b')
scout_result = manager.inference('eagle2-2b', 'Is this trading-relevant?', images=[roi.path])

# 5. Reviewer assessment (if relevant)
if 'trading' in scout_result['output'].lower():
    manager.load_model('qwen3.5-4b')
    review = manager.inference('qwen3.5-4b', 'Analyze risk level:', images=[roi.path])
```

---

## Integration Points

### MCP Server Interface

The system exposes tools via MCP (Model Context Protocol):

```python
# Available tools:
- advanced-vision.screenshot_full
- advanced-vision.screenshot_active_window
- advanced-vision.move_mouse
- advanced-vision.click
- advanced-vision.type_text
- advanced-vision.verify_screen_change
```

### OpenClaw Integration

```python
# From OpenClaw agents
import subprocess

result = subprocess.run(
    ["mcporter", "call", "advanced-vision.screenshot_full"],
    capture_output=True, text=True
)
```

---

## Configuration

### Model Registry (`config/model_registry.json`)

```json
{
  "models": {
    "qwen3.5-4b": {
      "path": "models/Qwen3.5-4B",
      "vram": {"bf16_gb": 8.4},
      "role": "reviewer",
      "residency": "resident"
    }
  }
}
```

---

## Performance Benchmarks (Verified)

| Operation | Time | VRAM Delta |
|-----------|------|------------|
| Screenshot capture | ~100ms | 0 |
| YOLOv8n detection | ~10ms | 0.4GB |
| MobileSAM segment | ~12ms | 0.5GB |
| Eagle2-2B inference | ~300-500ms | 4.0GB |
| Qwen3.5-2B inference | ~500ms-1s | 3.8GB |
| Qwen3.5-4B inference | ~1-2s | 8.4GB |
| Full pipeline | ~2-4s | ~14GB |

---

## Trust Boundaries

The system follows a three-plane architecture:

1. **Control Plane** - Policy/decision making (Kimi)
2. **Capability Plane** - This system (vision + UI control)
3. **Data Plane** - Secrets, credentials (isolated)

**Principle:** `advanced-vision` is a narrow capability service - a hand, not a mind.

---

## Related Documents

- `QUICKSTART.md` - Getting started
- `LIMITATIONS.md` - Known issues
- `VERIFIED_SETUP.md` - Exact working configurations
- `VRAM_USAGE.md` - Detailed VRAM breakdown
- `SEQUENTIAL_LOADING.md` - Loading strategies
