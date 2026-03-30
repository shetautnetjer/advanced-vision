"""MCP server exposing minimal local computer-use tools."""

from __future__ import annotations

from typing import Any

from .schemas import ActionProposal
from .tools.input import click, move_mouse, press_keys, scroll, type_text
from .tools.screen import screenshot_active_window, screenshot_full
from .tools.verify import verify_screen_change
from .tools.windows import focus_window, list_windows
from .vision_adapter import analyze_screenshot

try:
    from mcp.server.fastmcp import FastMCP
except Exception as exc:  # pragma: no cover
    FastMCP = None  # type: ignore[assignment]
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None


if FastMCP is not None:
    mcp = FastMCP("advanced-vision")

    @mcp.tool(name="screenshot_full")
    def screenshot_full_mcp() -> dict[str, Any]:
        return screenshot_full().model_dump()

    @mcp.tool(name="screenshot_active_window")
    def screenshot_active_window_mcp() -> dict[str, Any]:
        return screenshot_active_window().model_dump()

    @mcp.tool(name="list_windows")
    def list_windows_mcp() -> list[dict[str, Any]]:
        return [w.model_dump() for w in list_windows()]

    @mcp.tool(name="focus_window")
    def focus_window_mcp(title_query: str, app_name: str | None = None, dry_run: bool = False) -> dict[str, Any]:
        return focus_window(title_query=title_query, app_name=app_name, dry_run=dry_run).model_dump()

    @mcp.tool(name="move_mouse")
    def move_mouse_mcp(x: int, y: int, dry_run: bool = False) -> dict[str, Any]:
        return move_mouse(x, y, dry_run=dry_run).model_dump()

    @mcp.tool(name="click")
    def click_mcp(x: int, y: int, button: str = "left", dry_run: bool = False) -> dict[str, Any]:
        return click(x, y, button=button, dry_run=dry_run).model_dump()

    @mcp.tool(name="type_text")
    def type_text_mcp(text: str, dry_run: bool = False) -> dict[str, Any]:
        return type_text(text, dry_run=dry_run).model_dump()

    @mcp.tool(name="press_keys")
    def press_keys_mcp(keys: list[str], dry_run: bool = False) -> dict[str, Any]:
        return press_keys(keys, dry_run=dry_run).model_dump()

    @mcp.tool(name="scroll")
    def scroll_mcp(vertical: int = 0, horizontal: int = 0, dry_run: bool = False) -> dict[str, Any]:
        return scroll(vertical=vertical, horizontal=horizontal, dry_run=dry_run).model_dump()

    @mcp.tool(name="verify_screen_change")
    def verify_screen_change_mcp(
        previous_screenshot_path: str,
        current_screenshot_path: str | float | None = None,
        threshold: float = 0.99,
    ) -> dict[str, Any]:
        return verify_screen_change(
            previous_screenshot_path,
            current_screenshot_path=current_screenshot_path,
            threshold=threshold,
        ).model_dump()

    @mcp.tool(name="analyze_screenshot")
    def analyze_screenshot_mcp(screenshot_path: str, task: str) -> dict[str, Any]:
        proposal: ActionProposal = analyze_screenshot(screenshot_path, task)
        return proposal.model_dump()


def run() -> None:
    if FastMCP is None:
        raise RuntimeError(f"MCP dependency unavailable: {_IMPORT_ERROR}")
    mcp.run()


if __name__ == "__main__":
    run()
