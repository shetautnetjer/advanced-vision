# Computer Use Integration Guide

**Project:** advanced-vision  
**Integration:** Aya (Kimi) via OpenClaw  
**Last Updated:** 2026-03-18

---

## Overview

This document describes how Aya (Kimi K2.5) consumes image packets from the advanced-vision system and executes computer use actions through OpenClaw.

> **Key Principle:** Aya receives curated perception, not raw video. The local processing pipeline filters, annotates, and structures visual data before it reaches the agent.

---

## Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         COMPUTER USE DATA FLOW                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐   │
│  │   Screen    │───▶│   YOLOv8    │───▶│    Eagle    │───▶│   WSS       │   │
│  │  Capture    │    │  Detection  │    │   Scout     │    │  Stream     │   │
│  └─────────────┘    └─────────────┘    └─────────────┘    └──────┬──────┘   │
│        │                  │                  │                    │         │
│        ▼                  ▼                  ▼                    ▼         │
│   ┌──────────────────────────────────────────────────────────────────┐     │
│   │                    LOCAL PROCESSING LOOP                          │     │
│   │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │     │
│   │  │ Capture  │─▶│  Detect  │─▶│  Analyze │─▶│  Transform/Route   │  │     │
│   │  │  Frame   │  │ Objects  │  │  State   │  │  to OpenClaw       │  │     │
│   │  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘  │     │
│   └──────────────────────────────────────────────────────────────────┘     │
│                              │                                              │
│                              ▼                                              │
│   ┌──────────────────────────────────────────────────────────────────┐     │
│   │                      OPENCLAW AGENT (Aya)                         │     │
│   │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │     │
│   │  │ Receive  │─▶│ Reason   │─▶│ Propose  │─▶│  Execute Action   │  │     │
│   │  │  Packet  │  │  State   │  │  Action  │  │  (Click/Type)     │  │     │
│   │  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘  │     │
│   └──────────────────────────────────────────────────────────────────┘     │
│                              │                                              │
│                              ▼                                              │
│   ┌──────────────────────────────────────────────────────────────────┐     │
│   │                      ACTION EXECUTION                             │     │
│   │  ┌──────────┐  ┌──────────┐  ┌──────────┐                       │     │
│   │  │  Mouse   │  │ Keyboard │  │  Verify  │                       │     │
│   │  │  Move    │  │  Input   │  │  Result  │                       │     │
│   │  └──────────┘  └──────────┘  └──────────┘                       │     │
│   └──────────────────────────────────────────────────────────────────┘     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 1. Aya/OpenClaw Integration Flow

### Local Loop → Discrete Packets → OpenClaw Agent

The integration follows a three-stage pipeline:

#### Stage 1: Local Perception Loop
```python
# Running locally on the vision system
while monitoring_active:
    frame = capture_screen()
    detections = yolo.detect(frame)
    state = eagle.analyze(detections, context)
    
    if state.requires_agent_attention():
        packet = create_image_packet(frame, state)
        send_to_openclaw(packet)
```

#### Stage 2: Discrete Packet Generation
- The local system decides **when** to send packets (not continuous stream)
- Packets are generated based on:
  - Significant state changes (new UI elements appear)
  - Explicit user requests (`"Aya, check this screen"`)
  - Error conditions requiring recovery
  - Scheduled checkpoints

#### Stage 3: OpenClaw Agent Consumption
- Aya receives structured packets via WSS
- Each packet contains: full frame, ROIs, detected targets, scout analysis
- Aya reasons on the structured state (not raw pixels)
- Actions are proposed, then executed after confirmation

---

## 2. Image Packet Format

The standard packet format for vision-to-agent communication:

```python
{
  # Episode classification
  "episode_type": "fresh|burst|before_after",
  
  # Full frame reference (path or base64)
  "full_frame_ref": "path/to/frame.jpg" | "data:image/jpeg;base64,/9j/4AAQ...",
  
  # Regions of Interest (cropped elements)
  "roi_refs": [
    "roi_1.jpg",
    "roi_2.jpg"
  ],
  
  # Detected targets with bounding boxes
  "targets": [
    {
      "id": "btn_submit",
      "type": "button",
      "bbox": [x, y, w, h],  # Normalized coordinates [0.0-1.0]
      "confidence": 0.95,
      "text": "Submit",
      "roi_ref": "roi_1.jpg"
    },
    {
      "id": "input_email",
      "type": "text_field",
      "bbox": [x, y, w, h],
      "confidence": 0.92,
      "text": "",
      "roi_ref": "roi_2.jpg"
    }
  ],
  
  # Eagle scout's assessment
  "scout_note": "Login form detected. Email and password fields visible. Submit button active.",
  
  # Flag for human review
  "needs_review": false,
  
  # Additional metadata
  "metadata": {
    "timestamp": "2026-03-18T07:45:00Z",
    "resolution": [1920, 1080],
    "screen_id": "primary",
    "app_context": "browser_chrome"
  }
}
```

### Episode Types

| Type | Description | Trigger |
|------|-------------|---------|
| `fresh` | Initial state capture | First look at new screen/context |
| `burst` | Rapid sequence of frames | Animation, loading, or transition |
| `before_after` | Before and after action verification | Post-action confirmation needed |

### Bounding Box Format

All bounding boxes use normalized coordinates `[x, y, w, h]` where values are in range `[0.0, 1.0]`:

```python
bbox = [
    x / image_width,      # Left position
    y / image_height,     # Top position  
    w / image_width,      # Width
    h / image_height      # Height
]
```

---

## 3. MCP Flow

### Screenshot → YOLO → Eagle Scout → Structured State → Aya Decides

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Screenshot │────▶│    YOLO     │────▶│    Eagle    │────▶│ Structured  │
│   Capture   │     │  Detection  │     │   Scout     │     │    State    │
└─────────────┘     └─────────────┘     └─────────────┘     └──────┬──────┘
                                                                   │
                                                                   ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│    Action   │◀────│   Execute   │◀────│   Propose   │◀────│    Aya      │
│   Result    │     │   Action    │     │   Action    │     │   Reasoning │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

### Processing Stages

#### 1. Screenshot Capture
```python
# Capture screen at configurable interval
frame = screen.capture(
    region="full",      # or [x, y, w, h] for partial
    format="pil",       # PIL Image for processing
    resize=(1920, 1080) # Consistent resolution
)
```

#### 2. YOLO Object Detection
```python
# Detect UI elements using fine-tuned YOLOv8 model
results = yolo_model(frame)
detections = []

for box in results.boxes:
    detection = {
        "class": model.names[int(box.cls)],
        "confidence": float(box.conf),
        "bbox": box.xyxy[0].tolist(),
        "center": box.xywh[0][:2].tolist()
    }
    detections.append(detection)
```

**Supported Element Classes:**
- `button` - Clickable buttons
- `text_field` - Input fields
- `checkbox` - Toggle controls
- `dropdown` - Select menus
- `link` - Hyperlinks
- `icon` - Small interactive icons
- `menu_item` - Navigation elements

#### 3. Eagle Scout Analysis
```python
# Analyze detections in context
state = eagle_scout.analyze(
    detections=detections,
    previous_state=last_state,
    context=session_context
)

# Eagle produces:
# - Element relationships (form groups, navigation hierarchies)
# - State changes (what changed since last frame)
# - Intent hints (likely user goals based on current UI)
# - Priority ranking (which elements need attention first)
```

#### 4. Structured State Output
- Aya receives a **semantic description**, not raw pixels
- The scout's note explains what's on screen in natural language
- Targets include metadata (type, text, relationships)

#### 5. Aya Decision Making
```python
# Aya reasons on structured state
if "login_form" in packet.scout_note:
    if "already_logged_in" not in packet.scout_note:
        action = propose_action(
            type="fill_form",
            target="input_email",
            value="user@example.com"
        )
```

---

## 4. WSS Streaming

### Subscribe to vision.classification.eagle Topic

The WebSocket streaming interface for real-time vision data:

```python
import asyncio
import websockets
import json

async def subscribe_vision_stream():
    uri = "wss://netjer.ai/ws/vision"
    
    async with websockets.connect(uri) as ws:
        # Subscribe to Eagle classification topic
        await ws.send(json.dumps({
            "action": "subscribe",
            "topic": "vision.classification.eagle"
        }))
        
        async for message in ws:
            envelope = json.loads(message)
            handle_vision_packet(envelope)
```

### TransportEnvelope Format

```python
{
  "type": "vision.classification.eagle",
  "timestamp": "2026-03-18T07:45:00.123Z",
  "source": "advanced-vision-local",
  "payload": {
    # The Image Packet (see Section 2)
    "episode_type": "fresh",
    "full_frame_ref": "data:image/jpeg;base64,/9j/4AAQ...",
    "roi_refs": [...],
    "targets": [...],
    "scout_note": "...",
    "needs_review": false,
    "metadata": {...}
  },
  "routing": {
    "session_id": "sess_abc123",
    "agent_id": "aya_001",
    "priority": "normal"  # normal | urgent | background
  }
}
```

### Transform to OpenClaw Format

```python
def transform_to_openclaw(envelope: dict) -> dict:
    """Convert TransportEnvelope to OpenClaw-compatible format."""
    
    payload = envelope["payload"]
    
    return {
        "role": "system",
        "content": [
            {
                "type": "text",
                "text": f"[Vision Scout] {payload['scout_note']}"
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": payload["full_frame_ref"]
                }
            }
        ],
        "metadata": {
            "episode_type": payload["episode_type"],
            "targets": payload["targets"],
            "needs_review": payload["needs_review"],
            "timestamp": envelope["timestamp"]
        }
    }
```

### Connection Management

```python
class VisionStreamClient:
    def __init__(self, on_packet):
        self.on_packet = on_packet
        self.ws = None
        self.reconnect_delay = 1.0
        
    async def connect(self):
        while True:
            try:
                self.ws = await websockets.connect(VISION_WS_URI)
                self.reconnect_delay = 1.0
                await self._subscribe()
                await self._listen()
            except Exception as e:
                logger.error(f"Vision stream error: {e}")
                await asyncio.sleep(self.reconnect_delay)
                self.reconnect_delay = min(self.reconnect_delay * 2, 30)
    
    async def _subscribe(self):
        await self.ws.send(json.dumps({
            "action": "subscribe",
            "topic": "vision.classification.eagle",
            "filter": {
                "needs_review": True,  # Only reviewed packets
                "min_confidence": 0.8
            }
        }))
```

---

## 5. Response Format

### How Aya Sends Actions Back

Aya proposes actions in a structured format before execution:

```python
{
  "type": "action_proposal",
  "proposal_id": "prop_xyz789",
  "timestamp": "2026-03-18T07:45:01.456Z",
  "context": {
    "session_id": "sess_abc123",
    "trigger_packet": "pkt_def456"
  },
  "actions": [
    {
      "sequence": 1,
      "type": "click",
      "target": {
        "id": "btn_submit",
        "bbox": [0.45, 0.67, 0.10, 0.05],
        "reference": "center"
      },
      "reasoning": "Click submit to complete form",
      "human_approval": "suggested"  # required | suggested | auto
    },
    {
      "sequence": 2,
      "type": "type",
      "target": {
        "id": "input_email"
      },
      "text": "user@example.com",
      "clear_first": True,
      "reasoning": "Fill email field",
      "human_approval": "required"
    },
    {
      "sequence": 3,
      "type": "wait",
      "duration_ms": 500,
      "reasoning": "Wait for page transition"
    }
  ],
  "verification": {
    "expected_state": "form_submitted",
    "timeout_ms": 5000,
    "on_failure": "retry_once"
  }
}
```

### Action Types

| Type | Parameters | Description |
|------|------------|-------------|
| `click` | `target`, `button` (left/right) | Mouse click on element |
| `double_click` | `target` | Double-click action |
| `type` | `target`, `text`, `clear_first` | Keyboard input |
| `key_press` | `keys` (list) | Hotkey combinations |
| `scroll` | `direction`, `amount`, `target` | Scroll action |
| `move` | `target` | Move cursor without clicking |
| `wait` | `duration_ms`, `condition` | Pause execution |
| `screenshot` | `region` | Capture for verification |

### Proposal-Before-Execution Pattern

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│    Aya      │────▶│  Propose    │────▶│  Human/     │────▶│  Execute    │
│   Reasons   │     │   Action    │     │  Auto-Check │     │   Action    │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
                                              │
                                              ▼
                                        ┌─────────────┐
                                        │   Reject    │
                                        │  + Explain  │
                                        └─────────────┘
```

#### Approval Levels

| Level | Description | Use Case |
|-------|-------------|----------|
| `required` | Human must approve | Destructive actions, payments, sensitive data |
| `suggested` | Human notified, can override | Normal interactions, form fills |
| `auto` | Execute immediately | Low-risk, verified patterns, internal navigation |

#### Execution Confirmation

```python
# Response sent after action execution
{
  "type": "action_result",
  "proposal_id": "prop_xyz789",
  "status": "success",  # success | failure | timeout
  "executed_at": "2026-03-18T07:45:02.123Z",
  "actions_completed": [1, 2, 3],
  "verification": {
    "passed": True,
    "actual_state": "form_submitted",
    "screenshot_ref": "after_action.jpg"
  },
  "error": None  # or error details if failed
}
```

---

## Configuration

### Environment Variables

```bash
# Vision System
VISION_WS_URI=wss://netjer.ai/ws/vision
VISION_TOPIC=vision.classification.eagle
VISION_CAPTURE_INTERVAL_MS=1000

# OpenClaw Integration
OPENCLAW_AGENT_ID=aya_001
OPENCLAW_DEFAULT_APPROVAL=suggested  # required | suggested | auto

# YOLO Model
YOLO_MODEL_PATH=models/yolov8n-ui.pt
YOLO_CONFIDENCE_THRESHOLD=0.5
YOLO_IOU_THRESHOLD=0.45

# Eagle Scout
EAGLE_CONTEXT_WINDOW=5  # Frames to keep in context
EAGLE_MIN_CHANGE_THRESHOLD=0.1  # 10% change to trigger update
```

### Example Integration Code

```python
# Complete integration example
from advanced_vision import VisionSystem
from openclaw_client import OpenClawAgent

class ComputerUseController:
    def __init__(self):
        self.vision = VisionSystem()
        self.aya = OpenClawAgent(agent_id="aya_001")
        
    async def start(self):
        # Start vision pipeline
        await self.vision.start(
            on_detection=self._handle_detection
        )
        
        # Subscribe to vision stream
        await self.aya.subscribe_vision(
            callback=self._on_vision_packet
        )
    
    async def _on_vision_packet(self, packet):
        """Handle incoming vision packet from WSS."""
        
        # Skip if needs human review and we're in auto mode
        if packet["needs_review"] and not self.aya.is_supervised():
            return
            
        # Send to Aya for reasoning
        response = await self.aya.reason(
            context=packet,
            prompt=f"Analyze this screen state: {packet['scout_note']}"
        )
        
        # Handle action proposals
        if response.get("actions"):
            await self._handle_proposal(response)
    
    async def _handle_proposal(self, proposal):
        """Execute approved actions."""
        
        for action in proposal["actions"]:
            # Check approval level
            if action["human_approval"] == "required":
                approved = await self.request_human_approval(action)
                if not approved:
                    continue
                    
            # Execute action
            result = await self.vision.execute(action)
            
            # Verify result
            if not result["verification"]["passed"]:
                await self.handle_failure(action, result)
```

---

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| High latency | Large base64 images | Use file paths instead of inline base64 |
| Missed detections | Low confidence threshold | Adjust `YOLO_CONFIDENCE_THRESHOLD` |
| False positives | No NMS overlap filtering | Check `YOLO_IOU_THRESHOLD` |
| Connection drops | Network instability | Implement exponential backoff reconnect |
| Action failures | Coordinate scaling | Verify bbox normalization (0-1 vs pixels) |

### Debug Logging

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("vision.openclaw")

# Log packet flow
logger.debug(f"Packet generated: {packet['episode_type']}")
logger.debug(f"Targets detected: {len(packet['targets'])}")
logger.debug(f"Scout note: {packet['scout_note']}")
```

---

## Related Documents

- [ARCHITECTURE.md](./ARCHITECTURE.md) - System architecture overview
- [Service contracts](../SERVICE_CONTRACTS.md) - API contracts
- [Repo skill](../SKILL.md) - Skill configuration
- [Agent swarm contract](./process/agent-swarm-contract.md) - Multi-agent coordination

---

## Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2026-03-18 | 1.0.0 | Initial documentation |
