"""Action execution with verification for safe computer-use testing.

Phase E3: Live Action Verification
- Execute action → Wait → Capture after screenshot → Verify change
- Safe demo scenarios with preset coordinates
- Timing controls for delay between action and verification
"""

from __future__ import annotations

import time
from typing import Any

from ..logging_utils import append_jsonl, utc_now_iso
from ..schemas import ActionResult, VerificationResult
from .input import click, move_mouse, press_keys, scroll, type_text
from .screen import screenshot_full
from .verify import verify_screen_change_between


# Safe demo coordinates (center-ish screen, avoiding edges)
SAFE_COORDINATES = {
    "center": (960, 600),
    "safe_upper_left": (200, 200),
    "safe_upper_right": (1720, 200),
    "safe_lower_left": (200, 880),
    "safe_lower_right": (1720, 880),
}


def execute_and_verify(
    action_type: str,
    x: int | None = None,
    y: int | None = None,
    text: str | None = None,
    keys: list[str] | None = None,
    button: str = "left",
    delay_seconds: float = 0.5,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Execute an action, wait, and verify the screen changed.
    
    Args:
        action_type: Type of action (move_mouse, click, type_text, press_keys, scroll)
        x: X coordinate for mouse actions
        y: Y coordinate for mouse actions  
        text: Text to type for type_text action
        keys: Keys to press for press_keys action
        button: Mouse button (left/right/middle)
        delay_seconds: Time to wait between action and verification screenshot
        dry_run: If True, don't actually execute, just log what would happen
        
    Returns:
        Dict with before_screenshot, action_result, after_screenshot, verification
        
    Example:
        # Move mouse and verify cursor position changed
        result = execute_and_verify("move_mouse", x=500, y=500, delay_seconds=0.3)
        assert result["verification"]["changed"] is True
    """
    # Capture before screenshot
    before = screenshot_full()
    
    # Execute the action
    action_result: ActionResult
    if dry_run:
        action_result = ActionResult(
            ok=True,
            action_type=action_type,
            message=f"[DRY RUN] Would execute {action_type}",
        )
    else:
        if action_type == "move_mouse" and x is not None and y is not None:
            action_result = move_mouse(x, y)
        elif action_type == "click" and x is not None and y is not None:
            action_result = click(x, y, button=button)
        elif action_type == "type_text" and text is not None:
            action_result = type_text(text)
        elif action_type == "press_keys" and keys is not None:
            action_result = press_keys(keys)
        elif action_type == "scroll":
            action_result = scroll(vertical=y or 0, horizontal=x or 0)
        else:
            action_result = ActionResult(
                ok=False,
                action_type="noop",
                message=f"Unknown action_type: {action_type}",
            )
    
    # Wait for screen to update
    if not dry_run and delay_seconds > 0:
        time.sleep(delay_seconds)
    
    # Capture after screenshot
    after = screenshot_full()
    
    # Verify change occurred
    verification = verify_screen_change_between(before.path, after.path)
    
    # Log the full cycle
    result = {
        "timestamp": utc_now_iso(),
        "action_type": action_type,
        "dry_run": dry_run,
        "before_screenshot": before.model_dump(),
        "action_result": action_result.model_dump(),
        "after_screenshot": after.model_dump(),
        "verification": verification.model_dump(),
        "delay_seconds": delay_seconds,
    }
    append_jsonl("action_verification", result)
    
    return result


def demo_mouse_movement(dry_run: bool = True) -> dict[str, Any]:
    """Safe demo: Move mouse to preset safe coordinates.
    
    Args:
        dry_run: If True, don't actually move the mouse
        
    Returns:
        Action verification result
    """
    safe_x, safe_y = SAFE_COORDINATES["center"]
    return execute_and_verify(
        action_type="move_mouse",
        x=safe_x,
        y=safe_y,
        delay_seconds=0.3,
        dry_run=dry_run,
    )


def demo_typing_in_scratch_area(dry_run: bool = True) -> dict[str, Any]:
    """Safe demo: Type text that won't cause harm.
    
    This is meant to be run with a text editor already open
    in a disposable/scratch area.
    
    Args:
        dry_run: If True, don't actually type
        
    Returns:
        Action verification result
    """
    return execute_and_verify(
        action_type="type_text",
        text="Hello from advanced-vision testing! 123",
        delay_seconds=0.5,
        dry_run=dry_run,
    )


def demo_click_at_safe_location(dry_run: bool = True) -> dict[str, Any]:
    """Safe demo: Click at a preset safe location.
    
    The center coordinates should be safe (desktop area, not buttons).
    
    Args:
        dry_run: If True, don't actually click
        
    Returns:
        Action verification result
    """
    safe_x, safe_y = SAFE_COORDINATES["center"]
    return execute_and_verify(
        action_type="click",
        x=safe_x,
        y=safe_y,
        button="left",
        delay_seconds=0.5,
        dry_run=dry_run,
    )


def verify_rollback(
    original_screenshot_path: str,
    action_verification_result: dict[str, Any],
    timeout_seconds: float = 5.0,
    check_interval: float = 0.5,
) -> dict[str, Any]:
    """Verify screen returns to original state after an action.
    
    Useful for testing temporary changes (menus, tooltips, etc.).
    
    Args:
        original_screenshot_path: Path to original "before" screenshot
        action_verification_result: Result from execute_and_verify()
        timeout_seconds: Max time to wait for rollback
        check_interval: Time between checks
        
    Returns:
        Dict with rollback_verification and time_to_rollback
        
    Example:
        # Click menu, verify it closes
        result = demo_click_at_safe_location(dry_run=False)
        rollback = verify_rollback(result["before_screenshot"]["path"], result)
        assert rollback["rolled_back"] is True
    """
    start_time = time.time()
    
    while time.time() - start_time < timeout_seconds:
        current = screenshot_full()
        verification = verify_screen_change_between(
            original_screenshot_path, 
            current.path,
            threshold=0.99,
        )
        
        # If screen matches original (similarity high), rollback occurred
        if not verification.changed or verification.similarity and verification.similarity > 0.98:
            return {
                "rolled_back": True,
                "time_to_rollback": time.time() - start_time,
                "final_screenshot": current.model_dump(),
                "verification": verification.model_dump(),
            }
        
        time.sleep(check_interval)
    
    # Timeout - rollback didn't occur
    current = screenshot_full()
    verification = verify_screen_change_between(original_screenshot_path, current.path)
    return {
        "rolled_back": False,
        "timeout_seconds": timeout_seconds,
        "final_screenshot": current.model_dump(),
        "verification": verification.model_dump(),
    }
