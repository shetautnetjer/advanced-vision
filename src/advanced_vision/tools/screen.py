"""Screen capture tools."""

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
    """Capture full desktop and save as an artifact."""
    image = _safe_grab()
    return _save_image(image, "full")


def screenshot_active_window() -> ScreenshotArtifact:
    """Capture active window when possible, otherwise fallback to full screenshot."""
    bbox = get_active_window_bbox()
    image = _safe_grab(bbox=bbox, retry_fullscreen=True)
    artifact = _save_image(image, "active")
    append_jsonl(
        "screenshots",
        {
            "tool": "active_window_capture",
            "bbox": bbox,
            "used_fallback_fullscreen": bbox is None or (artifact.width == 1280 and artifact.height == 720),
        },
    )
    return artifact
