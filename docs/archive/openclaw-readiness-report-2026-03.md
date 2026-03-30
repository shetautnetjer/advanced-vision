# OpenClaw Integration Readiness Report

**Project:** advanced-vision  
**Location:** /home/netjer/.openclaw/workspace/plane-a/projects/advanced-vision  
**Audit Date:** 2026-03-18  
**Auditor:** Aya (Subagent)  

---

## Executive Summary

The advanced-vision project has **strong foundational architecture** for OpenClaw integration. The system is already designed around **image packets (not video)**, uses **structured JSON schemas**, and has a **clean WebSocket-based pub/sub architecture** that can bridge to OpenClaw agents.

**Readiness Score: 7/10** - Good foundation with specific gaps to address.

---

## ✅ What's Already Ready

### 1. Image Packets (NOT Video Streaming)

| Aspect | Status | Evidence |
|--------|--------|----------|
| Screenshot capture | ✅ Ready | `screenshot_full()` returns discrete PNG artifacts |
| ROI extraction | ✅ Ready | `ROI.crop_path` points to individual image files |
| Discrete frames | ✅ Ready | Each frame gets unique `frame_id` and `frame_ref` |
| Video is optional | ✅ Ready | Video recording exists but is NOT the primary data flow |

**Key Files:**
- `src/advanced_vision/tools/screen.py` - Screenshot capture
- `src/advanced_vision/trading/roi.py` - ROI extraction with crop paths

### 2. Curated Perception with Structured JSON

| Component | Status | Schema Location |
|-----------|--------|-----------------|
| Transport Envelope | ✅ Ready | `wss_server_v2.py::TransportEnvelope` |
| ROI References | ✅ Ready | `trading/events.py::ROI` + `trading/roi.py` |
| Frame References | ✅ Ready | `TransportEnvelope.frame_ref` field |
| Scout Notes | ✅ Ready | `EagleClassificationPayload` with reasoning |
| Reviewer Assessment | ✅ Ready | `ReviewerAssessment` + `QwenAnalysisPayload` |

**TransportEnvelope Schema (v2):**
```python
class TransportEnvelope(BaseModel):
    event_id: str           # UUID v4
    event_type: str         # "detection", "classification", etc.
    schema_family: SchemaFamily  # detection, segmentation, classification, analysis
    created_at: str         # ISO 8601 timestamp
    source: str             # "yolo", "eagle", "qwen", etc.
    frame_ref: str | None   # Reference to associated frame/image
    trace_id: str | None    # Distributed tracing ID
    payload: dict           # Event-specific data
```

### 3. Discrete Packet Architecture

| Feature | Status | Implementation |
|---------|--------|----------------|
| Discrete messages | ✅ Ready | WebSocket v2 uses individual TransportEnvelope |
| Micro-episode support | ✅ Partial | Single frames supported; burst/pair needs wrapper |
| Non-streaming | ✅ Ready | Each event is independent JSON packet |
| Batching available | ✅ Ready | `classification_batch` event type exists |

### 4. Clean Boundary for OpenClaw Agent

| Component | Status | Purpose |
|-----------|--------|---------|
| WSS Agent Subscriber | ✅ Ready | `wss_agent_subscriber.py` - Non-blocking WebSocket client |
| Schema filtering | ✅ Ready | Filter by "ui", "trading", or "both" |
| Ring buffer | ✅ Ready | Stores recent 100 messages |
| Callback support | ✅ Ready | Python callbacks on message receipt |
| v2 Subscriber | ✅ Ready | `wss_agent_subscriber_v2.py` - Topic-based |

**Current OpenClaw Integration Point:**
```python
from advanced_vision.wss_agent_subscriber import WSSAgentSubscriber

subscriber = WSSAgentSubscriber()
subscriber.subscribe(8004, schema="trading", callback=handle_pattern)
subscriber.start()  # Non-blocking
```

### 5. Scout Pre-Processing (Eagle Filters)

| Layer | Model | Role | Status |
|-------|-------|------|--------|
| Tripwire | YOLOv8n | Motion detection | ✅ Ready |
| Scout | Eagle2-2B | Fast classification | ✅ Ready |
| Reviewer | Qwen3.5-4B | Risk assessment | ✅ Ready |
| Overseer | Kimi | Escalation/second opinion | ✅ Designed |

**Evidence Bundle Structure:**
```python
class EvidenceBundle(BaseModel):
    event_id: str
    timestamp: str
    event_summary: str
    risk_indicators: list[str]
    roi_crop_paths: list[str]      # <-- Image packet refs (not full images!)
    reviewer_confidence: float | None
    reviewer_reasoning: str | None
    redacted_text: str | None
```

---

## ❌ What's Missing

### 1. Explicit OpenClaw Packet Schema

**Gap:** No dedicated packet format for sending to Aya/Kimi agents.

**Current State:** Uses generic WebSocket TransportEnvelope  
**Needed:** `OpenClawImagePacket` schema with OpenClaw-specific metadata

### 2. Micro-Episode Packet Types

**Gap:** No explicit support for "fresh screenshot", "burst of 3 frames", "before/after pair".

**Current State:** Single-frame events only  
**Needed:** Episode wrapper types:
- `SingleFramePacket` - One screenshot + metadata
- `BurstPacket` - 2-5 frames with temporal sequence
- `BeforeAfterPacket` - Pair with action context

### 3. OpenClaw Gateway/Bridge Module

**Gap:** No explicit bridge between WSS messages and OpenClaw agent format.

**Current State:** Agents must parse TransportEnvelope directly  
**Needed:** `OpenClawGateway` class that:
- Subscribes to WSS feeds
- Transforms to OpenClaw packets
- Handles image base64 encoding
- Manages agent context/session

### 4. Image Encoding for Agent Transport

**Gap:** ROIs are file paths, not embeddable image data.

**Current State:** `roi_crop_paths: list[str]` - paths only  
**Needed:** Option to include base64-encoded images for direct agent consumption

### 5. Agent Session Management

**Gap:** No explicit session/context tracking for multi-turn agent interactions.

**Current State:** `trace_id` exists but no session wrapper  
**Needed:** `AgentSession` with:
- Session ID
- Conversation history
- Pending image packets
- Context window management

---

## 📝 Specific Schema Recommendations

### Recommended: OpenClawImagePacket

```python
class OpenClawImagePacket(BaseModel):
    """Standard packet for sending curated perception to OpenClaw agents.
    
    Per Dad's guidance:
    - Image packets (NOT video)
    - Curated perception with ROI refs
    - Discrete packets (not continuous stream)
    - Micro-episodes: fresh screenshot, burst, before/after
    - Scout pre-processing via Eagle
    """
    
    # Packet metadata
    packet_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    packet_type: Literal["fresh_screenshot", "burst", "before_after", "roi_focus"]
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    # Source context
    source: str  # "advanced-vision"
    session_id: str | None = None
    trace_id: str | None = None
    
    # Episode data
    episode: EpisodeData
    
    # Curated perception (Dad's requirement #2)
    roi_refs: list[ROIRef] = Field(default_factory=list)
    scout_notes: ScoutNotes | None = None
    
    # Evidence for agent reasoning
    context: AgentContext


class EpisodeData(BaseModel):
    """Micro-episode content - one of these variants."""
    episode_type: Literal["single", "burst", "before_after"]
    
    # For packet_type="fresh_screenshot"
    single: SingleFrame | None = None
    
    # For packet_type="burst"
    burst: FrameBurst | None = None
    
    # For packet_type="before_after"
    before_after: BeforeAfterPair | None = None


class SingleFrame(BaseModel):
    """Single fresh screenshot."""
    frame_id: str
    image_path: str
    image_base64: str | None = None  # Optional inline encoding
    timestamp: str


class FrameBurst(BaseModel):
    """Burst of 2-5 frames for temporal context."""
    burst_id: str
    frames: list[SingleFrame]
    interval_ms: float  # Time between frames


class BeforeAfterPair(BaseModel):
    """Before/after pair showing action result."""
    action_id: str
    action_description: str
    before: SingleFrame
    after: SingleFrame
    change_detected: bool
    similarity_score: float | None = None


class ROIRef(BaseModel):
    """Reference to Region of Interest (not full image)."""
    roi_id: str
    frame_ref: str
    crop_path: str
    crop_base64: str | None = None  # Optional inline encoding
    bbox: BoundingBox
    element_type: str
    confidence: float


class ScoutNotes(BaseModel):
    """Pre-processed observations from Eagle scout."""
    classification: str  # e.g., "order_ticket", "chart_update"
    confidence: float
    is_trading_relevant: bool
    needs_reviewer: bool
    needs_overseer: bool
    quick_summary: str


class AgentContext(BaseModel):
    """Context for agent reasoning."""
    trading_event_type: str | None = None
    risk_level: str = "none"  # none, low, medium, high, critical
    urgency: str = "normal"   # low, normal, high, immediate
    previous_action: str | None = None
    pending_questions: list[str] = Field(default_factory=list)
```

### Recommended: OpenClawGateway

```python
class OpenClawGateway:
    """Bridge between advanced-vision WSS feeds and OpenClaw agents.
    
    Usage:
        gateway = OpenClawGateway(agent_callback=aya_handle_packet)
        gateway.start()
        
        # Packets auto-transformed and sent to agent
    """
    
    def __init__(
        self,
        agent_callback: Callable[[OpenClawImagePacket], None],
        wss_host: str = "localhost",
        wss_port: int = 8000,
        topics: list[str] = None,
        encode_images: bool = True,  # Base64 encode ROI crops
    ):
        self.agent_callback = agent_callback
        self.encode_images = encode_images
        self.subscriber = WSSSubscriberV2(topics=topics or ["vision.classification.eagle"])
    
    def start(self):
        """Start listening and forwarding to agent."""
        self.subscriber.on_message(self._transform_and_forward)
        self.subscriber.connect()
    
    def _transform_and_forward(self, envelope: TransportEnvelope):
        """Transform WSS envelope to OpenClaw packet."""
        packet = self._to_openclaw_packet(envelope)
        self.agent_callback(packet)
    
    def create_burst_packet(
        self,
        frames: list[str],  # Frame IDs
        scout_classifications: list[str],
    ) -> OpenClawImagePacket:
        """Create burst packet from multiple frames."""
        ...
    
    def create_before_after_packet(
        self,
        action: ActionResult,
        verification: VerificationResult,
    ) -> OpenClawImagePacket:
        """Create before/after packet showing action result."""
        ...
```

---

## 🎯 Example Packet Structures

### Example 1: Fresh Screenshot (Single Frame)

```json
{
  "packet_id": "pkt_abc123",
  "packet_type": "fresh_screenshot",
  "timestamp": "2026-03-18T14:30:00Z",
  "source": "advanced-vision",
  "session_id": "sess_tradingview_001",
  "trace_id": "trace_xyz789",
  "episode": {
    "episode_type": "single",
    "single": {
      "frame_id": "frame_0042",
      "image_path": "artifacts/screens/frame_0042.png",
      "timestamp": "2026-03-18T14:30:00Z"
    }
  },
  "roi_refs": [
    {
      "roi_id": "roi_chart_001",
      "frame_ref": "frame_0042",
      "crop_path": "artifacts/trading/roi_chart_001.png",
      "bbox": {"x": 100, "y": 100, "width": 800, "height": 500},
      "element_type": "chart_panel",
      "confidence": 0.95
    }
  ],
  "scout_notes": {
    "classification": "chart_update",
    "confidence": 0.92,
    "is_trading_relevant": true,
    "needs_reviewer": false,
    "needs_overseer": false,
    "quick_summary": "Price movement detected on AAPL chart"
  },
  "context": {
    "trading_event_type": "chart_update",
    "risk_level": "low",
    "urgency": "normal"
  }
}
```

### Example 2: Burst of 3 Frames

```json
{
  "packet_id": "pkt_def456",
  "packet_type": "burst",
  "timestamp": "2026-03-18T14:30:00Z",
  "source": "advanced-vision",
  "episode": {
    "episode_type": "burst",
    "burst": {
      "burst_id": "burst_001",
      "interval_ms": 500,
      "frames": [
        {"frame_id": "frame_0010", "image_path": "...", "timestamp": "..."},
        {"frame_id": "frame_0011", "image_path": "...", "timestamp": "..."},
        {"frame_id": "frame_0012", "image_path": "...", "timestamp": "..."}
      ]
    }
  },
  "roi_refs": [...],
  "scout_notes": {
    "classification": "order_ticket_sequence",
    "confidence": 0.88,
    "is_trading_relevant": true,
    "needs_reviewer": true,
    "quick_summary": "Order ticket appeared, user interacted, confirmation shown"
  },
  "context": {
    "trading_event_type": "order_ticket",
    "risk_level": "medium",
    "urgency": "high"
  }
}
```

### Example 3: Before/After Pair

```json
{
  "packet_id": "pkt_ghi789",
  "packet_type": "before_after",
  "timestamp": "2026-03-18T14:30:00Z",
  "source": "advanced-vision",
  "episode": {
    "episode_type": "before_after",
    "before_after": {
      "action_id": "action_click_submit",
      "action_description": "Clicked Submit Order button",
      "change_detected": true,
      "similarity_score": 0.72,
      "before": {
        "frame_id": "frame_0100",
        "image_path": "artifacts/screens/frame_0100.png",
        "timestamp": "2026-03-18T14:29:58Z"
      },
      "after": {
        "frame_id": "frame_0102",
        "image_path": "artifacts/screens/frame_0102.png",
        "timestamp": "2026-03-18T14:30:01Z"
      }
    }
  },
  "roi_refs": [...],
  "scout_notes": {
    "classification": "confirm_dialog",
    "confidence": 0.96,
    "is_trading_relevant": true,
    "needs_reviewer": true,
    "needs_overseer": true,
    "quick_summary": "Order submitted, confirmation dialog appeared - REQUIRES REVIEW"
  },
  "context": {
    "trading_event_type": "confirm_dialog",
    "risk_level": "high",
    "urgency": "immediate",
    "previous_action": "click_submit_order"
  }
}
```

---

## 🚀 Implementation Roadmap

### Phase 1: Schema Definition (1-2 days)
1. Create `src/advanced_vision/openclaw/schemas.py` with `OpenClawImagePacket`
2. Define episode types: SingleFrame, FrameBurst, BeforeAfterPair
3. Define ROIRef and ScoutNotes structures

### Phase 2: Gateway Module (2-3 days)
1. Create `src/advanced_vision/openclaw/gateway.py`
2. Implement WSS → OpenClaw packet transformation
3. Add optional base64 image encoding
4. Implement burst and before/after packet builders

### Phase 3: Integration (1-2 days)
1. Add OpenClaw gateway to skill_manifest.json
2. Create example: `examples/openclaw_bridge.py`
3. Document integration pattern in docs/

### Phase 4: Testing (1-2 days)
1. Test packet generation with real screenshots
2. Verify image encoding/decoding
3. Test end-to-end with mock agent callback

**Total Estimate: 5-9 days for production-ready integration**

---

## 📊 Compliance with Dad's Requirements

| Requirement | Status | Notes |
|-------------|--------|-------|
| 1. Image packets (NOT video) | ✅ **COMPLIANT** | PNG screenshots, ROI crops - no video streaming |
| 2. Curated perception | ✅ **COMPLIANT** | Eagle filters before Qwen/Kimi; structured JSON |
| 3. Discrete packets | ✅ **COMPLIANT** | TransportEnvelope is discrete; not continuous stream |
| 4. Micro-episodes | ⚠️ **PARTIAL** | Single frames ready; burst/pair needs wrapper |
| 5. Scout pre-processing | ✅ **COMPLIANT** | Eagle2-2B scout lane filters before escalation |

---

## 🎬 Bottom Line

**The advanced-vision project is architecturally sound for OpenClaw integration.**

The system already follows Dad's guidance:
- ✅ Image-based (not video)
- ✅ Structured JSON with ROI refs
- ✅ Discrete packets via WebSocket
- ✅ Scout (Eagle) pre-filters before reviewer/overseer

**Main gap:** Need explicit OpenClaw packet schema and gateway module to bridge WSS feeds to agent format.

**Recommendation:** Proceed with Phase 1 (schema definition) to unlock full OpenClaw integration.

---

## 📁 Key Files for Reference

| File | Purpose |
|------|---------|
| `src/advanced_vision/schemas.py` | Core Pydantic schemas |
| `src/advanced_vision/trading/events.py` | Trading event taxonomy |
| `src/advanced_vision/trading/roi.py` | ROI extraction & evidence bundles |
| `src/advanced_vision/wss_server_v2.py` | WebSocket v2 server with TransportEnvelope |
| `src/advanced_vision/wss_client_v2.py` | WebSocket v2 client/publisher |
| `src/advanced_vision/wss_agent_subscriber.py` | OpenClaw agent subscriber |
| `skill_manifest.json` | Tool definitions for MCP/OpenClaw |
| `dads-findings.md` | Dad's architecture guidance |
| `docs/WSS_V2_ARCHITECTURE.md` | WebSocket v2 documentation |
