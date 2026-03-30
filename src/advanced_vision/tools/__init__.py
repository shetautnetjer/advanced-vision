"""Tool modules for advanced_vision."""

from .action_verifier import (
    SAFE_COORDINATES,
    demo_click_at_safe_location,
    demo_mouse_movement,
    demo_typing_in_scratch_area,
    execute_and_verify,
    verify_rollback,
)
from .input import click, move_mouse, press_keys, scroll, type_text
from .screen import screenshot_active_window, screenshot_full
from .verify import verify_screen_change, verify_screen_change_between
from .windows import focus_window, get_active_window_bbox, list_windows

__all__ = [
    # Screen capture
    "screenshot_full",
    "screenshot_active_window",
    # Input actions
    "move_mouse",
    "click",
    "type_text",
    "press_keys",
    "scroll",
    # Verification
    "verify_screen_change",
    "verify_screen_change_between",
    # Window management
    "list_windows",
    "focus_window",
    "get_active_window_bbox",
    # Action verification (Phase E3)
    "execute_and_verify",
    "demo_mouse_movement",
    "demo_click_at_safe_location",
    "demo_typing_in_scratch_area",
    "verify_rollback",
    "SAFE_COORDINATES",
]
