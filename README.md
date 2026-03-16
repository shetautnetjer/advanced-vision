# advanced-vision

`advanced-vision` is a **standalone**, minimal local computer-use capability layer for AI systems.
It intentionally focuses on local primitives only, so it can be integrated into a larger system later.

## Scope

Implemented now:
- MCP server exposing the following tools:
  - `screenshot_full`
  - `screenshot_active_window` (best effort)
  - `list_windows` (best effort)
  - `move_mouse`
  - `click` (left/right)
  - `type_text`
  - `press_keys` (single keys and combos like `Ctrl+L` using `keys=["ctrl","l"]`)
  - `scroll` (vertical and best-effort horizontal)
  - `verify_screen_change`
  - `analyze_screenshot` (via vision adapter stub)
- Pydantic schemas for stable structured outputs
- Local artifact logging:
  - screenshots under `artifacts/screens/`
  - JSONL logs under `artifacts/logs/`
- A helper flow for one cycle: screenshot -> analyze -> (optional) act -> verify

Stubbed/minimal by design:
- `vision_adapter.py` returns a deterministic noop `ActionProposal`
- no external vision API calls and no secrets/API keys

## Non-goals in this repository

- No unrestricted shell/file tools
- No browser automation
- No autonomous multi-step planner
- No retries/orchestration engine
- No vector DB or SQL persistence
- No global governance/policy framework
- No Brain-harness dependency

## Platform notes

- `screenshot_active_window` uses `pygetwindow` + bounding-box capture when possible, and falls back to full-screen capture otherwise.
- `list_windows` uses a best-effort approach and may return an empty list in headless/minimal desktop environments.
- Input tools (`move_mouse`, `click`, `type_text`, etc.) rely on local GUI access and can fail gracefully when GUI backends are unavailable.
- Linux desktop sessions may require X11/Wayland compatibility for screenshot/input libraries.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

## Run MCP server

```bash
advanced-vision-server
```

## Quick flow demo

```bash
python -c "from advanced_vision.flow import run_single_cycle; print(run_single_cycle('Open address bar', execute=False))"
```

## Run tests

```bash
pytest -q
```

## Repository layout

```text
src/advanced_vision/
  server.py
  config.py
  schemas.py
  logging_utils.py
  vision_adapter.py
  flow.py
  tools/
    screen.py
    windows.py
    input.py
    verify.py
tests/
configs/
artifacts/
```
