# Architecture Principles

Hard rules. No exceptions.

---

## 1. Truth vs Transport

**Truth lives local.**

- Capture layer = truth
- Artifact layer = truth  
- Event layer = truth

**WSS is fanout only.** Not truth. Not storage. Fire and forget.

**JSONL logs are append-only.** Replayable. Immutable. That's your audit trail.

---

## 2. Advisory vs Governor

**Models advise. Governor decides.**

- Eagle scouts (fast detect)
- Qwen reviews (deep analysis)
- Kimi oversees (escalation)

None of them decide. Advice only.

**Governor decides.** Policy gate. Rules, not ML.

**Risk levels:**
- `continue` — proceed
- `note` — log it
- `warn` — alert, proceed
- `hold` — pause, queue for review
- `pause` — stop line
- `escalate` — human required

---

## 3. Local-First

**Raw frames never leave.**

- Store local
- Process local
- Send refs only

`frame_ref`, `roi_refs` — that's what travels.

Never stream raw video to cloud. Ever.

---

## 4. Three Planes

| Plane | Location | Purpose |
|-------|----------|---------|
| Control | External | Arbiter, OpenClaw, human commands |
| Capability | This repo | Code, logic, pipelines |
| Data/Secret | External | `.env`, credentials, secrets |

Separate by design. Merge on purpose.

---

## 5. Model Roles

| Model | Role | Latency |
|-------|------|---------|
| Eagle2-2B | Scout | ~400ms |
| Qwen3.5-4B | Reviewer | Deep analysis |
| Kimi | Overseer | Escalation, reasoning |
| Governor | Policy | Rules engine |

Scout finds. Reviewer validates. Overseer questions. Governor decides.

---

*Break these at your own risk.*
