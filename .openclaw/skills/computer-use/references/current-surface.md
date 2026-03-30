# Current Surface

Use this file to answer "what actually works right now?" before widening scope.

## Primary lane

- Local Linux desktop control via screenshots, mouse or keyboard actions, and window inspection.
- MCP access via `mcporter` from the workspace root.
- Python API access via `src/advanced_vision/tools/`.

## Current tools

- `screenshot_full`
- `screenshot_active_window`
- `list_windows`
- `focus_window`
- `move_mouse`
- `click`
- `type_text`
- `press_keys`
- `scroll`
- `verify_screen_change`
- `analyze_screenshot`

## Files that define the current lane

- `src/advanced_vision/server.py`
- `src/advanced_vision/tools/screen.py`
- `src/advanced_vision/tools/input.py`
- `src/advanced_vision/tools/windows.py`
- `src/advanced_vision/tools/verify.py`
- `src/advanced_vision/diagnostics.py`
- `scripts/run_advanced_vision_mcp.sh`
- `/home/netjer/Projects/AI Frame/optical.nerves/config/mcporter.json`

## Known-good checks

```bash
cd /home/netjer/Projects/AI\ Frame/optical.nerves/advanced-vision
source .venv-computer-use/bin/activate
PYTHONPATH=src python -m advanced_vision.diagnostics
```

```bash
cd /home/netjer/Projects/AI\ Frame/optical.nerves
mcporter list
mcporter call advanced-vision.screenshot_full
mcporter call advanced-vision.focus_window title_query="Google Chrome" dry_run=true
```

## What is not the primary lane

- Trading watcher architecture
- WSS pipeline design
- model benchmarking or TensorRT tuning
- custom YOLO or future vision-role orchestration

Those may be valid future work, but they should not shape day-one operational decisions for Linux PC control.
