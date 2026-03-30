# Mcporter

Use this file when the task is about registration, discovery, or MCP health.

## What is normal

- Project-level config lives at `/home/netjer/Projects/AI Frame/optical.nerves/config/mcporter.json`.
- Home-level config lives at `~/.mcporter/mcporter.json`.
- `mcporter config doctor`, `mcporter config list`, and `mcporter call ...` are the normal verification loop.
- Imported editor MCP sources may also appear in `mcporter list`.

## Current repo wiring

This workspace registers `advanced-vision` through:

- `/home/netjer/Projects/AI Frame/optical.nerves/config/mcporter.json`
- `scripts/run_advanced_vision_mcp.sh`

The wrapper exists because the repo path contains spaces and the older
`advanced-vision-server` console script inside `.venv-computer-use` has a stale shebang.

## Verification commands

```bash
cd /home/netjer/Projects/AI\ Frame/optical.nerves
mcporter config doctor
mcporter config list
mcporter config get advanced-vision --json
mcporter call advanced-vision.screenshot_full
```

## Failure interpretation

- `advanced-vision` missing from `mcporter list`: project config not loaded or malformed.
- `advanced-vision` listed but offline: wrapper script or Python env path is broken.
- `mcporter` call succeeds but tool output is wrong: repo code problem, not registration problem.
