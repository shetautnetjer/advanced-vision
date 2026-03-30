# Advanced Vision Skill

Repo router for `advanced-vision`.

## Core Rule

Treat local Linux desktop control as the primary lane.

The first question is:

“Can this repo reliably capture screenshots, expose the MCP server, and perform
safe local control on Linux?”

Treat broader model and vision work as secondary unless the task is explicitly
about those capabilities.

## Start Here

For current operational work, load:

- `.openclaw/skills/computer-use/SKILL.md`
- `docs/README.md` when you need the document map
- `ml/README.md` when the task is about future ML-facing structure

## Current Facts

- repo root:
  `/home/netjer/Projects/AI Frame/optical.nerves/advanced-vision`
- project mcporter config:
  `/home/netjer/Projects/AI Frame/optical.nerves/config/mcporter.json`
- preferred runtime:
  `.venv-computer-use`
- current reliable MCP launch path:
  `scripts/run_advanced_vision_mcp.sh`
- direct fallback launch path:
  `.venv-computer-use/bin/python -m advanced_vision.server` with `PYTHONPATH=src`

## Immediate Priorities

1. keep `mcporter` registration normal and boring
2. keep `.venv-computer-use` the clear default for local-control work
3. keep troubleshooting short and obvious
4. keep root docs small and route deeper material into `docs/`
5. avoid letting future model work muddy the current operating lane

## Secondary Priorities

- repo modularization
- modular docs and skills
- future CV/model normalization under `ml/`
- optional automation through n8n once the operating lane is stable

## Working Style

- use JetBrains semantic tooling for bounded code work
- use Spark sidecars for small discovery passes
- keep the blocking edit local
- use worktrees only when parallel write scopes truly justify them
