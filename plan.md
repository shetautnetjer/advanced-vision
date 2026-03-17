# Advanced Vision Plan

This repo now uses a **two-layer planning model**:

1. **`MASTER_ROADMAP.md`** — the full strategic map
2. **`EXECUTION_PLAN.md`** — the near-term grounded build order

That split exists because the earlier single-file plan mixed:
- core repo work
- trading-specific application ideas
- larger orchestration/platform ideas

all into one execution body.

The research in the earlier draft was valuable, but the repo needed a cleaner separation between:
- what should be built now
- what should be preserved as future direction

---

## Read these in order

### 1. `EXECUTION_PLAN.md`
Use this for actual implementation.

Current near-term focus:
- runtime truth
- screenshot/read path
- safe action testing
- action verification
- bounded recording/video experiment
- light integration guidance

### 2. `MASTER_ROADMAP.md`
Use this for the big map.

This keeps the larger future visible:
- trading-watch intelligence
- cloud escalation
- domain-specific reviewers
- governance layers
- workflow/orchestration integration

without forcing the current repo to carry all of it immediately.

---

## Research conclusions preserved from the earlier draft

- BoT-SORT should be treated as a built-in Ultralytics tracker path, not a separate heavyweight model program.
- Kimi K2.5 appears promising for recording/video analysis, but video is experimental and should be treated as an **official-API-specific experiment**, not assumed as a general current repo capability.
- NVFP4 model options are useful for later reviewer/scout experiments, but model-portfolio planning should not outrun the repo’s verified substrate.
- `advanced-vision` still needs to stay grounded in:
  - capture
  - action
  - verify
  - log

before it swells into trading/governance/orchestration layers.

---

## Practical rule

If you are asking:
> what should we build next?

read `EXECUTION_PLAN.md`.

If you are asking:
> where could this whole system go later?

read `MASTER_ROADMAP.md`.
