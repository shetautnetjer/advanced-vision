"""Window listing tools."""

from __future__ import annotations

from ..logging_utils import append_jsonl
from ..schemas import WindowInfo


def list_windows() -> list[WindowInfo]:
    """Return visible top-level windows using best-effort backend."""
    windows: list[WindowInfo] = []
    try:
        import pygetwindow as gw  # type: ignore

        active = gw.getActiveWindow()
        for w in gw.getAllWindows():
            title = (w.title or "").strip()
            if not title:
                continue
            windows.append(
                WindowInfo(
                    title=title,
                    app_name=None,
                    is_active=bool(active and w == active),
                )
            )
    except Exception:
        # Keep deterministic fallback in environments without GUI libs.
        windows = []

    append_jsonl("actions", {"action_type": "list_windows", "count": len(windows)})
    return windows
