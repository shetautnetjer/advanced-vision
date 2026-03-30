# brain/

This folder is the running engineering notebook for getting `advanced-vision` from a clean minimal repo to a working, governable computer-use capability.

## Purpose

Track, in one place:
- what is currently true
- what is broken
- what was fixed
- what remains blocked
- which implementation phase comes next
- concrete tasks to execute

## Current read of the repo

`advanced-vision` is already a strong minimal starting point:
- MCP server exists
- computer-use tool surface exists
- screenshot / input / verify primitives exist
- vision adapter boundary exists
- tests exist
- docs exist

But it is **not yet proven runnable in this environment**.

## Current blockers discovered

1. No project dependencies installed in the current host environment.
2. `python` is not on PATH here; `python3` is.
3. `pytest` is not installed.
4. Core runtime dependencies are missing:
   - `pydantic`
   - `Pillow`
   - `mcp`
   - `pyautogui`
   - `pygetwindow`
5. Tool-use behavior is only partially validated statically; live execution has not been confirmed yet.

## Working principle

We should progress in this order:

1. Make repo instructions accurate for this host (`python3`, env setup, diagnostics).
2. Record blockers and assumptions.
3. Install dependencies in an isolated virtualenv.
4. Run tests.
5. Run MCP server.
6. Validate screenshot capture.
7. Validate input tools.
8. Validate analysis / flow loop.
9. Add governance and policy improvements.

## Files in this folder

- `ISSUES.md` — discovered problems and risks
- `FIXES.md` — changes made to repo/docs/code
- `PHASES.md` — implementation roadmap
- `TASKS.md` — actionable checklist
- `WORKLOG.md` — chronological notes
