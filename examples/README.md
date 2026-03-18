# Advanced Vision Example Packets

This directory contains example JSON packets for testing and validating the advanced-vision schema system. These examples are used for development, testing, and integration verification.

## Directory Structure

```
examples/
├── packets/
│   ├── valid/          # Valid examples that should pass schema validation
│   │   ├── ui_packet_example.json
│   │   ├── trading_packet_example.json
│   │   ├── scout_event_example.json
│   │   ├── external_review_request_example.json
│   │   ├── external_review_result_example.json
│   │   └── artifact_manifest_example.json
│   └── invalid/        # Invalid examples that should fail specific validation rules
│       ├── ui_packet_missing_required.json
│       ├── trading_packet_bad_risk.json
│       ├── scout_event_low_confidence.json
│       └── malformed_envelope.json
└── README.md           # This file
```

## Valid Examples

These examples represent realistic, properly-formed packets that should pass full schema validation:

### 1. `ui_packet_example.json` - Confirmation Dialog Detected
**Scenario:** User clicks "Remove Account" and a destructive confirmation dialog appears.

**Key Fields Demonstrated:**
- `mode`: "ui" - Indicates UI-mode operation
- `event_type`: "modal_appeared" - Classification of UI event
- `roi_refs`: Array of region-of-interest crops highlighting the modal and buttons
- `targets`: Actionable UI elements with click coordinates
- `risk_tags`: ["requires_confirmation", "destructive_action"] - Risk indicators
- `needs_external_review`: true - Requires human/AI review before proceeding

### 2. `trading_packet_example.json` - Price Spike + Position Update
**Scenario:** EURUSD price spike during ECB announcement with active position approaching stop-loss.

**Key Fields Demonstrated:**
- `mode`: "trading" - Trading-mode operation
- `event_type`: "price_movement" - Trading event classification
- `chart_regions`: Multiple chart views with price snapshots
- `ticket_regions`: Active position data with extracted fields
- `indicators`: Technical indicator signals with confidence scores
- `risk_level`: "high" - Scout-assessed risk classification
- `suggested_action`: "review_details" - Recommended next step

### 3. `scout_event_example.json` - Meaningful UI Change Classification
**Scenario:** Eagle2-2B scout classifies a significant UI change requiring escalation.

**Key Fields Demonstrated:**
- `classification`: "meaningful_ui_change" - Scout's classification
- `confidence`: 0.89 - Model confidence (0.0 to 1.0)
- `motion_metrics`: Pixel-level change statistics
- `escalation_recommended`: true - Whether to escalate to reviewer
- `artifact_refs`: Links to input frame and output ROIs

### 4. `external_review_request_example.json` - Request to Aya
**Scenario:** Request sent to Aya (OpenClaw/Kimi) for review of a UI confirmation dialog.

**Key Fields Demonstrated:**
- `reviewer_target`: Specifies agent identity, provider, and model
- `packet_ref`: Reference to packet being reviewed
- `context.image_refs`: Images available for review
- `context.recent_history`: Last 5 events for context
- `decision_options`: Available actions for reviewer
- `timeout_seconds`: Maximum wait time for response

### 5. `external_review_result_example.json` - Continue Decision
**Scenario:** Aya's response recommending "continue" without action on destructive dialog.

**Key Fields Demonstrated:**
- `request_id`: Links back to original request
- `decision`: "continue" - The reviewer's decision
- `reasoning`: Detailed explanation for the decision
- `action_payload`: Parameters for actionable decisions
- `risk_assessment`: Risk level and concerns identified
- `latency_ms`: Time from request to result

### 6. `artifact_manifest_example.json` - Frame + ROI Manifest
**Scenario:** Manifest entry for a captured frame with associated ROI data.

**Key Fields Demonstrated:**
- `artifact_type`: "frame" - Type of artifact
- `checksum`: SHA256 for integrity verification
- `trace_id`: Distributed trace correlation ID
- `metadata`: Artifact-specific metadata (dimensions, format)
- `retention_policy`: How long to keep this artifact
- `access_log`: Audit trail of artifact access

## Invalid Examples

These examples are intentionally malformed to test specific validation failures:

### 1. `ui_packet_missing_required.json`
**Failure Type:** Missing required field

**Issue:** Missing `frame_ref` field (required by ui_packet schema)

**Expected Error:**
```
ValidationError: 'frame_ref' is a required property
```

**Use Case:** Testing that validation properly catches missing required fields before processing.

### 2. `trading_packet_bad_risk.json`
**Failure Type:** Invalid enum value

**Issue:** `risk_level` is set to "extreme" but only ["none", "low", "medium", "high", "critical"] are allowed

**Expected Error:**
```
ValidationError: 'extreme' is not one of ['none', 'low', 'medium', 'high', 'critical']
```

**Use Case:** Testing enum validation and ensuring only valid risk levels propagate through the system.

### 3. `scout_event_low_confidence.json`
**Failure Type:** Numeric constraint violation

**Issue:** `confidence` value of 1.25 exceeds the maximum of 1.0

**Expected Error:**
```
ValidationError: 1.25 is greater than the maximum of 1
```

**Use Case:** Testing numeric range constraints on confidence scores.

### 4. `malformed_envelope.json`
**Failure Type:** Missing required envelope field

**Issue:** Missing `event_id` field (required by event_envelope schema)

**Expected Error:**
```
ValidationError: 'event_id' is a required property
```

**Use Case:** Testing envelope validation - every event must have a unique identifier.

## Running Validation

### Python (jsonschema)

```python
import json
from jsonschema import validate, ValidationError

# Load schema
with open('schemas/ui_packet.schema.json') as f:
    schema = json.load(f)

# Load example
with open('examples/packets/valid/ui_packet_example.json') as f:
    example = json.load(f)

# Validate
try:
    validate(instance=example, schema=schema)
    print("✅ Valid!")
except ValidationError as e:
    print(f"❌ Invalid: {e.message}")
```

### Command Line (check-jsonschema)

```bash
# Install
pip install check-jsonschema

# Validate valid example (should pass)
check-jsonschema \
  --schemafile schemas/ui_packet.schema.json \
  examples/packets/valid/ui_packet_example.json

# Validate invalid example (should fail with specific error)
check-jsonschema \
  --schemafile schemas/ui_packet.schema.json \
  examples/packets/invalid/ui_packet_missing_required.json
```

### With Python Script

A validation script is available in the project:

```bash
# Validate all examples
python scripts/validate_examples.py

# Validate specific file
python scripts/validate_examples.py \
  --schema schemas/ui_packet.schema.json \
  --file examples/packets/valid/ui_packet_example.json
```

## Schema Reference

| Schema File | Description | Required Fields |
|-------------|-------------|-----------------|
| `ui_packet.schema.json` | UI-mode perception packets | packet_id, mode, event_type, frame_ref, scout_note |
| `trading_packet.schema.json` | Trading-mode perception packets | packet_id, mode, event_type, frame_ref, scout_note |
| `scout_event.schema.json` | Eagle2-2B classification events | event_id, timestamp, scout_version, classification, confidence |
| `external_review_request.schema.json` | External reviewer requests | request_id, timestamp, reviewer_target, packet_ref, context |
| `external_review_result.schema.json` | External reviewer responses | result_id, request_id, timestamp, decision |
| `artifact_manifest.schema.json` | Artifact audit trail | manifest_id, timestamp, artifact_type, path |
| `event_envelope.schema.json` | Common event wrapper | event_id, timestamp, source, mode, schema_version, payload |

## Adding New Examples

When adding new examples:

1. **Valid examples** should be realistic scenarios with complete, correct data
2. **Invalid examples** should target specific validation failures with comments explaining the issue
3. **Always include** a `//comment` field explaining the purpose of the example
4. **Document** new examples in this README

## Notes

- JSON does not natively support comments - the `//comment` and `//expected_error` fields are used for documentation
- All UUIDs in examples are static for reproducibility; production should generate unique UUIDs
- Timestamps use ISO 8601 format with timezone (Z for UTC)
- File paths in examples are relative to the project root
