"""Smoke tests for advanced-vision read path and safe action path.

These tests verify basic functionality without requiring complex setup:
- Screenshot capture (full and active window)
- Screen change verification (both signatures)
- Input actions (with dry_run for safety)
- Diagnostics

Running Tests Safely:
    All action tests use dry_run=True by default, so they won't actually
    move the mouse, click, or type. To run live tests, set the
    ADVANCED_VISION_LIVE_TESTS environment variable.

Example:
    # Safe dry-run tests (default)
    pytest tests/test_smoke.py -v
    
    # Live tests (actually moves mouse/clicks)
    ADVANCED_VISION_LIVE_TESTS=1 pytest tests/test_smoke.py -v
"""

import os
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from advanced_vision.diagnostics import collect_diagnostics
from advanced_vision.flow import run_single_cycle
from advanced_vision.tools.input import click, move_mouse, press_keys, scroll, type_text
from advanced_vision.tools.screen import screenshot_active_window, screenshot_full
from advanced_vision.tools.verify import verify_screen_change, verify_screen_change_between
from advanced_vision.vision_adapter import analyze_screenshot


# =============================================================================
# Phase E1: Read Path Hardening Tests
# =============================================================================


def test_smoke_capture_and_analyze() -> None:
    """Test full screenshot capture and basic analysis."""
    artifact = screenshot_full()
    assert Path(artifact.path).exists()
    proposal = analyze_screenshot(artifact.path, "Find the search box")
    assert proposal.action_type == "noop"


def test_smoke_flow() -> None:
    """Test the basic flow cycle without execution."""
    result = run_single_cycle(task="Do nothing", execute=False)
    assert "before" in result
    assert "verification" in result


def test_screenshot_full_creates_artifact() -> None:
    """E1.1: Confirm screenshot_full works reliably.
    
    Verifies that screenshot_full:
    - Returns a valid ScreenshotArtifact
    - Saves an actual file to disk
    - File has valid dimensions (>0 width and height)
    """
    artifact = screenshot_full()
    
    # Check artifact fields
    assert artifact.path is not None
    assert artifact.width > 0
    assert artifact.height > 0
    assert artifact.timestamp is not None
    
    # Check file exists
    path = Path(artifact.path)
    assert path.exists(), f"Screenshot file not found: {artifact.path}"
    assert path.stat().st_size > 0, "Screenshot file is empty"


def test_screenshot_active_window_with_fallback() -> None:
    """E1.2: Confirm screenshot_active_window works and documents fallback.
    
    Verifies that screenshot_active_window:
    - Returns a valid ScreenshotArtifact
    - Documents whether fallback occurred in the artifact
    - Falls back to full-screen or placeholder when window detection fails
    """
    artifact = screenshot_active_window()
    
    # Check artifact fields
    assert artifact.path is not None
    assert artifact.width > 0
    assert artifact.height > 0
    
    # Check file exists
    path = Path(artifact.path)
    assert path.exists(), f"Screenshot file not found: {artifact.path}"
    
    # On Linux/headless, may fall back to placeholder (1280x720)
    # On GUI systems, should capture actual window or full screen
    assert artifact.width in [1280, 1920, 2560, 1440, 3840, 800, 1024, 1366, 1600] or artifact.width > 0
    assert artifact.height in [720, 1080, 1440, 900, 768, 600, 1200] or artifact.height > 0


def test_verification_executes() -> None:
    """E1.3: Verify screen change detection with fresh capture.
    
    Tests the signature: verify_screen_change(previous_path)
    """
    first = screenshot_full()
    verification = verify_screen_change(first.path)
    assert verification.similarity is None or 0 <= verification.similarity <= 1


def test_verification_between_executes() -> None:
    """E1.3: Verify screen change detection between two screenshots.
    
    Tests the signature: verify_screen_change_between(prev_path, curr_path)
    """
    first = screenshot_full()
    second = screenshot_full()
    verification = verify_screen_change_between(first.path, second.path)
    assert verification.similarity is None or 0 <= verification.similarity <= 1


def test_verification_accepts_explicit_current_path() -> None:
    """E1.3: Verify screen change with explicit current path.
    
    Tests the signature: verify_screen_change(prev_path, curr_path)
    """
    first = screenshot_full()
    second = screenshot_full()
    verification = verify_screen_change(first.path, second.path)
    assert verification.similarity is None or 0 <= verification.similarity <= 1


def test_verification_accepts_threshold_as_second_arg() -> None:
    """E1.3: Verify backward-compatible threshold signature.
    
    Tests the legacy signature: verify_screen_change(prev_path, 0.95)
    """
    first = screenshot_full()
    # Pass threshold as second argument (backward compatibility)
    verification = verify_screen_change(first.path, 0.95)
    assert verification.similarity is None or 0 <= verification.similarity <= 1


def test_verification_detects_localized_change(tmp_path: Path) -> None:
    """E1.3: Verify localized changes are detected even with high similarity.
    
    Creates two images with a small difference and verifies the change
    is detected even when overall similarity is very high.
    """
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


# =============================================================================
# Phase E2: Safe Action Path Tests
# =============================================================================


def test_move_mouse_dry_run() -> None:
    """E2.1/2.2: Test move_mouse with dry_run returns structured result.
    
    Verifies:
    - dry_run=True prevents actual mouse movement
    - Returns structured ActionResult
    - Result includes dry_run indication in message
    """
    result = move_mouse(100, 200, dry_run=True)
    
    assert result.ok is True
    assert result.action_type == "move_mouse"
    assert "[DRY RUN]" in result.message
    assert "(100, 200)" in result.message


def test_click_dry_run() -> None:
    """E2.1/2.2: Test click with dry_run returns structured result."""
    result = click(300, 400, button="left", dry_run=True)
    
    assert result.ok is True
    assert result.action_type == "click"
    assert "[DRY RUN]" in result.message
    assert "(300, 400)" in result.message
    assert "left" in result.message


def test_type_text_dry_run() -> None:
    """E2.1/2.2: Test type_text with dry_run returns structured result."""
    result = type_text("Hello World", dry_run=True)
    
    assert result.ok is True
    assert result.action_type == "type_text"
    assert "[DRY RUN]" in result.message
    assert "11" in result.message  # Character count


def test_press_keys_dry_run() -> None:
    """E2.1/2.2: Test press_keys with dry_run returns structured result."""
    result = press_keys(["ctrl", "c"], dry_run=True)
    
    assert result.ok is True
    assert result.action_type == "press_keys"
    assert "[DRY RUN]" in result.message
    assert "ctrl+c" in result.message.lower().replace(" ", "")


def test_scroll_dry_run() -> None:
    """E2.1/2.2: Test scroll with dry_run returns structured result."""
    result = scroll(vertical=-3, horizontal=0, dry_run=True)
    
    assert result.ok is True
    assert result.action_type == "scroll"
    assert "[DRY RUN]" in result.message
    assert "vertical=-3" in result.message


@pytest.mark.skipif(
    not os.environ.get("ADVANCED_VISION_LIVE_TESTS"),
    reason="Live tests disabled. Set ADVANCED_VISION_LIVE_TESTS=1 to enable."
)
def test_move_mouse_live() -> None:
    """E2.3: Live test - actually moves the mouse.
    
    WARNING: This test actually moves the mouse cursor.
    Only run when ADVANCED_VISION_LIVE_TESTS environment variable is set.
    """
    # Move to a safe position (center of typical screen)
    result = move_mouse(960, 540, dry_run=False)
    
    assert result.ok is True
    assert result.action_type == "move_mouse"
    assert "[DRY RUN]" not in result.message
    assert "Moved mouse" in result.message


# =============================================================================
# Phase E1.4: Diagnostics Tests
# =============================================================================


def test_diagnostics_collects_data() -> None:
    """E1.4: Verify diagnostics collects required information.
    
    Checks that diagnostics returns:
    - Python version info
    - Platform details
    - Module status for core dependencies
    - GUI session hints
    - Summary with readiness flags
    """
    diag = collect_diagnostics()
    
    # Check structure
    assert "python" in diag
    assert "platform" in diag
    assert "modules" in diag
    assert "gui" in diag
    assert "summary" in diag
    
    # Check python info
    assert diag["python"]["executable"] is not None
    assert diag["python"]["version"] is not None
    
    # Check platform info
    assert diag["platform"]["system"] is not None
    assert diag["platform"]["release"] is not None
    
    # Check modules list is not empty
    assert len(diag["modules"]) > 0
    
    # Check GUI section
    assert "tkinter" in diag["gui"]
    assert "screenshot_test" in diag["gui"]
    assert "session_hints" in diag["gui"]
    
    # Check summary has expected fields
    summary = diag["summary"]
    assert "core_modules_ok" in summary
    assert "gui_ready" in summary


def test_diagnostics_modules_have_status() -> None:
    """E1.4: Verify each module has status fields."""
    diag = collect_diagnostics()
    
    for mod in diag["modules"]:
        assert "name" in mod
        assert "ok" in mod
        # ok should be a boolean
        assert isinstance(mod["ok"], bool)


def test_diagnostics_detects_tkinter() -> None:
    """E1.4: Verify tkinter detection works."""
    diag = collect_diagnostics()
    
    tk = diag["gui"]["tkinter"]
    assert "name" in tk
    assert "ok" in tk
    assert "version" in tk
    
    # Should report tkinter status
    assert tk["name"] == "tkinter"


def test_diagnostics_screenshot_test() -> None:
    """E1.4: Verify screenshot test is performed."""
    diag = collect_diagnostics()
    
    scr = diag["gui"]["screenshot_test"]
    assert "name" in scr
    assert "ok" in scr
    assert scr["name"] == "screenshot_capture"
    
    # If screenshot works, should have size info
    if scr["ok"]:
        assert "size" in scr
        assert scr["size"] is not None


def test_diagnostics_gui_session_hints() -> None:
    """E1.4: Verify GUI session hints are collected."""
    diag = collect_diagnostics()
    
    hints = diag["gui"]["session_hints"]
    assert "display_env" in hints
    assert "wayland_display" in hints
    assert "xdg_session_type" in hints
    assert "platform" in hints
    assert "is_linux" in hints
    
    # Platform should match
    import platform
    assert hints["platform"] == platform.system()


def test_diagnostics_summary_flags() -> None:
    """E1.4: Verify summary flags are present and boolean."""
    diag = collect_diagnostics()
    summary = diag["summary"]
    
    # Check expected boolean flags
    boolean_flags = [
        "core_modules_ok",
        "any_window_backend_ok", 
        "environment_ready",
        "gui_ready",
        "gui_hint",
    ]
    
    for flag in boolean_flags:
        assert flag in summary, f"Missing flag: {flag}"
        assert isinstance(summary[flag], bool), f"Flag {flag} should be boolean"


# =============================================================================
# Action Result Structure Tests
# =============================================================================


def test_all_actions_return_action_result() -> None:
    """E2.2: Verify all actions return ActionResult type."""
    from advanced_vision.schemas import ActionResult
    
    # Test each action returns correct type
    move_result = move_mouse(0, 0, dry_run=True)
    click_result = click(0, 0, dry_run=True)
    type_result = type_text("test", dry_run=True)
    keys_result = press_keys(["a"], dry_run=True)
    scroll_result = scroll(0, 0, dry_run=True)
    
    all_results = [move_result, click_result, type_result, keys_result, scroll_result]
    
    for result in all_results:
        assert isinstance(result, ActionResult)
        assert hasattr(result, "ok")
        assert hasattr(result, "action_type")
        assert hasattr(result, "message")
        # ok should be boolean
        assert isinstance(result.ok, bool)
        # action_type should be string
        assert isinstance(result.action_type, str)
        # message should be string
        assert isinstance(result.message, str)
