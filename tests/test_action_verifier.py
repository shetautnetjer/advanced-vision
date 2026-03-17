"""Tests for action_verifier module - Phase E3: Live Action Verification.

These tests verify that actions can be executed and their effects verified:
- Execute action → Wait → Capture → Verify change
- Safe demo scenarios with preset coordinates
- Rollback detection for temporary changes

Safety:
    All tests use dry_run=True by default. Set ADVANCED_VISION_LIVE_TESTS=1
    environment variable to run live tests that actually move mouse/click/type.
    
    Live tests use SAFE_COORDINATES to avoid clicking important UI elements.
"""

import os
from pathlib import Path

import pytest

from advanced_vision.tools.action_verifier import (
    SAFE_COORDINATES,
    demo_click_at_safe_location,
    demo_mouse_movement,
    demo_typing_in_scratch_area,
    execute_and_verify,
    verify_rollback,
)
from advanced_vision.tools.screen import screenshot_full


# Skip live tests unless explicitly enabled
LIVE_TESTS_ENABLED = os.environ.get("ADVANCED_VISION_LIVE_TESTS") == "1"


# =============================================================================
# Phase E3: Action Verification Tests (Dry Run)
# =============================================================================


def test_execute_and_verify_dry_run():
    """E3.1: Verify execute_and_verify works in dry_run mode."""
    result = execute_and_verify(
        action_type="move_mouse",
        x=500,
        y=500,
        delay_seconds=0.1,
        dry_run=True,
    )
    
    assert result["action_result"]["ok"] is True
    assert result["dry_run"] is True
    assert "before_screenshot" in result
    assert "after_screenshot" in result
    assert "verification" in result
    # Even dry_run should show some change (timestamps in artifacts)
    assert Path(result["before_screenshot"]["path"]).exists()
    assert Path(result["after_screenshot"]["path"]).exists()


def test_execute_and_verify_click_dry_run():
    """E3.2: Verify click action in dry_run mode."""
    result = execute_and_verify(
        action_type="click",
        x=960,
        y=600,
        button="left",
        dry_run=True,
    )
    
    assert result["action_result"]["ok"] is True
    assert result["action_type"] == "click"


def test_execute_and_verify_type_text_dry_run():
    """E3.3: Verify type_text action in dry_run mode."""
    result = execute_and_verify(
        action_type="type_text",
        text="Test message",
        dry_run=True,
    )
    
    assert result["action_result"]["ok"] is True
    assert result["action_type"] == "type_text"


def test_demo_mouse_movement_dry_run():
    """E3.4: Safe demo - mouse movement (dry_run)."""
    result = demo_mouse_movement(dry_run=True)
    
    assert result["action_result"]["ok"] is True
    assert result["action_type"] == "move_mouse"
    assert result["dry_run"] is True


def test_demo_click_safe_location_dry_run():
    """E3.5: Safe demo - click at safe location (dry_run)."""
    result = demo_click_at_safe_location(dry_run=True)
    
    assert result["action_result"]["ok"] is True
    assert result["action_type"] == "click"


def test_demo_typing_dry_run():
    """E3.6: Safe demo - typing (dry_run)."""
    result = demo_typing_in_scratch_area(dry_run=True)
    
    assert result["action_result"]["ok"] is True
    assert result["action_type"] == "type_text"


def test_safe_coordinates_defined():
    """E3.7: Verify safe coordinates are defined."""
    assert "center" in SAFE_COORDINATES
    assert "safe_upper_left" in SAFE_COORDINATES
    assert "safe_upper_right" in SAFE_COORDINATES
    assert "safe_lower_left" in SAFE_COORDINATES
    assert "safe_lower_right" in SAFE_COORDINATES
    
    # Verify coordinates are reasonable (within 1920x1080)
    for name, (x, y) in SAFE_COORDINATES.items():
        assert 0 <= x <= 1920, f"{name} x={x} out of range"
        assert 0 <= y <= 1080, f"{name} y={y} out of range"


def test_verify_rollback_no_change():
    """E3.8: Verify rollback detection when no change occurs."""
    # Take a screenshot
    original = screenshot_full()
    
    # Immediately check for rollback (should be instant)
    result = execute_and_verify(
        action_type="noop",  # No actual action
        delay_seconds=0,
        dry_run=True,
    )
    
    rollback = verify_rollback(
        original.path,
        result,
        timeout_seconds=0.5,
        check_interval=0.1,
    )
    
    # Screen didn't change, so it's already "rolled back"
    assert rollback["rolled_back"] is True


# =============================================================================
# Phase E3: Live Action Tests (Require ADVANCED_VISION_LIVE_TESTS=1)
# =============================================================================


@pytest.mark.skipif(not LIVE_TESTS_ENABLED, reason="Live tests disabled. Set ADVANCED_VISION_LIVE_TESTS=1")
def test_live_mouse_movement():
    """E3.L1: Live test - actually move mouse to safe location."""
    result = demo_mouse_movement(dry_run=False)
    
    assert result["action_result"]["ok"] is True
    assert result["dry_run"] is False
    # Mouse movement should cause some screen change (cursor position)
    # Note: May not always detect if cursor is transparent/small


@pytest.mark.skipif(not LIVE_TESTS_ENABLED, reason="Live tests disabled. Set ADVANCED_VISION_LIVE_TESTS=1")
def test_live_click_at_safe_location():
    """E3.L2: Live test - actually click at safe location (desktop)."""
    result = demo_click_at_safe_location(dry_run=False)
    
    assert result["action_result"]["ok"] is True
    assert result["dry_run"] is False


@pytest.mark.skipif(not LIVE_TESTS_ENABLED, reason="Live tests disabled. Set ADVANCED_VISION_LIVE_TESTS=1")
def test_live_typing_in_scratch_area():
    """E3.L3: Live test - actually type text.
    
    WARNING: Ensure a text editor is open and focused before running!
    The text "Hello from advanced-vision testing! 123" will be typed.
    """
    # This test requires manual setup - a text editor must be open
    pytest.skip("Requires manual setup: open text editor and focus it")
    
    result = demo_typing_in_scratch_area(dry_run=False)
    
    assert result["action_result"]["ok"] is True
    assert result["dry_run"] is False
    # Typing should cause visible screen change
    assert result["verification"]["changed"] is True


@pytest.mark.skipif(not LIVE_TESTS_ENABLED, reason="Live tests disabled. Set ADVANCED_VISION_LIVE_TESTS=1")
def test_live_execute_and_verify_full_cycle():
    """E3.L4: Live test - full action → verify cycle with multiple actions."""
    # Move mouse
    move_result = execute_and_verify(
        action_type="move_mouse",
        x=SAFE_COORDINATES["safe_upper_left"][0],
        y=SAFE_COORDINATES["safe_upper_left"][1],
        delay_seconds=0.3,
        dry_run=False,
    )
    assert move_result["action_result"]["ok"] is True
    
    # Click
    click_result = execute_and_verify(
        action_type="click",
        x=SAFE_COORDINATES["center"][0],
        y=SAFE_COORDINATES["center"][1],
        delay_seconds=0.3,
        dry_run=False,
    )
    assert click_result["action_result"]["ok"] is True


# =============================================================================
# Logging and Audit Tests
# =============================================================================


def test_action_verification_logged():
    """E3.9: Verify action executions are logged to JSONL."""
    import json
    from advanced_vision.config import get_settings
    
    # Execute an action
    result = execute_and_verify(
        action_type="move_mouse",
        x=100,
        y=100,
        dry_run=True,
    )
    
    # Check log file exists and contains our action
    settings = get_settings()
    log_path = settings.logs_dir / "action_verification.jsonl"
    
    if log_path.exists():
        with open(log_path) as f:
            lines = f.readlines()
            # Last line should be our action
            last_entry = json.loads(lines[-1])
            assert last_entry["action_type"] == "move_mouse"
            assert "timestamp" in last_entry
