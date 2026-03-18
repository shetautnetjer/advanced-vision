# Advanced Vision - WebSocket Server Architecture

Distributed computer vision processing pipeline using WebSocket servers.

## Architecture

```
Screen Capture → WSS Server (Port 8001) → Raw Frames
YOLO Detector → WSS Server (Port 8002) → Boxes + Classes
MobileSAM → WSS Server (Port 8003) → Segmentations
Eagle Vision → WSS Server (Port 8004) → Classifications
Reviewers → WSS Server (Port 8005) → Analysis Results
```

## Quick Start

### Start the Server

```bash
# Start all feeds
./scripts/start_wss_server.sh

# Start specific feeds only
./scripts/start_wss_server.sh -p 8001 -p 8004

# With custom config
./scripts/start_wss_server.sh -c /path/to/config.yaml
```

### Python API

```python
from advanced_vision import WSSServer, WSSPublisher, WSSSubscriber

# Start server
server = WSSServer("config/wss_config.yaml")
await server.start()

# Publish to a feed
publisher = WSSPublisher(feed_port=8001)
await publisher.connect()
await publisher.publish_classification("button", 0.95)

# Subscribe to a feed
subscriber = WSSSubscriber(feed_port=8004)
subscriber.on_json = lambda data: print(data)
await subscriber.connect()
```

## Feed Ports

| Port | Feed | Description |
|------|------|-------------|
| 8001 | capture | Screen Capture - Raw Frames |
| 8002 | yolo | YOLO Detector - Boxes + Classes |
| 8003 | mobilesam | MobileSAM - Segmentations |
| 8004 | eagle | Eagle Vision - Classifications |
| 8005 | reviewers | Reviewers - Analysis Results |

## Logs

- Text log: `logs/wss-feed-text.log`
- JSON log: `logs/wss-feed-classifications.json`
- Frame images: `logs/frames/`

## Dependencies

- websockets
- asyncio
- pyyaml
- pillow
- numpy
