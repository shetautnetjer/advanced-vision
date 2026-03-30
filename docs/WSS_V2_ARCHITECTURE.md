# WSS v2 Architecture Documentation

## Overview

The WSS (WebSocket Server) v2 architecture refactors the multi-port v1 design into a single-port, topic-based architecture. This document explains the changes, migration path, and benefits.

## Architecture Changes

### v1 (Legacy): Multi-Port

```
Port 8001: UI Updates (screenshots, status)
Port 8002: YOLO Detections
Port 8003: System Events (heartbeats, errors)
Port 8004: Eagle2 Classifications
Port 8005: Trading Signals / Analysis
```

**Problems with v1:**
- 5 ports to manage, monitor, and secure
- No easy way to subscribe to multiple message types
- Port-based routing is inflexible
- Harder to add new message types
- Auth needs to be handled per-port

### v2: Single Port + Typed Topics

```
Port 8000: All messages, routed by topic

Topics:
- vision.detection.yolo       (YOLO detection results)
- vision.segmentation.sam     (MobileSAM segmentation results)
- vision.classification.eagle (Eagle2-2B classification results)
- vision.analysis.qwen        (Chronos/Qwen/Kimi analysis results)
- system.heartbeat            (Server heartbeats)
- system.error                (Error messages)
- system.metrics              (Metrics/telemetry)
```

## Transport Envelope

All v2 messages use a standard transport envelope:

```json
{
  "event_id": "uuid-v4",
  "event_type": "detection",
  "schema_family": "detection",
  "created_at": "2026-03-17T12:00:00Z",
  "source": "yolo",
  "frame_ref": "frame_001",
  "trace_id": "uuid-v4-for-distributed-tracing",
  "payload": {
    // Event-specific data
  },
  // Server-side fields (added on receipt)
  "topic": "vision.detection.yolo",
  "received_at": "2026-03-17T12:00:00.001Z"
}
```

### Envelope Fields

| Field | Type | Description |
|-------|------|-------------|
| `event_id` | string | Unique event identifier (UUID v4) |
| `event_type` | string | Semantic event type (e.g., "detection", "classification") |
| `schema_family` | enum | High-level category (detection, segmentation, classification, analysis, system) |
| `created_at` | ISO8601 | Timestamp when event was created |
| `source` | string | Component that produced the event (yolo, sam, eagle, qwen) |
| `frame_ref` | string | Reference to associated frame/image |
| `trace_id` | string | Distributed tracing identifier (correlates related events) |
| `payload` | object | Event-specific data |
| `topic` | string | Filled by server: the topic this message was published to |
| `received_at` | ISO8601 | Filled by server: when message was received |

## File Structure

### New v2 Files

```
src/advanced_vision/
├── wss_server_v2.py          # Single-port server with topic routing
├── wss_client_v2.py          # Client with topic-based subscriptions
├── wss_agent_subscriber_v2.py # Agent subscriber using v2
└── trading/
    ├── wss_yolo_publisher_v2.py      # YOLO publisher (v2)
    ├── wss_sam_publisher_v2.py       # SAM publisher (v2)
    ├── wss_eagle_publisher_v2.py     # Eagle publisher (v2)
    └── wss_analysis_publisher_v2.py  # Analysis publisher (v2)

tests/
└── test_wss_v2.py            # ~50 tests for v2 architecture

docs/
└── WSS_V2_ARCHITECTURE.md    # This document
```

### Preserved v1 Files

All v1 files remain unchanged for backward compatibility:

```
src/advanced_vision/
├── wss_server.py             # v1: Multi-port server (preserved)
├── wss_client.py             # v1: Multi-port client (preserved)
├── wss_agent_subscriber.py   # v1: Agent subscriber (preserved)
└── trading/
    ├── wss_yolo_publisher.py      # v1: YOLO publisher (preserved)
    ├── wss_sam_publisher.py       # v1: SAM publisher (preserved)
    ├── wss_eagle_publisher.py     # v1: Eagle publisher (preserved)
    └── wss_analysis_publisher.py  # v1: Analysis publisher (preserved)

tests/
└── test_wss_server.py        # v1 tests (preserved)
```

## Usage Examples

### Server (v2)

```python
from advanced_vision.wss_server_v2 import WSSServerV2, WSSServerConfigV2

# Create server
config = WSSServerConfigV2(
    host="localhost",
    port=8000,
    auth_enabled=False,  # Set to True + provide auth_token for auth
)
server = WSSServerV2(config)

# Start
await server.start()

# Stop
await server.stop()
```

### Publisher (v2)

```python
from advanced_vision.trading.wss_yolo_publisher_v2 import create_yolo_publisher_v2

# Create and start publisher
publisher = create_yolo_publisher_v2(fps=15)
publisher.start()

# Publish detection
publisher.publish_detection(
    boxes=[{
        "x": 100, "y": 100, "w": 200, "h": 150,
        "class": "chart_panel", "confidence": 0.95
    }],
    frame_id="frame_001",
    inference_time_ms=15.5
)

# Set trace ID for distributed tracing
import uuid
publisher.set_trace_id(str(uuid.uuid4()))

# Stop
publisher.stop()
```

### Subscriber (v2)

```python
from advanced_vision.wss_agent_subscriber_v2 import WSSAgentSubscriberV2
from advanced_vision.wss_server_v2 import TransportEnvelope

# Create subscriber
subscriber = WSSAgentSubscriberV2()

# Define callback
def on_detection(envelope: TransportEnvelope):
    print(f"Detection: {envelope.payload}")
    print(f"Trace ID: {envelope.trace_id}")

def on_classification(envelope: TransportEnvelope):
    print(f"Classification: {envelope.payload.get('label')}")

# Subscribe to topics
subscriber.subscribe("vision.detection.yolo", callback=on_detection)
subscriber.subscribe("vision.classification.eagle", callback=on_classification)

# Start (non-blocking)
subscriber.start()

# Later...
subscriber.stop()
```

### Client (v2) - Direct Usage

```python
from advanced_vision.wss_client_v2 import WSSSubscriberV2, ClientConfigV2

# Create subscriber client
config = ClientConfigV2(host="localhost", port=8000)
client = WSSSubscriberV2(topics=["vision.detection.yolo"], config=config)

# Set up callback
client.on_topic("vision.detection.yolo", lambda env: print(env.payload))

# Connect and listen
await client.connect()
```

## Durable Logging

v2 uses JSONL format for durable logs:

```
logs/wss_v2/
├── events.jsonl           # All events (detection, segmentation, classification, analysis, system)
└── classifications.jsonl  # Classification events only (for easy filtering)
```

Each line is a valid JSON object (TransportEnvelope).

Example:
```bash
# View all events
$ tail -f logs/wss_v2/events.jsonl

# Filter classifications
$ cat logs/wss_v2/classifications.jsonl | jq '.payload.label'

# Search by trace_id
$ cat logs/wss_v2/events.jsonl | jq 'select(.trace_id == "abc-123")'
```

## Authentication

v2 supports optional token-based authentication:

```python
# Server with auth
config = WSSServerConfigV2(
    auth_enabled=True,
    auth_token="your-secret-token"
)

# Client with auth
config = ClientConfigV2(
    auth_token="your-secret-token"
)
```

Auth flow:
1. Client connects
2. Server requests auth (if enabled)
3. Client sends `{type: "auth", auth_token: "..."}`
4. Server responds with `{type: "auth_ok"}` or `{type: "auth_failed"}`

## Migration Guide

### From v1 to v2

#### Publishers

**v1 (old):**
```python
from advanced_vision.trading.wss_yolo_publisher import create_yolo_publisher

publisher = create_yolo_publisher(fps=15)  # Connects to port 8002
publisher.start()
publisher.publish_detection(boxes, frame_id)
```

**v2 (new):**
```python
from advanced_vision.trading.wss_yolo_publisher_v2 import create_yolo_publisher_v2

publisher = create_yolo_publisher_v2(fps=15)  # Connects to port 8000
publisher.start()
publisher.publish_detection(boxes=boxes, frame_id=frame_id)
```

#### Subscribers

**v1 (old):**
```python
from advanced_vision.wss_agent_subscriber import WSSAgentSubscriber

subscriber = WSSAgentSubscriber()
subscriber.subscribe(8002, schema="trading", callback=on_detection)  # Port-based
subscriber.start()
```

**v2 (new):**
```python
from advanced_vision.wss_agent_subscriber_v2 import WSSAgentSubscriberV2

subscriber = WSSAgentSubscriberV2()
subscriber.subscribe("vision.detection.yolo", callback=on_detection)  # Topic-based
subscriber.start()
```

#### Client Direct

**v1 (old):**
```python
from advanced_vision.wss_client import WSSSubscriber

subscriber = WSSSubscriber(feed_port=8002)  # Port-based
await subscriber.connect()
```

**v2 (new):**
```python
from advanced_vision.wss_client_v2 import WSSSubscriberV2

subscriber = WSSSubscriberV2(topics=["vision.detection.yolo"])  # Topic-based
await subscriber.connect()
```

### Running v1 and v2 Side-by-Side

Both versions can run simultaneously during migration:

```python
# Start v1 server (ports 8001-8005)
from advanced_vision.wss_server import create_server
v1_server = await create_server()

# Start v2 server (port 8000)
from advanced_vision.wss_server_v2 import create_server_v2
v2_server = await create_server_v2()

# Publishers can use either
v1_yolo = create_yolo_publisher()  # Publishes to port 8002
v2_yolo = create_yolo_publisher_v2()  # Publishes to port 8000
```

## Benefits of v2

1. **Simpler Operations**: Single port (8000) instead of 5 ports
2. **Flexible Subscriptions**: Subscribe to specific topics, not ports
3. **Better Observability**: Standard transport envelope with trace_id, timestamps
4. **Easier Auth**: Single auth point instead of per-port
5. **Easier Extension**: Add new topics without new ports
6. **Cleaner Logs**: JSONL format, separate classification log
7. **Distributed Tracing**: trace_id correlates events across pipeline

## API Summary

### Topics

| Topic | Purpose | Publisher |
|-------|---------|-----------|
| `vision.detection.yolo` | YOLO detection results | YOLO pipeline |
| `vision.segmentation.sam` | MobileSAM segmentation results | SAM pipeline |
| `vision.classification.eagle` | Eagle2-2B classification results | Eagle pipeline |
| `vision.analysis.qwen` | Chronos/Qwen/Kimi analysis results | Analysis pipeline |
| `system.heartbeat` | Server health check | Server |
| `system.error` | Error messages | Any component |
| `system.metrics` | Telemetry/metrics | Server |

### Client Messages

| Message Type | Description |
|--------------|-------------|
| `subscribe` | Subscribe to topics |
| `unsubscribe` | Unsubscribe from topics |
| `publish` | Publish an envelope (from clients) |
| `ping` / `pong` | Keepalive |
| `get_stats` | Request server statistics |
| `auth` | Authenticate (if auth enabled) |

## Testing

v2 includes ~50 tests covering:

- Server startup on port 8000
- Client connections and subscriptions
- Topic routing and filtering
- Durable logging (events.jsonl, classifications.jsonl)
- Authentication
- Transport envelope validation
- Connection management
- Statistics

Run tests:
```bash
cd "/home/netjer/Projects/AI Frame/optical.nerves/advanced-vision"
python -m pytest tests/test_wss_v2.py -v
```

## Future Enhancements

Potential future improvements for v2:

1. **WebSocket over TLS**: `wss://` support
2. **Message compression**: Per-message deflate
3. **Rate limiting**: Per-client rate controls
4. **Message replay**: Request historical messages
5. **Wildcard subscriptions**: `vision.detection.*`
6. **Dead letter queue**: For failed deliveries
