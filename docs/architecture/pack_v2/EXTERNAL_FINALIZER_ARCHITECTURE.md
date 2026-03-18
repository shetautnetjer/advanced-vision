# External Finalizer Architecture

## Goal

Enable any strong external reviewer/finalizer to consume curated perception packets from `advanced-vision` without requiring native video support.

This is important because OpenClaw currently supports images, not full video review.

---

## Core principle

The external agent should **not** be asked to solve raw perception from scratch.

The local substrate should do the cheap and frequent work first:
- notice changes
- ignore cursor-only noise
- isolate candidate ROIs
- classify likely UI elements
- package recent evidence

Then the external reviewer/finalizer consumes a **structured image packet**.

---

## Reviewer/finalizer roles supported by this architecture

### Today
- Aya running Kimi through OpenClaw

### Also supported by design
- ChatGPT as reviewer/finalizer
- Claude as reviewer/finalizer
- Gemini as reviewer/finalizer
- another OpenClaw-connected model
- future local reviewer/finalizer adapter

---

## Packet-oriented design

### Why packets
Since the external layer is image-capable but not video-native, the local loop should convert live screen activity into **micro-episodes**.

A micro-episode may contain:
- one full screenshot reference
- 1–5 ROI crops
- one previous frame reference if useful
- small burst of keyframes
- scout note
- candidate targets / click anchors
- risk tags
- schema type (`ui` or `trading`)

---

## Recommended packet schema

```json
{
  "packet_id": "uuid7",
  "mode": "ui|trading",
  "event_type": "ui_change|trading_signal|warning|unknown",
  "summary": "Confirmation modal appeared after click.",
  "frame_ref": "frames/frame_001233.jpg",
  "previous_frame_ref": "frames/frame_001232.jpg",
  "roi_refs": [
    {
      "id": "confirm_modal",
      "path": "rois/confirm_modal_001233.jpg",
      "bbox": [812, 601, 310, 180],
      "label": "modal"
    }
  ],
  "targets": [
    {
      "id": "confirm_btn",
      "bbox": [870, 712, 116, 40],
      "label": "button",
      "confidence": 0.94,
      "click_point": [928, 732]
    }
  ],
  "scout_note": "Real UI change, not cursor noise. Confirmation likely required.",
  "risk_tags": ["requires_confirmation"],
  "needs_local_review": false,
  "needs_external_review": true
}
```

---

## Interface contract

### What the substrate sends upward
- image refs
- ROI refs
- structured notes
- candidate targets
- local confidence / risk flags
- optional short event history slice

### What the reviewer/finalizer sends back
- continue
- click target X
- type text Y
- request fresh screenshot
- request deeper local review
- trading: warn / block / escalate / ask for approval

---

## Why this is better than video-first review

### Benefits
- reduces bandwidth
- lowers latency
- makes external reviewer inputs cleaner
- supports image-only external systems
- allows many finalizer choices
- preserves replayable artifacts locally

### Trade-off
The local substrate must do more packaging work.

That trade-off is worth it.

---

## UI mode flow

```text
capture
→ motion / cursor suppression
→ detector + tracker
→ Eagle scout
→ build UI packet
→ external reviewer chooses next move
→ action goes through governor / tool layer
```

---

## Trading mode flow

```text
capture
→ motion / cursor suppression
→ detector + tracker
→ Eagle scout
→ local Qwen review if needed
→ build trading packet
→ external finalizer reviews
→ governor decides whether any action is allowed
```

---

## Finalizer-agnostic requirement

Do not write the protocol as:
- `kimi_review_request`
- `kimi_result`

Write it as:
- `external_review_request`
- `external_review_result`

and store reviewer identity in metadata.

Example:

```json
{
  "reviewer": {
    "agent_identity": "aya",
    "provider": "openclaw",
    "model": "kimi"
  }
}
```

This makes the system portable.
