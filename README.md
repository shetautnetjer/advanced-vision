# Advanced Vision

Local Linux computer-use and screenshot-analysis capability layer.

The current first-class goal for this repo is simple:

1. capture the screen reliably
2. expose a boring, testable MCP surface
3. perform safe local actions on Linux
4. verify what changed

The active control stack now leans on:
- `xdotool` first for Linux window discovery and focus
- OCR-backed screenshot analysis for visible UI text like browser tabs and buttons
- YOLO as a secondary detector fallback when text is not the right cue

Heavier governance, trading, and model-driven vision work still exists here, but
it is secondary to keeping the local control lane clean and dependable.

## Current Operating Truth

- Git repo: `advanced-vision/`
- IDE/workspace wrapper root: `/home/netjer/Projects/AI Frame/optical.nerves`
- Default runtime for computer-use work: `.venv-computer-use`
- Stable MCP launch path: `scripts/run_advanced_vision_mcp.sh`
- Direct fallback launch path:
  `PYTHONPATH=src .venv-computer-use/bin/python -m advanced_vision.server`
- Project-level mcporter registration:
  `../config/mcporter.json`

## Quick Start

### 1. Validate the local computer-use environment

```bash
source .venv-computer-use/bin/activate
PYTHONPATH=src python -m advanced_vision.diagnostics
```

### 2. Run the MCP server directly

```bash
./scripts/run_advanced_vision_mcp.sh
```

### 3. Verify mcporter integration from the workspace root

```bash
cd ..
mcporter config doctor
mcporter list
mcporter call advanced-vision.screenshot_full
mcporter call advanced-vision.focus_window title_query="Google Chrome" dry_run=true
```

### 4. Run the focused validation suite

```bash
cd advanced-vision
source .venv-computer-use/bin/activate
PYTHONPATH=src pytest -q tests/test_smoke.py tests/test_execution_preconditions.py tests/test_integration_e5.py
```

## Repo Layout

- `src/advanced_vision/`
  - Python package and MCP server code
- `scripts/`
  - operational wrappers and launch helpers
- `config/`
  - canonical config home for registry and service settings
- `artifacts/`
  - screenshots and action/audit JSONL output
- `logs/`
  - WSS and e2e runtime logs
- `tests/`
  - smoke, integration, execution-gate, WSS, and benchmark coverage
- `docs/`
  - canonical docs, archived status/history, and deeper architecture material
- `examples/`
  - secondary demos and packet fixtures
- `yolo_training/`
  - secondary dataset and training workspace
- `ml/`
  - future ML-facing implementation notes and scaffolding
- `models/`
  - downloaded assets, checkouts, and model weights

## Documentation

Start with these:

- [Repo skill](SKILL.md)
- [Computer-use environment](COMPUTER_USE_ENV.md)
- [Service contracts](SERVICE_CONTRACTS.md)
- [Docs index](docs/README.md)
- [Future ML home](ml/README.md)

Useful deeper references:

- [Computer use integration](docs/COMPUTER_USE_INTEGRATION.md)
- [Quickstart](docs/QUICKSTART.md)
- [Architecture principles](docs/ARCHITECTURE_PRINCIPLES.md)
- [Trading watcher stack](docs/TRADING_WATCHER_STACK.md)

## Scope Boundaries

- Keep the MCP and Linux desktop-control path reliable first.
- Treat `models/` as artifact storage, not as the source of repo structure.
- Treat `ml/` as the future implementation home for ML-facing work.
- Use Perplexity, 1Password, or n8n only when they unblock a specific need; they
  are not part of the repo’s default runtime.
