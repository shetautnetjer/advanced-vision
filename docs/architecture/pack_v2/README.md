# Advanced Vision Architecture Pack v2

This bundle is a repo-aware architecture and planning pack for `advanced-vision`.

It is meant to be used as:
- a doctrine-aligned architecture reference
- a current-state alignment pack
- a forward plan for `advanced-vision` + `advanced-vision MCP` + Aya/OpenClaw integration
- a model-role reference that does **not** depend on Kimi specifically as the only external reviewer/finalizer

## Important framing

This pack separates:
1. **Verified / stated current state** — based on user-provided status updates from the live workstream
2. **Architecture target state** — the design we recommend moving toward
3. **Open questions / validation work** — things that still need proof in code/runtime

## Core idea

`advanced-vision` should become the **native eyes + fast attention substrate**.

That means:
- local capture, tripwire, tracking, ROI isolation, and scout classification happen locally
- OpenClaw / Aya receive curated **image packets** and structured state, not raw continuous video
- any external reviewer/finalizer can sit above the substrate:
  - Kimi inside Aya/OpenClaw
  - ChatGPT
  - Claude
  - Gemini
  - another local or cloud reviewer

## Bundle contents

- `advanced_vision_trading_prd.md`
- `advanced_vision_trading_sdd.md`
- `vision_plan.md`
- `vision_plan_v3.md`
- `tag_registry.yaml`
- `tag_registry.comms.yaml`
- `CURRENT_REPO_ALIGNMENT.md`
- `EXTERNAL_FINALIZER_ARCHITECTURE.md`
- `FORWARD_PLAN.md`
- `ARCHITECTURE_DECISIONS.md`
- `NEXT_BUILD_ORDER.md`

## Recommended reading order

1. `CURRENT_REPO_ALIGNMENT.md`
2. `ARCHITECTURE_DECISIONS.md`
3. `EXTERNAL_FINALIZER_ARCHITECTURE.md`
4. `FORWARD_PLAN.md`
5. `NEXT_BUILD_ORDER.md`
6. PRD / SDD
