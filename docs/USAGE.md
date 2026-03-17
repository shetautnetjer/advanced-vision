# Advanced Vision - Usage Guide

**Quick start guide for using advanced-vision tools from OpenClaw and other agents.**

---

## Installation

### Prerequisites

```bash
# Ubuntu/Debian
sudo apt-get install -y python3.11-tk scrot ffmpeg

# Verify X11 (not Wayland)
echo $XDG_SESSION_TYPE  # Should print: x11
```

### Setup

```bash
cd ~/.openclaw/workspace/plane-a/projects/advanced-vision
source .venv-computer-use/bin/activate
```

---

## Basic Usage

### 1. Screenshot Capture

```python
from advanced_vision.tools import screenshot_full, screenshot_active_window

# Full desktop
artifact = screenshot_full()
print(f"Saved: {artifact.path}")
# Output: Saved: artifacts/screens/full_2026-03-17T10-30-00.png

# Active window only
artifact = screenshot_active_window()
print(f"Size: {artifact.width}x{artifact.height}")
```

### 2. Safe Action Testing (Dry Run)

```python
from advanced_vision.tools import move_mouse, click, type_text

# Test without actually moving (dry_run=True)
result = move_mouse(500, 500, dry_run=True)
print(result.message)
# Output: [DRY RUN] Would move mouse to (500, 500)

# Test click
result = click(960, 600, button="left", dry_run=True)
print(result.ok)  # True

# Test typing
result = type_text("Hello World", dry_run=True)
print(result.message)
# Output: [DRY RUN] Would type 11 chars
```

### 3. Verify Screen Changes

```python
from advanced_vision.tools import screenshot_full, verify_screen_change

# Before action
before = screenshot_full()

# ... perform some action ...

# After action
result = verify_screen_change(before.path, threshold=0.95)
print(f"Changed: {result.changed}")
print(f"Similarity: {result.similarity:.4f}")
```

---

## Complete Workflow: See → Act → Verify

```python
from advanced_vision.tools import (
    screenshot_full,
    move_mouse,
    click,
    verify_screen_change,
)

# 1. See - Capture before state
before = screenshot_full()

# 2. Act - Move mouse and click (dry_run for safety)
move_mouse(500, 500, dry_run=False)
click(500, 500, dry_run=False)

# 3. Verify - Check what changed
after = screenshot_full()
result = verify_screen_change(before.path, after.path)

if result.changed:
    print(f"✅ Screen changed (similarity: {result.similarity:.2f})")
else:
    print(f"⚠️ No significant change detected")
```

---

## Phase E3: Action Verification

Execute action with automatic verification:

```python
from advanced_vision.tools import execute_and_verify

# Move mouse and verify cursor position changed
result = execute_and_verify(
    action_type="move_mouse",
    x=500,
    y=500,
    delay_seconds=0.3,
    dry_run=False,
)

print(f"Action: {result['action_result']['message']}")
print(f"Changed: {result['verification']['changed']}")
print(f"Before: {result['before_screenshot']['path']}")
print(f"After: {result['after_screenshot']['path']}")
```

### Safe Demo Scenarios

```python
from advanced_vision.tools import (
    demo_mouse_movement,
    demo_click_at_safe_location,
    demo_typing_in_scratch_area,
)

# Safe demos use preset coordinates
result = demo_mouse_movement(dry_run=True)
result = demo_click_at_safe_location(dry_run=True)
result = demo_typing_in_scratch_area(dry_run=True)
```

---

## Phase E4: Video Recording

```python
from advanced_vision.tools import record_and_analyze

# Record 10 seconds and analyze with Kimi
result = record_and_analyze(
    duration=10,
    question="What is happening on the screen?",
)

print(f"Video: {result.video_path}")
print(f"Analysis: {result.answer}")
```

### Manual Video Workflow

```python
from advanced_vision.tools import record_screen_video, extract_keyframes, analyze_video_with_kimi
from pathlib import Path

# 1. Record
video = record_screen_video(duration=15, fps=5)

# 2. Extract keyframes (for inspection)
frames = extract_keyframes(Path(video.path), n=5)
for frame in frames:
    print(f"Frame: {frame}")

# 3. Analyze
result = analyze_video_with_kimi(
    Path(video.path),
    question="Describe the workflow shown in this recording",
)
print(result.answer)
```

---

## OpenClaw Integration

### From mcporter CLI

```bash
# Screenshot
mcporter call advanced-vision.screenshot_full

# Move mouse (dry run)
mcporter call advanced-vision.move_mouse x=100 y=200 dry_run=true

# Click
mcporter call advanced-vision.click x=500 y=500 button=left

# Verify change
mcporter call advanced-vision.verify_screen_change \
  previous_screenshot_path="artifacts/screens/full_xxx.png" \
  threshold=0.95
```

### From Python (OpenClaw Agent)

```python
import subprocess
import json

def call_advanced_vision(tool: str, **kwargs):
    """Call advanced-vision tool via mcporter."""
    args = [f"{k}={v}" for k, v in kwargs.items()]
    result = subprocess.run(
        ["mcporter", "call", f"advanced-vision.{tool}"] + args,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)

# Usage
screenshot = call_advanced_vision("screenshot_full")
print(f"Saved to: {screenshot['path']}")

# With dry_run safety
result = call_advanced_vision("move_mouse", x=100, y=200, dry_run="true")
```

---

## Safety Guidelines

### 1. Always Use dry_run First

```python
# ✅ Good: Test before executing
result = move_mouse(500, 500, dry_run=True)
if result.ok:
    # Now execute for real
    move_mouse(500, 500, dry_run=False)
```

### 2. Safe Coordinates

Use `SAFE_COORDINATES` for demo/testing:

```python
from advanced_vision.tools import SAFE_COORDINATES

# These are safe (center-ish, avoiding edges)
center_x, center_y = SAFE_COORDINATES["center"]
move_mouse(center_x, center_y, dry_run=True)
```

Available presets:
- `center` - Center of screen
- `safe_upper_left` - Top-left quadrant
- `safe_upper_right` - Top-right quadrant
- `safe_lower_left` - Bottom-left quadrant
- `safe_lower_right` - Bottom-right quadrant

### 3. Live Tests Require Explicit Enable

```bash
# Dry run tests (default)
pytest tests/test_smoke.py -v

# Live tests (actually moves mouse/clicks)
ADVANCED_VISION_LIVE_TESTS=1 pytest tests/test_smoke.py -v
```

### 4. Verify Before Acting on Critical UI

```python
# Take screenshot before important actions
before = screenshot_full()

# ... perform action ...

# Verify the expected change occurred
after = screenshot_full()
result = verify_screen_change_between(before.path, after.path)

if not result.changed:
    print("⚠️ Action may have failed - no visual change detected")
```

---

## Troubleshooting

### Issue: Screenshots are all gray (1280x720)

**Cause:** No GUI session available (headless/SSH without X11)

**Solution:**
```bash
# Ensure DISPLAY is set
echo $DISPLAY  # Should show :1 or similar

# If using SSH, enable X11 forwarding
ssh -X user@host
```

### Issue: pyautogui fails with "display"

**Cause:** Missing tkinter or X11 dependencies

**Solution:**
```bash
sudo apt-get install python3-tk python3-dev scrot
```

### Issue: Window detection fails on Linux

**Cause:** Using Wayland instead of X11

**Solution:**
```bash
# Check session type
echo $XDG_SESSION_TYPE

# Switch to X11 if showing "wayland"
# (Logout and select "X11" or "Xorg" at login)
```

### Issue: ffmpeg not found (video recording)

**Solution:**
```bash
sudo apt-get install ffmpeg
```

---

## Next Steps

After mastering basic usage:

1. **Track B: Trading Intelligence**
   - YOLO for UI element detection
   - SAM3 for precision segmentation
   - Scout/Reviewer model pipeline

2. **Custom Workflows**
   - Build your own action sequences
   - Integrate with trading platforms
   - Create automated test suites

3. **Ralph Protocol**
   - Autonomous agent workflows
   - Self-directed task completion

---

## Support

- **Documentation:** `docs/` folder in repo
- **Status:** `EXECUTION_STATUS.md`
- **Tests:** `pytest tests/ -v`
- **Diagnostics:** `python3 -m advanced_vision.diagnostics`
