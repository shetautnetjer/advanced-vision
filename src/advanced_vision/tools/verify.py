"""Screen change verification utilities.

This module provides tools to verify visual changes between screenshots,
useful for confirming that actions had their intended effect.

Verification Methods:
    1. Global similarity: Compares overall pixel differences between images.
       Returns a similarity score (0.0 to 1.0) where 1.0 means identical.
    
    2. Localized change detection: Detects even small concentrated changes
       that might be missed by global similarity (e.g., a small button click
       on a large static screen).

Backward Compatibility:
    The verify_screen_change function supports multiple calling conventions
    for backward compatibility:
    
    - verify_screen_change(previous_path)
      Takes a fresh screenshot and compares with previous
    
    - verify_screen_change(previous_path, 0.95)
      Sets threshold via second positional argument
    
    - verify_screen_change(previous_path, current_path)
      Compares two existing screenshots
    
    - verify_screen_change(previous_path, current_path, 0.95)
      Explicit paths with custom threshold

    - verify_screen_change(previous_path, current_path, threshold=0.95)
      Keyword argument style

Usage Examples:
    # Capture baseline, perform action, verify change
    before = screenshot_full()
    click(100, 100, dry_run=False)  # Perform some action
    result = verify_screen_change(before.path)
    if result.changed:
        print(f"Screen changed! Similarity: {result.similarity}")
    
    # Compare two existing screenshots
    result = verify_screen_change_between("before.png", "after.png")
    
    # With custom threshold (default is 0.99)
    result = verify_screen_change(before.path, threshold=0.95)

Threshold Guidance:
    - 0.99 (default): Very sensitive, detects most changes
    - 0.95: Less sensitive, allows for minor rendering differences
    - 0.90: Tolerant of anti-aliasing, compression artifacts
"""

from __future__ import annotations

from PIL import Image, ImageChops, ImageStat

from ..logging_utils import append_jsonl
from ..schemas import VerificationResult
from .screen import screenshot_full


def _compare_images(previous_path: str, current_path: str, threshold: float) -> VerificationResult:
    """Compare two images and return change detection result.
    
    Args:
        previous_path: Path to the previous/baseline screenshot
        current_path: Path to the current screenshot to compare
        threshold: Similarity threshold (0.0-1.0). Change detected if similarity < threshold.
    
    Returns:
        VerificationResult with changed flag, similarity score, and message
    """
    threshold = float(threshold)

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
            f"Similarity={similarity:.4f}, threshold={threshold:.4f}, "
            f"changed_ratio={changed_ratio:.6f}, changed_pixels={changed_pixels}"
        ),
    )


def verify_screen_change(
    previous_screenshot_path: str,
    current_screenshot_path: str | float | None = None,
    threshold: float = 0.99,
) -> VerificationResult:
    """Compare a previous screenshot with either a provided current one or a fresh capture.

    This is the main verification function with backward-compatible signatures.
    It can either compare two existing screenshots or capture a new one for comparison.

    Args:
        previous_screenshot_path: Path to the baseline/previous screenshot
        current_screenshot_path: One of:
            - Path to current screenshot (str)
            - Threshold value (int/float) for backward compatibility
            - None to capture a fresh screenshot
        threshold: Similarity threshold (0.0-1.0). Default 0.99.
                   Change is detected if similarity < threshold.

    Returns:
        VerificationResult containing:
        - changed: True if screen changed significantly
        - similarity: Float 0.0-1.0 (1.0 = identical, None if error)
        - message: Human-readable description of results

    Backward-compatible forms:
        verify_screen_change(previous_path)
        verify_screen_change(previous_path, 0.95)
        verify_screen_change(previous_path, current_path)
        verify_screen_change(previous_path, current_path, 0.95)
        verify_screen_change(previous_path, threshold=0.95)
        verify_screen_change(previous_path, current_path, threshold=0.95)

    Example:
        # Basic usage - capture new screenshot and compare
        before = screenshot_full()
        # ... perform action ...
        result = verify_screen_change(before.path)
        print(f"Changed: {result.changed}, Similarity: {result.similarity}")

        # Compare two existing screenshots
        result = verify_screen_change("before.png", "after.png")

        # With custom threshold
        result = verify_screen_change(before.path, threshold=0.95)
    """
    explicit_current_path: str | None = None

    if isinstance(current_screenshot_path, (int, float)):
        threshold = float(current_screenshot_path)
    elif isinstance(current_screenshot_path, str):
        explicit_current_path = current_screenshot_path

    new_artifact_path: str | None = None
    try:
        if explicit_current_path is not None:
            new_artifact_path = explicit_current_path
        else:
            new_artifact_path = screenshot_full().path
        result = _compare_images(previous_screenshot_path, new_artifact_path, threshold)
    except Exception as exc:
        result = VerificationResult(changed=False, similarity=None, message=f"Verification failed: {exc}")

    append_jsonl(
        "verification",
        {
            "previous_screenshot_path": previous_screenshot_path,
            "new_screenshot_path": new_artifact_path,
            **result.model_dump(),
        },
    )
    return result


def verify_screen_change_between(
    previous_screenshot_path: str,
    current_screenshot_path: str,
    threshold: float = 0.99,
) -> VerificationResult:
    """Compare two explicit screenshots without taking a new one.

    This function is explicitly for comparing two existing screenshot files.
    Unlike verify_screen_change, it never captures a new screenshot.

    Args:
        previous_screenshot_path: Path to the baseline/previous screenshot
        current_screenshot_path: Path to the current screenshot to compare
        threshold: Similarity threshold (0.0-1.0). Default 0.99.

    Returns:
        VerificationResult containing:
        - changed: True if screen changed significantly
        - similarity: Float 0.0-1.0 (1.0 = identical, None if error)
        - message: Human-readable description of results

    Example:
        result = verify_screen_change_between("baseline.png", "current.png")
        if result.changed:
            print(f"Screen changed by {((1 - result.similarity) * 100):.1f}%")
    """
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
