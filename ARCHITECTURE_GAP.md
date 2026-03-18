# Architecture Gap Analysis: AD-001 to AD-010

**Audit Date:** 2026-03-18  
**Auditor:** Subagent audit-architecture-compliance  
**Scope:** `/home/netjer/.openclaw/workspace/plane-a/projects/advanced-vision`

---

## Executive Summary

| AD | Description | Status | Severity |
|----|-------------|--------|----------|
| AD-001 | Native eyes + fast-attention substrate | ✅ Compliant | - |
| AD-002 | External finalizer model-agnostic | ⚠️ Partial | MEDIUM |
| AD-003 | Video local; image packets | ✅ Compliant | - |
| AD-004 | WSS derived fanout, not authority | ⚠️ Partial | HIGH |
| AD-005 | Programmatic hot path | ✅ Compliant | - |
| AD-006 | LangGraph for stateful review | ✅ Compliant | - |
| AD-007 | Lobster at OpenClaw boundary | ✅ Compliant | - |
| AD-008 | Eagle2-2B scout-first | ✅ Compliant | - |
| AD-009 | Qwen reviewer-first | ✅ Compliant | - |
| AD-010 | Governor separate from reviewer | ❌ Violation | CRITICAL |

**Critical Gaps:** 1 (AD-010 - Missing Governor)  
**High Severity:** 1 (AD-004 - Authority/Logging gap)  
**Medium Severity:** 1 (AD-002 - Minor model-agnostic issues)

---

## Detailed Analysis

### AD-001 — Native Eyes + Fast-Attention Substrate

**Decision:** `advanced-vision` owns local capture, motion/cursor suppression, detector hot path, ROI isolation, scout classification, evidence packet generation.

**Status:** ✅ **COMPLIANT**

**Evidence:**
- **Local capture:** `src/advanced_vision/tools/screen.py` - `screenshot_full()`, `screenshot_active_window()` with PIL ImageGrab
- **Cursor suppression:** `src/advanced_vision/trading/detector.py` lines 97-130 - `CursorSuppressor` class with `is_cursor_region()`, `suppress_cursor_detections()`
- **Motion gating:** `src/advanced_vision/trading/detector.py` lines 50-95 - `MotionGate` class with `check_motion()` method
- **Eagle integration:** `src/advanced_vision/trading/wss_eagle_publisher_v2.py` - Full Eagle2-2B WebSocket publisher; `src/advanced_vision/models/model_manager.py` lines 130-144 - Eagle2-2B as resident model

**Notes:** All substrate components are implemented as plain Python code without workflow engine dependencies.

---

### AD-002 — External Finalizer Must Be Model-Agnostic

**Decision:** Top review/finalizer layer must not be hard-coded to Kimi. Interface must support ChatGPT, Claude, Gemini, future OpenClaw backends.

**Status:** ⚠️ **PARTIAL**

**Severity:** MEDIUM

**Evidence:**
- ✅ **Model-agnostic interface exists:** `schemas/external_review_request.schema.json` - Generic `reviewer_target` object with `agent_identity`, `provider`, `model` fields
- ✅ **Generic request/response:** `external_review_request.schema.json` and `external_review_result.schema.json` use model-agnostic field names
- ❌ **Hardcoded Kimi reference:** `src/advanced_vision/trading/events.py` line 193 - `OverseerResponse` model defaults to `model: str = "kimi-k2.5"`
- ❌ **Kimi-specific comments:** `src/advanced_vision/trading/events.py` line 187 - Docstring refers to "Cloud overseer (Kimi)" instead of generic "external finalizer"

**Gap:** While the schemas are model-agnostic, the code contains hardcoded defaults and naming that assumes Kimi as the external finalizer.

**Recommended Fix:**
```python
# In src/advanced_vision/trading/events.py line 193
# Change from:
model: str = "kimi-k2.5"
# To:
model: str = "external-finalizer"  # Generic default
```

---

### AD-003 — Video Stays Local; Reviewer Consumes Image Packets

**Decision:** Do not stream raw video externally. Convert continuous observation into discrete review packets (screenshot refs, ROI crops, before/after frames, keyframe bursts, structured notes).

**Status:** ✅ **COMPLIANT**

**Evidence:**
- ✅ **No raw video streaming:** No video streaming code found in the codebase
- ✅ **Packetization implemented:** 
  - `schemas/trading_packet.schema.json` - Complete trading packet schema with `frame_ref`, `chart_regions`, `ticket_regions`, `scout_note`
  - `schemas/ui_packet.schema.json` - UI packet schema with `frame_ref`, `roi_regions`
  - `schemas/scout_event.schema.json` - Scout classification events with `artifact_refs`
  - `src/advanced_vision/trading/roi.py` - `EvidenceBundle` class for curated packet assembly
- ✅ **ROI extraction:** `src/advanced_vision/trading/roi.py` lines 60-140 - `ROIExtractor` creates focused crops instead of full video

**Notes:** The architecture correctly avoids video streaming and uses image packet references.

---

### AD-004 — WSS Is Derived Fanout, Not Authority

**Decision:** WebSocket channels are for live subscriptions/fanout, not transport truth. Authority stays in append-only event records, image/ROI/clip manifests, replayable artifacts.

**Status:** ⚠️ **PARTIAL**

**Severity:** HIGH

**Evidence:**
- ✅ **WSS as fanout:** `src/advanced_vision/wss_server_v2.py` - WebSocket server correctly implements pub/sub with topic routing
- ✅ **Event logging:** `src/advanced_vision/wss_server_v2.py` lines 395-412 - `WSSLoggerV2.log_event()` writes to `events.jsonl`
- ❌ **Missing append-only guarantee:** Current logging uses simple JSONL append, but no checksums or immutability guarantees
- ❌ **Missing artifact manifest logging:** 
  - `schemas/artifact_manifest.schema.json` exists with SHA256 checksums, retention policies, access logs
  - **No implementation found** - No code writes artifact manifests with checksums
- ❌ **No event sourcing pattern:** Events are logged but not treated as the source of truth for replay

**Gap:** The artifact_manifest.schema.json defines the contract but there's no implementation that:
1. Computes SHA256 checksums for frames/ROIs
2. Writes append-only artifact manifest entries
3. Maintains trace IDs across the pipeline
4. Enforces retention policies

**Recommended Fix:**
Create `src/advanced_vision/artifact_log.py` implementing:
```python
class ArtifactLogger:
    def log_artifact(self, path: Path, artifact_type: str, trace_id: str) -> ArtifactManifest:
        checksum = sha256_file(path)
        entry = ArtifactManifest(
            manifest_id=str(uuid.uuid4()),
            timestamp=utc_now(),
            artifact_type=artifact_type,
            path=str(path),
            checksum=checksum,
            trace_id=trace_id,
        )
        append_jsonl("artifact_manifest", entry.model_dump())
        return entry
```

---

### AD-005 — Programmatic Hot Path, Not Workflow-Engine

**Decision:** Real-time visual loop (capture → cursor suppression → frame diff → YOLO → tracking → SAM → Eagle) should be plain programmatic code. Must be benchmarkable, low-latency, easy to reason about.

**Status:** ✅ **COMPLIANT**

**Evidence:**
- ✅ **Plain code hot path:** `src/advanced_vision/trading/detector.py` - `DetectionPipeline.process_frame()` shows sequential execution:
  1. Cursor tracking update (line 245)
  2. Motion gate check (lines 248-251)
  3. YOLO detection (line 254)
  4. Cursor suppression (lines 257-259)
  5. Class filtering (lines 262-266)
- ✅ **No workflow engine:** No LangGraph, Airflow, or similar workflow engines in the hot path
- ✅ **Simple flow:** `src/advanced_vision/flow.py` - `run_single_cycle()` is plain sequential code

**Notes:** The hot path is correctly implemented as plain Python without workflow engine overhead.

---

### AD-006 — LangGraph for Stateful Review, Not 60 FPS Loop

**Decision:** If workflow engine is used, it should sit in slower stateful review lane (evidence assembly, Qwen review, external-review request, clip commit, retry/escalate states).

**Status:** ✅ **COMPLIANT**

**Evidence:**
- ✅ **No LangGraph in codebase:** `grep -r "langgraph\|LangGraph" src/` returned no results
- ✅ **No workflow engine in 60 FPS loop:** The hot path is plain code (see AD-005)

**Notes:** LangGraph is not used anywhere in the codebase. While this means compliance with "not in 60 FPS loop," it also means the stateful review lane doesn't have workflow engine support yet (which is acceptable per AD-006's "if used" wording).

---

### AD-007 — Lobster at OpenClaw Tool Boundary Only

**Decision:** Use Lobster only for deterministic, approval-gated, resumable tool flows at the OpenClaw side. Not for raw frame handling, hot visual loop, ROI tracking.

**Status:** ✅ **COMPLIANT**

**Evidence:**
- ✅ **No Lobster in advanced-vision:** `grep -r "lobster\|Lobster" src/` returned no results
- ✅ **Clean separation:** All advanced-vision code is pure Python with no Lobster dependencies

**Notes:** Lobster is correctly kept at the OpenClaw boundary (if used at all), not in the vision pipeline.

---

### AD-008 — Eagle2-2B Is Scout-First

**Decision:** Treat Eagle2-2B as default scout. Scout distinguishes noise vs meaningful UI change, identifies UI element type, classifies chart/UI change, suggests continue/log/escalate. Not sole trade reviewer or execution authority.

**Status:** ✅ **COMPLIANT**

**Evidence:**
- ✅ **Eagle as resident:** `src/advanced_vision/models/model_manager.py` lines 130-144 - `eagle2-2b` configured with `residency="resident"`, `role=ModelRole.SCOUT`
- ✅ **First filter:** `schemas/scout_event.schema.json` - Defines scout event as first filter layer between raw capture and downstream review
- ✅ **Scout classification:** `src/advanced_vision/trading/wss_eagle_publisher_v2.py` - Publishes classifications like "order_ticket", "chart_update", "confirm_dialog"
- ✅ **Not execution authority:** `src/advanced_vision/trading/events.py` - Scout produces `ActionRecommendation` (advisory), but final action is determined by governor (per AD-010 design)

**Notes:** Eagle2-2B is correctly positioned as the fast scout/filter, not the final decision maker.

---

### AD-009 — Qwen Is Reviewer-First

**Decision:** Treat Qwen as deeper local reviewer, especially for trading mode. Reviewer interprets risk-relevant UI state, analyzes chart/ticket combinations, resolves ambiguity from scout outputs, produces structured judgment for external finalizer/governor.

**Status:** ✅ **COMPLIANT**

**Evidence:**
- ✅ **Qwen as reviewer role:** `src/advanced_vision/models/model_manager.py` lines 113-127 - Qwen models configured with `role=ModelRole.REVIEWER`
- ✅ **On-demand loading:** `src/advanced_vision/models/model_manager.py` lines 113-127 - Qwen3.5-4B and 7B have `residency="on_demand"` (not always resident)
- ✅ **Default reviewer model:** `src/advanced_vision/trading/reviewer.py` lines 36-37 - `ReviewerConfig` defaults to `model: ReviewerModel = ReviewerModel.QWEN_4B_NVFP4`
- ✅ **Deep review only:** `src/advanced_vision/trading/reviewer.py` lines 235-248 - Reviewer lane skips noise events, only processes events requiring review

**Notes:** Qwen is correctly positioned as the deeper reviewer, loaded on-demand rather than resident.

---

### AD-010 — Governor Separate from Reviewer/Finalizer

**Decision:** No reviewer, local or external, directly becomes action authority. Governor decides: continue, warn, ask for recheck, block, require approval, allow tool call/execution step.

**Status:** ❌ **VIOLATION**

**Severity:** CRITICAL

**Evidence:**
- ❌ **No governor component exists:** Only mentions are in comments/docstrings:
  - `src/advanced_vision/trading/events.py` line 29 - "Used by the governor layer to determine appropriate action" (comment only)
  - `src/advanced_vision/trading/events.py` line 35 - "Models produce recommendations; governor decides" (comment only)
  - `src/advanced_vision/trading/detector.py` line 19 - "Models produce evidence, governor decides" (comment only)
- ❌ **No governor implementation:** No `Governor` class, no `governor.py` file, no policy enforcement
- ❌ **Reviewer can directly escalate:** `src/advanced_vision/trading/reviewer.py` lines 241-248 - `should_escalate_to_overseer()` allows reviewer to trigger escalation without governor approval
- ❌ **No action gating:** Actions flow directly from reviewer recommendation to execution without independent governor review

**Gap:** The architecture acknowledges the governor concept but has no implementation. This means:
1. Reviewer recommendations could be executed without policy validation
2. No centralized policy enforcement point
3. No separation between assessment (reviewer) and authorization (governor)

**Recommended Fix:**
Create `src/advanced_vision/trading/governor.py`:
```python
class Governor:
    """Policy layer - final action authority."""
    
    def decide_action(
        self,
        scout_event: ScoutEvent,
        reviewer_assessment: ReviewerAssessment | None,
        external_review: ExternalReviewResult | None,
    ) -> GovernorDecision:
        # Policy enforcement logic
        # - Always block on CRITICAL risk
        # - Require approval for HIGH risk trades
        # - Escalate uncertain assessments
        # - Log all decisions
        pass
```

---

## File/Line Reference Summary

| File | Lines | AD | Issue |
|------|-------|-----|-------|
| `src/advanced_vision/trading/events.py` | 193 | AD-002 | Hardcoded `model: str = "kimi-k2.5"` |
| `src/advanced_vision/trading/events.py` | 187 | AD-002 | Kimi-specific docstring |
| `src/advanced_vision/wss_server_v2.py` | 395-412 | AD-004 | Logs events but no artifact manifest |
| `schemas/artifact_manifest.schema.json` | all | AD-004 | Schema defined but not implemented |
| `src/advanced_vision/trading/reviewer.py` | 241-248 | AD-010 | Escalation without governor |
| `src/advanced_vision/trading/` | - | AD-010 | No governor.py file exists |

---

## Recommended Priority Order

1. **CRITICAL - AD-010:** Implement Governor component immediately. This is a fundamental architectural requirement for safe operation.

2. **HIGH - AD-004:** Implement artifact manifest logging with SHA256 checksums. Required for auditability and truth/authority separation.

3. **MEDIUM - AD-002:** Fix hardcoded Kimi references to be truly model-agnostic.

---

## Appendix: Schema Compliance Matrix

| Schema | Defined | Implemented | Used in Hot Path |
|--------|---------|-------------|------------------|
| `trading_packet.schema.json` | ✅ | ⚠️ Partial | No |
| `ui_packet.schema.json` | ✅ | ⚠️ Partial | No |
| `external_review_request.schema.json` | ✅ | ⚠️ Partial | No |
| `external_review_result.schema.json` | ✅ | ⚠️ Partial | No |
| `scout_event.schema.json` | ✅ | ✅ Yes | Yes (Eagle publisher) |
| `artifact_manifest.schema.json` | ✅ | ❌ No | No |
| `event_envelope.schema.json` | ✅ | ✅ Yes | Yes (WSS v2) |

**Note:** Schemas exist but implementations are partial. The hot path correctly uses only scout_event and event_envelope.
