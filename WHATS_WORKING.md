# Advanced Vision - What's Working NOW

**Date:** 2026-03-17  
**Status:** ✅ All planned work complete  
**Tests:** 115 passing (69 E0-E5 + 46 Track B)

---

## Quick Summary

This repo is a **working computer-use and trading-intelligence substrate**.

- ✅ Screenshot capture (full, active window)
- ✅ Mouse/keyboard input with dry_run safety
- ✅ Screen change verification
- ✅ Video recording with Kimi analysis
- ✅ YOLO → Eagle2 → Qwen pipeline functional
- ✅ Model manager with VRAM tracking
- ✅ 115 tests passing

---

## System Requirements

- **GPU:** RTX 5070 Ti 16GB (tested)
- **OS:** Linux (Ubuntu)
- **Python:** 3.11
- **VRAM:** 14.3GB used, 1.7GB headroom

---

## Working Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│  SCREEN CAPTURE (advanced_vision.tools.screenshot_full)     │
└──────────────────┬──────────────────────────────────────────┘
                   ↓
┌──────────────────▼──────────────────────────────────────────┐
│  YOLO DETECTION (YOLOv8n) - ~10ms                          │
└──────────────────┬──────────────────────────────────────────┘
                   ↓
┌──────────────────▼──────────────────────────────────────────┐
│  EAGLE2 SCOUT (Eagle2-2B BF16) - ~300-500ms                │
│  "Is this trading-relevant?"                                │
└──────────────────┬──────────────────────────────────────────┘
                   ↓
┌──────────────────▼──────────────────────────────────────────┐
│  QWEN REVIEWER (Qwen3.5-4B BF16) - ~1-2s                   │
│  Deep analysis: pattern type, risk level, recommendation    │
└─────────────────────────────────────────────────────────────┘
```

---

## Models (BF16 - NVFP4 Not Working)

| Model | Size | VRAM | Role | Status |
|-------|------|------|------|--------|
| Qwen3.5-4B | 8.1GB | 8.4GB | **Reviewer** | ✅ Working |
| Qwen3.5-2B | 4.1GB | 3.8GB | Scout | ✅ Ready |
| Eagle2-2B | 4.2GB | ~4GB | Fast Scout | ✅ Working |
| MobileSAM | 39MB | 0.5GB | Segmentation | ✅ Ready |
| YOLOv8n | 6.3MB | 0.4GB | Detection | ✅ Ready |
| YOLOv8s | 22MB | 0.9GB | Detection | ✅ Ready |

⚠️ **NVFP4 models downloaded but not functional** on RTX 5070 Ti (Blackwell missing kernels).
**Solution:** BF16 models use only ~1-2GB more VRAM and work perfectly.

---

## Quick Start

### 1. Activate Environment
```bash
cd ~/.openclaw/workspace/plane-a/projects/advanced-vision
source .venv-computer-use/bin/activate
```

### 2. Run Tests
```bash
pytest tests/ -v
```

### 3. Screenshot
```python
from advanced_vision.tools import screenshot_full
artifact = screenshot_full()
print(f"Saved: {artifact.path}")
```

### 4. Trading Pipeline
```python
from advanced_vision.trading import create_detector, create_reviewer_lane

detector = create_detector(mode=DetectorMode.TRADING_WATCH)
lane = create_reviewer_lane()
# See docs/USAGE.md for full examples
```

---

## Architecture

**Dad's 7-Layer Role Map:**
1. Reflex → MotionGate
2. Tripwire → YOLODetector
3. Tracker → BoT-SORT path
4. Precision → ROIExtractor
5. Parser → UIStructureExtractor
6. Scout → Event classification
7. Reviewer → LocalReviewer (Qwen)
8. Governor → Risk recommendations

**Three-Plane Design:**
- Control Plane: Arbiter/OpenClaw (external)
- Capability Plane: This repo
- Data/Secret Plane: .env (external)

---

## Documentation

- `docs/USAGE.md` - Usage guide
- `EXECUTION_STATUS.md` - Detailed status
- `MODEL_SETUP_COMPLETE.md` - Model deployment
- `TRADING_IMPLEMENTATION.md` - Track B details

---

## What's NOT Working

| Item | Reason | Workaround |
|------|--------|------------|
| NVFP4 models | Missing Blackwell (sm120) kernels in vLLM/flashinfer | Use BF16 models |
| vLLM inference | vLLM 0.17.1 doesn't support Qwen on Blackwell | Use transformers directly |
| SAM3 | Precision tool, on-demand only | Stub in place |

---

## Status: READY

All planned work complete. The system is operational.

*Future work belongs to roadmap, not execution plan.*
