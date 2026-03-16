# Computer-Use Environment Setup

## Status

✅ **Created:** `.venv-computer-use` with Python 3.11  
✅ **Installed:** PyAutoGUI, Pillow, PyScreeze, MouseInfo  
⚠️ **Pending:** tkinter (requires system package)

## Environment Location

```
~/.openclaw/workspace/plane-a/projects/advanced-vision/.venv-computer-use/
```

## Installation

```bash
cd ~/.openclaw/workspace/plane-a/projects/advanced-vision

# Create environment
/usr/bin/python3.11 -m venv .venv-computer-use

# Activate
source .venv-computer-use/bin/activate

# Install packages
pip install --upgrade pip
pip install pyautogui pillow pygetwindow pyscreeze mouseinfo
```

## System Dependencies (Required)

```bash
# Install tkinter for Linux (requires sudo)
sudo apt-get update
sudo apt-get install -y python3.11-tk python3-tk scrot python3-dev
```

**Note:** `scrot` is needed for screenshots on Linux.

## Validation Checklist

After system deps installed:

```bash
source .venv-computer-use/bin/activate
python3 -c "
import tkinter
import pyautogui
import pyscreeze
print('✅ All imports working!')
"
```

## Usage

```bash
# Always activate before use
source .venv-computer-use/bin/activate

# Run advanced-vision
python -m src.mcp_server  # or whatever entry point
```

## What's Installed

| Package | Purpose |
|---------|---------|
| pyautogui | Mouse/keyboard automation |
| pillow | Image processing |
| pyscreeze | Screenshots |
| pygetwindow | Window management |
| mouseinfo | Mouse position tracking |
| python3-Xlib | X11 bindings for Linux |

## Architecture

Following Dad's recommendation:
- **Dedicated env** for computer-use capabilities
- **Python 3.11** (known-good for Tk/GUI)
- **Separate from** Linuxbrew 3.14 stack
- **Isolated** trust domain for GUI automation

## Next Steps

1. Install system tkinter: `sudo apt install python3.11-tk scrot`
2. Validate imports work
3. Test screenshot and mouse movement
4. Document any host-specific quirks
