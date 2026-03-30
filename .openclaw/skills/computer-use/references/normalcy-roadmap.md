# Normalcy Roadmap

Use this order when cleaning the repo over multiple loops.

## Phase 1: Make local control boring

Goal:

- screenshots always work
- `mcporter` registration is obvious
- dry-run input actions are safe
- troubleshooting path is short

Deliverables:

- stable project `mcporter` config
- clear `.venv-computer-use` guidance
- repeatable verification commands

## Phase 2: Separate present from future

Goal:

- local Linux control is documented as current
- model-heavy work is clearly labeled as later or optional

Deliverables:

- skill and docs route current operator work away from model sprawl
- future ML and vision paths are left in place but deprioritized

## Phase 3: Modular cleanup

Goal:

- fewer giant mixed documents
- clearer routing by task

Prefer splitting by operating concern:

- `mcporter`
- Linux control
- troubleshooting
- future model work
- integration or orchestration

## Phase 4: Only then deepen vision

Once local control is easy and stable, then invest in:

- richer screenshot analysis
- better target proposal logic
- model selection and optimization
- packet or orchestration layers

Do not invert this order unless the user explicitly wants model work first.
