"""Video recording and analysis tests - Phase E4: Recording/Video Experiment.

These tests verify:
- Screen recording to MP4
- Keyframe extraction from videos
- Video analysis via Kimi (frames-based fallback)
- Action verification with video evidence

Requirements:
- ffmpeg must be installed (sudo apt install ffmpeg)
- For live tests: KIMI_API_KEY in .env file

Video Support Notes:
- Direct video upload to Kimi is not implemented (API limitations)
- Current path: video → keyframes → analyze frames as images
- This works reliably and avoids large upload issues
"""

import os
from pathlib import Path

import pytest

from advanced_vision.tools.video import (
    _artifacts_dirs,
    _get_kimi_config,
    _load_env_file,
    _probe_video_duration,
    extract_keyframes,
    record_screen_video,
)


# Skip tests requiring ffmpeg if not installed
FFMPEG_AVAILABLE = False
try:
    import subprocess
    subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
    FFMPEG_AVAILABLE = True
except (subprocess.CalledProcessError, FileNotFoundError):
    pass

# Skip tests requiring Kimi API key
KIMI_AVAILABLE = bool(_get_kimi_config()[0])


# =============================================================================
# Phase E4: Video Recording Tests
# =============================================================================


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg not installed")
def test_record_screen_video_creates_mp4():
    """E4.1: Record a short screen video and verify MP4 is created."""
    artifact = record_screen_video(duration=2, fps=5)
    
    assert Path(artifact.path).exists()
    assert artifact.duration == 2
    assert artifact.fps == 5
    assert artifact.width == 1920
    assert artifact.height == 1080
    assert artifact.file_size > 0


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg not installed")
def test_record_screen_video_custom_path(tmp_path: Path):
    """E4.2: Record video to custom path."""
    custom_path = tmp_path / "custom_recording.mp4"
    artifact = record_screen_video(duration=1, fps=5, output_path=custom_path)
    
    assert artifact.path == str(custom_path)
    assert custom_path.exists()


# =============================================================================
# Phase E4: Keyframe Extraction Tests
# =============================================================================


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg not installed")
def test_extract_keyframes_from_recorded_video():
    """E4.3: Extract keyframes from a recorded video."""
    # First record a short video
    video = record_screen_video(duration=3, fps=5)
    
    # Extract 5 keyframes
    frames = extract_keyframes(Path(video.path), n=5)
    
    assert len(frames) == 5
    for frame in frames:
        assert frame.exists()
        assert frame.suffix == ".png"


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg not installed")
def test_extract_keyframes_creates_directory():
    """E4.4: Keyframe extraction creates frames directory."""
    video = record_screen_video(duration=2, fps=5)
    frames = extract_keyframes(Path(video.path), n=3)
    
    # Directory should be created
    frames_dir = frames[0].parent
    assert frames_dir.exists()
    assert frames_dir.name.startswith("frames_")


# =============================================================================
# Phase E4: Video Analysis Tests
# =============================================================================


@pytest.mark.skipif(not KIMI_AVAILABLE, reason="KIMI_API_KEY not configured")
@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg not installed")
def test_analyze_video_with_kimi_frames():
    """E4.5: Analyze a recorded video using Kimi (frames fallback).
    
    This test:
    1. Records a 5-second video
    2. Extracts keyframes
    3. Sends to Kimi for analysis
    4. Verifies we get a meaningful response
    
    Note: Requires KIMI_API_KEY in .env
    """
    from advanced_vision.tools.video import analyze_video_with_kimi
    
    # Record a video
    video = record_screen_video(duration=5, fps=5)
    
    # Analyze it
    result = analyze_video_with_kimi(
        Path(video.path),
        question="What do you see on the screen?",
        use_frames_fallback=True,
    )
    
    assert result.video_path == video.path
    assert len(result.answer) > 10  # Got some analysis
    assert result.model is not None
    assert result.frames_used == 5


@pytest.mark.skipif(not KIMI_AVAILABLE, reason="KIMI_API_KEY not configured")
@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg not installed")
def test_verify_action_with_video():
    """E4.6: Verify an action using video recording.
    
    Records a video and asks Kimi if an expected outcome occurred.
    """
    from advanced_vision.tools.video import verify_action_with_video, record_screen_video
    
    # Record a video (simulating some action)
    video = record_screen_video(duration=3, fps=5)
    
    # Verify what happened
    verification = verify_action_with_video(
        action_description="I moved the mouse around",
        video_path=Path(video.path),
        expected_result="the mouse cursor should have moved",
    )
    
    assert "explanation" in verification
    assert "success" in verification
    assert "video_path" in verification


# =============================================================================
# Phase E4: Video Metadata Tests
# =============================================================================


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg not installed")
def test_probe_video_duration():
    """E4.7: Probe video duration from recorded file."""
    video = record_screen_video(duration=3, fps=5)
    duration = _probe_video_duration(Path(video.path))
    
    assert duration is not None
    assert 2.5 <= duration <= 3.5  # Allow small variance


def test_artifacts_dirs_creates_directories(tmp_path: Path, monkeypatch):
    """E4.8: Verify artifact directories are created."""
    from advanced_vision.config import Settings
    
    # Mock settings to use temp path
    class MockSettings:
        screens_dir = tmp_path / "screens"
        artifacts_dir = tmp_path / "artifacts"
    
    # Test would need config injection - skipping for now
    screenshot_dir, video_dir = _artifacts_dirs()
    
    assert screenshot_dir.exists()
    assert video_dir.exists()


# =============================================================================
# Phase E4: Configuration Tests
# =============================================================================


def test_get_kimi_config_from_env(monkeypatch):
    """E4.9: Read Kimi config from environment."""
    monkeypatch.setenv("KIMI_API_KEY", "test-key-123")
    monkeypatch.setenv("KIMI_BASE_URL", "https://test.example.com")
    monkeypatch.setenv("KIMI_MODEL", "test-model")
    
    api_key, base_url, model = _get_kimi_config()
    
    assert api_key == "test-key-123"
    assert base_url == "https://test.example.com"
    assert model == "test-model"


def test_get_kimi_config_defaults(monkeypatch):
    """E4.10: Kimi config uses defaults when env not set."""
    monkeypatch.delenv("KIMI_API_KEY", raising=False)
    monkeypatch.delenv("KIMI_BASE_URL", raising=False)
    monkeypatch.delenv("KIMI_MODEL", raising=False)
    
    api_key, base_url, model = _get_kimi_config()
    
    assert api_key is None
    assert base_url == "https://api.moonshot.cn/v1"
    assert model == "kimi-k2-5"


# =============================================================================
# Phase E4: Error Handling Tests
# =============================================================================


def test_extract_keyframes_missing_file():
    """E4.11: Extract keyframes raises FileNotFoundError for missing video."""
    with pytest.raises(FileNotFoundError):
        extract_keyframes(Path("/nonexistent/video.mp4"))


def test_record_screen_video_without_ffmpeg():
    """E4.12: Recording without ffmpeg raises appropriate error."""
    # This test only runs if ffmpeg is NOT available
    if FFMPEG_AVAILABLE:
        pytest.skip("ffmpeg is available")
    
    with pytest.raises(RuntimeError) as exc_info:
        record_screen_video(duration=1, fps=5)
    
    assert "ffmpeg" in str(exc_info.value).lower()


# =============================================================================
# Integration: Record and Analyze Workflow
# =============================================================================


@pytest.mark.skipif(not KIMI_AVAILABLE, reason="KIMI_API_KEY not configured")
@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg not installed")
def test_record_and_analyze_workflow():
    """E4.13: Full workflow: Record → Extract → Analyze.
    
    This is the primary E4 integration test demonstrating the complete flow.
    """
    from advanced_vision.tools.video import record_and_analyze
    
    result = record_and_analyze(
        duration=5,
        question="Describe what is visible on the screen in this recording.",
    )
    
    assert result.video_path is not None
    assert Path(result.video_path).exists()
    assert len(result.answer) > 20  # Substantial analysis
    assert result.frames_used >= 3
