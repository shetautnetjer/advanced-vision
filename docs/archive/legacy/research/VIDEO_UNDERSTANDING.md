# Video Understanding Research for Advanced-Vision

**Research Date:** 2026-03-16  
**Agent:** Aya (Kimi K2.5)  
**Purpose:** Investigate native video/screen recording capabilities for enhanced computer-use

---

## Key Finding: Kimi K2.5 Supports Video! ✅

**From Moonshot AI Platform Docs:**
- Kimi K2.5 has **multimodal capabilities** including **video understanding**
- Can process video content natively (not just frame-by-frame)
- Supports **screen recordings**, **video files**, and **video streams**

**Research Sources:**
- Moonshot AI Platform: `platform.moonshot.cn/docs/guide/kimi-k2-5-quickstart`
- Kimi K2.5 Official: Video understanding is a core capability
- Model Context: K2.5 processes video as native modality (not converted to images)

---

## Current State vs. Potential

### What We Have Now (Screenshots)
- ✅ Static screenshots every N seconds
- ✅ Image comparison for verification
- ⚠️ No temporal understanding (motion, transitions, animations)
- ⚠️ Manual frame extraction needed for video analysis

### What Video Understanding Enables
- 🎬 **Screen recording analysis** — Understand UI animations, loading states
- 🎬 **Motion detection** — Detect when screen changes dynamically
- 🎬 **Video verification** — Record action + verify with video playback
- 🎬 **Temporal reasoning** — "What happened between these two timestamps?"
- 🎬 **Native video QA** — Ask questions about screen recordings

---

## Implementation Ideas

### 1. Screen Recording + Video QA

```python
# Record screen as video instead of static screenshots
record_screen_video(duration=30)  # 30 second MP4

# Ask Kimi about the video
ask_video("What happened when I clicked the submit button?")
# → "The button showed a loading spinner for 2 seconds, 
#    then the page transitioned to a success screen"
```

### 2. Video-Based Verification

```python
# Instead of image comparison, use video verification
execute_action(click(100, 200))

# Record 5 second video after action
video = record_video(duration=5)

# Verify with video understanding
verify = ask_video("Did the expected change happen?", video)
# → "Yes, a dropdown menu appeared with 4 options"
```

### 3. Motion-Based Screenshot Trigger

```python
# Record continuously, trigger screenshot when motion detected
# Use video understanding to detect "significant change"
while True:
    video_segment = record_video(duration=3)
    if detect_motion(video_segment, threshold=0.1):
        screenshot = capture_frame(video_segment, timestamp='peak_motion')
        analyze_screenshot(screenshot)
```

### 4. Video Episode Cards

Instead of text-only episode cards with screenshot pointers:
```json
{
  "episode_id": "ep_123",
  "video_manifest": [
    "artifacts/videos/screen_001.mp4",
    "artifacts/videos/screen_002.mp4"
  ],
  "video_summary": "[Kimi generates from video]"
}
```

---

## Technical Requirements

### For Native Kimi Video Support (Ideal)

**If OpenClaw/Moonshot API supports video:**
- Upload MP4 directly to Kimi API
- Kimi processes video natively
- Return video understanding results

**API would look like:**
```python
response = kimi.chat.completions.create(
    model="kimi-k2-5",
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "What happened in this screen recording?"},
            {"type": "video_url", "video_url": {"url": "file://artifacts/screen.mp4"}}
        ]
    }]
)
```

### For OpenClaw Integration (Current Path)

**Since OpenClaw may not support video yet:**
1. **Extract frames** from video at key intervals
2. **Send frames as images** to Kimi (current image pipeline)
3. **Future:** Extend OpenClaw to support video content type

**Workaround implementation:**
```python
def video_to_kimi(video_path: str) -> str:
    """Convert video to Kimi-compatible format"""
    # Extract key frames
    frames = extract_keyframes(video_path, n=5)
    
    # Send as image sequence with temporal context
    return format_as_image_sequence(frames)
```

---

## OpenClaw Considerations

### Current State
- OpenClaw supports: `image` content type in messages
- OpenClaw may NOT support: `video` content type yet
- Need to verify: Can mcporter/OpenClaw pass video to Kimi?

### Enhancement Path
1. **Short term:** Extract frames from video, send as images
2. **Medium term:** Extend OpenClaw message schema to support video
3. **Long term:** Native video streaming/understanding pipeline

---

## Recommendation

### Immediate Enhancement (This Repo)

Add **video recording capability** to advanced-vision:

```python
# New tool: record_screen_video
def record_screen_video(duration: int = 10, fps: int = 5) -> VideoArtifact:
    """Record screen as MP4 video"""
    # Use ffmpeg or similar
    # Save to artifacts/videos/
    # Return VideoArtifact with path and metadata

# New tool: extract_keyframes
def extract_keyframes(video_path: str, n: int = 5) -> list[ImageArtifact]:
    """Extract key frames for Kimi analysis"""
    # Use ffmpeg or OpenCV
    # Return list of screenshots at key moments

# New tool: video_verification
def verify_with_video(action: Action, expected: str) -> VerificationResult:
    """Execute action, record video, verify with Kimi"""
    # Record before/during/after
    # Ask Kimi about the video
    # Return verification result
```

### Benefits
1. **Better verification** — Video captures animations, loading states
2. **Temporal understanding** — What happened over time, not just snapshots
3. **Debugging** — Replay screen recordings for troubleshooting
4. **Episode cards** — Richer evidence with video manifests

---

## Research Links

- Moonshot Platform: https://platform.moonshot.cn/docs/guide/kimi-k2-5-quickstart
- Kimi K2.5 Capabilities: Multimodal (text, image, video)
- OpenClaw Video Support: To be verified with project maintainers

---

## Next Steps

1. **Verify:** Can OpenClaw/mcporter pass video content to Kimi?
2. **Implement:** Add `record_screen_video()` tool to advanced-vision
3. **Test:** Video-based verification vs. screenshot-based
4. **Document:** Performance comparison, use cases

---

*Researched by: Aya (Kimi K2.5)*  
*Date: 2026-03-16*  
*Purpose: Enhanced computer-use with video understanding*
