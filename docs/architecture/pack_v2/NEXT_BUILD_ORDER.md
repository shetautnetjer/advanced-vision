# Next Build Order

## Build order philosophy

Build the smallest set of pieces that prove the architecture without overcommitting to a transport or workflow substrate too early.

---

## 1. Define core schemas first

Create:
- `schemas/ui_packet.schema.json`
- `schemas/trading_packet.schema.json`
- `schemas/scout_event.schema.json`
- `schemas/external_review_request.schema.json`
- `schemas/external_review_result.schema.json`
- `schemas/artifact_manifest.schema.json`

Reason:
interfaces should harden before fanout/server complexity grows.

---

## 2. Build authoritative local storage and logs

Create:
- append-only event JSONL
- artifact manifest JSONL
- local image/ROI storage layout

Reason:
this becomes the truth layer no matter what transport is used later.

---

## 3. Stabilize the hot visual loop

Implement:
- capture
- cursor suppression
- frame diff / motion gate
- YOLO
- tracking
- MobileSAM on trigger
- Eagle scout classification

Reason:
prove the eyes/attention layer before the reviewer/finalizer layer expands.

---

## 4. Build packetization upward

Implement:
- UI packet builder
- trading packet builder
- candidate click target builder
- recent-frame bundle builder

Reason:
this is the bridge to Aya/OpenClaw and any external reviewer.

---

## 5. Add Aya/OpenClaw adapter

Implement:
- packet ingestion for image-capable external review
- structured response capture
- reviewer metadata recording

Reason:
this lets Aya/Kimi become useful without needing native video support.

---

## 6. Add local reviewer lane

Implement:
- optional Qwen review step
- trigger policy: only for meaningful or ambiguous events
- compact review schema

Reason:
keep local review conditional, not always-on.

---

## 7. Add WSS fanout only after truth layer exists

Implement:
- live packet and event fanout
- subscriber channels
- reconnect-friendly behavior

Reason:
WSS should be derived transport, not truth.

---

## 8. Add governor / risk gate

Implement:
- continue / warn / block / ask_recheck / require_approval
- trading-specific gates
- policy evaluation records

Reason:
this is what keeps the substrate governed.

---

## 9. Optional: LangGraph packaging of slow review flow

Implement only after the steps above work.

Reason:
workflow framework should serve the system, not define it prematurely.
