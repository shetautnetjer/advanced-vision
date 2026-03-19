# YOLO Models for UI & Trading — Research Findings

**Date:** 2026-03-18  
**Source:** Perplexity Search (2024-2026 papers/models)

---

## 🎯 UI Element Detection YOLO Models

### 1. Roboflow UI Element Detect (Recommended)
- **URL:** https://universe.roboflow.com/yolo-ui/ui-element-detect-yt5su-xf6rx
- **Classes:** 61 UI elements including:
  - Text Button, Button-filled, Button-Outlined
  - Card, Modal, Switch, Checkbox
  - EditText, TextView, Input
  - Toolbar, Drawer, Bottom_Navigation
  - ImageView, Video, Slider, Spinner
- **Dataset:** Open source, ready to use
- **Use case:** General UI element detection

### 2. foduucom/web-form-ui-field-detection
- **URL:** https://github.com/foduucom/web-form-ui-field-detection
- **Base:** YOLOv8s architecture
- **Classes:** Form fields (Name, Email, Password, Button, Radio, etc.)
- **Training:** 600 web UI images
- **Performance:** 
  - mAP@0.95: 0.52
  - Precision: 0.80
  - Recall: 0.70
  - F1: 0.71
- **Speed:** ~2.5ms inference (T4 TensorRT)

### 3. VINS Dataset + YOLOv5R7s (Research Best)
- **Paper:** "GUI Element Detection Using SOTA YOLO Deep Learning Models" (2024)
- **Dataset:** VINS (Visual Inspection of Native Screenshots)
- **Best Model:** YOLOv5R7s
- **Performance:** 94.7% mAP@0.5 (IoU > 0.5)
- **Classes:** 12 mobile GUI elements
  - Icon, EditText, Image, Text, TextButton
  - Drawer, PageIndicator, UpperTaskBar, etc.
- **GitHub:** https://github.com/shayandaneshvar/gui-element-detection

### 4. Huawei GUI Component Detection
- **Paper:** ELECO 2023
- **Models:** YOLOv8 vs Faster R-CNN
- **Custom Dataset:** 600 mobile app screenshots, 7 classes
- **Results:**
  - YOLOv8: 81% mAP
  - Faster R-CNN: 77% mAP
- **Classes:** EditText, TextView, Button, ImageView, ImageButton, HeaderBar, TextButton

---

## 📈 Trading Pattern Detection YOLO Models

### 1. YOLO + Moving Averages (Buy/Sell Signals)
- **Paper:** Brazilian Symposium on Neural Networks (2024)
- **Innovation:** Combines candlestick patterns + moving average crossovers
- **YOLO Versions Tested:** v3, v8, v9, v11
- **Best:** YOLOv8
- **Performance:**
  - Precision: 0.88
  - Recall: 0.87 (vs 0.69 in previous work = +18%)
  - F1-Score: 0.87
- **Signals:** Buy (golden cross + bullish pattern), Sell (death cross + bearish pattern)
- **Dataset:** 519 NASDAQ images → 1,356 with augmentation

### 2. StockSense — Candlestick Pattern Detection
- **System:** StockSense
- **Model:** YOLOv8 custom trained
- **Patterns Detected:**
  - Hammer, Doji, Engulfing (Bullish/Bearish)
  - Morning Star, Evening Star
- **Performance:**
  - Under 1 second per chart
  - 1000+ test images
  - High precision/recall
- **Integration:** Yahoo Finance data → Chart → YOLO detection

### 3. MetaTrader 5 + YOLOv8 Pattern Detection
- **Source:** MQL5 Article (2025)
- **Model:** foduucom/stockmarket-pattern-detection-yolov8
- **Patterns:**
  - Head and Shoulders (Top/Bottom)
  - Triangles (Ascending/Descending/Symmetrical)
  - Double Top/Bottom
  - Flags, Wedges, Cup and Handle
- **Implementation:**
  - Python + MetaTrader 5 integration
  - Screenshot → YOLO → BMP overlay on chart
  - Real-time detection loop

### 4. YOLO-LITE-V1 for Candlestick Patterns (Stanford)
- **Paper:** Stanford CS231n (2022)
- **Technique:** RGB Gramian Angular Field + YOLO-LITE
- **Focus:** Limited training samples
- **Use case:** Fast pattern detection with small datasets

---

## 🏆 Recommendations for Advanced Vision

### For UI Detection:

**Option A: Quick Win**
- Use **foduucom/web-form-ui-field-detection** (YOLOv8)
- Already trained, ready to use
- Good for forms, buttons, inputs

**Option B: Best Accuracy**
- Train on **VINS dataset** with **YOLOv5R7s**
- 94.7% mAP proven in research
- Requires training but highest accuracy

**Option C: Maximum Coverage**
- Use **Roboflow UI Element Detect**
- 61 classes = most comprehensive
- May need fine-tuning for trading apps

### For Trading Pattern Detection:

**Option A: Proven System**
- Use **foduucom/stockmarket-pattern-detection-yolov8**
- Already detects Head & Shoulders, Triangles, etc.
- Ready to integrate with MetaTrader

**Option B: Custom Signals**
- Train YOLOv8 on candlestick + moving averages
- Follow Brazilian paper methodology
- Golden/Death cross + pattern confirmation

**Option C: Multi-Modal**
- YOLO for pattern detection
- Eagle2-2B for classification/reasoning
- Governor for risk evaluation

---

## 📦 Quick Implementation

```bash
# UI Detection
pip install ultralytics
from ultralytics import YOLO
model = YOLO('foduucom/web-form-ui-field-detection')
results = model('screenshot.png')

# Trading Patterns  
model = YOLO('foduucom/stockmarket-pattern-detection-yolov8')
results = model('chart.png')
```

---

## 🔬 Research Insights

1. **GUI detection ≠ Natural object detection**
   - Elements overlap more
   - Smaller objects
   - Different class distribution
   - YOLOv5R7s > YOLOv8 for GUI specifically

2. **Moving averages improve trading detection**
   - Candlestick alone: 69% recall
   - + Moving averages: 87% recall
   - Double confirmation strategy works

3. **Speed vs Accuracy trade-off**
   - MobileSAM: 12ms, 73% accuracy
   - SAM3: 2921ms, 88% accuracy
   - For real-time: accept lower accuracy

---

## Next Steps

1. **Download and test** foduucom models
2. **Benchmark** on advanced-vision screenshots
3. **Compare** with current Eagle2 + MobileSAM pipeline
4. **Integrate** best performing model into hot path
5. **Train custom** if needed (using VINS or Roboflow datasets)

---

**Bottom Line:** Pre-trained YOLO models exist for both UI and trading. No need to train from scratch — can use existing models and fine-tune if needed.
