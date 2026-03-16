# Worklog

## 2026-03-16

- Assessed repo structure and core source files.
- Confirmed the implementation includes:
  - MCP server
  - screenshot tools
  - input tools
  - verification logic
  - stub vision adapter
  - smoke tests
- Attempted to run tests and server.
- Found host-level execution blockers:
  - `python` command missing
  - `pytest` missing
  - project dependencies missing from import path
- Confirmed `python3` and `pip3` are available.
- Added architecture and service-contract documentation at repo root.
- Added `brain/` folder to track issues, tasks, phases, and fixes.
- Added a diagnostics module and console-script entrypoint.
- Ran diagnostics with `PYTHONPATH=src python3 -m advanced_vision.diagnostics`.
- Diagnostics confirmed:
  - GUI hint is present (`DISPLAY=:1`, X11)
  - but all required Python modules are still missing in the current environment

## Additional validation after dependency install

- Created `.venv` and installed package with dev dependencies successfully.
- Ran test suite: `6 passed`.
- Ran screenshot and flow smoke checks successfully.
- Confirmed:
  - `screenshot_full()` works
  - `screenshot_active_window()` works (fell back to full-screen-sized capture here)
  - `run_single_cycle(execute=False)` works
  - artifacts and JSONL logs are being written
- Confirmed `list_windows()` currently returns `0` windows on this host.
- Confirmed input actions are still blocked because `pyautogui` imports `mouseinfo`, which requires `tkinter` on Linux.

## Current status

The repo is now partially proven runnable in this environment:
- tests pass
- screenshot and verification path works
- MCP dependencies install cleanly

Remaining blocker for full computer-use tool use:
- system packages needed for input stack (`python3-tk`, likely `python3-dev`)
