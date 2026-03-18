# Forward Plan

## Objective

Move from promising local model demos and partial runtime work to a stable, governed `advanced-vision` substrate that can power both:
- general computer-use assistance
- trading-specific watch/review flows

---

## Phase 1 — Lock the truth boundary

### Deliverables
- append-only event log format
- image / ROI / clip manifest format
- packet schema for external review
- clear statement that WSS is derived fanout only

### Success criteria
- replayable event and artifact trail exists independent of live subscribers
- disconnecting a subscriber does not lose authoritative truth

---

## Phase 2 — Stabilize the hot path

### Deliverables
- cursor suppression
- frame diff / motion gate
- YOLO detection
- hot-path tracking
- MobileSAM triggered usage
- Eagle scout result schema

### Success criteria
- cursor-only motion does not cause escalations
- benign UI movement rarely pauses the system
- hot-path latency is measured and logged

---

## Phase 3 — Standardize packetization upward

### Deliverables
- UI packet builder
- trading packet builder
- packet storage and image refs
- candidate-target schema

### Success criteria
- Aya/OpenClaw can consume packets consistently using image-only support
- packets are small, inspectable, and replayable

---

## Phase 4 — Add local review lane

### Deliverables
- local reviewer call contract
- Qwen review schema
- review trigger policy
- retry / recheck behavior

### Success criteria
- Qwen only runs when the scout says the event is meaningful or ambiguous
- review outputs are compact and structured

---

## Phase 5 — External finalizer integration

### Deliverables
- external review request envelope
- external review result envelope
- Aya/OpenClaw adapter
- reviewer metadata capture

### Success criteria
- Aya can act as external finalizer using image packets
- another reviewer could replace Aya without changing substrate truth records

---

## Phase 6 — Trading-specific governor

### Deliverables
- trading review policy
- anomaly / risk event schema
- explicit allow / block / recheck decisions
- optional approval checkpoints

### Success criteria
- no direct trade action from raw scout output
- ambiguous or risky cases are gated

---

## Phase 7 — LangGraph / Lobster boundary (optional hardening)

### LangGraph lane
- package slower review/escalation graph
- retry / escalate / commit branches

### Lobster lane
- only for deterministic OpenClaw tool workflows with approvals/resume

### Success criteria
- substrate choice stays implementation-level, not doctrine-level

---

## Ongoing validation work

- benchmark Eagle scout role against Qwen-based alternatives on real UI/trading tasks
- validate packet sizes and latency under normal desktop use
- prove replay from logs/manifests
- test subscriber disconnect/reconnect behavior
- measure false positives on cursor noise and benign UI transitions
