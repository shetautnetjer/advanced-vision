# Quick Start Guide - Advanced Vision Trading System

This is a secondary, model-heavy setup guide. For the current day-to-day local
computer-use runtime, start with `../README.md` and `../COMPUTER_USE_ENV.md`.

**Last Verified:** 2026-03-17  
**Hardware:** NVIDIA RTX 5070 Ti 16GB  
**Status:** ✅ Working Configuration

---

## Prerequisites

```bash
# Ubuntu/Debian dependencies
sudo apt-get install -y python3.11-tk scrot ffmpeg

# Verify X11 (Wayland not supported)
echo $XDG_SESSION_TYPE  # Must print: x11
```

---

## 1. Environment Setup

```bash
cd "/home/netjer/Projects/AI Frame/optical.nerves/advanced-vision"
source .venv-computer-use/bin/activate

# Verify Python environment
python --version  # Python 3.11.x
```

---

## 2. Tested Working Models

| Model | Path | VRAM | Status | Role |
|-------|------|------|--------|------|
| **Qwen3.5-4B (BF16)** | `models/Qwen3.5-4B/` | 8.4GB | ✅ Working | Reviewer |
| **Qwen3.5-2B (BF16)** | `models/Qwen3.5-2B/` | 3.8GB | ✅ Ready | Scout |
| **Eagle2-2B** | `models/Eagle2-2B/` | ~4GB | ⚠️ flash-attn compiling | Fast Scout |
| **MobileSAM** | `models/MobileSAM/` | 0.5GB | ✅ Ready | Segmentation |
| **YOLOv8n** | `models/yolov8n.pt` | 0.4GB | ✅ Ready | Detection |
| **YOLOv8s** | `models/yolov8s.pt` | 0.9GB | ✅ Ready | Detection |

**Total Working Set:** ~14GB / 16GB VRAM

---

## 3. Quick Tests

### Test Qwen3.5-4B (Reviewer)

```python
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

model = AutoModelForCausalLM.from_pretrained(
    'models/Qwen3.5-4B',
    torch_dtype=torch.bfloat16,
    device_map='cuda',
    trust_remote_code=True
)
tokenizer = AutoTokenizer.from_pretrained('models/Qwen3.5-4B', trust_remote_code=True)

# Test inference
inputs = tokenizer('Analyze this chart pattern:', return_tensors='pt').to('cuda')
outputs = model.generate(**inputs, max_new_tokens=50)
print(tokenizer.decode(outputs[0]))
```

**Expected:** Model loads in ~10s, inference ~1-2s for 50 tokens.

---

### Test Qwen3.5-2B (Scout)

```python
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

model = AutoModelForCausalLM.from_pretrained(
    'models/Qwen3.5-2B',
    torch_dtype=torch.bfloat16,
    device_map='cuda',
    trust_remote_code=True
)
tokenizer = AutoTokenizer.from_pretrained('models/Qwen3.5-2B', trust_remote_code=True)

# Test inference (faster)
inputs = tokenizer('Quick check:', return_tensors='pt').to('cuda')
outputs = model.generate(**inputs, max_new_tokens=30)
print(tokenizer.decode(outputs[0]))
```

**Expected:** Model loads in ~5s, inference ~500ms-1s for 30 tokens.

---

### Test YOLO Detection

```python
from ultralytics import YOLO

# Load YOLOv8n (fastest)
model = YOLO('models/yolov8n.pt')

# Test on screenshot
results = model('artifacts/screens/full_2026-03-17T10-30-00.png')
print(f"Detected {len(results[0].boxes)} objects")
```

**Expected:** ~10ms inference time per image.

---

### Test Model Manager

```python
from advanced_vision.models import ModelManager

# Initialize manager
manager = ModelManager(project_root='.', dry_run=False)

# Check status
manager.print_status()

# Load specific model
manager.load_model('qwen3.5-2b-nvfp4')  # Uses BF16 fallback

# Get VRAM stats
stats = manager.get_vram_stats()
print(f"Available VRAM: {stats.available_gb:.1f}GB")
```

---

## 4. Running the Trading Pipeline

### Full Pipeline (Verified Working)

```python
from advanced_vision.trading.reviewer import create_reviewer_lane
from advanced_vision.trading.events import TradingEvent, TradingEventType

# Create reviewer lane
lane = create_reviewer_lane(dry_run=True)

# Create test event
event = TradingEvent(
    event_id="test-001",
    event_type=TradingEventType.CHART_UPDATE,
    timestamp="2026-03-17T20:00:00",
    confidence=0.85,
    summary="Price moved up 2%",
)

# Process through reviewer
result = lane.process_event(event, dry_run=True)
print(f"Risk Level: {result.reviewer_assessment.risk_level}")
print(f"Recommendation: {result.reviewer_assessment.recommendation}")
```

---

## 5. Screenshots & Computer Use

```python
from advanced_vision.tools import screenshot_full, move_mouse, click

# Capture full screen
artifact = screenshot_full()
print(f"Saved: {artifact.path}")

# Move mouse (dry_run for safety)
result = move_mouse(500, 500, dry_run=True)
print(result.message)

# Click (dry_run)
result = click(960, 600, button="left", dry_run=True)
```

---

## 6. Using from CLI (mcporter)

```bash
# Screenshot
mcporter call advanced-vision.screenshot_full

# Move mouse (dry run)
mcporter call advanced-vision.move_mouse x=100 y=200 dry_run=true

# Click
mcporter call advanced-vision.click x=500 y=500 button=left
```

---

## 7. VRAM Monitoring

```bash
# Real-time GPU monitoring
watch -n 0.5 nvidia-smi

# Python VRAM check
python -c "
import torch
print(f'Allocated: {torch.cuda.memory_allocated()/1e9:.2f}GB')
print(f'Reserved:  {torch.cuda.memory_reserved()/1e9:.2f}GB')
print(f'Max:       {torch.cuda.max_memory_allocated()/1e9:.2f}GB')
"
```

---

## 8. What Works Right Now

✅ **Verified Working:**
- Qwen3.5-4B and Qwen3.5-2B in BF16 mode
- YOLOv8n/s detection
- MobileSAM segmentation
- Screenshot capture
- Mouse/keyboard control (dry_run and live)
- Model manager with VRAM tracking
- Reviewer lane (stub mode, rule-based)

⚠️ **In Progress:**
- Eagle2-2B (waiting on flash-attn compile)
- Full inference pipeline (stub → real models)

❌ **Not Working (See LIMITATIONS.md):**
- NVFP4 quantization on RTX 5070 Ti
- vLLM serving

---

## Troubleshooting

### "CUDA out of memory"
```python
# Use 2B instead of 4B
model = AutoModelForCausalLM.from_pretrained('models/Qwen3.5-2B', ...)

# Or clear cache
import torch
torch.cuda.empty_cache()
```

### "Model not found"
```bash
# Verify model exists
ls -lh models/Qwen3.5-4B/model.safetensors*

# If missing, models are NOT in git (see .gitignore)
# They must be downloaded separately
```

### "X11 display error"
```bash
# Check display
export DISPLAY=:1  # or :0
echo $DISPLAY

# For SSH, use X11 forwarding
ssh -X user@host
```

---

## Next Steps

1. Test individual components above
2. Verify VRAM usage stays under 14GB
3. Review `ARCHITECTURE.md` for pipeline flow
4. Check `LIMITATIONS.md` for known issues
5. See `VERIFIED_SETUP.md` for exact working configurations
