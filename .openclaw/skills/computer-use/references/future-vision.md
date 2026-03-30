# future-vision

Model and vision work belongs in a separate lane from the core Linux control path.

## Treat As Future-Facing

- richer UI understanding beyond simple local detection
- multi-model orchestration
- GPU-heavy optimization
- benchmark cleanup
- broad model registry normalization

## Why

This repo is already carrying too many conceptual layers. If model work is mixed
into the current operating lane, it becomes hard to answer the simple question:

“Can this repo take reliable local control of the Linux desktop right now?”

Keep that answer easy.

## Rule Of Thumb

If a task does not improve:

- screenshots
- dry-run actions
- window inspection
- mcporter health
- or troubleshooting clarity

then it is probably not part of the primary lane.
