"""Reusable screenshot -> analyze -> act -> verify helper flow."""

from __future__ import annotations

from typing import Any

from .schemas import ActionProposal
from .tools.input import click, move_mouse, press_keys, scroll, type_text
from .tools.screen import screenshot_full
from .tools.verify import verify_screen_change_between
from .vision_adapter import analyze_screenshot


def _execute_proposed_action(proposal: ActionProposal) -> dict[str, Any]:
    if proposal.action_type == "move_mouse" and proposal.x is not None and proposal.y is not None:
        return move_mouse(proposal.x, proposal.y).model_dump()
    if proposal.action_type == "click" and proposal.x is not None and proposal.y is not None:
        return click(proposal.x, proposal.y).model_dump()
    if proposal.action_type == "type_text" and proposal.text is not None:
        return type_text(proposal.text).model_dump()
    if proposal.action_type == "press_keys" and proposal.keys:
        return press_keys(proposal.keys).model_dump()
    if proposal.action_type == "scroll":
        return scroll(vertical=proposal.y or 0, horizontal=proposal.x or 0).model_dump()
    return {"ok": True, "action_type": "noop", "message": "No action executed."}


def run_single_cycle(task: str, execute: bool = False) -> dict[str, Any]:
    """Run one inspectable cycle: capture -> analyze -> optional act -> verify."""
    before = screenshot_full()
    proposal = analyze_screenshot(before.path, task)
    action_result = _execute_proposed_action(proposal) if execute else {
        "ok": True,
        "action_type": proposal.action_type,
        "message": "Execution skipped.",
    }
    after = screenshot_full()
    verification = verify_screen_change_between(before.path, after.path)
    return {
        "before": before.model_dump(),
        "proposal": proposal.model_dump(),
        "action_result": action_result,
        "after": after.model_dump(),
        "verification": verification.model_dump(),
    }
