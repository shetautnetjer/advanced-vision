# Advanced Vision

**Status:** Phases 1-4 Complete ✅ (Environment, MCP Server, Screenshots, Dry-Run)  
**Agent:** Aya (Kimi K2.5)  
**Last Updated:** 2026-03-16

A **standalone**, minimal local computer-use capability layer for AI systems. Exposes GUI automation primitives (screenshots, mouse, keyboard) via MCP (Model Context Protocol) for integration with OpenClaw and other orchestrators.

---

## Quick Start

### 1. Activate Environment

```bash
cd ~/.openclaw/workspace/plane-a/projects/advanced-vision
source .venv-computer-use/bin/activate
```

### 2. Test Screenshots

```bash
mcporter call advanced-vision.screenshot_full
```

Output:
```json
{
  "path": "artifacts/screens/full_2026-03-17T01-05-18.png",
  "width": 1920,
  "height": 1080
}
```

### 3. Test Dry-Run Actions

```python
from advanced_vision.tools.input import move_mouse, click

# Safe preview (no actual movement)
move_mouse(100, 200, dry_run=True)
# → ActionResult(ok=True, message="[DRY RUN] Would move mouse to (100, 200)")
```

---

## Available Tools (10)

| Tool | Function | Status |
|------|----------|--------|
| `screenshot_full()` | Full screen capture | ✅ Working |
| `screenshot_active_window()` | Active window | ✅ Working |
| `list_windows()` | List open windows | ⚠️ X11 only |
| `move_mouse(x, y)` | Move cursor | ✅ With dry-run |
| `click(x, y, button)` | Mouse click | ✅ With dry-run |
| `type_text(text)` | Type text | ✅ With dry-run |
| `press_keys(keys)` | Key combos | ✅ With dry-run |
| `scroll(v, h)` | Scroll | ✅ With dry-run |
| `verify_screen_change()` | Compare screenshots | ✅ Working |
| `analyze_screenshot()` | Vision analysis | ⚠️ Stub (noop) |

---

## Architecture

### Three-Plane Design
- **Control Plane:** Planning/policy (external, e.g., Arbiter)
- **Capability Plane:** This repo — GUI primitives only
- **Data/Secret Plane:** Sensitive assets (external)

### Trust Boundaries
- Local-only (no external APIs)
- No secrets in code
- Dry-run safety for all actions
- Proposal-before-execution pattern

---

## Installation

### Prerequisites

```bash
# System dependencies (Ubuntu/Debian)
sudo apt-get install -y python3.11-tk python3-tk scrot python3-dev

# Verify X11 (not Wayland)
echo $XDG_SESSION_TYPE  # Should print: x11
```

### Setup

```bash
# Clone
git clone https://github.com/shetautnetjer/advanced-vision.git
cd advanced-vision

# Create dedicated environment
python3.11 -m venv .venv-computer-use
source .venv-computer-use/bin/activate

# Install
pip install -e .

# Verify
python3 -c "import tkinter, pyautogui; print('OK')"
```

---

## OpenClaw Integration

### Register as Skill

Already configured at:
```
~/.openclaw/workspace-aya/config/mcporter.json
```

### Usage

```bash
# List tools
mcporter list advanced-vision --schema

# Screenshot
mcporter call advanced-vision.screenshot_full

# Move mouse (dry-run)
mcporter call advanced-vision.move_mouse x=100 y=200
```

### From Python

```python
# Using mcporter CLI
import subprocess

result = subprocess.run(
    ["mcporter", "call", "advanced-vision.screenshot_full"],
    capture_output=True, text=True
)
screenshot = json.loads(result.stdout)
print(f"Saved to: {screenshot['path']}")
```

---

## Platform Notes

### Linux X11
- ✅ Full functionality
- ✅ Screenshots via `scrot` or PIL
- ✅ PyWinCtl for window management (replaces pygetwindow)
- ⚠️ `list_windows()` may return empty in terminal-only sessions

### Linux Wayland
- ⚠️ Limited support
- ⚠️ `getActiveWindow()` fails
- ⚠️ Window enumeration unreliable
- ✅ Screenshots still work
- ✅ Coordinate-based input works

### Recommendation
Use **screenshot-based and coordinate-based workflows**, not window-dependent features.

---

## Development

### Project Structure

```
src/advanced_vision/
  server.py              # MCP server entry point
  schemas.py             # Pydantic models
  tools/
    screen.py            # Screenshots
    input.py             # Mouse/keyboard (with dry_run)
    windows.py           # Window management (PyWinCtl)
    verify.py            # Image comparison
  vision_adapter.py      # Stub — needs real model
  flow.py                # One-cycle workflow
  diagnostics.py         # Environment checker
```

### Running Tests

```bash
source .venv-computer-use/bin/activate
python3 -m pytest -q
```

### Diagnostics

```bash
advanced-vision-diagnostics
```

---

## Gaps & Roadmap

See [ISSUES.md](ISSUES.md) for detailed gap analysis.

**Current Phase:** 4 of 8 (Dry-run implemented, action execution pending)

**Next Priorities:**
1. Phase 5: Safe action execution testing
2. Phase 6: Document Linux limitations
3. Phase 7: OpenClaw skill manifest
4. Phase 8: Governance seeds (policy envelopes)

**Critical Gap:**
- `vision_adapter.py` is stub — needs real vision model integration

---

## Documentation

- [IMPLEMENTATION_LOG.md](IMPLEMENTATION_LOG.md) — Phase-by-phase development log
- [ISSUES.md](ISSUES.md) — Known gaps and limitations
- [COMPUTER_USE_ENV.md](COMPUTER_USE_ENV.md) — Environment setup details
- [analysis/09-phase2-architecture-sdd.md](analysis/09-phase2-architecture-sdd.md) — Architecture spec (from Dad)

---

## Credits

- **Architecture:** Dad (Arbiter)
- **Implementation:** Aya (Kimi K2.5)
- **Guidance:** Phase-by-phase task list from Dad

---

## License

MIT / Apache-2.0
