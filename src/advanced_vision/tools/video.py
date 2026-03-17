#!/usr/bin/env python3
"""Video recording and Kimi analysis helpers.

Phase-1/2 implementation note:
- Direct video upload is not implemented yet.
- The current real path is: record video -> extract keyframes -> send frames as images.
- This module intentionally avoids third-party HTTP dependencies so it can run in the
  existing repo environments without requiring `requests`.
"""

from __future__ import annotations

import base64
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ..config import get_settings
from ..logging_utils import append_jsonl
from ..schemas import VideoArtifact, VideoAnalysisResult

REPO_ROOT = Path(__file__).resolve().parents[3]
ENV_FILE = REPO_ROOT / ".env"
DEFAULT_BASE_URL = "https://api.moonshot.cn/v1"
DEFAULT_MODEL = "kimi-k2-5"


def _load_env_file(env_file: Path = ENV_FILE) -> None:
    """Load simple KEY=VALUE pairs into os.environ if not already present."""
    if not env_file.exists():
        return

    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _get_kimi_config() -> tuple[str | None, str, str]:
    _load_env_file()
    api_key = os.environ.get("KIMI_API_KEY")
    base_url = os.environ.get("KIMI_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    model = os.environ.get("KIMI_MODEL", DEFAULT_MODEL)
    return api_key, base_url, model


def _artifacts_dirs() -> tuple[Path, Path]:
    settings = get_settings()
    screenshot_dir = settings.screens_dir
    video_dir = settings.artifacts_dir / "videos"
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    video_dir.mkdir(parents=True, exist_ok=True)
    return screenshot_dir, video_dir


def _post_json(url: str, headers: dict[str, str], payload: dict, timeout: int = 60) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = Request(url, data=data, headers=headers, method="POST")
    try:
        with urlopen(req, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            return json.loads(body)
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Kimi API HTTP {exc.code}: {body[:1000]}") from exc
    except URLError as exc:
        raise RuntimeError(f"Kimi API connection failed: {exc}") from exc


def _probe_video_duration(video_path: Path) -> float | None:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(video_path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        value = result.stdout.strip()
        return float(value) if value else None
    except Exception:
        return None


def record_screen_video(
    duration: int = 10,
    fps: int = 5,
    output_path: Optional[Path] = None,
) -> VideoArtifact:
    """Record screen as MP4 video using ffmpeg."""
    _, video_dir = _artifacts_dirs()

    if output_path is None:
        timestamp = datetime.utcnow().isoformat().replace(":", "-")
        output_path = video_dir / f"screen_{timestamp}.mp4"
    else:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

    display = os.environ.get("DISPLAY", ":1")
    cmd = [
        "ffmpeg",
        "-f",
        "x11grab",
        "-video_size",
        "1920x1080",
        "-framerate",
        str(fps),
        "-i",
        display,
        "-t",
        str(duration),
        "-pix_fmt",
        "yuv420p",
        "-y",
        str(output_path),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=duration + 10)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed: {result.stderr}")

        artifact = VideoArtifact(
            path=str(output_path),
            duration=duration,
            fps=fps,
            width=1920,
            height=1080,
            file_size=output_path.stat().st_size,
            timestamp=datetime.utcnow().isoformat() + "Z",
        )
        append_jsonl("video_recordings", artifact.model_dump())
        return artifact
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("ffmpeg timed out") from exc
    except FileNotFoundError as exc:
        raise RuntimeError("ffmpeg not found. Install with: sudo apt install ffmpeg") from exc


def extract_keyframes(video_path: Path, n: int = 5) -> list[Path]:
    """Extract approximately evenly spaced keyframes from a video."""
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    screenshot_dir, _ = _artifacts_dirs()
    frames_dir = screenshot_dir / f"frames_{video_path.stem}"
    frames_dir.mkdir(exist_ok=True)

    duration = _probe_video_duration(video_path) or max(float(n), 1.0)
    fps_filter = max(n / duration, 0.2)

    cmd = [
        "ffmpeg",
        "-i",
        str(video_path),
        "-vf",
        f"fps={fps_filter},scale=1920:1080",
        "-frames:v",
        str(n),
        "-y",
        str(frames_dir / "frame_%03d.png"),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg frame extraction failed: {result.stderr}")

    return sorted(frames_dir.glob("frame_*.png"))


def analyze_video_with_kimi(
    video_path: Path,
    question: str = "What is happening in this screen recording?",
    use_frames_fallback: bool = True,
) -> VideoAnalysisResult:
    """Analyze a video using Kimi.

    Current implemented path: extract frames and send them as images.
    """
    api_key, _, _ = _get_kimi_config()
    if not api_key:
        raise RuntimeError("KIMI_API_KEY not set. Check .env file.")

    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    if use_frames_fallback:
        return _analyze_with_frames(video_path, question)
    return _analyze_with_video_api(video_path, question)


def _analyze_with_frames(video_path: Path, question: str) -> VideoAnalysisResult:
    frames = extract_keyframes(video_path, n=5)
    if not frames:
        raise RuntimeError("Could not extract frames from video")

    api_key, base_url, model = _get_kimi_config()
    if not api_key:
        raise RuntimeError("KIMI_API_KEY not set. Check .env file.")

    content = [{"type": "text", "text": f"Analyze this screen recording. {question}"}]
    for frame in frames:
        with open(frame, "rb") as f:
            image_data = base64.b64encode(f.read()).decode()
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{image_data}"},
            }
        )

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "temperature": 0.2,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    result = _post_json(f"{base_url}/chat/completions", headers=headers, payload=payload, timeout=60)
    answer = result["choices"][0]["message"]["content"]

    analysis_result = VideoAnalysisResult(
        video_path=str(video_path),
        question=question,
        answer=answer,
        model=model,
        frames_used=len(frames),
        timestamp=datetime.utcnow().isoformat() + "Z",
    )
    append_jsonl("video_analyses", analysis_result.model_dump())
    return analysis_result


def _analyze_with_video_api(video_path: Path, question: str) -> VideoAnalysisResult:
    """Placeholder for future native video upload path."""
    raise NotImplementedError(
        "Direct video API not yet implemented. Use use_frames_fallback=True for now."
    )


def verify_action_with_video(action_description: str, video_path: Path, expected_result: str) -> dict:
    """Verify an action by analyzing a recording of the action."""
    question = (
        f"I performed this action: {action_description}. "
        f"I expected: {expected_result}. "
        "Did the expected result happen? Explain what you see."
    )
    analysis = analyze_video_with_kimi(video_path, question)
    answer_lower = analysis.answer.lower()
    success = any(token in answer_lower for token in ["yes", "success", "happened"])
    return {
        "success": success,
        "explanation": analysis.answer,
        "confidence": "high" if success else "uncertain",
        "video_path": str(video_path),
        "timestamp": analysis.timestamp,
    }


def record_and_analyze(duration: int = 10, question: str = "What is happening on screen?") -> VideoAnalysisResult:
    """Record screen for N seconds and immediately analyze with Kimi."""
    video = record_screen_video(duration=duration)
    return analyze_video_with_kimi(Path(video.path), question)
