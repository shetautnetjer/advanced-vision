# Advanced Vision — Master Roadmap

**Status:** strategic roadmap  
**Purpose:** preserve the big vision without forcing near-term execution to carry too much at once

---

## 1. Why this roadmap exists

Aya’s original `plan.md` contained valuable research and real systems thinking, but it collapsed too many futures into one immediate implementation body.

This roadmap keeps the full ambition while separating:
- what belongs to the core repo now
- what belongs to application-layer experiments later
- what belongs to orchestration/platform work much later

The guiding principle is:

**Build the hand first. Then build the watcher. Then build the governor. Then build the larger system.**

---

## 2. Strategic thesis

`advanced-vision` should mature in this order:

1. **Local computer-use substrate**
   - see
   - act
   - verify
   - log

2. **Visual analysis extensions**
   - recording analysis
   - targeted model-assisted review
   - simple escalation to stronger cloud reasoning where justified

3. **Application-specific intelligence**
   - trading-watch workflows
   - domain-specific classifiers and reviewers
   - policy/gating for higher-risk actions

4. **Platform/orchestration integration**
   - message bus
   - workflow engine
   - Lobster / OpenClaw / Ralph integration
   - cross-agent coordination

This sequencing matters because the repo is still in the early substrate stage.

---

## 3. Tracks

The roadmap is best understood as **three tracks**, not one giant monolith.

## Track A — Core `advanced-vision`

This is the repo’s true center.

### A0. Runtime and environment
- dedicated computer-use environment
- GPU/runtime verification
- dependency/bootstrap tooling
- exact server startup path

### A1. Capture and artifact basics
- screenshot capture
- optional recording ingestion path
- artifact layout
- basic performance profiling
- logging cleanup

### A2. Simple perception loop
- motion gate / cursor suppression
- lightweight detection
- lightweight tracking
- one scout/reviewer path at most

### A3. Action and verification loop
- input actions
- safe dry-run behavior
- action → verify → log
- short local demo scenario

### A4. Video/recording experiment
- test short MP4 support
- confirm whether official Moonshot API path is required
- choose between:
  - direct video API
  - local frame extraction
  - hybrid approach

### A5. Light hardening
- structured logs
- cleanup/retention helpers
- small provenance improvements
- modest integration notes

This track should stay the repo’s implementation center until it is clearly real.

---

## Track B — Trading watch / domain intelligence

This is a valid future direction, but it should sit **on top of** Track A rather than distort it.

### B0. Domain framing
- define first supported workflow
- decide supported platforms (TradingView, ThinkOrSwim, custom app, etc.)
- define event taxonomy

### B1. Higher-precision visual review
- segment/chart-region refinement
- UI structure extraction
- chart/indicator understanding

### B2. Local reviewer lane
- lightweight reviewer model
- uncertainty thresholds
- selective escalation only

### B3. Cloud escalation lane
- Kimi escalation for ambiguous/high-value visual cases
- sanitized bundles only
- evidence-first responses

### B4. Domain policy layer
- pause/warn/hold recommendations
- deterministic rules
- no direct trade execution from raw model output

### B5. Optional time-series / chart-pattern modules
- Chronos or equivalent
- specialized pattern detectors
- anomaly detectors

This track should remain secondary until Track A proves the body works.

---

## Track C — Orchestration / platform layer

This is the largest future layer and should come last.

### C0. Workflow representation
- simple graph/state machine
- bounded node contracts

### C1. Event bus / message envelopes
- frame available
- candidate change
- track bundle ready
- review requested
- action result

### C2. OpenClaw boundary
- registration guidance
- narrow adapter surface
- approval-aware escalation patterns

### C3. Lobster / Ralph / larger system integration
- external workflow handoff
- resume tokens
- approval gates
- higher-level orchestration

This track is real future work, but it should not control the repo before the core runtime is stable.

---

## 4. Research-backed corrections to the original plan

### Correction 1 — BoT-SORT is built into Ultralytics
Per current Ultralytics docs, BoT-SORT is available as a built-in tracker via the `track` mode and `botsort.yaml`; it should not be treated as a separate model acquisition problem.

### Correction 2 — Video support is promising but not yet a repo guarantee
Per Moonshot/Kimi K2.5 usage guidance and model card references:
- K2.5 supports image and video input
- video is **experimental**
- chat with video content is supported in the **official API** path, not something to assume on every compatibility route

So recording analysis belongs in the roadmap, but not as a core assumption for current implementation.

### Correction 3 — `pygetwindow` is not reliable on Linux here
Direct testing in the dedicated env confirmed:
- `tkinter`, `pyautogui`, and `PIL` import
- `pygetwindow` still fails on Linux here

So the architecture should remain screenshot/coordinate/verification-centered rather than window-enumeration-centered.

### Correction 4 — NVFP4 is useful, but runtime truth beats checkpoint optimism
The original plan usefully surfaced NVFP4 options, but runtime VRAM remains higher than checkpoint size because:
- KV cache remains unquantized
- vision components stay at original precision
- runtime and framework overhead matter

So model-choice planning belongs in Track B and later Track A experiments, not as the repo’s first identity.

---

## 5. What belongs in the roadmap but not near-term execution

Keep these in the map, but out of the first execution ladder:
- Chronos-2
- Nemotron
- Cosmos anomaly detection
- stock pattern detectors
- Ralph human-simulation layer
- LangGraph workflow engine
- message bus
- Lobster integration
- broad multi-model concurrent residency assumptions

These are legitimate future directions. They are just not the next body of work.

---

## 6. Decision rules

Use these rules when deciding whether a feature belongs in the near-term execution plan.

A feature belongs in near-term execution only if it directly improves one or more of:
- runtime truth
- local computer-use capability
- safe testing
- documentation accuracy
- integration clarity for the current substrate

If it mainly improves:
- future policy architecture
- domain specialization
- large-scale orchestration
- speculative concurrency

then it belongs in the roadmap, not the immediate build plan.

---

## 7. Big phases

These are roadmap phases, not immediate sprint boundaries.

### Phase R0 — Runtime body
Get the local body working.

### Phase R1 — Visual scout
Get capture, lightweight detection, and review loop working.

### Phase R2 — Action loop
Get safe local action and verification working.

### Phase R3 — Recording/video extension
Test short recording analysis through the right path.

### Phase R4 — Domain watch mode
Add trading-specific or other domain-specific logic.

### Phase R5 — Policy and orchestration layering
Add governors, workflow systems, and cross-system bridges.

---

## 8. Bottom line

Aya’s original plan should be preserved as research energy, but the repo should not try to become all of it at once.

The healthy hierarchy is:
- **Execution plan:** what we build now
- **Master roadmap:** what we may grow into

That is how `advanced-vision` stays coherent instead of swelling into three repos trapped in one folder.
