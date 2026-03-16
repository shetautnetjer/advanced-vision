"""Verification utilities."""

from __future__ import annotations

from PIL import Image, ImageChops, ImageStat

from ..logging_utils import append_jsonl
from ..schemas import VerificationResult
from .screen import screenshot_full


def _compare_images(previous_path: str, current_path: str, threshold: float) -> VerificationResult:
    prev = Image.open(previous_path).convert("RGB")
    curr = Image.open(current_path).convert("RGB")
    if prev.size != curr.size:
        curr = curr.resize(prev.size)

    diff = ImageChops.difference(prev, curr)

    # Global similarity keeps backward-compatible behavior.
    stat = ImageStat.Stat(diff)
    mean = sum(stat.mean) / len(stat.mean)
    similarity = max(0.0, min(1.0, 1 - (mean / 255.0)))

    # Localized-change metric: threshold per-pixel luminance diff and count changed pixels.
    binary_diff = diff.convert("L").point(lambda p: 255 if p >= 16 else 0)
    changed_pixels = binary_diff.histogram()[255]
    total_pixels = prev.size[0] * prev.size[1]
    changed_ratio = changed_pixels / total_pixels if total_pixels else 0.0

    # Keep public API unchanged: use original threshold + small localized-change trigger.
    changed = similarity < threshold or changed_ratio >= 0.0005
    return VerificationResult(
        changed=changed,
        similarity=similarity,
        message=(
            f"Similarity={similarity:.4f}, threshold={threshold}, "
            f"changed_ratio={changed_ratio:.6f}, changed_pixels={changed_pixels}"
        ),
    )


def verify_screen_change(previous_screenshot_path: str, threshold: float = 0.99) -> VerificationResult:
    """Capture a fresh screenshot and compare similarity with a previous one."""
    new_artifact = screenshot_full()
    try:
        result = _compare_images(previous_screenshot_path, new_artifact.path, threshold)
    except Exception as exc:
        result = VerificationResult(changed=False, similarity=None, message=f"Verification failed: {exc}")

    append_jsonl(
        "verification",
        {
            "previous_screenshot_path": previous_screenshot_path,
            "new_screenshot_path": new_artifact.path,
            **result.model_dump(),
        },
    )
    return result


def verify_screen_change_between(
    previous_screenshot_path: str,
    current_screenshot_path: str,
    threshold: float = 0.99,
) -> VerificationResult:
    """Compare two explicit screenshots without taking a new one."""
    try:
        result = _compare_images(previous_screenshot_path, current_screenshot_path, threshold)
    except Exception as exc:
        result = VerificationResult(changed=False, similarity=None, message=f"Verification failed: {exc}")

    append_jsonl(
        "verification",
        {
            "previous_screenshot_path": previous_screenshot_path,
            "new_screenshot_path": current_screenshot_path,
            **result.model_dump(),
        },
    )
    return result
