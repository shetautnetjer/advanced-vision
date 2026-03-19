# Baseline Computer Use Approach

## Philosophy

**Use fewer models, get baseline working first.**

Instead of:
- YOLO → Eagle → Qwen → Governor (complex stack)

Start with:
- Basic capture → Simple YOLO → Action

## Current Baseline

### What Works Now
1. **Screen capture** — `gnome-screenshot`, `import`, or Python `mss`
2. **Basic YOLO** — Currently stub/dry_run mode (not real inference)
3. **Mock detections** — Fixed positions, not adaptive

### What's Missing
- Real YOLO inference on trading UI
- Adaptive ROI detection
- Connection to Eagle for classification

## Minimal Viable Pipeline

```
Screen Capture
      ↓
YOLO Detection (6 P0 classes)
      ↓
ROI Extraction
      ↓
Basic Action Logic
```

No Eagle, no Qwen, no Governor for baseline.
Just: Can YOLO find the chart? Can it find the button?

## Capture Tools Created

### 1. Interactive Python Tool
```bash
python3 tools/capture_trading_screenshots.py
```
- Single capture
- Sequence capture  
- State-labeled capture (buy, sell, alert, etc.)

### 2. Quick Bash Script
```bash
./tools/quick_capture.sh 20 3  # 20 screenshots, 3s delay
```

### 3. Prerequisites
```bash
# Option 1: gnome-screenshot
sudo apt install gnome-screenshot

# Option 2: ImageMagick
sudo apt install imagemagick

# Option 3: Python (best)
pip install mss pillow
```

## Workflow

### Step 1: Capture Screenshots
```bash
# Open your trading platform (TradingView, MetaTrader, etc.)
# Navigate to different states:
#   - Normal chart view
#   - Buy order screen
#   - Sell order screen
#   - Position open
#   - Alert showing

./tools/quick_capture.sh 30 2
```

### Step 2: Label (Manual)
```bash
pip install labelImg
labelImg yolo_training/annotations/raw_images/
```

Draw boxes for 6 P0 classes:
- chart_panel
- order_ticket
- primary_action_button
- confirm_modal
- alert_indicator
- position_panel

### Step 3: Split by Session
```bash
./yolo_training/apply_split.sh
```

### Step 4: Train
```bash
./yolo_training/train_phase1_p0.sh
```

### Step 5: Test Baseline
```python
from ultralytics import YOLO

model = YOLO('yolo_training/runs/phase1_p0_nano/weights/best.pt')
results = model('test_screenshot.png')

# Just see if it finds the regions
for box in results[0].boxes:
    print(f"Found: {model.names[int(box.cls)]} at {box.xyxy}")
```

## Success Criteria (Baseline)

| Metric | Target | Why |
|--------|--------|-----|
| Detection rate | >80% | Finds regions most of the time |
| False positives | <10% | Doesn't spam wrong regions |
| Inference | <100ms | Fast enough for real-time |
| Manual effort | Low | Easy to label, easy to verify |

## Next Steps After Baseline

Once baseline YOLO works:
1. **Add Eagle** — Classify what's in the ROIs
2. **Add Governor** — Policy decisions on detections
3. **Add Qwen** — Deep review when needed

But get baseline working first.

## Tools Created

- `tools/capture_trading_screenshots.py` — Interactive capture
- `tools/quick_capture.sh` — Quick batch capture
- `yolo_training/` — Complete training pipeline

## Login Challenge

**The hard part:** Most trading platforms require login.

**Options:**
1. **Demo accounts** — Most platforms have free demo mode
2. **Web platforms** — TradingView web doesn't need install
3. **Manual capture** — You login, we capture
4. **Browser automation** — Selenium/Playwright (future)

For now: **Manual login + automated capture** is the practical path.

## Immediate Next Step

1. Open trading platform (TradingView, MetaTrader, etc.)
2. Login to demo account
3. Run: `./tools/quick_capture.sh 50 2`
4. Label with: `labelImg yolo_training/annotations/raw_images/`
5. Train with: `./yolo_training/train_phase1_p0.sh`

That's the baseline. ✊🏾
