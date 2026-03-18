# Trading Watcher Stack

> **7-Layer Vision Pipeline + Governor for Trading Surveillance**
> 
> A sub-5s latency event detection and decision system for live trading environments.

---

## The Stack

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│  Reflex │───▶│ Tripwire│───▶│Precision│───▶│  Parser │───▶│  Scout  │───▶│ Reviewer│───▶│ Overseer│───▶│ Governor│
│ (Motion)│    │  (YOLO) │    │  (SAM)  │    │  (UI)   │    │ (Eagle) │    │  (Qwen) │    │  (Kimi) │    │(Policy) │
└─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘
    │              │              │              │              │              │              │              │
   5ms            10ms           50ms          100ms          400ms          1-2s          2-3s          3-5s
```

### Layer Responsibilities

| Layer | Component | Latency | Purpose |
|-------|-----------|---------|---------|
| **Reflex** | Motion Detection | 5ms | Trigger on any pixel change |
| **Tripwire** | YOLO Object Detection | 10ms | Classify objects, establish bounding boxes |
| **Precision** | MobileSAM | 50ms | Precise segmentation when triggered |
| **Parser** | UI Parser | 100ms | Extract text/numbers from UI elements |
| **Scout** | Eagle2-2B | 400ms | "What changed?" — visual state diff |
| **Reviewer** | Qwen3.5-4B | 1-2s | "What does this mean?" — semantic interpretation |
| **Overseer** | Kimi (Escalation) | 2-3s | "Do I agree?" — validation & override |
| **Governor** | Policy Engine | 3-5s | "Is action allowed?" — final gate |

---

## Exact Trading Lane

The hot path for trading-critical events:

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Frame Input │────▶│ YOLO Detect  │────▶│ BoT-SORT     │────▶│  Trigger     │
│   (Camera)   │     │   (10ms)     │     │  Tracking    │     │  Check       │
└──────────────┘     └──────────────┘     └──────────────┘     └──────┬───────┘
                                                                      │
                                                                      ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Governor   │◀────│    Kimi      │◀────│    Qwen      │◀────│ MobileSAM    │
│    Gate      │     │  Overseer    │     │  Reviewer    │     │  (Precision) │
│  (Policy)    │     │"Do I agree?" │     │"What does    │     │              │
└──────────────┘     └──────────────┘     │ this mean?"  │     └──────────────┘
                                          └──────────────┘
                                                  ▲
┌─────────────────────────────────────────────────┘
│
▼
┌──────────────┐
│ Eagle2-2B    │
│   Scout      │
│"What changed?"│
└──────────────┘
```

### Stage Breakdown

1. **YOLO Detection** (10ms)
   - Fast object detection for UI elements, charts, popups
   - Output: Bounding boxes + class labels

2. **BoT-SORT Tracking** (hot path)
   - Persistent tracking across frames
   - Assigns IDs to detected objects
   - Filters noise, maintains continuity

3. **MobileSAM on Trigger** (precision)
   - Activated on significant state change
   - Pixel-perfect segmentation of regions of interest

4. **Eagle2-2B Scout** (400ms)
   - Vision encoder analyzes visual changes
   - Question: "What changed compared to last frame?"
   - Output: Structured diff description

5. **Qwen3.5-4B Reviewer** (1-2s)
   - Language model interprets the visual diff
   - Question: "What does this mean for the trade?"
   - Output: Risk assessment + recommended action

6. **Kimi Overseer** (escalation)
   - Final validation layer
   - Question: "Do I agree with this assessment?"
   - Can override, request re-analysis, or escalate

7. **Governor Gate** (policy enforcement)
   - Question: "Is this action allowed?"
   - Applies risk limits, trading rules, compliance
   - Final yes/no with logging

---

## Governor Decision Matrix

The Governor applies this decision framework to every event:

| Risk Level | Criteria | Action | Log Level |
|------------|----------|--------|-----------|
| **none** | Normal UI operation, no position impact | `continue` | INFO |
| **low** | Minor UI change, monitored but safe | `note` | INFO |
| **medium** | Notable change, requires attention | `warn` | WARNING |
| **high** | Significant risk to position/PnL | `hold` | ERROR |
| **critical** | Account-threatening event | `pause / escalate` | CRITICAL |

### Decision Flow

```
                    ┌─────────────────┐
                    │   Event Input   │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  Risk Assessment│
                    │   (Qwen/Kimi)   │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
        ┌─────────┐    ┌─────────┐    ┌─────────┐
        │  none   │    │   low   │    │ medium  │
        │  /low   │    │         │    │         │
        └────┬────┘    └────┬────┘    └────┬────┘
             │              │              │
             ▼              ▼              ▼
        ┌─────────┐    ┌─────────┐    ┌─────────┐
        │ continue│    │  note   │    │  warn   │
        │ (pass)  │    │ (log)   │    │ (alert) │
        └─────────┘    └─────────┘    └─────────┘

              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
        ┌─────────┐    ┌─────────┐    ┌─────────┐
        │  high   │    │ critical│    │ unknown │
        │         │    │         │    │         │
        └────┬────┘    └────┬────┘    └────┬────┘
             │              │              │
             ▼              ▼              ▼
        ┌─────────┐    ┌─────────┐    ┌─────────┐
        │  hold   │    │ pause / │    │  hold   │
        │(block)  │    │escalate │    │(manual) │
        └─────────┘    └─────────┘    └─────────┘
```

---

## Schema Routing

Events are routed through the stack based on their type and urgency.

### Event Types

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           INCOMING EVENT                                    │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │                           │
                    ▼                           ▼
           ┌─────────────┐             ┌─────────────┐
           │  UI Event   │             │Trading Event│
           │             │             │             │
           └──────┬──────┘             └──────┬──────┘
                  │                           │
                  ▼                           ▼
        ┌─────────────────┐         ┌─────────────────┐
        │  Reflex Layer   │         │  Full Pipeline  │
        │  (Motion Only)  │         │  (All Layers)   │
        └────────┬────────┘         └────────┬────────┘
                 │                           │
                 ▼                           ▼
        ┌─────────────────┐         ┌─────────────────┐
        │  UI Parser      │         │  YOLO Detection │
        │  (Quick Check)  │         │  (Full Stack)   │
        └────────┬────────┘         └────────┬────────┘
                 │                           │
                 ▼                           ▼
        ┌─────────────────┐         ┌─────────────────┐
        │  Update State   │         │  Risk Analysis  │
        │  (No Alert)     │         │  + Governor     │
        └─────────────────┘         └────────┬────────┘
                                             │
                              ┌──────────────┼──────────────┐
                              │              │              │
                              ▼              ▼              ▼
                        ┌─────────┐    ┌─────────┐    ┌─────────┐
                        │  Pass   │    │  Hold   │    │ Escalate│
                        │         │    │         │    │         │
                        └─────────┘    └─────────┘    └─────────┘
```

### Routing Rules

| Event Source | Examples | Route | Priority |
|--------------|----------|-------|----------|
| **UI Update** | Price tick, chart refresh | Reflex → Parser → State | Low |
| **Alert Popup** | Margin call, order fill | Full Stack | High |
| **Price Spike** | Rapid PnL change | Full Stack + Immediate | Critical |
| **Order Book** | Large market order | Tripwire → Parser | Medium |
| **News Feed** | Breaking headline | Scout → Reviewer | Medium |

---

## Performance Targets

### Latency Budget

| Component | Target | Max | Notes |
|-----------|--------|-----|-------|
| **YOLO** | <50ms | 100ms | Local GPU inference |
| **Eagle** | <500ms | 800ms | VLM encoding + decode |
| **Qwen** | <2s | 3s | 4B parameter model |
| **Kimi** | <3s | 5s | Escalation only |
| **Governor** | <5s | 10s | Policy lookup + decision |

### Total Pipeline Budget

```
┌────────────────────────────────────────────────────────────┐
│                    TOTAL PIPELINE: <5s                      │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  YOLO (10ms) ──────────────────────────────────────────────│
│  BoT-SORT ─────────────────────────────────────────────────│
│  MobileSAM ────────────────────────────────────────────────│
│  Eagle Scout (400ms) ──────────────────────────────────────│
│  Qwen Reviewer (1000ms) ───────────────────────────────────│
│  Kimi Overseer (2000ms) ───────────────────────────────────│
│  Governor (500ms) ─────────────────────────────────────────│
│                                                            │
│  Fast Path: YOLO → BoT-SORT → Governor = ~100ms            │
│  Full Path: All layers = ~4s                               │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### Optimization Notes

- **Hot path** skips Scout/Reviewer for known-safe events
- **Batching** allows multiple frames per Eagle call
- **Caching** previous Qwen responses for similar events
- **Early exit** on Governor `hold` decisions

---

## Example Event Flow

### Scenario: Sudden Price Drop Detected

```
T+0ms     ┌─────────────────────────────────────────────────────────┐
          │ Frame captured: Chart shows -5% candle                  │
          └─────────────────────────────────────────────────────────┘
                    │
                    ▼
T+10ms    ┌─────────────────────────────────────────────────────────┐
          │ [YOLO] Detects: Chart region, Price label, Alert banner │
          │ Output: bbox_chart=[x,y,w,h], class="price_chart"       │
          └─────────────────────────────────────────────────────────┘
                    │
                    ▼
T+20ms    ┌─────────────────────────────────────────────────────────┐
          │ [BoT-SORT] Tracking ID #42 assigned to chart region     │
          │ State: Position changed from +2% to -5%                 │
          │ Trigger: SIGNIFICANT_CHANGE flagged                     │
          └─────────────────────────────────────────────────────────┘
                    │
                    ▼
T+50ms    ┌─────────────────────────────────────────────────────────┐
          │ [MobileSAM] Precision mask on price region              │
          │ Output: Segmented "-5.23%" text region                  │
          └─────────────────────────────────────────────────────────┘
                    │
                    ▼
T+100ms   ┌─────────────────────────────────────────────────────────┐
          │ [UI Parser] OCR extracts: "-5.23%", "$1,240.00"         │
          │ Output: price=1240.00, change=-5.23%, timestamp=...    │
          └─────────────────────────────────────────────────────────┘
                    │
                    ▼
T+500ms   ┌─────────────────────────────────────────────────────────┐
          │ [Eagle Scout] "What changed?"                           │
          │ Input: Current frame vs. T-30s frame                    │
          │ Output: {                                               │
          │   "change_type": "price_drop",                          │
          │   "magnitude": "significant",                           │
          │   "affected_region": "main_chart",                      │
          │   "confidence": 0.94                                    │
          │ }                                                       │
          └─────────────────────────────────────────────────────────┘
                    │
                    ▼
T+1500ms  ┌─────────────────────────────────────────────────────────┐
          │ [Qwen Reviewer] "What does this mean?"                  │
          │ Context: Position size=100 units, entry=$1,300          │
          │ Output: {                                               │
          │   "risk_level": "high",                                 │
          │   "pnl_impact": "-$6,000 unrealized",                   │
          │   "recommended_action": "review_position",              │
          │   "urgency": "immediate"                                │
          │ }                                                       │
          └─────────────────────────────────────────────────────────┘
                    │
                    ▼
T+3000ms  ┌─────────────────────────────────────────────────────────┐
          │ [Kimi Overseer] "Do I agree?"                           │
          │ Review: Validates Qwen assessment, checks context       │
          │ Output: {                                               │
          │   "validation": "confirmed",                            │
          │   "confidence": 0.91,                                   │
          │   "override": null                                      │
          │ }                                                       │
          └─────────────────────────────────────────────────────────┘
                    │
                    ▼
T+3500ms  ┌─────────────────────────────────────────────────────────┐
          │ [Governor] "Is action allowed?"                         │
          │ Policy Check:                                           │
          │   - Max daily loss: $10,000 (currently -$6,000) ✓       │
          │   - Position limit: 100 units (at limit) ⚠️              │
          │   - Auto-hedge enabled: true                            │
          │                                                         │
          │ DECISION: hold                                          │
          │ ACTION: Trigger auto-hedge, notify trader               │
          │ LOG: CRITICAL - Position auto-hedged at -$6,000 PnL     │
          └─────────────────────────────────────────────────────────┘
```

---

## Configuration

### Environment Variables

```bash
# Performance tuning
YOLO_INFERENCE_DEVICE=cuda:0
EAGLE_BATCH_SIZE=4
QWEN_MAX_TOKENS=512
KIMI_MAX_TOKENS=1024

# Risk thresholds
GOVERNOR_MAX_DAILY_LOSS_USD=10000
GOVERNOR_POSITION_LIMIT=100
GOVERNOR_AUTO_HEDGE=true

# Escalation
ESCALATION_WEBHOOK_URL=https://alerts.trading.internal/escalate
NOTIFICATION_CHANNEL=trading-alerts
```

### Policy File

```yaml
# governor_policy.yaml
risk_levels:
  none:
    max_position_delta: 0.01    # 1%
    action: continue
  
  low:
    max_position_delta: 0.05    # 5%
    action: note
    notify: false
  
  medium:
    max_position_delta: 0.10    # 10%
    action: warn
    notify: true
  
  high:
    max_position_delta: 0.20    # 20%
    action: hold
    notify: true
    require_approval: true
  
  critical:
    max_position_delta: 0.50    # 50%
    action: pause
    notify: true
    auto_hedge: true
    escalate: true
```

---

## Deployment

### Docker Compose

```yaml
version: '3.8'
services:
  reflex:
    image: advanced-vision/reflex:latest
    runtime: nvidia
    
  yolo:
    image: advanced-vision/yolo:latest
    runtime: nvidia
    
  sam:
    image: advanced-vision/mobilesam:latest
    runtime: nvidia
    
  eagle:
    image: advanced-vision/eagle:latest
    runtime: nvidia
    
  qwen:
    image: advanced-vision/qwen:latest
    runtime: nvidia
    
  governor:
    image: advanced-vision/governor:latest
    ports:
      - "8080:8080"
    environment:
      - POLICY_FILE=/config/governor_policy.yaml
```

---

## Monitoring

### Metrics

| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| `pipeline_latency_p99` | 99th percentile latency | >5s |
| `governor_decisions_total` | Total decisions by type | N/A |
| `yolo_fps` | YOLO frames per second | <30 |
| `qwen_queue_depth` | Pending Qwen requests | >10 |
| `critical_events_1h` | Critical events in last hour | >5 |

### Dashboard

```
┌─────────────────────────────────────────────────────────────┐
│  Trading Watcher Stack - Live Status                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [YOLO]  ████████████████████████████████████████  45fps  │
│  [Eagle] ████████████████████████░░░░░░░░░░░░░░░░░  380ms  │
│  [Qwen]  ████████████████████░░░░░░░░░░░░░░░░░░░░░  1.2s   │
│  [Kimi]  ████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  2.8s   │
│                                                             │
│  Last Event: 2s ago (medium risk)                          │
│  Governor Status: ACTIVE (0 holds, 1 warning today)        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Troubleshooting

### Common Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| YOLO latency >100ms | GPU throttling | Check nvidia-smi, reduce batch size |
| Eagle timeout | VLM overloaded | Increase replica count, cache responses |
| False positives | Motion sensitivity | Tune Reflex threshold, add RoI mask |
| Governor blocking safe events | Policy too strict | Adjust risk thresholds |
| Pipeline >5s | Kimi bottleneck | Enable fast-path for known events |

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-03-18 | Initial 7-layer + Governor architecture |

---

## References

- [YOLOv8 Documentation](https://docs.ultralytics.com/)
- [MobileSAM Paper](https://arxiv.org/abs/2306.14289)
- [BoT-SORT Tracking](https://github.com/NirAharon/BoT-SORT)
- [Eagle2-2B Model Card](https://huggingface.co/...)
- [Qwen3.5 Technical Report](https://arxiv.org/abs/...)

---

> *"The Governor doesn't predict the market. It predicts regret."* — Dad's Architecture Note #7
