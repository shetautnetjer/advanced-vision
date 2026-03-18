# WSS Architecture - Advanced Vision Trading System

**Version:** 1.0  
**Last Updated:** 2026-03-17  
**Status:** ✅ Implementation Complete

---

## Overview

The WebSocket Server (WSS) architecture provides real-time communication infrastructure for the Advanced Vision Trading System. It enables decoupled, event-driven communication between vision pipeline components, trading algorithms, and UI displays.

---

## Architecture Goals

1. **Real-time Broadcasting**: Publish detection results, classifications, and trading signals with minimal latency
2. **Schema-Based Routing**: Route messages to appropriate channels based on message type
3. **Multi-Channel Design**: Separate concerns across different ports for UI, detection, classification, and trading
4. **Observability**: Comprehensive logging in both text and JSON formats
5. **Scalability**: Support multiple concurrent subscribers per channel

---

## Port Assignments

| Port | Channel | Purpose | Message Types |
|------|---------|---------|---------------|
| **8001** | UI Updates | Screenshot previews, status updates, display data | `ui_update` |
| **8002** | YOLO Detections | Raw detection results from YOLO inference | `detection` |
| **8003** | System Events | Heartbeats, errors, diagnostics, resource warnings | `system_event` |
| **8004** | Eagle2 Classifications | Scout lane classifications and relevance scores | `classification` |
| **8005** | Trading Signals | Final trading decisions and risk assessments | `trading_signal` |

### Port Selection Strategy

- **UI Port (8001)**: High-frequency updates, non-sensitive display data
- **Detection Port (8002)**: Raw YOLO outputs, bounding boxes, element types
- **System Port (8003)**: Infrastructure health, VRAM usage, heartbeats
- **Classification Port (8004)**: Eagle2 scout results, event classification
- **Trading Port (8005)**: Final recommendations, risk levels, action signals

---

## Message Schema Definitions

### Base Message Schema

All messages extend this base schema:

```json
{
  "timestamp": "2026-03-17T12:00:00.000Z",
  "source": "component_name",
  "msg_type": "message_type",
  "payload": {},
  "schema_version": "1.0"
}
```

### Detection Message (Port 8002)

YOLO detection results:

```json
{
  "timestamp": "2026-03-17T12:00:00.000Z",
  "source": "yolo_detector",
  "msg_type": "detection",
  "schema_version": "1.0",
  "payload": {
    "frame_id": "frame_001",
    "inference_time_ms": 12.5,
    "model": "yolov8n",
    "device": "cuda:0",
    "detections": [
      {
        "element_id": "elem_001",
        "element_type": "chart_panel",
        "bbox": {"x": 100, "y": 100, "width": 400, "height": 300},
        "confidence": 0.89
      },
      {
        "element_id": "elem_002", 
        "element_type": "order_ticket_panel",
        "bbox": {"x": 600, "y": 150, "width": 250, "height": 400},
        "confidence": 0.76
      }
    ]
  }
}
```

### Classification Message (Port 8004)

Eagle2 scout classification results:

```json
{
  "timestamp": "2026-03-17T12:00:00.350Z",
  "source": "eagle2_scout",
  "msg_type": "classification",
  "schema_version": "1.0",
  "payload": {
    "frame_id": "frame_001",
    "event_type": "CHART_UPDATE",
    "is_trading_relevant": true,
    "requires_reviewer": false,
    "confidence": 0.94,
    "inference_time_ms": 320,
    "model": "eagle2-2b",
    "raw_output": "Trading relevant: Chart showing price movement"
  }
}
```

### Trading Signal Message (Port 8005)

Final trading decisions from reviewer:

```json
{
  "timestamp": "2026-03-17T12:00:02.100Z",
  "source": "qwen_reviewer",
  "msg_type": "trading_signal",
  "schema_version": "1.0",
  "payload": {
    "frame_id": "frame_001",
    "signal_type": "ANALYSIS_COMPLETE",
    "risk_level": "HIGH",
    "recommendation": "PAUSE",
    "confidence": 0.82,
    "reasoning": "Warning dialog detected on order confirmation screen",
    "action_required": true,
    "reviewer_model": "qwen3.5-4b"
  }
}
```

### UI Update Message (Port 8001)

Display updates for UI clients:

```json
{
  "timestamp": "2026-03-17T12:00:00.100Z",
  "source": "display_manager",
  "msg_type": "ui_update",
  "schema_version": "1.0",
  "payload": {
    "update_type": "screenshot_preview",
    "frame_id": "frame_001",
    "data": {
      "thumbnail_path": "/tmp/preview_001.jpg",
      "resolution": "320x180",
      "detection_overlay": true,
      "elements_highlighted": 2
    }
  }
}
```

### System Event Message (Port 8003)

System health and diagnostics:

```json
{
  "timestamp": "2026-03-17T12:00:30.000Z",
  "source": "wss_server",
  "msg_type": "system_event",
  "schema_version": "1.0",
  "payload": {
    "event_type": "heartbeat",
    "status": "ok",
    "uptime_seconds": 300,
    "connections": {
      "8001": {"current": 2, "total": 5, "peak": 3},
      "8002": {"current": 1, "total": 3, "peak": 2},
      "8003": {"current": 1, "total": 1, "peak": 1},
      "8004": {"current": 1, "total": 2, "peak": 2},
      "8005": {"current": 2, "total": 4, "peak": 3}
    },
    "message_counts": {
      "8001": 150,
      "8002": 75,
      "8003": 10,
      "8004": 50,
      "8005": 25
    }
  }
}
```

---

## Pipeline Flow

### Complete Data Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│  SCREEN CAPTURE (100ms)                                                 │
│  └─→ Screenshot saved to artifacts/screens/                             │
└───────────────────────────────┬─────────────────────────────────────────┘
                                ↓
┌───────────────────────────────▼─────────────────────────────────────────┐
│  YOLO DETECTION (10ms) → Port 8002                                      │
│  └─→ Detected elements with bounding boxes                              │
│  └─→ Publishes: DetectionMessage                                        │
└───────────────────────────────┬─────────────────────────────────────────┘
                                ↓
┌───────────────────────────────▼─────────────────────────────────────────┐
│  EAGLE2 CLASSIFICATION (300-500ms) → Port 8004                          │
│  └─→ "Is this trading-relevant?"                                        │
│  └─→ Event type classification                                          │
│  └─→ Publishes: ClassificationMessage                                   │
└───────────────────────────────┬─────────────────────────────────────────┘
                                ↓
┌───────────────────────────────▼─────────────────────────────────────────┐
│  QWEN REVIEWER (1-2s) → Port 8005                                       │
│  └─→ Risk assessment and recommendations                                │
│  └─→ Publishes: TradingSignalMessage                                    │
└─────────────────────────────────────────────────────────────────────────┘
                                ↓
                    ┌───────────┴───────────┐
                    ↓                       ↓
            ┌───────▼───────┐       ┌───────▼───────┐
            │  UI Updates   │       │ Trading Bot   │
            │  Port 8001    │       │ Port 8005     │
            └───────────────┘       └───────────────┘
```

### Schema Routing Logic

```python
# Automatic routing based on message type
ROUTES = {
    "ui_update":       8001,  # UI channel
    "detection":       8002,  # Detection channel
    "system_event":    8003,  # System channel
    "classification":  8004,  # Classification channel
    "trading_signal":  8005,  # Trading channel
}
```

---

## Performance Benchmarks

### Measured Latencies

| Component | Target | Measured | Status |
|-----------|--------|----------|--------|
| Screenshot Capture | < 150ms | ~100ms | ✅ |
| YOLO Detection | < 20ms | ~10ms | ✅ |
| Eagle2 Classification | < 500ms | 300-500ms | ✅ |
| Qwen Reviewer | < 2s | 1-2s | ✅ |
| WSS Publish | < 10ms | ~2ms | ✅ |
| **Total Pipeline** | < 4s | **~2-4s** | ✅ |

### Throughput

| Metric | Value |
|--------|-------|
| Max clients per port | 100 (configurable) |
| Message broadcast latency | < 5ms for 10 subscribers |
| Heartbeat interval | 30s (configurable) |
| Log rotation | Per-port, append-only |

### VRAM Usage (Full Pipeline)

```
Component                    VRAM
────────────────────────────────────────
YOLOv8n (detection)          0.4 GB
MobileSAM (segmentation)     0.5 GB  
Eagle2-2B (scout)            4.0 GB
Qwen3.5-4B (reviewer)        8.4 GB
WSS Server                   ~50 MB
────────────────────────────────────────
Total:                      13.3 GB
Available:                   2.7 GB / 16 GB ✅
```

---

## File Locations

### Source Code

```
src/advanced_vision/
├── wss_server.py          # Main WSS server implementation
└── trading/
    ├── events.py          # TradingEvent schemas
    ├── detector.py        # YOLO detection pipeline
    └── reviewer.py        # Qwen reviewer lane
```

### Tests

```
tests/
├── test_wss_server.py      # Unit tests for WSS server
└── test_wss_integration.py # Integration tests
```

### Demo

```
examples/
└── wss_demo.py            # Full pipeline demo
```

### Logs

```
logs/
├── wss/
│   ├── port_8001.json.log
│   ├── port_8002.json.log
│   ├── port_8003.json.log
│   ├── port_8004.json.log
│   └── port_8005.json.log
└── demo/
    ├── demo_YYYYMMDD_HHMMSS.log
    └── latency_YYYYMMDD_HHMMSS.jsonl
```

---

## Usage Examples

### Starting the WSS Server

```python
from advanced_vision.wss_server import WSSServer, WSSServerConfig
import asyncio

# Configure
config = WSSServerConfig(
    host="localhost",
    ports=[8001, 8002, 8003, 8004, 8005],
    log_dir="logs/wss",
    log_format="json",
)

# Start server
server = WSSServer(config)
await server.start()
```

### Publishing Detection Results

```python
from advanced_vision.wss_server import DetectionMessage

# Create detection message
msg = DetectionMessage(
    timestamp=datetime.utcnow().isoformat(),
    source="yolo_detector",
    payload={
        "frame_id": "frame_001",
        "detections": [...],
        "inference_time_ms": 12.5,
    }
)

# Publish to port 8002
await server.publish(8002, msg)
```

### Subscribing to Trading Signals

```python
import asyncio
from websockets import connect

async def trading_subscriber():
    uri = "ws://localhost:8005"
    async with connect(uri) as websocket:
        async for message in websocket:
            data = json.loads(message)
            if data["msg_type"] == "trading_signal":
                risk = data["payload"]["risk_level"]
                print(f"Risk: {risk}, Signal: {data['payload']['recommendation']}")

asyncio.run(trading_subscriber())
```

### Running the Demo

```bash
# Dry-run mode (safe, no actual inference)
python examples/wss_demo.py --dry-run --duration 30

# Trading mode with live inference
python examples/wss_demo.py --mode trading --duration 60

# With custom log directory
python examples/wss_demo.py --log-dir /var/log/vision --duration 120
```

---

## Testing

### Run All WSS Tests

```bash
# Server unit tests
pytest tests/test_wss_server.py -v

# Integration tests
pytest tests/test_wss_integration.py -v

# All WSS tests
pytest tests/test_wss_*.py -v
```

### Test Coverage

| Test File | Coverage |
|-----------|----------|
| Server startup (all ports) | ✅ |
| Client connections | ✅ |
| Message broadcasting | ✅ |
| Schema routing | ✅ |
| Text logging | ✅ |
| JSON logging | ✅ |
| YOLO → WSS flow | ✅ |
| Eagle2 → WSS flow | ✅ |
| Trading signal flow | ✅ |
| Multi-subscriber support | ✅ |
| Latency measurements | ✅ |

---

## Configuration Options

### WSSServerConfig

```python
@dataclass
class WSSServerConfig:
    host: str = "localhost"           # Bind address
    ports: list[int] = [8001-8005]    # Active ports
    log_dir: Path = "logs/wss"        # Log directory
    log_format: str = "json"          # "text" or "json"
    log_level: str = "INFO"           # Logging level
    max_clients_per_port: int = 100   # Connection limit
    heartbeat_interval: float = 30.0  # Seconds between heartbeats
    message_queue_size: int = 1000    # Queue depth per port
```

### Environment Variables

```bash
# Optional: Override default ports
export VISION_WSS_UI_PORT=8001
export VISION_WSS_DETECTION_PORT=8002
export VISION_WSS_SYSTEM_PORT=8003
export VISION_WSS_CLASSIFICATION_PORT=8004
export VISION_WSS_TRADING_PORT=8005

# Optional: Log configuration
export VISION_WSS_LOG_DIR=/var/log/vision
export VISION_WSS_LOG_FORMAT=json
```

---

## Security Considerations

1. **Local-Only Binding**: Server binds to `localhost` by default
2. **No Authentication**: Internal service, no auth required
3. **Log Sanitization**: No sensitive data in WSS messages
4. **Rate Limiting**: Connection limits per port
5. **No Persistence**: Messages are ephemeral, only logs persist

---

## Future Enhancements

### Planned

- [ ] TLS/WSS support for secure connections
- [ ] Message persistence for replay
- [ ] Web dashboard for real-time monitoring
- [ ] Alert integration (Discord/Slack webhooks)

### Under Consideration

- [ ] Message queuing with Redis
- [ ] Horizontal scaling with load balancing
- [ ] GraphQL subscription API
- [ ] Browser-based visualization tool

---

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Port already in use | Another process using port | Change ports or kill process |
| Connection refused | Server not running | Start server with `server.start()` |
| High latency | Too many subscribers | Reduce subscriber count or scale horizontally |
| Log files not created | Permissions issue | Check `log_dir` permissions |
| Messages not received | Wrong port/subscriber | Verify port mapping in schema router |

### Debug Mode

```python
# Enable debug logging
config = WSSServerConfig(log_level="DEBUG")
```

---

## References

- **WebSockets Library**: https://websockets.readthedocs.io/
- **Pydantic Models**: https://docs.pydantic.dev/
- **YOLOv8**: https://docs.ultralytics.com/
- **Service Contracts**: See `SERVICE_CONTRACTS.md`
- **Trading Events**: See `src/advanced_vision/trading/events.py`

---

## Verification Checklist

- [x] Server starts on ports 8001-8005
- [x] YOLO publishes detections to port 8002
- [x] Eagle publishes classifications to port 8004
- [x] Subscriber receives messages
- [x] Schema routing works (UI vs Trading)
- [x] Logs are written correctly (text + JSON)
- [x] Demo script runs end-to-end
- [x] All tests pass
- [x] Performance benchmarks documented
- [x] Architecture documented