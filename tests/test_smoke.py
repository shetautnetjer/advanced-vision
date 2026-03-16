from pathlib import Path

from advanced_vision.flow import run_single_cycle
from advanced_vision.tools.screen import screenshot_full
from advanced_vision.tools.verify import verify_screen_change, verify_screen_change_between
from advanced_vision.vision_adapter import analyze_screenshot


def test_smoke_capture_and_analyze() -> None:
    artifact = screenshot_full()
    assert Path(artifact.path).exists()
    proposal = analyze_screenshot(artifact.path, "Find the search box")
    assert proposal.action_type == "noop"


def test_smoke_flow() -> None:
    result = run_single_cycle(task="Do nothing", execute=False)
    assert "before" in result
    assert "verification" in result


def test_verification_executes() -> None:
    first = screenshot_full()
    verification = verify_screen_change(first.path)
    assert verification.similarity is None or 0 <= verification.similarity <= 1


def test_verification_between_executes() -> None:
    first = screenshot_full()
    second = screenshot_full()
    verification = verify_screen_change_between(first.path, second.path)
    assert verification.similarity is None or 0 <= verification.similarity <= 1
