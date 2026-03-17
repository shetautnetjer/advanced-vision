# Software Design Document (SDD)
## Advanced Vision Watcher for Desktop Scout + Trading Watch Modes

**Document status:** Draft SDD v1  
**Primary repo:** `advanced-vision`  
**Related repos:** `OpenClaw`, `Brain-harness`  
**Primary plane:** Plane A operational system with governed escalation and selective promotion  
**Primary runtime style:** local-first, event-driven, replayable, inspectable

---

## 1. Purpose

This SDD translates the product goals from the PRD into a concrete technical design for the first implementation of the Advanced Vision Watcher. The design supports two operating modes:

- **Desktop Scout Mode** for lightweight continuous desktop awareness
- **Trading Watch Mode** for higher-sensitivity market, ticket, and risk monitoring

The system is designed to behave like a human attention stack rather than a monolithic vision agent. Cheap reflex filters run first. Targeted perception runs second. Judgment runs later and only on evidence worth spending compute on. High-trust review is gated and separate from the operational watcher path.

This design preserves the existing doctrine:

- plane separation is real
- promotion is governed
- vector indexes are not authored truth
- event history must be append-only and replayable
- notifier outputs are hints, not authoritative truth
- specialized model roles must stay specialized

This document is implementation-oriented and intended to guide initial repo layout, service boundaries, schema design, runtime wiring, and phased delivery.

---

## 2. Scope

### 2.1 In scope

This design covers:

- live screen capture
- cursor suppression / reflex filters
- frame-diff and YOLO tripwire logic
- SAM3-based ROI tracking
- optional UI structure extraction via OmniParser-like component
- Eagle2-2B scout role
- Qwen reviewer role for trading mode
- Kimi escalation path
- append-only event logs
- replayable clip / keyframe / ROI artifacts
- sanitized escalation manifests
- mode-specific control flow
- configuration, testing, and future integration hooks

### 2.2 Out of scope

This design does not implement:

- autonomous final trade placement without policy gating
- full governed learning or promotion workflows in Brain-harness
- final OpenClaw runtime orchestration
- final vector memory indexing strategy
- production multi-device notification infrastructure
- one-step end-to-end AGI watcher

---

## 3. Design principles

### 3.1 Local-first hot path

All always-on work must stay local and cheap enough to preserve responsiveness. The system must avoid routing raw full desktop video to cloud models by default.

### 3.2 Layered attention

The design follows this order:

1. **Reflex lane** — ignore obvious noise
2. **Tripwire lane** — detect meaningful change candidates
3. **Structure lane** — isolate, track, and parse ROIs
4. **Scout lane** — perform lightweight semantic classification
5. **Reviewer lane** — perform stronger local reasoning when warranted
6. **Overseer lane** — request second opinion only when needed
7. **Governor lane** — keep final action authority separate from model outputs

### 3.3 Evidence-first architecture

The system should move evidence forward, not vague summaries. That means:

- ROI crops
- sampled frame groups
- tracked IDs
- parser output
- event JSON
- keyframes
- clip manifests

### 3.4 Append-only and replayable

All watcher decisions must be reconstructable from logs and artifacts. Logs are append-only. Derived summaries must not erase the underlying event history.

### 3.5 Role separation

The following roles must remain separate:

- tripwire/detector
- tracker/segmenter
- UI structure reader
- scout VLM
- reviewer VLM
- cloud overseer
- policy/governor

---

## 4. System context

### 4.1 Repository boundaries

#### `advanced-vision`
Owns:
- capture
- local watcher runtime
- ROI extraction
- model adapters
- event logs
- local manifests
- local redaction pipeline
- replay artifacts

#### `OpenClaw`
Later owns:
- higher orchestration
- tasking and runtime coordination
- external session control
- possible mailbox integration with watcher outputs

#### `Brain-harness`
Owns:
- doctrine
- promotion rules
- trust lane policy
- canonical schemas/tags
- governed learning/promotion
- memory law

### 4.2 Plane model

#### Plane A
Operational lane for:
- raw frames
- raw sampled clips
- raw model outputs
- local event logs
- working manifests
- temporary parsed UI structures

#### Plane B
Canonical lane for:
- approved templates
- promoted lessons
- governed summaries
- trusted schema docs
- curated retrieval records

The watcher runtime operates primarily in Plane A. Promotion to Plane B is a separate process, not part of hot-path inference.

---

## 5. High-level architecture

```text
Screen Capture
  -> Cursor Suppressor / Reflex Filters
  -> Frame Diff / Motion Gate
  -> YOLO Tripwire
  -> SAM3 ROI Tracking
  -> Optional UI Parser
  -> Eagle Scout
  -> Mode Router
     -> Desktop Scout Action Path
     -> Trading Reviewer Path (Qwen)
  -> Optional Kimi Overseer Escalation
  -> Governor / Policy Gate
  -> Artifact Commit + Append-Only Logs
```

### 5.1 Major runtime lanes

- **Capture lane**
- **Reflex lane**
- **Tripwire lane**
- **Tracking lane**
- **Parsing lane**
- **Scout lane**
- **Reviewer lane**
- **Escalation lane**
- **Artifact lane**
- **Governor lane**

---

## 6. Operating modes

## 6.1 Desktop Scout Mode

### Goal
Provide continuous awareness during general computer use without interrupting the user unnecessarily.

### Behavior
- strongly suppress cursor-only and low-value motion
- classify UI changes quickly
- avoid pausing for benign or familiar changes
- capture notes and evidence bundles only when needed

### Primary lane usage
- capture
- reflex filters
- tripwire
- tracking if change is meaningful
- Eagle scout
- note / continue / notify

### Typical outputs
- `ignore`
- `note`
- `notify`
- `capture_evidence`
- `resume`

## 6.2 Trading Watch Mode

### Goal
Monitor charting/order-entry workflows like a careful human reviewer and route ambiguous or risky states into stronger review.

### Behavior
- watch trading-specific ROIs
- track chart panel, order ticket, confirmation dialog, warnings, P&L/risk widgets
- use Eagle as scout
- use Qwen as local reviewer
- use Kimi as second opinion for uncertain/high-risk states
- never let raw model output directly imply ungoverned execution

### Primary lane usage
- capture
- reflex filters
- tripwire
- tracking
- UI parsing
- Eagle scout
- Qwen reviewer
- Kimi escalation
- governor gate

### Typical outputs
- `continue`
- `warn`
- `hold`
- `pause`
- `escalate`
- `capture_forensic_bundle`

---

## 7. Component design

## 7.1 Capture Service

### Responsibilities
- capture screen frames from one or more sources
- timestamp frames
- write frames into rolling ring buffer
- emit lightweight frame-available signals

### Inputs
- configured display source
- capture FPS target
- region or full desktop selection

### Outputs
- frame buffer slot
- frame metadata
- optional low-res preview frame

### Key requirements
- no blocking on disk writes
- no model inference in capture thread
- preallocated ring buffer
- monotonic frame IDs

### Notes
Capture should support:
- full desktop
- selected monitor
- selected window/app in future

## 7.2 Cursor Suppressor / Reflex Filter Service

### Responsibilities
- suppress pointer-only movement from triggering downstream work
- optionally mask cursor region out of frame diff
- reduce noise from tiny transient animations

### Inputs
- frame N
- frame N-1
- optional OS cursor position if available

### Outputs
- `reflex_result`
- candidate masked frame for tripwire lane

### Reflex decisions
- `ignore_cursor_only`
- `ignore_micro_motion`
- `pass_to_tripwire`

### Notes
This is intentionally cheaper than VLM reasoning. This is the first place where “that was only the mouse pointer” should be filtered out.

## 7.3 Motion Gate / Frame-Diff Service

### Responsibilities
- compute change score between frames
- identify candidate change windows
- suppress low-value noise

### Inputs
- masked or raw frame deltas

### Outputs
- motion score
- bounding regions for changed areas
- confidence that a meaningful change occurred

### Notes
This service may be enough by itself for some Desktop Scout Mode cases. YOLO is not required on every frame if frame-diff says nothing meaningful happened.

## 7.4 YOLO Tripwire Service

### Responsibilities
- classify rough changed regions quickly
- identify candidate UI elements or warning objects
- wake the heavier lanes only when needed

### Example classes
- modal
- popup
- button
- warning_badge
- chart_area
- ticket_panel
- dropdown
- tooltip
- notification

### Inputs
- triggered frames
- change windows

### Outputs
- `tripwire_result`
- bounding boxes
- class labels
- object confidence

### Notes
YOLO is tripwire, not final truth. Its job is: “something meaningful probably changed here.”

## 7.5 SAM3 Tracking Service

### Responsibilities
- isolate triggered object/region
- track ROI across sampled frames
- assign stable track IDs
- produce masks or bboxes for downstream processing

### Inputs
- triggered frames or short frame slice
- tripwire detections
- optional prompt library for known UI concepts

### Outputs
- tracked ROI objects
- stable `track_id`
- bbox / mask / confidence

### Notes
This service should run only on trigger or periodic validation, not continuously on every frame.

## 7.6 UI Parser Service

### Responsibilities
- convert ROI screenshots into structured UI element descriptions
- extract visible text, element boxes, roles, layout hints
- provide additional semantic grounding for the scout/reviewer layers

### Inputs
- ROI crops
- optional full-frame context crop

### Outputs
- UI structure JSON
- OCR strings
- element types
- positions / relationships

### Notes
This can be OmniParser or a similar pluggable adapter. It should be optional for Desktop Scout Mode and more common in Trading Watch Mode.

## 7.7 Eagle Scout Service

### Responsibilities
- perform fast semantic classification over selected ROIs or short image bursts
- distinguish benign movement from real UI changes
- create compact notes for downstream lanes
- avoid pausing normal flow unless explicitly warranted

### Inputs
- ROI crops
- optional sampled frame set
- optional parser output
- mode context

### Outputs
- `scout_event`
- classification type
- confidence
- summary note
- handoff recommendation

### Intended use
Eagle is the “notice and jot” model, not the final authority.

### Typical scout labels
- `noise`
- `cursor_only`
- `ui_change`
- `warning`
- `trading_relevant`
- `unknown`
- `needs_qwen`
- `needs_kimi`

## 7.8 Qwen Reviewer Service

### Responsibilities
- perform stronger local multimodal reasoning on trading-relevant evidence
- interpret chart/ticket/warning combinations
- combine Eagle note + ROI evidence + parser structure
- recommend continue/warn/hold/pause/escalate

### Inputs
- Eagle scout output
- ROI crops
- frame group or short clip slice
- UI parser output
- mode-specific policy prompt

### Outputs
- `review_event`
- risk classification
- evidence-backed reasoning
- action recommendation
- escalation recommendation

### Notes
Qwen reviewer runs only in Trading Watch Mode or other high-sensitivity contexts.

## 7.9 Kimi Overseer Adapter

### Responsibilities
- request second-opinion multimodal review on selected evidence bundles
- return deeper explanation or anomaly interpretation
- challenge local reviewer output when uncertainty is high

### Inputs
- sanitized ROI bundle
- selected keyframes or short clip
- scout and reviewer event history slice
- escalation manifest

### Outputs
- `overseer_review`
- anomaly hypothesis
- confidence / caution level
- recommendation for hold/warn/pause/review

### Notes
Kimi does not watch every frame. Kimi gets curated evidence bundles only.

## 7.10 Governor / Policy Gate

### Responsibilities
- keep final action authority separate from model outputs
- apply mode-specific rules
- map reviewer recommendations into allowed actions
- block unsafe autonomous behavior

### Inputs
- scout/reviewer/overseer events
- user policy mode
- configured risk settings

### Outputs
- final watcher action
- `continue`
- `note`
- `warn`
- `hold`
- `pause`
- `notify_user`
- `request_manual_review`

### Notes
In MVP, this can be a rule engine or deterministic policy layer. It must remain separate from model inference.

## 7.11 Artifact Commit Service

### Responsibilities
- commit clips, keyframes, ROI crops, logs, and manifests when required
- run redaction before cloud escalation
- slice ring buffer into replayable evidence windows

### Inputs
- event timeline slice
- frame IDs / time window
- ROI paths or in-memory images
- escalation flags

### Outputs
- saved clip
- saved keyframes
- saved ROI crops
- manifest JSON
- append-only artifact event record

---

## 8. Runtime topology

## 8.1 Process model

Recommended initial process layout:

### Process A — `watcher-core`
Owns:
- capture
- cursor suppression
- frame diff
- YOLO tripwire
- event router
- ring buffer management

### Process B — `tracker-parser`
Owns:
- SAM3
- parser adapter
- ROI extraction

### Process C — `scout-service`
Owns:
- Eagle runtime
- scout event generation

### Process D — `reviewer-service`
Owns:
- Qwen runtime
- review event generation

### Process E — `escalation-service`
Owns:
- redaction
- Kimi API adapter
- escalation bundle assembly

### Process F — `artifact-service`
Owns:
- clip commit
- keyframe extraction
- manifest write
- append-only logs

### Process G — `governor-service`
Owns:
- policy rules
- final state decision
- user notification hooks

## 8.2 Why split this way

- capture must never wait on VLM inference
- SAM3 should not block Eagle or Qwen
- scout and reviewer can evolve independently
- Kimi integration should remain optional and isolated
- replay artifacts should still commit even if cloud escalation fails

---

## 9. Control flow

## 9.1 Desktop Scout Mode flow

```text
capture_frame
  -> cursor_suppress
  -> motion_gate
  -> if no meaningful change: continue
  -> yolo_tripwire
  -> if class is low-value: note_or_ignore
  -> sam3_track (optional when needed)
  -> ui_parse (optional)
  -> eagle_scout
  -> governor decides continue/note/notify/capture
  -> artifact commit if needed
```

## 9.2 Trading Watch Mode flow

```text
capture_frame
  -> cursor_suppress
  -> motion_gate
  -> if meaningful change: yolo_tripwire
  -> sam3_track
  -> ui_parse
  -> eagle_scout
  -> if not trading-relevant: continue/note
  -> qwen_reviewer
  -> if uncertain or high-risk: prepare escalation bundle
  -> kimi_overseer (optional/gated)
  -> governor decides continue/warn/hold/pause
  -> artifact commit + replay log
```

---

## 10. State machine

## 10.1 Primary states

- `idle`
- `observing`
- `candidate_change`
- `tracking`
- `scouting`
- `reviewing`
- `escalating`
- `holding`
- `paused`
- `artifact_commit`
- `resuming`
- `error`

## 10.2 State transitions

### `idle -> observing`
System starts capture and event loop.

### `observing -> candidate_change`
Motion gate or periodic sampling says a meaningful change may exist.

### `candidate_change -> observing`
Change suppressed as cursor-only, low-value animation, or benign transient.

### `candidate_change -> tracking`
Tripwire confirms candidate ROI worth isolating.

### `tracking -> scouting`
Tracked ROI and optional parser output become available.

### `scouting -> observing`
Scout classifies event as harmless or non-blocking.

### `scouting -> reviewing`
Scout says event is trading-relevant, uncertain, or requires stronger judgment.

### `reviewing -> observing`
Reviewer decides safe/continue.

### `reviewing -> escalating`
Reviewer says uncertainty/risk is high enough for second opinion.

### `escalating -> holding`
Governor elects to hold actions until overseer response.

### `escalating -> paused`
Governor elects to pause due to explicit risk or policy.

### `escalating -> observing`
Escalation returns low concern and governor clears system to continue.

### `any -> artifact_commit`
Evidence capture required for replay or forensic logging.

### `artifact_commit -> resuming`
Artifacts committed successfully.

### `resuming -> observing`
System returns to watch loop.

### `any -> error`
Unrecoverable runtime error.

---

## 11. Data contracts

## 11.1 Core event envelope

All events should share a common envelope:

```json
{
  "event_id": "uuid7",
  "ts_ms": 1730000000123,
  "event_type": "watcher.scout_event",
  "source": "advanced-vision",
  "mode": "desktop_scout",
  "plane": "plane_a",
  "session_id": "sess_001",
  "frame_id": 98123,
  "parent_event_id": null,
  "payload": {}
}
```

## 11.2 Reflex result

```json
{
  "kind": "reflex_result",
  "decision": "ignore_cursor_only | ignore_micro_motion | pass_to_tripwire",
  "cursor_bbox": [100, 200, 24, 24],
  "motion_score": 0.08,
  "notes": ["cursor_only_motion_detected"]
}
```

## 11.3 Tripwire result

```json
{
  "kind": "tripwire_result",
  "detections": [
    {"class": "modal", "bbox": [200, 100, 500, 320], "conf": 0.93},
    {"class": "chart_area", "bbox": [20, 60, 1260, 700], "conf": 0.88}
  ],
  "triggered": true
}
```

## 11.4 Track result

```json
{
  "kind": "track_result",
  "tracks": [
    {
      "track_id": "confirm_modal",
      "bbox": [200, 100, 500, 320],
      "mask_ref": "mask://frame_98123_confirm_modal",
      "conf": 0.91
    }
  ]
}
```

## 11.5 Parser result

```json
{
  "kind": "parser_result",
  "elements": [
    {"element_id": "btn_confirm", "role": "button", "text": "Confirm", "bbox": [520, 360, 92, 32]},
    {"element_id": "lbl_symbol", "role": "label", "text": "AAPL", "bbox": [210, 160, 60, 20]}
  ],
  "ocr_text": ["Confirm", "AAPL", "Market Order"]
}
```

## 11.6 Scout event

```json
{
  "kind": "scout_event",
  "classification": "ui_change",
  "summary": "confirmation dialog appeared",
  "confidence": 0.84,
  "evidence": [
    {"track_id": "confirm_modal", "claim": "dialog visible", "conf": 0.88},
    {"track_id": "confirm_modal", "claim": "button labeled Confirm", "conf": 0.80}
  ],
  "routing": {
    "needs_qwen": true,
    "needs_kimi": false,
    "priority": "medium"
  }
}
```

## 11.7 Reviewer event

```json
{
  "kind": "review_event",
  "state": "uncertain",
  "risk_level": "high",
  "summary": "ticket and confirmation dialog imply trade entry requires higher-confidence review",
  "reasons": [
    "confirmation_required",
    "order_ticket_changed",
    "price_movement_detected"
  ],
  "recommendations": [
    "hold",
    "request_second_opinion",
    "commit_evidence"
  ]
}
```

## 11.8 Overseer review

```json
{
  "kind": "overseer_review",
  "state": "caution",
  "anomaly_guess": "possible slippage or route-risk condition",
  "confidence": 0.71,
  "recommendations": ["hold", "manual_review"],
  "notes": ["additional confirmation advised before execution"]
}
```

## 11.9 Escalation manifest

```json
{
  "manifest_id": "esc_2026_03_17_001",
  "mode": "trading_watch",
  "window": {"pre_s": 10, "post_s": 5},
  "clip_path": "vision/capture/clips/esc_2026_03_17_001.mp4",
  "keyframes": [
    "vision/capture/keyframes/esc_2026_03_17_001_kf001.png",
    "vision/capture/keyframes/esc_2026_03_17_001_kf002.png"
  ],
  "roi_crops": [
    {"track_id": "chart_panel", "path": "vision/capture/rois/chart_panel_001.png"},
    {"track_id": "confirm_modal", "path": "vision/capture/rois/confirm_modal_001.png"}
  ],
  "watcher_events": ["evt_1", "evt_2", "evt_3"],
  "redaction": {"performed": true, "ruleset": "default_v1"},
  "approved_for_cloud": false
}
```

---

## 12. Storage design

## 12.1 Ring buffer

### Responsibilities
- hold recent frames in memory
- support slicing pre/post event windows
- preserve smooth capture while heavier lanes operate asynchronously

### Initial targets
- default capture: 60 FPS where feasible
- default buffer horizon: 10 seconds for MVP benchmark path
- larger windows available by mode/config

### Implementation requirements
- preallocated memory
- one writer, multiple readers by index
- avoid frame copies when possible
- offload commit/encode to separate thread

## 12.2 Append-only logs

Minimum logs:
- `watcher_events.jsonl`
- `tripwire_events.jsonl`
- `sam_tracks.jsonl`
- `review_events.jsonl`
- `escalation_manifest.jsonl`
- `governor_actions.jsonl`

## 12.3 Artifact directories

```text
vision/
  capture/
    clips/
    keyframes/
    rois/
  logs/
  pipeline/
  models/
  storage/
  docs/
```

## 12.4 Future retrieval storage

This design leaves room for later ROI embedding and LanceDB storage, but that is not required for the first implementation.

---

## 13. Model/runtime placement

## 13.1 Recommended local roles

### Eagle2-2B
Use for:
- fast scout classification
- grouped screenshot understanding
- short image-burst interpretation
- quick “this is a real UI element” notes

Do not use as:
- sole trading authority
- first reflex filter
- final execution decider

### Qwen reviewer
Use for:
- trading-specific local judgment
- UI/ticket/chart synthesis
- deeper reasoning over structured evidence

### Kimi
Use for:
- second-opinion review
- anomaly challenge
- deeper explanation of risk state

## 13.2 Runtime recommendations

### Eagle
Prefer separate runtime adapter; may start in Transformers path.

### Qwen
Prefer vLLM when using FP8 / larger efficient multimodal deployment.

### SAM3 / YOLO / parser
Run outside vLLM in dedicated local inference lanes.

---

## 13.3 Workflow Substrate Decision

This section documents the workflow engine selection for the agentic watcher pipeline. Both candidates remain Plane A operational choices, not settled doctrine.

### LangGraph — Implementation Target for Watcher Pipeline

**Role:** Local stateful orchestration for the 60 FPS vision pipeline  
**Use case:** Graph-based agent coordination with shared state, branching, and conditional heavy-lane triggering  
**Rationale:** The watcher design naturally maps to a state graph: nodes = lanes (reflex, tripwire, scout, reviewer), edges = event-driven handoffs  
**Status:** `workflow-substrate/langgraph` — candidate, pending validation

**Implementation scope:**
- Capture → Reflex → Tripwire → Tracking → Scout as state nodes
- Conditional edges based on `scout_event.classification`
- Shared state for `track_ids`, `roi_crops`, `frame_buffer` pointers
- Interrupt points for Qwen reviewer and Kimi escalation

### Lobster — Integration Target for OpenClaw Boundary

**Role:** Deterministic workflow runtime for approval-gated, resumable tool sequences  
**Use case:** Multi-step tool workflows as single deterministic operations with approval checkpoints  
**Rationale:** OpenClaw's Lobster handles "one call instead of many" for tool execution, with built-in pause/resume tokens  
**Status:** `workflow-substrate/lobster` — candidate, pending integration  

**Integration scope:**
- Escalation workflows that cross the advanced-vision → OpenClaw boundary
- Approval gates for pause/warn/hold recommendations
- Resumable halted workflows (human reviews, then resumes)
- Side-effect tool sequences (notifications, external API calls)

### Architecture Principle

> The workflow contract is canonical; the engine that runs it is replaceable.

This preserves doctrine: advanced-vision owns local perception/runtime; OpenClaw owns orchestration/tool execution; Brain-harness owns governance. Either substrate can be swapped without rewriting the lane contracts or event schemas.

### Decision Summary

| Layer | Substrate | Responsibility |
|-------|-----------|----------------|
| advanced-vision | LangGraph | Hot-path watcher graph (60 FPS), local agent coordination |
| OpenClaw | Lobster | Approval workflows, resumable escalations, tool sequences |
| Brain-harness | — | Doctrine validation, governance gates, promotion rules |

Do not merge substrates prematurely. LangGraph stays inside the vision runtime; Lobster stays at the OpenClaw boundary.

---

## 14. Scheduling and concurrency

## 14.1 Threading model

### Thread A — capture
- screen capture
- ring write
- frame timestamps

### Thread B — reflex/motion
- cursor suppression
- frame diff
- wake tripwire only as needed

### Thread C — tripwire
- YOLO or equivalent detector
- candidate ROI production

### Thread D — tracker/parser
- SAM3 on triggered slices
- parser/OCR on ROI crops

### Thread E — scout
- Eagle inference on selected ROI bundle

### Thread F — reviewer
- Qwen inference on escalated local evidence

### Thread G — artifacts
- clip/keyframe commit
- redaction
- manifest write

### Thread H — overseer
- Kimi request/response
- asynchronous to local watch loop where possible

## 14.2 Channel design

Use explicit message contracts between lanes, such as:
- `FrameAvailable`
- `CandidateChange`
- `TrackBundleReady`
- `ScoutReviewNeeded`
- `ReviewerEscalationNeeded`
- `ArtifactCommitRequested`
- `GovernorDecision`

---

## 15. Error handling and degradation

## 15.1 Failure classes

- capture failure
- model runtime unavailable
- parser timeout
- Kimi API unavailable
- artifact commit failure
- redaction failure
- governor policy conflict

## 15.2 Degradation rules

### If capture degrades
- enter `error` state
- emit diagnostic event
- stop making watcher decisions

### If YOLO unavailable
- fall back to frame-diff-only mode

### If SAM3 unavailable
- use bounding boxes from tripwire and parser-only path when possible

### If Eagle unavailable
- skip scout and escalate only selected events to reviewer in high-sensitivity mode

### If Qwen unavailable
- trading mode falls back to scout + governor + optional Kimi escalation

### If Kimi unavailable
- system continues local mode only, emits `overseer_unavailable` event, does not claim second-opinion coverage

### If artifact commit fails
- do not lose primary event record; emit `artifact_commit_failed` event

---

## 16. Redaction and privacy

## 16.1 Redaction policy

Before cloud escalation, default rules should mask or blur:
- wallet addresses
- account IDs
- emails
- names
- browser URL bars
- OS notifications
- secrets and tokens

## 16.2 Escalation safety

Only sanitized bundles may move into the cloud escalation lane. Raw unredacted assets remain local by default.

## 16.3 Permissions

Artifacts should be stored under restrictive filesystem permissions where feasible.

---

## 17. Configuration

## 17.1 Mode configuration

Example:

```yaml
mode: trading_watch
capture:
  fps: 60
  buffer_seconds: 10
reflex:
  cursor_suppression: true
  micro_motion_threshold: 0.05
tripwire:
  enabled: true
  detector: yolo
tracking:
  enabled: true
  model: sam3
parser:
  enabled: true
  provider: omniparser
scout:
  model: eagle2_2b
reviewer:
  model: qwen3_vl_4b_fp8
overseer:
  provider: kimi
policy:
  allow_pause: true
  allow_hold: true
  require_manual_review_for_trade: true
```

## 17.2 App profiles

Future per-app profiles should define:
- ROI target list
- known UI element templates
- risk-specific prompts
- parser hints
- chart/ticket heuristics

---

## 18. Test plan

## 18.1 Unit tests

- cursor suppression logic
- frame-diff thresholding
- event schema validation
- state machine transitions
- manifest generation
- redaction rules

## 18.2 Integration tests

- recorded desktop session in Desktop Scout Mode
- recorded trade-entry session in Trading Watch Mode
- replay-driven deterministic event reconstruction
- Qwen reviewer invoked only on expected events
- Kimi escalation bundle contains only approved fields

## 18.3 Performance tests

- 60 FPS capture benchmark
- dropped frame count
- event latency by lane
- GPU memory under Desktop Scout Mode
- GPU memory under Trading Watch Mode
- SAM3 trigger latency
- scout turnaround on 1/3/5 image burst

## 18.4 Evaluation metrics

### General
- false trigger rate
- missed meaningful change rate
- average event latency
- artifact commit success rate

### Scout-specific
- cursor/noise suppression precision
- UI change classification precision
- handoff quality to reviewer

### Trading-specific
- warning detection recall
- confirmation dialog recall
- anomaly escalation recall
- false hold / false pause rate

---

## 19. Phased delivery

## Phase 0 — foundation
- capture loop
- ring buffer benchmark
- append-only event envelope
- artifact directory structure

## Phase 1 — Desktop Scout MVP
- cursor suppression
- frame diff
- YOLO tripwire
- Eagle scout
- note/continue/notify path

## Phase 2 — Trading Watch MVP
- SAM3 tracking
- parser integration
- Qwen reviewer
- governor hold/pause path

## Phase 3 — Overseer escalation
- redaction pipeline
- Kimi adapter
- escalation manifest
- replay bundle commit

## Phase 4 — Learning/retrieval preparation
- ROI archive conventions
- labels/outcomes
- optional embedding hook

---

## 20. Open questions

1. Which exact local reviewer becomes default in trading mode: Qwen3-VL-4B-FP8 or Qwen3.5-4B?
2. Should Eagle remain always-on in trading mode, or should some sessions bypass Eagle and go straight from parser to reviewer?
3. What is the first supported app profile: browser trading UI, desktop trading platform, or generic charting app?
4. What level of automatic pause/hold is acceptable before explicit user confirmation?
5. Should Desktop Scout Mode support optional user notifications immediately, or just log + later replay in the first release?
6. What evidence minimum is required before a Kimi escalation request is allowed?
7. When later retrieval is added, which fields become stable canonical ROI metadata vs working-only fields?

---

## 21. Recommended first implementation path

1. Implement capture + cursor suppression + frame diff.
2. Add YOLO tripwire with bounding-box logs.
3. Add SAM3 ROI tracking and artifact snapshots.
4. Integrate Eagle scout on sampled ROI bundles.
5. Add Desktop Scout Mode end-to-end.
6. Add parser + Qwen reviewer for Trading Watch Mode.
7. Add governor rules for hold/pause/warn.
8. Add redaction + Kimi escalation.
9. Add replay tooling and timeline inspection.

This sequence keeps the system additive, inspectable, and aligned with the existing watcher doctrine rather than forcing a giant refactor.

---

## 22. Summary

This design creates a layered, local-first visual attention system that behaves more like a human at the PC:

- cheap reflexes ignore obvious noise
- tripwires notice candidate changes
- trackers isolate meaningful regions
- Eagle scouts and jots
- Qwen reviews in high-sensitivity trading workflows
- Kimi provides second-opinion oversight
- the governor keeps final authority separate
- artifacts and events remain append-only and replayable

This preserves repo boundaries, governance boundaries, and model-role boundaries while giving `advanced-vision` a strong, realistic implementation path.
