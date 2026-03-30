# Computer-Use Environment

This is the day-to-day operating guide for the local Linux control lane.

## Current Default

- Repo: `/home/netjer/Projects/AI Frame/optical.nerves/advanced-vision`
- Environment: `.venv-computer-use`
- Launch path: `scripts/run_advanced_vision_mcp.sh`
- Direct fallback:
  `PYTHONPATH=src .venv-computer-use/bin/python -m advanced_vision.server`

## Quick Start

```bash
cd "/home/netjer/Projects/AI Frame/optical.nerves/advanced-vision"
source .venv-computer-use/bin/activate
```

## Health Check

```bash
PYTHONPATH=src python -m advanced_vision.diagnostics
```

Healthy output should confirm the GUI stack is usable on this Linux machine.

## Direct Validation

```bash
python - <<'PY'
import tkinter
import pyautogui

print("tk:", tkinter.Tcl().eval("info patchlevel"))
print("pyautogui:", pyautogui.__version__)
print("screen:", pyautogui.size())
print("mouse:", pyautogui.position())
PY
```

## Running the MCP Server

```bash
./scripts/run_advanced_vision_mcp.sh
```

## Verifying mcporter

`mcporter` must be run from the workspace root because that is where the
project-level config lives:

```bash
cd "/home/netjer/Projects/AI Frame/optical.nerves"
mcporter config doctor
mcporter list
mcporter call advanced-vision.screenshot_full
```

## Notes

- `.venv-computer-use/bin/advanced-vision-server` is not the reliable default
  entrypoint; its shebang can go stale.
- `artifacts/screens/` holds screenshots and frame evidence.
- `artifacts/logs/` holds action and verification JSONL logs.
- `logs/` is reserved for WSS and e2e runtime logs.
- Keep this file focused on the local control lane. Future model-heavy work
  belongs under `ml/` and deeper docs, not in the day-one operating guide.
