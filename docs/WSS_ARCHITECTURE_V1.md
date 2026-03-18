# WSS Architecture - Version 1 (Multi-Port Baseline)

**Status:** Experimental / Working Baseline  
**Date:** 2026-03-17  
**Tests:** 50 passing (31 unit + 19 integration)

---

## ⚠️ Important Notice

This is **WSS v1** - a **multi-port experimental baseline** that works and is tested.

**v2 (Planned):** Single-port with typed topics (Dad's preferred architecture)
- Easier auth, reconnect, observability
- Cleaner network shape
- See: `docs/WSS_V2_ROADMAP.md`

**Current v1 is:**
- ✅ Working (50 tests pass)
- ✅ Plane A (provisional)
- ⚠️ Experimental transport layout
- ❌ Not final canonical network law

---

## v1 Architecture (Multi-Port)

```
┌─────────────────────────────────────────────────────────┐
│  WSS Server (5 Ports)                                    │
├─────────┬───────────────────────────────────────────────┤
│ Port    │ Purpose                                       │
├─────────┼───────────────────────────────────────────────┤
│ 8001    │ Raw Frames (screen capture)                   │
│ 8002    │ YOLO Detections (boxes + classes)             │
│ 8003    │ SAM Segmentations (masks)                     │
│ 8004    │ Eagle2 Classifications (scout results)        │
│ 8005    │ Analysis Results (Qwen/Kimi/Chronos)          │
└─────────┴───────────────────────────────────────────────┘
```

### Message Format (v1)
```json
{
  "event_id": "uuid",
  "event_type": "detection.yolo",
  "schema_family": "trading",
  "created_at": "2026-03-17T21:30:00Z",
  "source": "yolov8n",
  "frame_ref": "frames/2026-03-17_213000.png",
  "trace_id": "session-abc-123",
  "payload": { ... }
}
```

---

## Files Created (v1)

| File | Purpose | Tests |
|------|---------|-------|
| `src/advanced_vision/wss_server.py` | Multi-port server (5 ports) | 31 |
| `src/advanced_vision/wss_client.py` | Publisher/subscriber clients | - |
| `src/advanced_vision/schema_router.py` | UI vs Trading routing | - |
| `src/advanced_vision/wss_logger.py` | Text + JSON logging | - |
| `src/advanced_vision/wss_agent_subscriber.py` | OpenClaw agent subscriber | 24 |
| `wss_yolo_publisher.py` | YOLO → port 8002 | - |
| `wss_sam_publisher.py` | MobileSAM → port 8003 | - |
| `wss_eagle_publisher.py` | Eagle2 → port 8004 | - |
| `wss_analysis_publisher.py` | Qwen/Kimi → port 8005 | - |
| `wss_manager.py` | Unified orchestrator | - |
| `tests/test_wss_server.py` | Unit tests | 31 |
| `tests/test_wss_agent_subscriber.py` | Subscriber tests | 24 |
| `tests/test_wss_integration.py` | Integration tests | 19 |
| `examples/wss_demo.py` | Full demo | - |

**Total: 50 tests passing**

---

## Usage (v1)

### Start Server
```bash
./scripts/start_wss_server.sh              # All ports
./scripts/start_wss_server.sh -p 8002 8004 # Specific ports
```

### Subscribe as Agent
```python
from advanced_vision.wss_agent_subscriber import WSSAgentSubscriber

subscriber = WSSAgentSubscriber()
subscriber.subscribe(8004, schema="trading", callback=on_pattern)
subscriber.start()  # Non-blocking
```

### Publish Detection
```python
from advanced_vision.trading import YOLOWSSPublisher

publisher = YOLOWSSPublisher(port=8002)
publisher.publish(frame, detections)
```

---

## Performance (v1)

| Component | Latency |
|-----------|---------|
| WSS publish | < 10ms |
| YOLO detection | ~10ms |
| Eagle inference | ~300-500ms |
| Qwen inference | ~1-2s |
| End-to-end | ~2-3s |

---

## Migration Path to v2

**v2 Target (Single Port):**
```python
# v2 will use:
ws://localhost:8000
  → {"event_type": "vision.detection.yolo", ...}
  → {"event_type": "vision.segmentation.sam", ...}
  → {"event_type": "vision.classification.eagle", ...}
  → {"event_type": "vision.analysis.qwen", ...}
```

**Why v2 is better:**
- Easier authentication (one endpoint)
- Simpler reconnect logic
- Better observability (one connection to monitor)
- Less orchestration sprawl

**Migration Plan:**
1. ✅ v1 committed as baseline
2. 🔄 v2 refactor (single port + topics)
3. 🔄 Update publishers/subscribers
4. 🔄 Migrate tests
5. ✅ Deprecate v1

See: `docs/WSS_V2_ROADMAP.md` (to be created)

---

## Dad's Governance Ruling

> "Commit v1 now as experimental baseline, then refactor to v2 single-port."
>
> "v1 is Plane A, working, provisional, experimental transport layout, not canonical network law."
>
> "v2 target: one port, typed topics, transport envelope, append-only durable logs."

---

## Schema Definitions (v1)

### UI Schema Events
- `ui.button_detected`
- `ui.modal_appeared`
- `ui.chart_panel_visible`
- `ui.text_input_focused`

### Trading Schema Events
- `trading.pattern_candidate`
- `trading.signal_detected`
- `trading.risk_observation`
- `trading.escalation_triggered`

---

## Logs (Durable Records)

**WSS = Transport only (not truth)**

**Truth = Append-only files:**
- `logs/wss-feed-text.log` - Text log
- `logs/wss-feed-events.jsonl` - Structured events
- `frames/` - Image references
- `masks/` - Segmentation masks

---

## Known Limitations (v1)

1. **5 ports** = more complex auth/reconnect
2. **One type per port** = less flexible
3. **No built-in persistence** = WSS only
4. **Schema validation** = basic (v2 will be stricter)

---

## Quick Start

```bash
# Terminal 1: Start WSS server
cd ~/.openclaw/workspace/plane-a/projects/advanced-vision
./scripts/start_wss_server.sh

# Terminal 2: Run demo
python examples/wss_demo.py

# Terminal 3: Subscribe
python -c "
from advanced_vision.wss_agent_subscriber import WSSAgentSubscriber
s = WSSAgentSubscriber()
s.subscribe(8004, schema='trading', callback=lambda m: print(m))
s.start()
"
```

---

## Status

- ✅ 50 tests passing
- ✅ All ports functional
- ✅ Publishers/subscribers working
- ⚠️ v1 = experimental baseline
- 🔄 v2 = planned refactor to single-port

**Last Updated:** 2026-03-17
