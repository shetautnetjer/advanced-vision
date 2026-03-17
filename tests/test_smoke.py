from pathlib import Path

from PIL import Image, ImageDraw

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


def test_verification_accepts_explicit_current_path() -> None:
    first = screenshot_full()
    second = screenshot_full()
    verification = verify_screen_change(first.path, second.path)
    assert verification.similarity is None or 0 <= verification.similarity <= 1


def test_verification_detects_localized_change(tmp_path: Path) -> None:
    before = tmp_path / "before.png"
    after = tmp_path / "after.png"

    image_before = Image.new("RGB", (200, 120), color=(255, 255, 255))
    image_after = image_before.copy()
    draw = ImageDraw.Draw(image_after)
    draw.rectangle((10, 10, 22, 22), fill=(0, 0, 0))

    image_before.save(before)
    image_after.save(after)

    result = verify_screen_change_between(str(before), str(after), threshold=0.9999)
    assert result.changed is True
