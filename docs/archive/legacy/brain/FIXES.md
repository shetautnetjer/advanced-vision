# Fixes

## Changes made

### 2026-03-16

#### Added architecture and service contract docs
- Added `ARCHITECTURE.md`
- Added `SERVICE_CONTRACTS.md`

Purpose:
- define safe trust-boundary architecture
- define contracts for advanced-vision, GitHub, policy broker, secrets broker, and workspace services

#### Added engineering notebook folder
- Added `brain/README.md`
- Added `brain/ISSUES.md`
- Added `brain/FIXES.md`
- Added `brain/PHASES.md`
- Added `brain/TASKS.md`
- Added `brain/WORKLOG.md`

Purpose:
- track discovered blockers
- track repo-readiness work
- keep implementation phases and tasks visible

#### Updated setup docs for this host reality
- Updated README examples from `python` to `python3`
- Updated test command to `python3 -m pytest -q`
- Added diagnostics usage section to README

#### Added diagnostics entrypoint
- Added `src/advanced_vision/diagnostics.py`
- Added console script: `advanced-vision-diagnostics`

Purpose:
- separate dependency/setup failures from code failures quickly
- report Python path, package-import status, and GUI environment hints

#### Research conclusion captured
- Upstream docs/issues support the current diagnosis:
  - PyAutoGUI on Linux commonly needs `python3-tk`, `python3-dev`, and often `scrot`
  - however, non-system Python builds (for example Linuxbrew/pyenv/custom Python) may still fail even after installing distro Tk packages
- This means the host interpreter choice may be part of the blocker, not just repo dependencies

#### Planned next repo-side fixes
- add setup notes for GUI/backend behavior
- document preferred interpreter strategy for Linux input-capable environments
- validate MCP server startup after dependencies are installed
- validate screenshot/input behavior after environment bootstrapping
