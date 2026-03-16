"""Screen capture tools."""

from __future__ import annotations

from PIL import Image, ImageGrab

from ..config import get_settings
from ..logging_utils import append_jsonl, utc_now_iso
from ..schemas import ScreenshotArtifact


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


def _safe_grab(bbox: tuple[int, int, int, int] | None = None) -> Image.Image:
    try:
        return ImageGrab.grab(bbox=bbox)
    except Exception:
        # Best-effort fallback for headless environments.
        return Image.new("RGB", (1280, 720), color=(40, 40, 40))


def screenshot_full() -> ScreenshotArtifact:
    """Capture full desktop and save as an artifact."""
    image = _safe_grab()
    return _save_image(image, "full")


def _active_window_bbox() -> tuple[int, int, int, int] | None:
    """Return active window bbox when available via pygetwindow."""
    try:
        import pygetwindow as gw  # type: ignore

        active = gw.getActiveWindow()
        if active is None:
            return None
        left, top = int(active.left), int(active.top)
        width, height = int(active.width), int(active.height)
        if width <= 0 or height <= 0:
            return None
        return (left, top, left + width, top + height)
    except Exception:
        return None


def screenshot_active_window() -> ScreenshotArtifact:
    """Capture active window when possible, otherwise fallback to full screenshot."""
    bbox = _active_window_bbox()
    image = _safe_grab(bbox=bbox)
    return _save_image(image, "active")
