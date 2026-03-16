# Advanced Vision Skill

**Status:** Environment ready, MCP server integration pending  
**Agent:** Aya  
**Repository:** https://github.com/shetautnetjer/advanced-vision

## Overview

Local MCP server for computer-use capabilities (screenshots, mouse/keyboard control, window management).

## Current Status

### ✅ Phase 1: Environment Setup (COMPLETE)

**Delivered:**
- Python 3.11 dedicated environment (`.venv-computer-use`)
- All GUI automation packages installed and validated:
  - tkinter 8.6.14 ✅
  - pyautogui 0.9.54 ✅
  - pyscreeze 1.0.1 ✅
  - python3-Xlib ✅
- System dependencies: python3.11-tk, scrot, python3-dev
- Screen detection: 1920x1080 confirmed
- Mouse tracking: Operational
- Documentation: COMPUTER_USE_ENV.md

**Commit:** `b1a73b9`

### 📋 Phase 2: MCP Server Integration (PENDING)

**Planned:**
- MCP server entry point
- Tool definitions for OpenClaw
- Screenshot tools
- Mouse/keyboard control tools
- Window management tools

## Quick Start

```bash
cd ~/.openclaw/workspace/plane-a/projects/advanced-vision
source .venv-computer-use/bin/activate

# Validate environment
python3 -c "
import tkinter
import pyautogui
print('tkinter:', tkinter.Tcl().eval('info patchlevel'))
print('Screen:', pyautogui.size())
print('Mouse:', pyautogui.position())
"
```

## Tools (Planned)

| Tool | Function | Status |
|------|----------|--------|
| `screenshot_full` | Capture entire screen | 📋 |
| `screenshot_region` | Capture screen region | 📋 |
| `screenshot_window` | Capture specific window | 📋 |
| `move_mouse` | Move cursor to coordinates | 📋 |
| `click` | Mouse click (left/right) | 📋 |
| `type_text` | Type text | 📋 |
| `press_keys` | Key combinations | 📋 |
| `list_windows` | List open windows | 📋 |
| `get_window` | Get window info | 📋 |

## Architecture

- **Runtime:** Python 3.11 (dedicated venv)
- **Protocol:** MCP (Model Context Protocol)
- **Host:** Local only (no external APIs)
- **Trust:** Narrow domain (GUI automation only)
- **Artifacts:** Screenshots saved to `artifacts/screens/`

## Work Log

| Date | Phase | Deliverables | Status |
|------|-------|--------------|--------|
| 2026-03-16 | Environment Setup | Python 3.11, tkinter, pyautogui, docs | ✅ Complete |
| TBD | MCP Server | Tool definitions, integration | 📋 Pending |

## Files

- `COMPUTER_USE_ENV.md` — Environment documentation
- `work_log_*.json` — Work history
- `src/mcp_server.py` — MCP server (pending)
- `.venv-computer-use/` — Python environment (gitignored)

## Next Steps

1. Implement MCP server entry point
2. Define tool schemas for OpenClaw
3. Test screenshot functionality
4. Test mouse/keyboard control
5. Integrate with OpenClaw as MCP skill

## Credits

- Architecture design: Dad (Arbiter)
- Environment strategy: Python 3.11 dedicated venv
- Implementation: Aya
