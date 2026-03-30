# WSS Schema Migration Plan

## Overview

This document outlines the migration from WSS v2 transport envelopes to full schema-compliant event envelopes as defined in `schemas/`.

**Current State:** WSS v2 is active with `TransportEnvelope` (basic wrapper)
**Target State:** Full schema compliance with `event_envelope` + typed payloads

---

## Current State Analysis

### TransportEnvelope (Current)
```python
class TransportEnvelope(BaseModel):
    event_id: str
    event_type: str
    schema_family: SchemaFamily  # detection, segmentation, classification, analysis, system
    created_at: str
    source: str
    frame_ref: str | None
    trace_id: str | None
    payload: dict[str, Any]
    topic: str | None  # Server-side filled
    received_at: str | None  # Server-side filled
```

### Schema Requirements (Target)
```json
{
  "event_id": "uuid",
  "timestamp": "ISO8601",           // Different field name from created_at
  "source": "enum",                 // capture, yolo, mobilesam, eagle, qwen, governor, external_review, system
  "mode": "enum",                   // ui, trading, system, diagnostic (NEW)
  "schema_version": "1.0.0",        // SemVer (NEW)
  "trace_id": "uuid",
  "parent_event_id": "uuid",        // NEW
  "artifact_refs": [...],           // Structured artifact refs (NEW)
  "work_item_id": "string",         // NEW
  "payload": {...},
  "payload_type": "enum",           // discriminator: ui_packet, trading_packet, scout_event, etc.
  "metadata": {...}
}
```

---

## Changes Needed Per Topic

### 1. vision.detection.yolo
**Current Publisher:** `wss_yolo_publisher_v2.py`

**Current Payload:**
```python
{
    "timestamp": "ISO8601",
    "count": 10,
    "detections": [...]
}
```

**Required Changes:**
| Field | Current | Required | Action |
|-------|---------|----------|--------|
| `source` | `"yolo"` | `"yolo"` in enum | ✅ Valid |
| `mode` | Missing | `"trading"` or `"ui"` | Add |
| `schema_version` | Missing | `"1.0.0"` | Add |
| `payload_type` | Missing | `"scout_event"` | Add |
| `artifact_refs` | Missing | Array with frame refs | Add |
| `frame_ref` | In envelope | Move to artifact_refs[0] | Restructure |

**Mapping:**
```python
# Current
TransportEnvelope(
    event_type="detection_batch",
    schema_family=SchemaFamily.DETECTION,
    source="yolo",
    frame_ref=frame_id,
    payload={"detections": [...]}
)

# Target EventEnvelope
EventEnvelope(
    event_id=uuid7(),
    timestamp=datetime.now(timezone.utc).isoformat(),
    source="yolo",
    mode="trading",  # or "ui" based on config
    schema_version="1.0.0",
    trace_id=trace_id,
    artifact_refs=[
        {"type": "frame", "path": f"frames/{frame_id}.png", "checksum": "..."}
    ],
    payload_type="scout_event",
    payload=ScoutEventPayload(...)  # Or keep as dict for flexibility
)
```

---

### 2. vision.segmentation.sam
**Current Publisher:** `wss_sam_publisher_v2.py`

**Current Payload:**
```python
{
    "timestamp": "ISO8601",
    "count": 5,
    "masks": [...]
}
```

**Required Changes:**
| Field | Current | Required | Action |
|-------|---------|----------|--------|
| `source` | `"sam"` | `"mobilesam"` | **Rename** |
| `mode` | Missing | `"trading"` | Add |
| `schema_version` | Missing | `"1.0.0"` | Add |
| `payload_type` | Missing | `"scout_event"` | Add |
| `artifact_refs` | Missing | Array with mask refs | Add |

**Mapping:**
```python
# Source rename
"sam" → "mobilesam"

# Artifact refs for masks
artifact_refs=[
    {"type": "frame", "path": f"frames/{frame_id}.png"},
    {"type": "roi", "path": f"masks/{roi_id}.png", "checksum": mask_checksum}
]
```

---

### 3. vision.classification.eagle
**Current Publisher:** `wss_eagle_publisher_v2.py`

**Current Payload:**
```python
{
    "timestamp": "ISO8601",
    "frame_id": "...",
    "roi_id": "...",
    "classification": "order_ticket",
    "confidence": 0.95
}
```

**Required Changes:**
| Field | Current | Required | Action |
|-------|---------|----------|--------|
| `source` | `"eagle"` | `"eagle"` not in enum | **Add to enum** or use `"capture"` |
| `mode` | Missing | `"trading"` | Add |
| `schema_version` | Missing | `"1.0.0"` | Add |
| `payload_type` | Missing | `"scout_event"` | Add |
| `classification` | String | Must be in scout_event enum | Validate |

**Scout Event Classification Mapping:**
```python
# Current eagle classifications → Scout event classifications
{
    "order_ticket": "ticket_update",
    "chart_update": "chart_update", 
    "confirm_dialog": "modal_dialog",
    "warning_dialog": "alert_condition",
    "price_change": "chart_update",
    "signal_detected": "alert_condition"
}
```

---

### 4. vision.analysis.qwen
**Current Publisher:** `wss_analysis_publisher_v2.py`

**Current Payload:**
```python
{
    "timestamp": "ISO8601",
    "frame_id": "...",
    "analysis": "...",
    "risk_level": "high",
    "recommendation": "pause"
}
```

**Required Changes:**
| Field | Current | Required | Action |
|-------|---------|----------|--------|
| `source` | `"qwen"` | `"qwen"` in enum | ✅ Valid |
| `mode` | Missing | `"trading"` | Add |
| `schema_version` | Missing | `"1.0.0"` | Add |
| `payload_type` | Missing | `"trading_packet"` or `"ui_packet"` | Add |
| `risk_level` | String | Must match enum | Validate values |
| `recommendation` | String | Must match suggested_action enum | Map values |

**Risk Level Mapping:**
```python
# Current → trading_packet.risk_level
{
    "none": "none",
    "low": "low", 
    "medium": "medium",
    "high": "high",
    "critical": "critical"
}  # Direct mapping, just validate
```

**Recommendation Mapping:**
```python
# Current → trading_packet.suggested_action
{
    "continue": "monitor",
    "note": "monitor",
    "warn": "review_details", 
    "hold": "hold",
    "pause": "alert_human",
    "escalate": "confirm_exit"
}
```

---

## Artifact Reference Structure

### Current
- `frame_ref` - Single string reference to frame

### Required
```json
{
  "artifact_refs": [
    {
      "type": "frame",
      "path": "frames/frame_001234.png",
      "checksum": "sha256:abc123..."
    },
    {
      "type": "roi", 
      "path": "masks/roi_001.png",
      "checksum": "sha256:def456..."
    },
    {
      "type": "clip",
      "path": "clips/clip_001.webm"
    }
  ]
}
```

---

## Migration Steps

### Phase 1: Adapter Implementation (Ready)
1. ✅ Create `wss_schema_adapter.py`
   - `EventEnvelope` class matching schema
   - `SchemaAdapter` for wrapping TransportEnvelope
   - `ArtifactRefBuilder` for generating artifact_refs
   - `PayloadTypeMapper` for determining payload_type

### Phase 2: Publisher Updates (Next)
2. Update `wss_yolo_publisher_v2.py`
   - Import `SchemaAdapter`
   - Use `adapter.wrap_detection_batch()` instead of raw TransportEnvelope
   - Add frame checksum calculation
   - Set mode from config

3. Update `wss_sam_publisher_v2.py`
   - Change source from `"sam"` to `"mobilesam"`
   - Use `adapter.wrap_segmentation_batch()`
   - Add ROI artifact refs

4. Update `wss_eagle_publisher_v2.py`
   - Use `adapter.wrap_classification()`
   - Map classifications to scout_event schema
   - Add frame + ROI artifact refs

5. Update `wss_analysis_publisher_v2.py`
   - Use `adapter.wrap_analysis()`
   - Map risk_level/recommendation to trading_packet schema
   - Support both trading and ui modes

### Phase 3: Schema Enum Updates
6. Update `event_envelope.schema.json`
   - Add `"eagle"` to source enum OR
   - Map eagle to `"capture"` source in adapter

### Phase 4: Testing
7. Schema validation tests
   - Validate all published envelopes against JSON schemas
   - Check payload_type discriminator values
   - Verify artifact_refs paths exist

8. Integration tests
   - Full pipeline: detection → segmentation → classification → analysis
   - Trace ID propagation
   - Artifact ref resolution

### Phase 5: Rollout
9. Deploy adapter alongside existing code
10. Enable schema validation (optional, log-only)
11. Switch to schema-compliant publishing
12. Remove old TransportEnvelope path

---

## Testing Approach

### Unit Tests
```python
def test_detection_envelope_schema_compliance():
    adapter = SchemaAdapter(mode="trading")
    envelope = adapter.wrap_detection_batch(
        frame_id="frame_001",
        detections=[...],
        trace_id="..."
    )
    
    # Validate against JSON schema
    validate(envelope.to_dict(), event_envelope_schema)
    assert envelope.payload_type == "scout_event"
    assert envelope.source == "yolo"
    assert len(envelope.artifact_refs) >= 1
```

### Integration Tests
```python
def test_full_pipeline_trace_propagation():
    trace_id = uuid7()
    
    # Detection
    yolo_pub.publish_detection(..., trace_id=trace_id)
    
    # Segmentation  
    sam_pub.publish_segmentation(..., trace_id=trace_id)
    
    # Classification
    eagle_pub.publish_classification(..., trace_id=trace_id)
    
    # Analysis
    analysis_pub.publish_analysis(..., trace_id=trace_id)
    
    # All envelopes should have same trace_id
    assert all(e.trace_id == trace_id for e in received_envelopes)
```

### Validation Tests
```python
def test_artifact_refs_point_to_valid_paths():
    envelope = create_test_envelope()
    for ref in envelope.artifact_refs:
        full_path = base_dir / ref["path"]
        assert full_path.exists(), f"Missing artifact: {ref['path']}"
```

---

## Files to Modify

### New Files
1. `src/advanced_vision/trading/wss_schema_adapter.py` - Adapter implementation

### Modified Files (in order)
1. `src/advanced_vision/trading/wss_yolo_publisher_v2.py`
2. `src/advanced_vision/trading/wss_sam_publisher_v2.py` 
3. `src/advanced_vision/trading/wss_eagle_publisher_v2.py`
4. `src/advanced_vision/trading/wss_analysis_publisher_v2.py`

### Optional Schema Updates
1. `schemas/event_envelope.schema.json` - Add "eagle" to source enum

---

## Backward Compatibility

### Strategy: Dual-Path Publishing
During migration, publishers can support both formats:

```python
def publish_detection(self, ..., schema_compliant: bool = False):
    if schema_compliant:
        envelope = self._adapter.wrap_detection_batch(...)
    else:
        envelope = TransportEnvelope(...)  # Legacy
    
    await self._publisher.publish(envelope)
```

### Configuration
```yaml
# config/wss_config.yaml
schema_compliant: false  # Default to false during migration
schema_version: "1.0.0"
mode: "trading"  # or "ui"
```

---

## Success Criteria

- [ ] All publishers emit schema-compliant event envelopes
- [ ] All envelopes pass JSON schema validation
- [ ] Trace IDs propagate correctly through pipeline
- [ ] Artifact refs point to valid, existing files
- [ ] payload_type discriminator is set correctly for all events
- [ ] Mode (ui/trading) is correctly configured per deployment
- [ ] Backward compatibility maintained during transition
- [ ] All tests pass with schema validation enabled

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Schema validation fails | High | Log-only validation during transition |
| Artifact refs invalid | Medium | Checksum validation, graceful degradation |
| Performance overhead | Low | Adapter uses efficient dataclasses |
| Breaking change | High | Dual-path publishing, feature flag |
| Source enum mismatch | Medium | Adapter handles mapping internally |
