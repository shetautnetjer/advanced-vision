# linux-control

## Primary Operational Scope

The current scope for `advanced-vision` should be treated as:

- screenshot capture
- dry-run mouse control
- dry-run click, type, key, and scroll actions
- best-effort window listing and focus on Linux
- screen-change verification
- OCR-backed click proposals for visible UI text
- local MCP exposure through `mcporter`

This is the "working now" lane.

## Current Capability Boundary

What should be considered normal today:

- `screenshot_full`
- `screenshot_active_window`
- `list_windows`
- `focus_window`
- `move_mouse` with `dry_run`
- `click` with `dry_run`
- `type_text` with `dry_run`
- `press_keys` with `dry_run`
- `scroll` with `dry_run`
- `verify_screen_change`
- `analyze_screenshot`

What should be considered secondary or future-facing:

- full DOM-aware browser automation
- broad computer-vision reasoning over arbitrary desktop UIs
- multi-model orchestration
- GPU-heavy inference as a prerequisite for basic desktop control

## Code Areas That Matter

- `src/advanced_vision/tools/screen.py`
- `src/advanced_vision/tools/input.py`
- `src/advanced_vision/tools/windows.py`
- `src/advanced_vision/tools/verify.py`
- `src/advanced_vision/server.py`
- `src/advanced_vision/diagnostics.py`

## Bias For Cleanup

When the repo feels convoluted, bias cleanup toward:

1. making the local-control lane reliable
2. separating future-model work from today’s operating path
3. shrinking the number of places a human has to look during a failure
