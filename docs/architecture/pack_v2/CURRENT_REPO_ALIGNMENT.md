# Current Repo Alignment

## Status of this note

This document is **not** a code audit of the live repository.

It is aligned to:
- the user-provided status summary from the active workstream
- the architecture/doctrine pack created in this conversation
- the watcher / trust-zone design from `vision_plan.md` and `vision_plan_v3.md`

Anything listed under **Verified from user report** should still be re-confirmed in code before being treated as runtime truth.

---

## Verified from user report

The following were reported as currently working or prepared:

### Models / components
- YOLOv8 detect — reported working
- MobileSAM segment — reported working
- Eagle2-2B fast vision — reported ready
- Qwen3.5-2B scout — reported ready
- Qwen3.5-4B reviewer — reported working

### VRAM budget (reported)
- Qwen3.5-4B reviewer: ~8.4 GB
- Qwen3.5-2B scout: ~3.8 GB
- Eagle2-2B fast vision: ~4 GB
- MobileSAM: ~0.5 GB
- YOLOv8: ~0.4 GB
- Total in reported setup: ~14 GB / 16 GB

### Documentation / artifacts reported created
- `docs/QUICKSTART.md`
- `docs/ARCHITECTURE.md`
- `docs/LIMITATIONS.md`
- `docs/VERIFIED_SETUP.md`
- `WHATS_WORKING.md`
- execution and memory update files

### Reported runtime direction
- Eagle2-2B as primary fast visual scout
- YOLO + lightweight segmentation/tracking feeding Eagle
- Qwen as deeper reviewer
- BF16 used in practice instead of relying on NVFP4

---

## Architecture-level interpretation of current repo direction

The repo appears to be trending toward a layered perception stack:

1. **Fast perception helpers**
   - YOLO
   - MobileSAM
   - tracking / ROI boxing

2. **Fast scout**
   - Eagle2-2B

3. **Deeper reviewer**
   - Qwen family model

4. **Optional external reviewer / finalizer**
   - Aya/OpenClaw carrying Kimi today
   - but should remain reviewer-agnostic by design

This direction is good and consistent with the architecture target.

---

## What should not be treated as settled truth yet

### 1. "Eagle is perfect"
Treat Eagle2-2B as a **strong scout candidate**, not a proven final answer.

### 2. WSS as authoritative backbone
Do **not** treat WebSocket fanout as transport truth. Live fanout is useful, but authoritative truth should remain in append-only event/artifact records.

### 3. "Agents spawned" == system verified
Spawning agents or sessions is not the same thing as end-to-end proof.

### 4. Multi-port WSS as permanent architecture
A one-port-per-stage sketch may be useful for initial testing, but should not be assumed to be the final interface shape.

---

## Repo-aware interpretation

The best way to interpret the current repo state is:

- **implementation energy is real**
- **the direction is solid**
- **the transport and authority boundaries still need to be tightened**
- **the external-reviewer layer should be generalized beyond Kimi**

---

## Immediate gap to close

The repo should now make the following distinction explicit:

### Local native substrate
- capture
- motion suppression
- detector / tracker / ROI extraction
- Eagle scout
- evidence packet creation

### Review layer
- local reviewer (Qwen or equivalent)
- external reviewer/finalizer (Aya/OpenClaw today, but general by interface)

### Authoritative layer
- append-only event log
- image/ROI/clip manifests
- replayable episode history
- policy / governor decisions

That separation is the main thing needed to keep the repo aligned with the watcher doctrine.
