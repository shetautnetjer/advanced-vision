"""Vision adapter abstraction for screenshot interpretation.

The default adapter is intentionally a stub. It returns a conservative proposal and is
structured so a real model-backed implementation (for example Kimi) can be added later.
"""

from __future__ import annotations

from .schemas import ActionProposal


class VisionAdapter:
    """Simple interface for screenshot analysis."""

    def analyze_screenshot(self, image_path: str, task: str) -> ActionProposal:
        raise NotImplementedError


class StubVisionAdapter(VisionAdapter):
    """Default no-op adapter with deterministic behavior."""

    def analyze_screenshot(self, image_path: str, task: str) -> ActionProposal:
        return ActionProposal(
            action_type="noop",
            confidence=0.1,
            rationale=(
                "Stub adapter: integrate a real vision model later. "
                f"Received task='{task}' for image_path='{image_path}'."
            ),
        )


def analyze_screenshot(image_path: str, task: str) -> ActionProposal:
    """Convenience function using the default stub adapter."""
    return StubVisionAdapter().analyze_screenshot(image_path=image_path, task=task)
