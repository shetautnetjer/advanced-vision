# computer-use

Linux GUI automation for screen capture, browser control, and interactive workflows.

## Overview

Control Linux desktop environment programmatically:
- Screen capture (screenshots, video)
- Mouse and keyboard automation
- Browser control (Chrome, Firefox)
- Application launching and interaction
- Screen unlock and session management

## When to Use

- Automating repetitive GUI tasks
- Capturing screenshots for ML training data
- Browser automation without Selenium
- Quick interactive demos
- Screen recording and documentation

## When NOT to Use

- Production web scraping (use Selenium/Playwright)
- Complex form filling (use dedicated tools)
- Headless environments (use Xvfb or cloud)
- Security-sensitive operations (screen recording risks)

## Prerequisites

### Required Tools

```bash
# Option 1: System tools (fastest)
sudo apt install gnome-screenshot imagemagick xdotool

# Option 2: Python (most flexible)
pip install mss pillow pyautogui
```

### Verify Display

```bash
# Check display variable
echo $DISPLAY  # Should output :1 or :0

# If not set:
export DISPLAY=:1
```

## Quick Start

### Capture Screenshot

```bash
export DISPLAY=:1

# Using ImageMagick (most reliable)
import -window root screenshot.png

# Using gnome-screenshot
gnome-screenshot -f screenshot.png
```

### Python Capture

```python
import subprocess

# Fast capture with ImageMagick
subprocess.run(['import', '-window', 'root', 'output.png'])

# Or with mss (faster, no temp files)
import mss
with mss.mss() as sct:
    sct.shot(output='output.png')
```

### Mouse and Keyboard

```bash
export DISPLAY=:1

# Move mouse
xdotool mousemove 500 300

# Click
xdotool click 1

# Type text
xdotool type "Hello World"

# Press keys
xdotool key Return
xdotool key Escape
xdotool key Alt+F4
```

### Browser Automation

```bash
# Open Chrome with URL
google-chrome --new-window "https://tradingview.com"

# Wait for load
sleep 3

# Capture
import -window root browser.png
```

### Screen Unlock

```bash
export DISPLAY=:1

# Wake screen
xdotool mousemove 10 10
sleep 0.5
xdotool mousemove 20 20

# Type password (if at lock screen)
xdotool type "your_password"
xdotool key Return
```

## Common Patterns

### Pattern 1: Capture Sequence

```python
import subprocess
import time

def capture_sequence(count=10, delay=2, prefix="capture"):
    """Capture multiple screenshots."""
    for i in range(count):
        filename = f"{prefix}_{i:02d}.png"
        subprocess.run([
            'import', '-window', 'root', filename
        ], check=True)
        print(f"Captured: {filename}")
        time.sleep(delay)
```

### Pattern 2: Interactive Navigation

```python
import subprocess
import time

def navigate_and_capture():
    """Navigate UI and capture states."""
    # Click at coordinates
    subprocess.run(['xdotool', 'mousemove', '500', '300'])
    subprocess.run(['xdotool', 'click', '1'])
    time.sleep(1)
    
    # Capture
    subprocess.run(['import', '-window', 'root', 'state1.png'])
    
    # Press key
    subprocess.run(['xdotool', 'key', 'Escape'])
    time.sleep(0.5)
    
    # Capture again
    subprocess.run(['import', '-window', 'root', 'state2.png'])
```

### Pattern 3: Browser Workflow

```python
import subprocess
import time

def browser_workflow():
    """Open browser, navigate, capture."""
    # Open browser
    subprocess.Popen([
        'google-chrome', '--new-window', 
        'https://example.com'
    ])
    time.sleep(5)  # Wait for load
    
    # Capture initial state
    subprocess.run(['import', '-window', 'root', 'page_loaded.png'])
    
    # Click something
    subprocess.run(['xdotool', 'mousemove', '800', '400'])
    subprocess.run(['xdotool', 'click', '1'])
    time.sleep(2)
    
    # Capture result
    subprocess.run(['import', '-window', 'root', 'after_click.png'])
```

## Platform-Specific Notes

### Ubuntu/GNOME

- Uses `gnome-screenshot` (if installed)
- Display usually `:1` for remote/VNC
- `xdotool` works reliably

### Headless/SSH

```bash
# Start virtual display
Xvfb :99 -screen 0 1920x1080x24 &
export DISPLAY=:99

# Now run GUI apps
import -window root screenshot.png
```

### WSL

- Install VcXsrv or similar X server
- Set `export DISPLAY=:0`
- May need `export LIBGL_ALWAYS_INDIRECT=1`

## Troubleshooting

### "Cannot open display"

```bash
# Set display variable
export DISPLAY=:1

# Or find correct display
ps aux | grep Xorg  # Check running X servers
```

### "Command not found"

```bash
# Install tools
sudo apt install imagemagick xdotool gnome-screenshot

# Or use Python
pip install mss pillow
```

### Screenshot is black/empty

- Screen may be locked/asleep
- Try waking first with mouse movement
- Check if compositor is running

### Permission denied

- User must have X11 access
- Check `xhost` permissions
- Try: `xhost +local:`

## Security Considerations

⚠️ **Screen capture can expose sensitive data**

- Never capture without user consent in production
- Passwords typed with xdotool may be logged
- Screenshots may contain personal information
- Use only in controlled environments

## Examples

### Example 1: TradingView Capture (What We Did)

```python
#!/usr/bin/env python3
import subprocess
import time

export DISPLAY=:1

# Unlock
subprocess.run(['xdotool', 'type', 'password'])
subprocess.run(['xdotool', 'key', 'Return'])
time.sleep(2)

# Open TradingView
subprocess.Popen([
    'google-chrome', '--new-window',
    'https://tradingview.com/chart/'
])
time.sleep(5)

# Capture sequence
for i in range(10):
    subprocess.run([
        'import', '-window', 'root',
        f'trading_{i:02d}.png'
    ])
    time.sleep(2)
```

### Example 2: Form Automation

```python
#!/usr/bin/env python3
import subprocess
import time

def fill_form():
    export DISPLAY=:1
    
    # Click first field
    subprocess.run(['xdotool', 'mousemove', '400', '300'])
    subprocess.run(['xdotool', 'click', '1'])
    subprocess.run(['xdotool', 'type', 'username'])
    
    # Tab to next field
    subprocess.run(['xdotool', 'key', 'Tab'])
    subprocess.run(['xdotool', 'type', 'password'])
    
    # Submit
    subprocess.run(['xdotool', 'key', 'Return'])
```

### Example 3: Screen Recording

```bash
# Using ffmpeg
ffmpeg -f x11grab -r 30 -s 1920x1080 -i :1.0 output.mp4

# Stop with Ctrl+C
```

## Related Skills

- `browser-automation` — Selenium/Playwright for complex web tasks
- `ocr` — Extract text from screenshots
- `image-processing` — PIL/OpenCV for screenshot analysis
- `video-frames` — Extract frames from video

## References

- ImageMagick: https://imagemagick.org/script/import.php
- xdotool: https://github.com/jordansissel/xdotool
- mss: https://python-mss.readthedocs.io/
- X11 security: https://wiki.archlinux.org/title/X11_security
