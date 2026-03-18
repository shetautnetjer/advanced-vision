# Advanced Vision - WebSocket Server Architecture

> **WSS v2 Active | 2.5GB VRAM Saved | 38 Tests Passing**

Distributed computer vision processing pipeline using WebSocket servers.

## Architecture

```
Single Port 8000 with Typed Topics:
- vision.detection.yolo       → YOLO Detection - Boxes + Classes
- vision.segmentation.sam     → MobileSAM - Segmentations
- vision.classification.eagle → Eagle Vision - Classifications
- vision.analysis.qwen        → Qwen Analysis - Deep Reasoning
- system.*                    → Heartbeat, Error, Metrics
```

## Model Roles

| Model | Role | Speed | Memory | Notes |
|-------|------|-------|--------|-------|
| **Eagle2-2B** | Scout | ~400ms | Resident | Fast preliminary classification |
| **Qwen3.5-4B** | Reviewer | On-demand | On-demand | Deep analysis when needed |

**VRAM Savings:** ~2.5GB by consolidating to single-port architecture with on-demand model loading.

## Quick Start

### Start the Server

```bash
# Start WSS v2 server (single port 8000)
./scripts/start_wss_server.sh

# With custom config
./scripts/start_wss_server.sh -c /path/to/wss_config.yaml
```

The `wss_config.yaml` uses topic-based configuration for routing messages between vision components.

### Python API

```python
from advanced_vision import WSSServer, WSSPublisher, WSSSubscriber

# Start server with topic-based config
server = WSSServer("config/wss_config.yaml")
await server.start()

# Publish to a topic
publisher = WSSPublisher(topic="vision.classification.eagle")
await publisher.connect()
await publisher.publish({"class": "button", "confidence": 0.95})

# Subscribe to a topic
subscriber = WSSSubscriber(topic="vision.detection.yolo")
subscriber.on_json = lambda data: print(data)
await subscriber.connect()
```

## Topics

| Topic | Type | Description |
|-------|------|-------------|
| `vision.detection.yolo` | Detection | YOLO - Boxes + Classes |
| `vision.segmentation.sam` | Segmentation | MobileSAM - Object Masks |
| `vision.classification.eagle` | Classification | Eagle2-2B - Fast Classifications |
| `vision.analysis.qwen` | Analysis | Qwen3.5-4B - Deep Reasoning |
| `system.heartbeat` | System | Health checks |
| `system.error` | System | Error reporting |
| `system.metrics` | System | Performance metrics |

## Logs

- Text log: `logs/wss-feed-text.log`
- JSON log: `logs/wss-feed-classifications.json`
- Frame images: `logs/frames/`

## Documentation

- [Architecture Principles](docs/ARCHITECTURE_PRINCIPLES.md) - Core design decisions
- [Trading Watcher Stack](docs/TRADING_WATCHER_STACK.md) - Trading-specific vision pipeline
- [Computer Use Integration](docs/COMPUTER_USE_INTEGRATION.md) - GUI automation integration

## Dependencies

- websockets
- asyncio
- pyyaml
- pillow
- numpy
