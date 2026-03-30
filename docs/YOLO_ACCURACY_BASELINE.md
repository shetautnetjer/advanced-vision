# YOLO Training Accuracy Baseline

**Project:** Advanced Vision Trading System  
**Document Version:** 1.0  
**Date:** 2026-03-18  
**Author:** Accuracy Documentation Agent  

---

## Purpose

This document establishes a "before and after" accuracy baseline for the YOLO training pipeline. It documents the current state of ROI detection (pre-custom-YOLO) and defines target metrics for Phase 1 P0 training.

---

## Current State (Before Custom YOLO)

### Detection Method

The current pipeline uses a **stub-based detection system** with the following characteristics:

| Component | Implementation | Status |
|-----------|---------------|--------|
| **Primary Detector** | `YOLODetector` class with stub implementation | Dry-run mode only |
| **Model** | YOLOv8n (nano) - referenced but not loaded | Not downloaded |
| **ROI Extraction** | `ROIExtractor` class with rule-based bounding boxes | Functional |
| **Motion Gating** | `MotionGate` with frame differencing | Stub implementation |
| **Cursor Suppression** | `CursorSuppressor` with position tracking | Functional |
| **Tracking** | BoT-SORT (via Ultralytics) - referenced | Not implemented |

**Current Detection Flow:**
```
Capture → MotionGate (stub) → YOLODetector (stub) → CursorSuppression → ROIExtractor
```

The `YOLODetector.detect()` method returns **stub/mock detections** when in dry_run mode (which is the default):
- Simulated chart_panel at screen center (confidence: 0.85)
- Simulated order_ticket_panel at right side (confidence: 0.78)
- Fixed inference time: ~15ms (simulated)

### Performance Metrics (Current)

| Metric | Current Value | Notes |
|--------|---------------|-------|
| **Inference time** | ~15ms (simulated) | Actual would be ~10-50ms with real YOLOv8n |
| **Detection accuracy** | N/A (stub mode) | No real detection being performed |
| **False positive rate** | N/A (stub mode) | No real negatives being processed |
| **ROI quality** | Low | Based on hardcoded positions, not actual detection |
| **mAP@0.5** | N/A | No ground truth evaluation possible |

### Regions Currently Analyzed

The pipeline is **designed** to analyze these regions (from `events.py` UIElementType enum):

| Element Type | Priority | Used By |
|--------------|----------|---------|
| `CHART_PANEL` | High | Eagle2 for chart analysis |
| `ORDER_TICKET_PANEL` | High | Reviewer for order validation |
| `POSITION_PANEL` | Medium | PnL tracking |
| `CONFIRM_MODAL` | Critical | Governor for blocking decisions |
| `WARNING_MODAL` | Critical | Governor for hold decisions |
| `ERROR_MODAL` | Critical | Governor for pause decisions |
| `PNL_WIDGET` | Medium | Position monitoring |
| `PRICE_DISPLAY` | Low | Price tracking |
| `BUTTON` | Low | Action detection |

### Issues Identified (Current System)

1. **No Real Detection**
   - Current YOLO detector runs in `dry_run=True` mode exclusively
   - Returns mock detections with fixed positions
   - No actual inference on screenshots

2. **Generic COCO Classes**
   - If YOLOv8n COCO were loaded, it would detect generic objects (person, car, dog)
   - No trading-specific UI element classes
   - Would require extensive post-processing to map to UI elements

3. **No ROI Quality Guarantee**
   - Stub ROIs are placed at fixed positions
   - Don't adapt to actual UI layout
   - Eagle2 receives irrelevant crops

4. **False Escalation Risk**
   - With stub detections, Eagle2 classifies arbitrary regions
   - High chance of misclassification
   - Triggers unnecessary reviewer/governor escalations

5. **No Small Object Detection**
   - Alert indicators, warning badges not detected
   - Critical for trading safety

6. **Poor Modal Detection**
   - Modals are critical for governor decisions
   - Current stub doesn't simulate modal appearance/disappearance

---

## Target State (After Phase 1 P0 Training)

### Expected Improvements

1. **Accurate Region Detection**
   - Custom YOLO trained on 6 P0 classes
   - Actual bounding boxes based on visual features
   - Adapts to different UI layouts and themes

2. **Better ROI Quality for Eagle**
   - Tight bounding boxes around relevant regions
   - Consistent crop quality across different platforms
   - Reduced noise in Eagle2 input

3. **Reliable Modal Detection**
   - `confirm_modal` class specifically trained
   - Detects blocking dialogs that require governor attention
   - Distinguishes from passive notifications

4. **Alert Indicator Recognition**
   - Small but critical `alert_indicator` class
   - Warning badges, margin call indicators
   - Early warning system for risk conditions

5. **Reduced False Escalations**
   - Accurate detection reduces Eagle misclassification
   - Governor receives higher-quality evidence
   - Fewer unnecessary pauses/holds

### Target Metrics

| Metric | Target | Current | Improvement |
|--------|--------|---------|-------------|
| **mAP@0.5** | > 0.75 | N/A | Establish baseline |
| **mAP@0.75** | > 0.60 | N/A | Tighter localization |
| **Inference** | < 50ms | ~15ms (stub) | Real inference within budget |
| **False Positive Rate** | < 5% | N/A | Reduced noise |
| **False Negative Rate** | < 10% | N/A | Catch critical UI |
| **Eagle ROI Quality** | Better relevance | Low | Meaningful crops |
| **Escalation Reduction** | -30% | Baseline | Fewer false alarms |

### P0 Class-Specific Targets

| Class | Target mAP@0.5 | Critical For | Failure Mode |
|-------|----------------|--------------|--------------|
| `chart_panel` | > 0.80 | Eagle chart analysis | Missed chart updates |
| `order_ticket` | > 0.75 | Order validation | Unvalidated orders |
| `primary_action_button` | > 0.70 | Action confirmation | Wrong button clicks |
| `confirm_modal` | > 0.85 | Governor blocking | Missed confirmations |
| `alert_indicator` | > 0.65 | Risk warnings | Missed margin calls |
| `position_panel` | > 0.75 | PnL tracking | Stale position data |

### Success Criteria

1. **Fewer False Escalations to Reviewer**
   - **Metric:** Escalation rate reduction of 30%+
   - **Measurement:** Compare `escalated_to_overseer=true` events before/after
   - **Target:** < 20% of events escalated (vs current stub-based unknown rate)

2. **Better ROI Quality for Eagle Classification**
   - **Metric:** Eagle2 classification accuracy improvement
   - **Measurement:** Compare Eagle2 accuracy on YOLO-derived ROIs vs stub ROIs
   - **Target:** > 85% classification accuracy on P0-class ROIs

3. **Faster Correct Screen Understanding**
   - **Metric:** End-to-end pipeline latency
   - **Measurement:** Time from capture to governor verdict
   - **Target:** < 500ms total (YOLO < 50ms, Eagle < 500ms)

4. **Reliable Modal Detection**
   - **Metric:** Modal detection recall
   - **Measurement:** % of actual modals detected
   - **Target:** > 90% recall for confirm_modal

5. **Acceptable False Positive Rate**
   - **Metric:** Detections per frame on negative examples
   - **Measurement:** Average detections on "nothing changed" frames
   - **Target:** < 0.5 false detections per negative frame

---

## Downstream Impact Analysis

### Eagle2-2B Scout Lane

**Current:**
- Receives stub ROIs at fixed positions
- Classifies arbitrary image regions
- Confidence varies based on irrelevant content

**After P0 YOLO:**
- Receives focused crops of actual chart/ticket/modal regions
- Consistent input quality across sessions
- Higher classification confidence
- Expected accuracy improvement: 15-20%

### Governor Policy Layer

**Current:**
- Receives classifications based on stub detections
- Risk assessments may not match actual UI state
- Verdicts based on incomplete evidence

**After P0 YOLO:**
- Classifications based on actual detected regions
- Risk levels aligned with real UI elements
- More accurate HOLD/PAUSE/CONTINUE decisions
- Expected false block reduction: 25-30%

### Reviewer (Qwen) Lane

**Current:**
- May receive escalations based on misclassifications
- Wastes compute on irrelevant regions
- High uncertainty due to poor input quality

**After P0 YOLO:**
- Relevant ROIs only
- Better context for judgment
- Lower uncertainty rate
- Expected escalation reduction: 30%+

---

## Measurement Methodology

### Before State (Current)

1. **Baseline Recording**
   - Run current pipeline on test screenshot set
   - Record all stage outputs
   - Document stub detection behavior

2. **Synthetic Evaluation**
   - Create ground truth annotations for test set
   - Measure stub detector "accuracy" (will be poor)
   - Establish baseline for comparison

### After State (Post-Training)

1. **mAP Evaluation**
   ```bash
   yolo detect val model=yolov8n-p0.pt data=data_phase1_p0.yaml
   ```
   - Report mAP@0.5, mAP@0.75 per class
   - Compare against targets in table above

2. **Inference Benchmark**
   ```bash
   pytest tests/benchmarks/test_pipeline_latency.py -v
   ```
   - Measure YOLO stage latency
   - Verify < 50ms target

3. **End-to-End Testing**
   - Run full pipeline on test scenarios
   - Measure escalation rates
   - Compare Eagle classification accuracy

4. **False Positive Testing**
   - Run on negative examples (no UI changes)
   - Count false detections
   - Verify < 5% FP rate

---

## Risk Assessment

### If Targets Are Not Met

| Scenario | Impact | Mitigation |
|----------|--------|------------|
| mAP@0.5 < 0.75 | Poor detection quality | Add more training data, augment |
| Inference > 50ms | Pipeline latency increase | Use YOLOv8n (nano) not s/m/l |
| FP rate > 5% | Reviewer spam | Increase confidence threshold |
| FN rate > 10% | Missed critical UI | Add hard negatives, retrain |

### Critical Dependencies

1. **Training Data Quality**
   - Requires 100+ labeled screenshots per class
   - Must split by session, not frame
   - Negative examples essential

2. **Annotation Consistency**
   - Tight bounding boxes required
   - Consistent class definitions
   - Reviewer arbitration for edge cases

3. **Hardware Compatibility**
   - YOLOv8n runs on RTX 5070 Ti (verified)
   - 0.4GB VRAM budget available
   - TensorRT optimization possible later

---

## Appendix: Class Definitions (P0)

### 0: chart_panel
Main price chart area (candlesticks, lines, volume). Full chart region including price axis.

### 1: order_ticket
Buy/Sell order entry panel. Full ticket panel with all fields, market/limit selectors, price/quantity inputs.

### 2: primary_action_button
Main CTA — the button that triggers the key action. "Buy", "Sell", "Close Position", "Confirm", "Place Order" buttons.

### 3: confirm_modal
Confirmation dialogs, popups, alerts that block the flow. "Are you sure?" dialogs, order confirmations, error/warning popups.

### 4: alert_indicator
Warning badges, notification dots, status indicators. Red warning triangles, "Margin Call" badges, connection lost indicators.

### 5: position_panel
Open positions widget, PnL display, trade list. "Positions" tab content, open trade list with PnL, current exposure summary.

---

## References

- [YOLO Training Config](../yolo_training/data_phase1_p0.yaml)
- [Annotation Guide P0](../yolo_training/ANNOTATION_GUIDE_P0.md)
- [Pipeline Stages](../src/advanced_vision/trading/pipeline_stages.py)
- [Detector Module](../src/advanced_vision/trading/detector.py)
- [YOLO Benchmark Methodology](YOLO_BENCHMARK_METHODOLOGY.md)

---

*Document generated by Accuracy Documentation Agent*  
*Part of advanced-vision YOLO training preparation*
