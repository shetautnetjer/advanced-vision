"""Mouse and keyboard control tools."""

from __future__ import annotations

from ..logging_utils import append_jsonl
from ..schemas import ActionResult


def _get_pyautogui():
    import pyautogui  # type: ignore

    pyautogui.FAILSAFE = True
    return pyautogui


def move_mouse(x: int, y: int, dry_run: bool = False) -> ActionResult:
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
