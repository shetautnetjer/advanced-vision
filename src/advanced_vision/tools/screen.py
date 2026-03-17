"""Screen capture tools.

This module provides screenshot capabilities with robust fallback behavior
for different platforms and GUI environments.

Fallback Behavior:
- screenshot_full: Always attempts to capture the full screen. Falls back to
  a blank placeholder image (1280x720 gray) if capture fails (e.g., headless).
  
- screenshot_active_window: Attempts to capture the currently active window.
  If the active window cannot be determined (common on Linux without proper
  window manager support), it automatically falls back to a full-screen capture.
  The fallback behavior is logged via the artifact metadata.

Platform Notes:
- Linux: Window enumeration may be limited depending on the display server
  (X11 vs Wayland) and window manager. pywinctl is preferred over pygetwindow.
- Headless environments: Screenshots will fall back to placeholder images.
  For testing, consider using Xvfb (virtual framebuffer).
"""

from __future__ import annotations

from PIL import Image, ImageGrab

from ..config import get_settings
from ..logging_utils import append_jsonl, utc_now_iso
from ..schemas import ScreenshotArtifact
from .windows import get_active_window_bbox


def _save_image(image: Image.Image, prefix: str) -> ScreenshotArtifact:
    settings = get_settings()
    ts = utc_now_iso().replace(":", "-")
    out_path = settings.screens_dir / f"{prefix}_{ts}.png"
    image.save(out_path)
    artifact = ScreenshotArtifact(
        path=str(out_path),
        width=image.width,
        height=image.height,
        timestamp=utc_now_iso(),
    )
    append_jsonl("screenshots", {"tool": prefix, **artifact.model_dump()})
    return artifact


def _safe_grab(bbox: tuple[int, int, int, int] | None = None, retry_fullscreen: bool = False) -> Image.Image:
    """Safely grab a screenshot with optional bbox and fallback.
    
    Args:
        bbox: Optional bounding box (left, top, right, bottom) to capture.
              If None, captures full screen.
        retry_fullscreen: If True and bbox capture fails, retry without bbox.
    
    Returns:
        PIL Image of the captured region, or a placeholder gray image if capture fails.
    """
    try:
        return ImageGrab.grab(bbox=bbox)
    except Exception:
        if retry_fullscreen and bbox is not None:
            try:
                return ImageGrab.grab()
            except Exception:
                pass
        # Best-effort fallback for headless environments.
        return Image.new("RGB", (1280, 720), color=(40, 40, 40))


def screenshot_full() -> ScreenshotArtifact:
    """Capture full desktop and save as an artifact.
    
    Returns:
        ScreenshotArtifact with path, dimensions, and timestamp.
        
    Note:
        On headless systems or when DISPLAY is not set, this will return
        a placeholder image (1280x720 gray) instead of failing.
    """
    image = _safe_grab()
    return _save_image(image, "full")


def screenshot_active_window() -> ScreenshotArtifact:
    """Capture active window when possible, otherwise fallback to full screenshot.
    
    This function attempts to capture only the currently active window.
    If the active window cannot be determined (common on Linux without full
    window manager support), it automatically falls back to a full-screen capture.
    
    Returns:
        ScreenshotArtifact with path, dimensions, and timestamp.
        The artifact metadata includes whether fallback was used.
        
    Fallback Detection:
        - If bbox is None (can't determine window), full-screen is used
        - If resulting image is 1280x720 (placeholder size), fallback occurred
        
    Platform Notes:
        - Windows/macOS: Usually works correctly with proper window detection
        - Linux/X11: Works with pywinctl if window manager supports it
        - Linux/Wayland: Limited support depending on compositor
        - Headless: Always falls back to full-screen or placeholder
    """
    bbox = get_active_window_bbox()
    image = _safe_grab(bbox=bbox, retry_fullscreen=True)
    artifact = _save_image(image, "active")
    
    # Determine if fallback occurred
    used_fallback_fullscreen = bbox is None
    used_fallback_placeholder = (artifact.width == 1280 and artifact.height == 720)
    
    append_jsonl(
        "screenshots",
        {
            "tool": "active_window_capture",
            "bbox": bbox,
            "used_fallback_fullscreen": used_fallback_fullscreen,
            "used_fallback_placeholder": used_fallback_placeholder,
            "fallback_reason": (
                "window_detection_failed" if used_fallback_fullscreen 
                else "placeholder_used" if used_fallback_placeholder
                else None
            ),
        },
    )
    return artifact
