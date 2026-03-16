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
    stat = ImageStat.Stat(diff)
    mean = sum(stat.mean) / len(stat.mean)
    similarity = max(0.0, min(1.0, 1 - (mean / 255.0)))
    changed = similarity < threshold
    return VerificationResult(
        changed=changed,
        similarity=similarity,
        message=f"Similarity={similarity:.4f}, threshold={threshold}",
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
