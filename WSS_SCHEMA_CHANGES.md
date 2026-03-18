# WSS Schema Compliance - Changes Needed

## Summary

This document lists the **specific changes** required for each publisher to achieve full schema compliance.

**Status:** Adapter ready, migration plan documented, implementation pending.

---

## Files Created

1. **`src/advanced_vision/trading/wss_schema_adapter.py`** - Schema adapter implementation
   - `EventEnvelope` dataclass matching event_envelope.schema.json
   - `SchemaAdapter` class with wrap methods for each topic
   - Payload builders for scout_event, trading_packet, ui_packet
   - Artifact reference builders with checksum support
   - Validation helper functions

2. **`WSS_SCHEMA_MIGRATION.md`** - Comprehensive migration plan
   - Current vs target state analysis
   - Per-topic changes needed
   - Migration phases and testing approach

---

## Specific Changes Per Publisher

### 1. wss_yolo_publisher_v2.py

**Current Code:**
```python
envelope = TransportEnvelope(
    event_type="detection_batch",
    schema_family=SchemaFamily.DETECTION,
    source="yolo",
    frame_ref=frame_id,
    trace_id=self._trace_id,
    payload={
        "timestamp": timestamp,
        "count": len(self._batch_buffer),
        "detections": self._batch_buffer,
    }
)
```

**Required Changes:**

| Line | Change | Details |
|------|--------|---------|
| Import | Add | `from advanced_vision.trading.wss_schema_adapter import SchemaAdapter, Mode` |
| `__init__` | Add | `self._adapter = SchemaAdapter(mode=Mode.TRADING, base_dir=frame_save_dir)` |
| `set_trace_id` | Modify | Also call `self._adapter.set_trace_id(trace_id)` |
| `clear_trace_id` | Modify | Also call `self._adapter.clear_trace_id()` |
| `_flush_batch` | Replace | Use `self._adapter.wrap_detection_batch()` |

**New `_flush_batch` implementation:**
```python
async def _flush_batch(self) -> None:
    """Send batched detections as schema-compliant envelope."""
    if not self._batch_buffer:
        return
    
    # Get frame_id from first detection
    frame_id = self._batch_buffer[0].get("frame_id", "unknown")
    inference_time = self._batch_buffer[0].get("inference_time_ms", 0.0)
    
    envelope = self._adapter.wrap_detection_batch(
        frame_id=frame_id,
        detections=self._batch_buffer,
        inference_time_ms=inference_time,
        trace_id=self._trace_id,
        metadata={"batch_size": len(self._batch_buffer)},
    )
    
    if self._publisher.is_connected:
        await self._publisher.publish(envelope, self.DEFAULT_TOPIC)
    
    self._batch_buffer = []
```

---

### 2. wss_sam_publisher_v2.py

**Current Code:**
```python
envelope = TransportEnvelope(
    event_type="segmentation_batch",
    schema_family=SchemaFamily.SEGMENTATION,
    source="sam",  # ❌ Wrong source
    trace_id=self._trace_id,
    payload={
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "count": len(self._batch_buffer),
        "masks": self._batch_buffer,
    }
)
```

**Required Changes:**

| Line | Change | Details |
|------|--------|---------|
| Import | Add | `from advanced_vision.trading.wss_schema_adapter import SchemaAdapter, Mode` |
| `__init__` | Add | `self._adapter = SchemaAdapter(mode=Mode.TRADING, base_dir=mask_save_dir)` |
| `set_trace_id` | Modify | Also call `self._adapter.set_trace_id(trace_id)` |
| `source="sam"` | **Rename** | Source should be `"mobilesam"` |
| `_flush_batch` | Replace | Use `self._adapter.wrap_segmentation_batch()` |

**Note:** The `publish_segmentation` method needs to track roi_ids for artifact_refs.

---

### 3. wss_eagle_publisher_v2.py

**Current Code:**
```python
envelope = TransportEnvelope(
    event_type="classification_batch",
    schema_family=SchemaFamily.CLASSIFICATION,
    source="eagle",  # ❌ Not in source enum (needs mapping)
    trace_id=self._trace_id,
    payload={...}
)
```

**Required Changes:**

| Line | Change | Details |
|------|--------|---------|
| Import | Add | `from advanced_vision.trading.wss_schema_adapter import SchemaAdapter, Mode` |
| `__init__` | Add | `self._adapter = SchemaAdapter(mode=Mode.TRADING)` |
| `set_trace_id` | Modify | Also call `self._adapter.set_trace_id(trace_id)` |
| `_flush_batch` | Replace | Use `self._adapter.wrap_classification()` |
| Classification | Map | Use `EAGLE_TO_SCOUT_CLASSIFICATION` mapping |

**Key Mapping:**
```python
# Classifications need to map to scout_event.schema.json enum:
"order_ticket" → ScoutClassification.TICKET_UPDATE
"chart_update" → ScoutClassification.CHART_UPDATE
"confirm_dialog" → ScoutClassification.MODAL_DIALOG
"warning_dialog" → ScoutClassification.ALERT_CONDITION
```

---

### 4. wss_analysis_publisher_v2.py

**Current Code:**
```python
envelope = TransportEnvelope(
    event_type="analysis",
    schema_family=SchemaFamily.ANALYSIS,
    source="qwen",
    frame_ref=frame_id,
    trace_id=self._trace_id,
    payload={
        "timestamp": timestamp,
        "frame_id": frame_id,
        "analysis": analysis,
        "risk_level": risk_level,
        "recommendation": recommendation,
    }
)
```

**Required Changes:**

| Line | Change | Details |
|------|--------|---------|
| Import | Add | `from advanced_vision.trading.wss_schema_adapter import SchemaAdapter, Mode, RiskLevel, SuggestedAction` |
| `__init__` | Add | `self._adapter = SchemaAdapter(mode=Mode.TRADING)` and accept mode parameter |
| `set_trace_id` | Modify | Also call `self._adapter.set_trace_id(trace_id)` |
| `publish_analysis` | Replace | Use `self._adapter.wrap_analysis()` |
| Risk level | Validate | Must be one of: none, low, medium, high, critical |
| Recommendation | Map | Map to trading_packet.suggested_action enum |

**Recommendation Mapping:**
```python
# Current recommendations → trading_packet.suggested_action
"continue" → SuggestedAction.MONITOR
"note" → SuggestedAction.MONITOR
"warn" → SuggestedAction.REVIEW_DETAILS
"hold" → SuggestedAction.HOLD
"pause" → SuggestedAction.ALERT_HUMAN
"escalate" → SuggestedAction.CONFIRM_EXIT
```

---

## Configuration Changes

### config/wss_config.yaml

Add schema compliance configuration:

```yaml
# New section for schema compliance
schema_compliance:
  enabled: false  # Set to true to enable (default false during migration)
  schema_version: "1.0.0"
  mode: "trading"  # or "ui"
  enable_checksums: true
  
  # Artifact paths (relative to base_dir)
  artifact_paths:
    frames: "frames"
    masks: "masks"
    clips: "clips"
    logs: "logs"
```

---

## Schema Updates Needed

### schemas/event_envelope.schema.json

The source enum may need updating:

```json
"source": {
  "type": "string",
  "enum": [
    "capture",
    "yolo",
    "mobilesam",
    "eagle",  // <- Add this (currently missing)
    "qwen",
    "governor",
    "external_review",
    "system"
  ]
}
```

**Alternative:** Map "eagle" to "capture" in the adapter (already done).

---

## Testing Requirements

### Unit Tests to Add

1. **test_schema_adapter.py**
```python
def test_detection_envelope_structure():
    """Verify detection envelope has all required fields."""
    adapter = SchemaAdapter(mode="trading")
    envelope = adapter.wrap_detection_batch(...)
    
    assert envelope.event_id
    assert envelope.timestamp
    assert envelope.source == Source.YOLO
    assert envelope.mode == Mode.TRADING
    assert envelope.schema_version == "1.0.0"
    assert envelope.payload_type == PayloadType.SCOUT_EVENT
    assert len(envelope.artifact_refs) >= 1

def test_trace_id_propagation():
    """Verify trace_id is passed through correctly."""
    adapter = SchemaAdapter(mode="trading")
    adapter.set_trace_id("trace-123")
    
    envelope = adapter.wrap_detection_batch(...)
    assert envelope.trace_id == "trace-123"

def test_parent_child_relationship():
    """Verify parent_event_id links events correctly."""
    adapter = SchemaAdapter(mode="trading")
    parent = adapter.wrap_detection_batch(...)
    child = adapter.wrap_classification(..., parent_event_id=parent.event_id)
    
    assert child.parent_event_id == parent.event_id

def test_artifact_refs_valid_paths():
    """Verify artifact_refs point to valid relative paths."""
    envelope = adapter.wrap_detection_batch(frame_id="frame_001", ...)
    
    for ref in envelope.artifact_refs:
        assert ref.path.startswith("frames/") or ref.path.startswith("masks/")
        assert not ref.path.startswith("/")  # Must be relative
```

### Integration Tests to Add

1. **test_schema_pipeline.py**
```python
def test_full_pipeline_schema_compliance():
    """Verify all pipeline stages produce schema-compliant envelopes."""
    # Run detection → segmentation → classification → analysis
    # Verify each envelope passes JSON schema validation

def test_mode_switching():
    """Verify trading vs ui mode produces correct payload types."""
    trading_adapter = SchemaAdapter(mode="trading")
    ui_adapter = SchemaAdapter(mode="ui")
    
    trading_envelope = trading_adapter.wrap_analysis(...)
    ui_envelope = ui_adapter.wrap_analysis(...)
    
    assert trading_envelope.payload_type == PayloadType.TRADING_PACKET
    assert ui_envelope.payload_type == PayloadType.UI_PACKET
```

---

## Rollout Plan

### Phase 1: Adapter Deployment (Week 1)
- [x] Create `wss_schema_adapter.py`
- [x] Create `WSS_SCHEMA_MIGRATION.md`
- [ ] Add unit tests for adapter
- [ ] Add integration tests
- [ ] Code review

### Phase 2: Feature Flag Integration (Week 2)
- [ ] Add `schema_compliance.enabled` config option
- [ ] Update each publisher to use adapter when enabled
- [ ] Default to `false` (backward compatible)
- [ ] Test both paths

### Phase 3: Validation (Week 3)
- [ ] Enable schema validation (log-only mode)
- [ ] Run full pipeline tests
- [ ] Fix any validation errors
- [ ] Monitor logs for issues

### Phase 4: Migration (Week 4)
- [ ] Enable schema compliance in dev environment
- [ ] Run integration tests
- [ ] Enable in production (with rollback plan)
- [ ] Remove old TransportEnvelope path

---

## Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Schema validation fails | Medium | High | Feature flag, log-only validation first |
| Artifact refs invalid | Low | Medium | Checksum validation, graceful degradation |
| Performance overhead | Low | Low | Efficient dataclasses, async checksums |
| Breaking change | High | High | Dual-path publishing, gradual rollout |

---

## Success Metrics

- [ ] All 4 publishers emit schema-compliant envelopes
- [ ] 100% of envelopes pass JSON schema validation
- [ ] Trace ID propagation works across all stages
- [ ] Zero breaking changes during migration
- [ ] All tests pass with schema validation enabled
- [ ] Performance overhead < 5ms per envelope

---

## Quick Reference: Adapter Usage

```python
from advanced_vision.trading.wss_schema_adapter import (
    SchemaAdapter, Mode, validate_envelope_against_schema
)

# Create adapter
adapter = SchemaAdapter(
    mode=Mode.TRADING,  # or Mode.UI
    schema_version="1.0.0",
    base_dir="/tmp/advanced_vision",
)

# Set trace ID for distributed tracing
adapter.set_trace_id(str(uuid.uuid4()))

# Wrap detection results
envelope = adapter.wrap_detection_batch(
    frame_id="frame_001",
    detections=[{"class": "chart", "confidence": 0.95}],
    inference_time_ms=15.5,
)

# Validate (optional)
is_valid, errors = validate_envelope_against_schema(envelope)
assert is_valid, errors

# Publish
await publisher.publish(envelope)
```
