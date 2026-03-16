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

#### Planned next repo-side fixes
- add setup notes for GUI/backend behavior
- validate MCP server startup after dependencies are installed
- validate screenshot/input behavior after environment bootstrapping
