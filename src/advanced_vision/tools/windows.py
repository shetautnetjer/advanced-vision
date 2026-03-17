"""Window listing and active-window helpers."""

from __future__ import annotations

from typing import Any

from ..logging_utils import append_jsonl
from ..schemas import WindowInfo


def _normalize_app_name(value: Any) -> str | None:
    if value is None:
        return None
    app_name = str(value).strip()
    return app_name or None


def _list_windows_pywinctl() -> list[WindowInfo]:
    import pywinctl as pwc  # type: ignore

    windows: list[WindowInfo] = []
    for w in pwc.getAllWindows():
        title = str(getattr(w, "title", "") or "").strip()
        if not title:
            continue
        is_visible = bool(getattr(w, "isVisible", True))
        is_minimized = bool(getattr(w, "isMinimized", False))
        if not is_visible or is_minimized:
            continue

        app_name = None
        try:
            get_app_name = getattr(w, "getAppName", None)
            app_name = _normalize_app_name(get_app_name() if callable(get_app_name) else None)
        except Exception:
            app_name = None

        windows.append(
            WindowInfo(
                title=title,
                app_name=app_name,
                is_active=bool(getattr(w, "isActive", False)),
            )
        )
    return windows


def _list_windows_pygetwindow() -> list[WindowInfo]:
    import pygetwindow as gw  # type: ignore

    windows: list[WindowInfo] = []
    active = None
    try:
        active = gw.getActiveWindow()
    except Exception:
        active = None

    for w in gw.getAllWindows():
        title = str(getattr(w, "title", "") or "").strip()
        if not title:
            continue
        windows.append(
            WindowInfo(
                title=title,
                app_name=None,
                is_active=bool(active and w == active),
            )
        )
    return windows


def list_windows() -> list[WindowInfo]:
    """Return visible top-level windows using best-effort backend."""
    windows: list[WindowInfo] = []
    backend = None

    try:
        windows = _list_windows_pywinctl()
        backend = "pywinctl"
    except Exception:
        try:
            windows = _list_windows_pygetwindow()
            backend = "pygetwindow"
        except Exception:
            windows = []
            backend = None

    append_jsonl(
        "actions",
        {
            "action_type": "list_windows",
            "count": len(windows),
            "backend": backend,
        },
    )
    return windows


def get_active_window_bbox() -> tuple[int, int, int, int] | None:
    """Return active window bbox using the best available backend."""
    try:
        import pywinctl as pwc  # type: ignore

        active = None
        try:
            active = pwc.getActiveWindow()
        except Exception:
            active = None

        candidate = active
        if candidate is None:
            for w in pwc.getAllWindows():
                if bool(getattr(w, "isActive", False)):
                    candidate = w
                    break

        if candidate is not None:
            left, top = int(getattr(candidate, "left")), int(getattr(candidate, "top"))
            width, height = int(getattr(candidate, "width")), int(getattr(candidate, "height"))
            if width > 0 and height > 0:
                return (left, top, left + width, top + height)
    except Exception:
        pass

    try:
        import pygetwindow as gw  # type: ignore

        active = gw.getActiveWindow()
        if active is None:
            return None
        left, top = int(active.left), int(active.top)
        width, height = int(active.width), int(active.height)
        if width <= 0 or height <= 0:
            return None
        return (left, top, left + width, top + height)
    except Exception:
        return None
