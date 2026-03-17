# Computer-Use Environment Setup

## Status

✅ **COMPLETE** — Environment operational!

| Component | Status | Version |
|-----------|--------|---------|
| Python | ✅ | 3.11 |
| tkinter | ✅ | 8.6.14 |
| pyautogui | ✅ | 0.9.54 |
| pyscreeze | ✅ | 1.0.1 |
| Screen detection | ✅ | 1920x1080 |
| Mouse tracking | ✅ | Working |

## Environment Location

```
~/.openclaw/workspace/plane-a/projects/advanced-vision/.venv-computer-use/
```

## Quick Start

```bash
cd ~/.openclaw/workspace/plane-a/projects/advanced-vision
source .venv-computer-use/bin/activate
```

## Validation

```bash
source .venv-computer-use/bin/activate
python3 -c "
import tkinter
import pyautogui
print('✅ tkinter:', tkinter.Tcl().eval('info patchlevel'))
print('✅ pyautogui:', pyautogui.__version__)
print('✅ Screen:', pyautogui.size())
print('✅ Mouse:', pyautogui.position())
"
```

## Packages Installed

| Package | Purpose | Status |
|---------|---------|--------|
| pyautogui | Mouse/keyboard automation | ✅ |
| pillow | Image processing | ✅ |
| pyscreeze | Screenshots | ✅ |
| pygetwindow | Window management | ✅ |
| mouseinfo | Mouse position | ✅ |
| python3-Xlib | X11 bindings | ✅ |
| tkinter | GUI framework | ✅ 8.6.14 |

## System Dependencies (Installed)

```bash
sudo apt-get install -y python3.11-tk python3-tk scrot python3-dev
```

## Architecture

Following Dad's recommendation:
- ✅ **Dedicated env** for computer-use capabilities
- ✅ **Python 3.11** (known-good for Tk/GUI)
- ✅ **Separate from** Linuxbrew 3.14 stack
- ✅ **Isolated** trust domain for GUI automation

## What's Next

1. Test screenshot functionality: `pyautogui.screenshot()`
2. Test mouse movement: `pyautogui.moveTo(x, y)`
3. Integrate with MCP server
4. Document any host-specific behavior

## Files

- `.venv-computer-use/` — Python environment (gitignored)
- `COMPUTER_USE_ENV.md` — This documentation
- `src/mcp_server.py` — MCP server entry point

## Trust Boundaries

| Capability | Status | Notes |
|------------|--------|-------|
| File operations | ✅ | Standard Python |
| Screen capture | ✅ | PyScreeze + scrot |
| Mouse control | ✅ | PyAutoGUI |
| Keyboard control | ✅ | PyAutoGUI |
| Window management | ✅ | PyGetWindow |

## Update: Window Management Solved

**Problem:** pygetwindow fails on Linux with NotImplementedError

**Solution:** PyWinCtl (cross-platform fork with Linux/X11 support)

```bash
pip install pywinctl
```

**Tested:**
- ✅ pywinctl 0.4.1 installed
- ✅ getAllWindows() finds 4 windows
- ✅ X11 backend working

**Linux Note:**
- Works on X11 (your system)
- Limited on Wayland (getActiveWindow/getAllWindows may fail)

**Migration:**
Replace pygetwindow imports with pywinctl:
```python
# Old (fails on Linux)
import pygetwindow

# New (works on Linux)
import pywinctl as pwc
windows = pwc.getAllWindows()
```
