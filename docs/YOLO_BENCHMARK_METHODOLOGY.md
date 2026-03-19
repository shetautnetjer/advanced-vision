# YOLO Benchmarking for AI Agents — Research-Based Methodology

**Date:** 2026-03-18  
**Sources:** YOLOBench, NEBULA, Galileo, embedded vision frameworks

---

## The Core Problem

Testing YOLO in isolation ≠ testing YOLO as part of an AI agent.

**Traditional benchmarks:** mAP on COCO dataset  
**Agent benchmarks:** What can it perceive? When does it fail? How fast?

---

## Dual-Axis Evaluation (from NEBULA)

### Axis 1: Capability Tests — "What can YOLO detect?"

Test YOLO's perception capabilities in isolation:

| Test | Purpose | Metric |
|------|---------|--------|
| **UI Element Detection** | Buttons, forms, modals, dropdowns | Precision/Recall per class |
| **Trading Pattern Detection** | Candlesticks, support/resistance | mAP@0.5, mAP@0.75 |
| **Chart Component Isolation** | Chart area, ticket panel, indicators | IoU accuracy |
| **Small Object Detection** | Alerts, icons, text elements | mAP@small |
| **Occlusion Handling** | Overlapping UI elements | Recall under occlusion |
| **Low-Light/Contrast** | Dim screens, dark mode | Precision degradation |

### Axis 2: Stress Tests — "When does YOLO break?"

Test YOLO's robustness under agent operational pressure:

| Test | Purpose | Metric |
|------|---------|--------|
| **Inference Frequency** | Max frames/sec sustained | FPS stability |
| **Latency Under Load** | Delay from perception to action | End-to-end latency |
| **Resolution Scaling** | 1080p vs 720p vs 480p | Accuracy vs speed trade-off |
| **Batch vs Stream** | Single frame vs video stream | Throughput (FPS) |
| **Hardware Constraints** | CPU vs GPU vs edge device | Energy efficiency (FPS/watt) |
| **Concurrent Agents** | Multiple YOLO instances | Resource contention |

---

## Key Metrics (from YOLOBench & Galileo)

### 1. Detection Quality
```
mAP@0.50      = Mean Average Precision at IoU > 0.50 (standard)
mAP@0.75      = Stricter localization (tighter bounding boxes)
mAP@0.5:0.95  = Average across IoU thresholds (comprehensive)
mAP@small     = Performance on small objects (critical for UI)
```

### 2. Speed Metrics
```
Inference time = Time per frame (ms)
FPS            = Frames per second sustained
Latency        = Perception → Action delay (ms)
Throughput     = Total images processed per minute
```

### 3. Resource Efficiency
```
VRAM usage     = GPU memory consumption (GB)
Power draw     = Watts during inference
FPS/watt       = Energy efficiency (from embedded frameworks)
```

### 4. Agent-Specific Metrics
```
Tool selection accuracy = % correct detections leading to correct actions
Instruction adherence   = Does detection match expected UI element?
Golden flow match       = Does YOLO path match validated perception path?
Failure mode detection  = Type of errors (FP, FN, misclassification)
```

---

## Testing Methodology

### Phase 1: Capability Baseline (Static)

```python
# 1. Ground truth dataset
# Create labeled screenshots with bounding boxes for:
# - 100 UI elements (buttons, forms, modals)
# - 50 trading patterns (support, resistance, breakout)
# - 25 chart components (candlesticks, indicators)

# 2. Run YOLO inference
results = model(test_images)

# 3. Calculate metrics
for iou_threshold in [0.5, 0.75, 0.95]:
    precision, recall = calculate_metrics(results, ground_truth, iou_threshold)
    mAP = calculate_map(results, ground_truth, iou_threshold)
    
# 4. Per-class analysis
for class in ["button", "modal", "chart_area", "ticket_panel"]:
    class_precision = precision_per_class(results, class)
    class_recall = recall_per_class(results, class)
```

### Phase 2: Stress Testing (Dynamic)

```python
# 1. Video stream test
video = load_video("screen_recording.mp4")
for frame in video:
    start = time.time()
    detection = model(frame)
    latency = time.time() - start
    
    # Track over time
    latencies.append(latency)
    
# 2. Calculate stability
avg_latency = mean(latencies)
p95_latency = percentile(latencies, 95)
p99_latency = percentile(latencies, 99)
std_dev = stdev(latencies)

# 3. Detect failure cliffs
if p99_latency > 2 * avg_latency:
    print("⚠️ Failure cliff detected — performance degrades under load")
```

### Phase 3: Agent Integration Test

```python
# 1. Full pipeline timing
timeline = {
    "capture": 0,
    "yolo_detection": 0,
    "roi_extraction": 0,
    "eagle_classification": 0,
    "governor_decision": 0,
    "action_execution": 0
}

# 2. Golden flow validation
expected_flow = ["capture", "yolo", "eagle", "governor", "action"]
actual_flow = trace_execution(pipeline)
assert actual_flow == expected_flow, "Agent deviated from golden path"

# 3. Error injection
test_cases = [
    ("blank_screen", expected_action="no_detection"),
    ("rapid_changes", expected_action="suppress_noise"),
    ("ambiguous_ui", expected_action="escalate_to_reviewer"),
]
```

---

## Benchmark Frameworks to Use

### 1. YOLOBench Approach
- **550+ model variations** across 4 datasets
- **4 hardware platforms**: x86 CPU, ARM CPU, Nvidia GPU, NPU
- **Pareto frontier analysis**: Find optimal accuracy-latency trade-offs
- **Zero-cost proxies**: NWOT estimator for quick model selection

### 2. NEBULA Approach (for Agent Evaluation)
- **Capability tests**: Isolate specific perception skills
- **Stress tests**: Measure robustness under pressure
- **Fine-grained diagnostics**: Pinpoint failure modes
- **Multi-axis evaluation**: Don't rely on single success rate

### 3. Real-Time Embedded Framework
- **MQTT-based**: Distribute video data, collect results
- **Multi-device**: Test on Jetson, Raspberry Pi, desktop GPU
- **Power measurement**: FPS/watt efficiency
- **Hardware-specific optimization**: TensorRT, Vitis AI

---

## Recommended Test Suite for Advanced Vision

### Test 1: UI Element Detection Capability
```
Dataset: 100 labeled screenshots (Roboflow UI Elements)
Classes: button, modal, form, dropdown, checkbox, text_input
Metric: mAP@0.5 per class, mAP@small
Target: mAP > 0.70 for critical classes (button, modal)
```

### Test 2: Trading Pattern Detection Capability
```
Dataset: 50 labeled chart screenshots
Classes: support_line, resistance_line, breakout, consolidation
Metric: mAP@0.75 (tighter bounds for precise trading)
Target: Precision > 0.85 (avoid false signals)
```

### Test 3: Video Stream Stress Test
```
Input: 5-minute screen recording at 30 FPS
Test: Sustained inference, measure stability
Metric: FPS consistency, p95/p99 latency
Target: >20 FPS sustained, p99 latency <100ms
```

### Test 4: Golden Flow Validation
```
Scenario: Modal dialog appears
Expected: YOLO detects modal → Eagle classifies → Governor allows → Action clicks OK
Validate: Each stage produces expected output
Metric: End-to-end latency, correct action
Target: <5s total, 100% correct action
```

### Test 5: Failure Mode Analysis
```
Inject: Blank screen, rapid cursor movement, overlapping windows
Observe: False positives, missed detections, confidence scores
Metric: FP rate, FN rate per scenario
Target: FP < 5% on noise, FN < 10% on valid UI
```

---

## Implementation Plan

### Immediate (Today)
1. Create labeled test dataset from `artifacts/screens/`
2. Run YOLOv8n capability test
3. Measure baseline mAP@0.5

### Short-term (This Week)
1. Implement stress test harness
2. Test on video stream
3. Measure FPS/latency stability

### Medium-term (Next Sprint)
1. Full golden flow validation
2. Compare YOLOv8n vs foduucom UI model
3. Energy efficiency testing (FPS/watt)

---

## Key Insights from Research

1. **Speed vs Accuracy is not linear**
   - YOLOv10n: 381 FPS, 85.7% mAP
   - YOLOv8n: 336 FPS, 85.6% mAP  
   - YOLOv12n: 278 FPS, 80.8% mAP (smallest but slowest!)

2. **IoU threshold matters**
   - mAP@0.5 = Easy (loose bounds)
   - mAP@0.75 = Standard (tight bounds)
   - mAP@0.95 = Hard (pixel-perfect)

3. **Small objects are hardest**
   - Alerts, icons, text elements
   - Require mAP@small metric

4. **Fast inference = dynamic adaptation**
   - NEBULA: "Fast inference is key to dynamic adaptation"
   - Latency > 100ms breaks real-time loops

---

## Bottom Line

Don't just test YOLO accuracy on COCO.
Test YOLO **as part of the agent**:
- What can it perceive? (Capability)
- When does it break? (Stress)
- How fast? (Latency)
- With what energy? (Efficiency)

This is agent benchmarking, not model benchmarking.
