# Phase E4: Recording/Video Experiment - COMPLETE ✅

**Status:** Implemented and tested  
**Date:** 2026-03-17  
**Tests:** 13 tests (conditional on ffmpeg/Kimi availability)

---

## E4.1: Video Recording ✅

**Implementation:** `record_screen_video()`

Records screen to MP4 using ffmpeg with X11 capture:
- Duration: Configurable (default 10s)
- FPS: Configurable (default 5)
- Resolution: 1920x1080
- Output: `artifacts/videos/screen_{timestamp}.mp4`

**Usage:**
```python
from advanced_vision.tools.video import record_screen_video

video = record_screen_video(duration=10, fps=5)
print(f"Saved to: {video.path}")
```

---

## E4.2: Keyframe Extraction ✅

**Implementation:** `extract_keyframes()`

Extracts N evenly-spaced frames from video using ffmpeg:
- Uses fps filter to sample frames
- Scales to 1920x1080 for consistency
- Saves to `artifacts/screens/frames_{video_name}/`

**Usage:**
```python
from advanced_vision.tools.video import extract_keyframes
from pathlib import Path

frames = extract_keyframes(Path(video.path), n=5)
for frame in frames:
    print(f"Frame: {frame}")
```

---

## E4.3: Video Analysis via Kimi ✅

**Implementation:** `analyze_video_with_kimi()`

**Important:** Direct video upload is NOT implemented. Current path:
```
Video → Extract Keyframes → Send as Images → Kimi Analysis
```

This fallback approach works reliably and avoids API limitations.

**Usage:**
```python
from advanced_vision.tools.video import analyze_video_with_kimi
from pathlib import Path

result = analyze_video_with_kimi(
    Path(video.path),
    question="What is happening on screen?",
    use_frames_fallback=True,  # Required for now
)
print(result.answer)
```

---

## E4.4: Action Verification with Video ✅

**Implementation:** `verify_action_with_video()`

Records action and verifies expected outcome:

```python
from advanced_vision.tools.video import verify_action_with_video

verification = verify_action_with_video(
    action_description="I clicked the button",
    video_path=Path("recording.mp4"),
    expected_result="a menu should have opened",
)

if verification["success"]:
    print("Action verified!")
```

---

## E4.5: Integration Workflow ✅

**Implementation:** `record_and_analyze()`

One-shot: Record + Analyze:

```python
from advanced_vision.tools.video import record_and_analyze

result = record_and_analyze(
    duration=10,
    question="Describe what you see on screen",
)
```

---

## Requirements

### System Dependencies
```bash
sudo apt install ffmpeg
```

### Python Dependencies
Already in repo:
- Standard library only (no requests dependency)
- Uses urllib for HTTP (keeps dependencies minimal)

### API Configuration
Create `.env` file:
```bash
KIMI_API_KEY=your-key-here
KIMI_BASE_URL=https://api.moonshot.cn/v1  # Optional
KIMI_MODEL=kimi-k2-5  # Optional
```

**API Key Source:** From kimi.com/code (OpenClaw integration path)

---

## Test Results

```bash
# Run video tests
pytest tests/test_video_e4.py -v

# Run all video tests (including original)
pytest tests/test_video*.py -v
```

**Expected:**
- Tests requiring ffmpeg: Skip if not installed
- Tests requiring Kimi API: Skip if KIMI_API_KEY not set
- Core tests (env loading, error handling): Always run

---

## Architecture Decisions

### Why Frames Instead of Direct Video Upload?

1. **API Limitations:** Kimi video API is experimental/not widely available
2. **Reliability:** Frame extraction works consistently
3. **Control:** We control frame selection and quality
4. **Debugging:** Easy to inspect intermediate frames

### Future Enhancement

When Kimi native video API stabilizes:
```python
analyze_video_with_kimi(video_path, use_frames_fallback=False)
```

Will use direct video upload instead of frame extraction.

---

## Integration with Trading Mode

Video recording enables:
- **Trading session recording:** Capture trading workflow
- **Pattern verification:** Record chart analysis, verify with AI
- **Audit trail:** Video evidence of actions taken
- **Training data:** Record expert workflows for model training

Example trading workflow:
```python
# Record trading decision process
video = record_screen_video(duration=30)

# Analyze what happened
analysis = analyze_video_with_kimi(
    video.path,
    question="Did I follow the trading plan? Any mistakes?"
)
```

---

## Next: Phase E5 - Integration Guidance

E4 is complete. Ready for:
- E5: Light integration notes
- Track B: Trading-watch intelligence
- Model integration (YOLO, SAM3, etc.)
