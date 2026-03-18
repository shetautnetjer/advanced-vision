# Architecture Decisions

## Purpose

This file captures the main architectural decisions to carry forward.

It is intentionally opinionated.

---

## AD-001 — `advanced-vision` is the native eyes + fast-attention substrate

### Decision
`advanced-vision` owns:
- local capture
- motion / cursor suppression
- detector and tracker hot path
- ROI isolation
- scout classification
- evidence packet generation

### Why
Most models are not reliably strong enough at raw computer use from full screenshots alone. The substrate should reduce the problem before any planner/reviewer sees it.

---

## AD-002 — External finalizer must be model-agnostic

### Decision
The top review/finalizer layer must not be hard-coded to Kimi.

### Current reality
Today:
- Aya is the agent identity
- Kimi is the model inside Aya/OpenClaw
- OpenClaw supports images, not full native video review

### Required future-proofing
The interface must also support:
- ChatGPT
- Claude
- Gemini
- future OpenClaw-supported model backends
- local reviewer/finalizer adapters

### Result
Design the upward interface around **image packets + structured state**, not a Kimi-specific contract.

---

## AD-003 — Video stays local; reviewer layer consumes image packets

### Decision
Do not make external reviewers consume raw continuous video by default.

### Instead
The local runtime converts continuous observation into discrete review packets:
- full screenshot reference
- ROI crops
- before/after frames
- keyframe burst
- structured notes
- candidate targets

### Why
OpenClaw currently supports images, and this also reduces bandwidth, latency, and ambiguity for any external reviewer.

---

## AD-004 — WSS is derived live fanout, not authority

### Decision
WebSocket/WSS channels may be used for live subscriptions and fanout, but they are not transport truth.

### Authority stays in
- append-only event records
- image / ROI / clip manifests
- replayable episode artifacts
- governor / policy decisions

### Why
This preserves replayability, disconnect tolerance, and doctrine alignment.

---

## AD-005 — Programmatic hot path, not workflow-engine hot path

### Decision
The real-time visual loop should be plain programmatic code.

### Includes
- capture
- cursor suppression
- frame diff / motion gate
- YOLO
- hot-path tracking
- MobileSAM on trigger
- Eagle scout

### Why
This path must be benchmarkable, low-latency, and easy to reason about.

---

## AD-006 — LangGraph is for stateful review/escalation, not the 60 FPS loop

### Decision
If a workflow engine is used in `advanced-vision`, it should sit in the slower stateful review lane.

### Good uses
- evidence packet assembly
- Qwen review branch
- external-review request branch
- clip commit branch
- retry / escalate / pause states

---

## AD-007 — Lobster belongs at the OpenClaw deterministic tool-workflow boundary

### Decision
Use Lobster only for deterministic, approval-gated, resumable tool flows at the OpenClaw side.

### Not for
- raw frame handling
- hot visual loop
- ROI tracking

---

## AD-008 — Eagle2-2B is scout-first

### Decision
Treat Eagle2-2B as the default scout candidate.

### Scout responsibilities
- distinguish noise vs meaningful UI change
- identify likely UI element type
- classify basic chart/UI change
- suggest whether to continue, log, or escalate

### Not default responsibilities
- sole trade reviewer
- sole execution authority
- sole finalizer for ambiguous decisions

---

## AD-009 — Qwen family is reviewer-first

### Decision
Treat Qwen as the deeper local reviewer, especially for trading mode.

### Reviewer responsibilities
- interpret risk-relevant UI state
- analyze chart/ticket combinations
- resolve ambiguity from scout outputs
- produce structured judgment for external finalizer/governor

---

## AD-010 — Governor remains separate from reviewer/finalizer

### Decision
No reviewer, local or external, directly becomes the action authority.

### Governor decides
- continue
- warn
- ask for recheck
- block
- require approval
- allow tool call / execution step

This preserves the system as a governed substrate instead of an unconstrained auto-agent.
