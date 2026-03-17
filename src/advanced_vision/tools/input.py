"""Mouse and keyboard control tools.

This module provides safe, structured input actions with dry_run support.
All actions return structured ActionResult objects for consistent logging
and potential future governance layering.

Dry Run Mode:
    All functions support dry_run=True which simulates the action without
    actually performing it. This is useful for:
    - Testing action sequences safely
    - Validating coordinates before execution
    - Logging intended actions for review
    - CI/CD testing without actual GUI interaction

Safety Features:
    - pyautogui.FAILSAFE is enabled (move mouse to corner to abort)
    - All actions are wrapped in try/except with structured error returns
    - dry_run mode available for all actions
    - Actions are logged to JSONL for audit trails

Example:
    # Safe testing with dry_run
    result = move_mouse(100, 200, dry_run=True)
    print(result.message)  # "[DRY RUN] Would move mouse to (100, 200)"
    
    # Live execution
    result = click(100, 200)
    if result.ok:
        print(f"Action succeeded: {result.message}")
    else:
        print(f"Action failed: {result.message}")
"""

from __future__ import annotations

from ..logging_utils import append_jsonl
from ..schemas import ActionResult


def _get_pyautogui():
    """Get pyautogui instance with failsafe enabled."""
    import pyautogui  # type: ignore

    pyautogui.FAILSAFE = True
    return pyautogui


def move_mouse(x: int, y: int, dry_run: bool = False) -> ActionResult:
    """Move mouse cursor to specified coordinates.
    
    Args:
        x: Horizontal screen coordinate (pixels from left)
        y: Vertical screen coordinate (pixels from top)
        dry_run: If True, simulate without moving the mouse
        
    Returns:
        ActionResult with ok status, action_type, and message
        
    Safety:
        pyautogui.FAILSAFE is enabled - move mouse to screen corner
        to trigger an emergency stop if needed.
    """
    try:
        if dry_run:
            result = ActionResult(ok=True, action_type="move_mouse", message=f"[DRY RUN] Would move mouse to ({x}, {y})")
        else:
            pag = _get_pyautogui()
            pag.moveTo(x, y)
            result = ActionResult(ok=True, action_type="move_mouse", message=f"Moved mouse to ({x}, {y})")
    except Exception as exc:
        result = ActionResult(ok=False, action_type="move_mouse", message=f"Failed to move mouse: {exc}")
    append_jsonl("actions", result.model_dump())
    return result


def click(x: int, y: int, button: str = "left", dry_run: bool = False) -> ActionResult:
    """Click at specified coordinates.
    
    Args:
        x: Horizontal screen coordinate (pixels from left)
        y: Vertical screen coordinate (pixels from top)
        button: Mouse button to click ('left', 'right', 'middle')
        dry_run: If True, simulate without clicking
        
    Returns:
        ActionResult with ok status, action_type, and message
    """
    try:
        if dry_run:
            result = ActionResult(ok=True, action_type="click", message=f"[DRY RUN] Would click {button} at ({x}, {y})")
        else:
            pag = _get_pyautogui()
            pag.click(x=x, y=y, button=button)
            result = ActionResult(ok=True, action_type="click", message=f"Clicked {button} at ({x}, {y})")
    except Exception as exc:
        result = ActionResult(ok=False, action_type="click", message=f"Failed to click: {exc}")
    append_jsonl("actions", result.model_dump())
    return result


def type_text(text: str, dry_run: bool = False) -> ActionResult:
    """Type the specified text.
    
    Args:
        text: String to type
        dry_run: If True, simulate without typing
        
    Returns:
        ActionResult with ok status, action_type, and message
        
    Note:
        Text content is redacted from logs for privacy/security.
        Only the character count is logged.
    """
    try:
        if dry_run:
            result = ActionResult(ok=True, action_type="type_text", message=f"[DRY RUN] Would type {len(text)} chars")
        else:
            pag = _get_pyautogui()
            pag.write(text)
            result = ActionResult(ok=True, action_type="type_text", message=f"Typed {len(text)} chars")
    except Exception as exc:
        result = ActionResult(ok=False, action_type="type_text", message=f"Failed to type text: {exc}")
    append_jsonl("actions", {**result.model_dump(), "text_length": len(text), "text_redacted": True})
    return result


def press_keys(keys: list[str], dry_run: bool = False) -> ActionResult:
    """Press keyboard keys.
    
    Args:
        keys: List of keys to press. Single key = press once.
              Multiple keys = press as hotkey combination.
        dry_run: If True, simulate without pressing keys
        
    Returns:
        ActionResult with ok status, action_type, and message
        
    Examples:
        press_keys(['f5'])  # Press F5
        press_keys(['ctrl', 'c'])  # Press Ctrl+C
        press_keys(['alt', 'tab'])  # Press Alt+Tab
    """
    try:
        if dry_run:
            result = ActionResult(ok=True, action_type="press_keys", message=f"[DRY RUN] Would press keys: {'+'.join(keys)}")
        else:
            pag = _get_pyautogui()
            if len(keys) == 1:
                pag.press(keys[0])
            else:
                pag.hotkey(*keys)
            result = ActionResult(ok=True, action_type="press_keys", message=f"Pressed keys: {'+'.join(keys)}")
    except Exception as exc:
        result = ActionResult(ok=False, action_type="press_keys", message=f"Failed to press keys: {exc}")
    append_jsonl("actions", {**result.model_dump(), "keys": keys})
    return result


def scroll(vertical: int = 0, horizontal: int = 0, dry_run: bool = False) -> ActionResult:
    """Scroll the mouse wheel.
    
    Args:
        vertical: Vertical scroll amount (positive = up, negative = down)
        horizontal: Horizontal scroll amount (positive = right, negative = left)
        dry_run: If True, simulate without scrolling
        
    Returns:
        ActionResult with ok status, action_type, and message
        
    Note:
        Horizontal scroll requires pyautogui hscroll support (may not work
        on all platforms).
    """
    try:
        if dry_run:
            result = ActionResult(
                ok=True,
                action_type="scroll",
                message=f"[DRY RUN] Would scroll vertical={vertical}, horizontal={horizontal}",
            )
        else:
            pag = _get_pyautogui()
            if vertical:
                pag.scroll(vertical)
            if horizontal and hasattr(pag, "hscroll"):
                pag.hscroll(horizontal)
            result = ActionResult(
                ok=True,
                action_type="scroll",
                message=f"Scrolled vertical={vertical}, horizontal={horizontal}",
            )
    except Exception as exc:
        result = ActionResult(ok=False, action_type="scroll", message=f"Failed to scroll: {exc}")
    append_jsonl("actions", {**result.model_dump(), "vertical": vertical, "horizontal": horizontal})
    return result
