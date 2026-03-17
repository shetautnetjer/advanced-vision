#!/usr/bin/env python3
"""
Video Recording and Kimi API Integration
Records screen as video and analyzes with Kimi K2.5 video understanding
"""

import os
import json
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Optional
import requests

from ..logging_utils import append_jsonl
from ..schemas import VideoArtifact, VideoAnalysisResult

# Load API key from environment
KIMI_API_KEY = os.environ.get("KIMI_API_KEY")
# API endpoint - moonshot.cn for most keys, kimi-code.com for IDE keys
KIMI_BASE_URL = os.environ.get("KIMI_BASE_URL", "https://api.moonshot.cn/v1")
# Model to use - text models: moonshot-v1-*, vision models: kimi-vl, k2.5-latest (if available)
KIMI_MODEL = os.environ.get("KIMI_MODEL", "moonshot-v1-8k")  # Default to text-only

SCREENSHOT_DIR = Path.home() / ".openclaw/workspace/plane-a/projects/advanced-vision/artifacts/screens"
VIDEO_DIR = Path.home() / ".openclaw/workspace/plane-a/projects/advanced-vision/artifacts/videos"


def ensure_directories():
    """Ensure artifact directories exist"""
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)


def record_screen_video(
    duration: int = 10,
    fps: int = 5,
    output_path: Optional[Path] = None
) -> VideoArtifact:
    """
    Record screen as MP4 video using ffmpeg
    
    Args:
        duration: Recording duration in seconds
        fps: Frames per second
        output_path: Optional custom output path
    
    Returns:
        VideoArtifact with path and metadata
    """
    ensure_directories()
    
    if output_path is None:
        timestamp = datetime.utcnow().isoformat().replace(":", "-")
        output_path = VIDEO_DIR / f"screen_{timestamp}.mp4"
    else:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Display from environment (default :1 for X11)
    display = os.environ.get("DISPLAY", ":1")
    
    # ffmpeg command to record screen
    cmd = [
        "ffmpeg",
        "-f", "x11grab",           # X11 screen capture
        "-video_size", "1920x1080", # Screen resolution
        "-i", display,              # Display to capture
        "-framerate", str(fps),     # FPS
        "-t", str(duration),        # Duration
        "-pix_fmt", "yuv420p",      # Pixel format for compatibility
        "-y",                       # Overwrite if exists
        str(output_path)
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=duration + 10
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed: {result.stderr}")
        
        # Get video info
        file_size = output_path.stat().st_size
        
        artifact = VideoArtifact(
            path=str(output_path),
            duration=duration,
            fps=fps,
            width=1920,
            height=1080,
            file_size=file_size,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
        
        # Log action
        append_jsonl("video_recordings", artifact.model_dump())
        
        return artifact
        
    except subprocess.TimeoutExpired:
        raise RuntimeError("ffmpeg timed out")
    except FileNotFoundError:
        raise RuntimeError("ffmpeg not found. Install with: sudo apt install ffmpeg")


def extract_keyframes(
    video_path: Path,
    n: int = 5
) -> list[Path]:
    """
    Extract n keyframes from video for image-based analysis
    
    Args:
        video_path: Path to video file
        n: Number of keyframes to extract
    
    Returns:
        List of paths to extracted frame images
    """
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")
    
    frames_dir = SCREENSHOT_DIR / f"frames_{video_path.stem}"
    frames_dir.mkdir(exist_ok=True)
    
    # Extract frames at regular intervals
    cmd = [
        "ffmpeg",
        "-i", str(video_path),
        "-vf", f"select='not(mod(n,{int(30/n)}))',scale=1920:1080",
        "-vframes", str(n),
        "-y",
        str(frames_dir / "frame_%03d.png")
    ]
    
    subprocess.run(cmd, capture_output=True, check=True)
    
    # Return list of extracted frames
    return sorted(frames_dir.glob("frame_*.png"))


def analyze_video_with_kimi(
    video_path: Path,
    question: str = "What is happening in this screen recording?",
    use_frames_fallback: bool = True
) -> VideoAnalysisResult:
    """
    Analyze video using Kimi K2.5 API
    
    Args:
        video_path: Path to video file
        question: Question to ask about the video
        use_frames_fallback: If video API fails, extract frames and use image API
    
    Returns:
        VideoAnalysisResult with answer and metadata
    """
    if not KIMI_API_KEY:
        raise RuntimeError("KIMI_API_KEY not set. Check .env file.")
    
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")
    
    # Try video API first (if Moonshot supports direct video)
    # For now, use frame-based approach as fallback
    if use_frames_fallback:
        return _analyze_with_frames(video_path, question)
    else:
        return _analyze_with_video_api(video_path, question)


def _analyze_with_frames(
    video_path: Path,
    question: str
) -> VideoAnalysisResult:
    """
    Analyze video by extracting keyframes and sending to Kimi as images
    """
    # Extract keyframes
    frames = extract_keyframes(video_path, n=5)
    
    if not frames:
        raise RuntimeError("Could not extract frames from video")
    
    # Build message with frames
    content = [{"type": "text", "text": f"Analyze this screen recording. {question}"}]
    
    for frame in frames:
        # Read image and convert to base64
        import base64
        with open(frame, "rb") as f:
            image_data = base64.b64encode(f.read()).decode()
        
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{image_data}"
            }
        })
    
    # Call Kimi API
    headers = {
        "Authorization": f"Bearer {KIMI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": KIMI_MODEL,
        "messages": [{
            "role": "user",
            "content": content
        }],
        "temperature": 0.2
    }
    
    response = requests.post(
        f"{KIMI_BASE_URL}/chat/completions",
        headers=headers,
        json=payload,
        timeout=60
    )
    
    response.raise_for_status()
    result = response.json()
    
    answer = result["choices"][0]["message"]["content"]
    
    # Log analysis
    analysis_result = VideoAnalysisResult(
        video_path=str(video_path),
        question=question,
        answer=answer,
        model=KIMI_MODEL,
        frames_used=len(frames),
        timestamp=datetime.utcnow().isoformat() + "Z"
    )
    
    append_jsonl("video_analyses", analysis_result.model_dump())
    
    return analysis_result


def _analyze_with_video_api(
    video_path: Path,
    question: str
) -> VideoAnalysisResult:
    """
    Analyze video using direct video API (if supported)
    NOTE: This is a placeholder for when Moonshot adds native video API
    """
    # TODO: Implement when Kimi API supports direct video upload
    raise NotImplementedError(
        "Direct video API not yet implemented. "
        "Use use_frames_fallback=True for now."
    )


def verify_action_with_video(
    action_description: str,
    video_path: Path,
    expected_result: str
) -> dict:
    """
    Verify an action by analyzing the video recording
    
    Args:
        action_description: What action was performed
        video_path: Path to recording of the action
        expected_result: What should have happened
    
    Returns:
        dict with verification result and confidence
    """
    question = (
        f"I performed this action: {action_description}. "
        f"I expected: {expected_result}. "
        f"Did the expected result happen? Explain what you see."
    )
    
    analysis = analyze_video_with_kimi(video_path, question)
    
    # Parse result for yes/no
    answer_lower = analysis.answer.lower()
    success = "yes" in answer_lower or "success" in answer_lower or "happened" in answer_lower
    
    return {
        "success": success,
        "explanation": analysis.answer,
        "confidence": "high" if success else "uncertain",
        "video_path": str(video_path),
        "timestamp": analysis.timestamp
    }


# Convenience function for quick recording + analysis
def record_and_analyze(
    duration: int = 10,
    question: str = "What is happening on screen?"
) -> VideoAnalysisResult:
    """
    Record screen for N seconds and immediately analyze with Kimi
    
    Args:
        duration: How long to record
        question: What to ask about the recording
    
    Returns:
        VideoAnalysisResult with answer
    """
    video = record_screen_video(duration=duration)
    return analyze_video_with_kimi(Path(video.path), question)