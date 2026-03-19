# Advanced Vision - Governed Vision Pipeline

> **Governor Active | WSS v2 | Eagle2-2B Scout + Qwen3.5-4B Reviewer | 38 Tests Passing**

Distributed computer vision processing pipeline with constitutional governance, structured data contracts, and WebSocket-based architecture.

## Features

- ✅ **Governor** — Constitutional policy gate (AD-010) - Enforces trading rules and safety constraints
- ✅ **7 JSON Schemas** — Structured contracts for all packets - Type-safe message validation
- ✅ **SchemaRegistry** — Versioned, cached schema loading - Fast schema resolution with versioning
- ✅ **PacketValidator** — Runtime validation with fast-path - Validates all packets before processing
- ✅ **TruthWriter** — Append-only event/artifact logging - Immutable audit trail for all decisions
- ✅ **ExecutionGate** — Precondition checks before execution - Prevents unsafe operations
- ✅ **WSS v2** — Single port 8000 with typed topics - Unified WebSocket communication layer
- ✅ **Eagle2-2B Scout** — Fast visual classification (~400ms) - Resident model for quick analysis
- ✅ **Qwen3.5-4B Reviewer** — Deep analysis on-demand - Powerful reasoning when needed
- ✅ **Model-agnostic external finalizer interface** - Pluggable final decision layer

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        GOVERNOR (AD-010)                        │
│              Constitutional Policy Gate - All traffic           │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│ PacketValidator│    │ ExecutionGate │    │  TruthWriter  │
│   (Schemas)   │    │  (Preconditions)│   │ (Audit Trail) │
└───────────────┘    └───────────────┘    └───────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    WSS v2 - Single Port 8000                    │
│  vision.detection.yolo | vision.segmentation.sam               │
│  vision.classification.eagle | vision.analysis.qwen            │
│  system.heartbeat | system.error | system.metrics              │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┴─────────────────────┐
        ▼                                           ▼
┌───────────────┐                         ┌───────────────┐
│ Eagle2-2B     │                         │ Qwen3.5-4B    │
│ Scout         │◄───────────────────────►│ Reviewer      │
│ (Resident)    │   Escalation Path       │ (On-demand)   │
└───────────────┘                         └───────────────┘
        │                                           │
        └─────────────────────┬─────────────────────┘
                              ▼
                    ┌─────────────────┐
                    │ Finalizer       │
                    │ (Model-agnostic)│
                    └─────────────────┘
```

## Model Roles

| Model | Role | Speed | Memory | Notes |
|-------|------|-------|--------|-------|
| **Eagle2-2B** | Scout | ~400ms | Resident | Fast preliminary classification |
| **Qwen3.5-4B** | Reviewer | On-demand | On-demand | Deep analysis when needed |

**VRAM Savings:** ~2.5GB by consolidating to single-port architecture with on-demand model loading.

## Quick Start

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Start the Governed Pipeline

```bash
# Start the full governed trading pipeline
python -m advanced_vision.trading.governed_pipeline
```

### Or Start WSS v2 Server Only

```bash
# Start WSS v2 server (single port 8000)
./scripts/start_wss_server.sh

# With custom config
./scripts/start_wss_server.sh -c /path/to/wss_config.yaml
```

### Subscribe to Governed Events

```bash
# Subscribe and monitor governed events
python examples/subscribe_governed.py
```

## Governance Components

### Governor (AD-010)
The constitutional policy gate that enforces trading rules and safety constraints. All packets must pass through the Governor before processing.

### JSON Schemas
Seven structured schemas define contracts for all packets:
- Detection packets
- Segmentation packets
- Classification packets
- Analysis packets
- System packets (heartbeat, error, metrics)
- Governance packets
- Trading action packets

### SchemaRegistry
Versioned, cached schema loading for fast schema resolution without filesystem overhead.

### PacketValidator
Runtime validation with fast-path caching. Validates packet structure and content before processing.

### TruthWriter
Append-only logging for events and artifacts. Provides an immutable audit trail for all system decisions.

### ExecutionGate
Precondition checks before any execution. Ensures all safety constraints are met before actions are taken.

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
| `governance.policy` | Governance | Policy enforcement events |
| `governance.audit` | Governance | Audit trail entries |

## Python API

```python
from advanced_vision import (
    WSSServer, WSSPublisher, WSSSubscriber,
    Governor, PacketValidator, TruthWriter
)

# Start governed server
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

# Use governance components
validator = PacketValidator()
is_valid = validator.validate(packet, schema_name="classification")
```

## Logs

- Text log: `logs/wss-feed-text.log`
- JSON log: `logs/wss-feed-classifications.json`
- Frame images: `logs/frames/`
- Audit trail: `logs/audit/`

## Documentation

- [Architecture Principles](docs/ARCHITECTURE_PRINCIPLES.md) - Core design decisions
- [Trading Watcher Stack](docs/TRADING_WATCHER_STACK.md) - Trading-specific vision pipeline
- [Computer Use Integration](docs/COMPUTER_USE_INTEGRATION.md) - GUI automation integration
- [Governance Specification](docs/AD-010-GOVERNANCE.md) - Constitutional policy gate specification

## Dependencies

- websockets
- asyncio
- pyyaml
- pillow
- numpy
- jsonschema
