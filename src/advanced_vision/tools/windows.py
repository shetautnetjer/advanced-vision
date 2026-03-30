"""Window listing and active-window helpers."""

from __future__ import annotations

import subprocess
from typing import Any

from ..logging_utils import append_jsonl
from ..schemas import ActionResult, WindowInfo


def _normalize_app_name(value: Any) -> str | None:
    if value is None:
        return None
    app_name = str(value).strip()
    return app_name or None


def _run_xdotool(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["xdotool", *args],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )


def _get_xdotool_active_window_id() -> str | None:
    result = _run_xdotool("getactivewindow")
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    return value or None


def _list_windows_xdotool() -> list[WindowInfo]:
    search = _run_xdotool("search", "--onlyvisible", "--name", ".*")
    if search.returncode != 0:
        return []

    active_id = _get_xdotool_active_window_id()
    windows: list[WindowInfo] = []
    seen_ids: set[str] = set()
    for line in search.stdout.splitlines():
        window_id = line.strip()
        if not window_id or window_id in seen_ids:
            continue
        seen_ids.add(window_id)

        name_result = _run_xdotool("getwindowname", window_id)
        title = name_result.stdout.strip()
        if not title:
            continue

        class_result = _run_xdotool("getwindowclassname", window_id)
        class_name = _normalize_app_name(class_result.stdout.strip())
        if class_name is None:
            pid_result = _run_xdotool("getwindowpid", window_id)
            pid = pid_result.stdout.strip()
            if pid:
                try:
                    proc = subprocess.run(
                        ["ps", "-p", pid, "-o", "comm="],
                        capture_output=True,
                        text=True,
                        timeout=5,
                        check=False,
                    )
                    class_name = _normalize_app_name(proc.stdout.strip())
                except Exception:
                    class_name = None

        windows.append(
            WindowInfo(
                window_id=window_id,
                title=title,
                app_name=class_name,
                is_active=(window_id == active_id),
            )
        )
    return windows


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    normalized = "".join(ch.lower() if ch.isalnum() else " " for ch in value)
    return " ".join(normalized.split())


def _score_window_match(window: WindowInfo, title_query: str, app_query: str | None = None) -> int:
    normalized_title = _normalize_text(window.title)
    normalized_app = _normalize_text(window.app_name)
    score = 0
    title_matched = not title_query

    if title_query:
        if title_query == normalized_title:
            score += 100
            title_matched = True
        elif title_query in normalized_title:
            score += 70
            title_matched = True
        else:
            title_tokens = set(normalized_title.split())
            query_tokens = {token for token in title_query.split() if token}
            overlap = len(query_tokens & title_tokens)
            if overlap:
                score += overlap * 15
                title_matched = True

    if title_query and not title_matched:
        return 0

    if app_query:
        if app_query == normalized_app:
            score += 40
        elif app_query in normalized_app:
            score += 25

    if window.is_active:
        score += 5
    return score


def _select_window_candidate(
    windows: list[WindowInfo], title_query: str, app_query: str | None = None
) -> WindowInfo | None:
    normalized_title = _normalize_text(title_query)
    normalized_app = _normalize_text(app_query)
    candidates = []
    for window in windows:
        score = _score_window_match(window, normalized_title, normalized_app or None)
        if score > 0:
            candidates.append((score, window))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


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
        windows = _list_windows_xdotool()
        backend = "xdotool"
    except Exception:
        windows = []

    if not windows:
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
        active_id = _get_xdotool_active_window_id()
        if active_id:
            geometry = _run_xdotool("getwindowgeometry", "--shell", active_id)
            if geometry.returncode == 0:
                values: dict[str, int] = {}
                for line in geometry.stdout.splitlines():
                    if "=" not in line:
                        continue
                    key, value = line.split("=", 1)
                    if key in {"X", "Y", "WIDTH", "HEIGHT"}:
                        values[key] = int(value.strip())
                if {"X", "Y", "WIDTH", "HEIGHT"} <= values.keys():
                    left = values["X"]
                    top = values["Y"]
                    width = values["WIDTH"]
                    height = values["HEIGHT"]
                    if width > 0 and height > 0:
                        return (left, top, left + width, top + height)
    except Exception:
        pass

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


def focus_window(title_query: str, app_name: str | None = None, dry_run: bool = False) -> ActionResult:
    """Focus the best-matching visible window by title and optional app name."""
    windows = list_windows()
    candidate = _select_window_candidate(windows, title_query, app_name)
    if candidate is None or not candidate.window_id:
        message = f"No visible window matched title_query='{title_query}'"
        if app_name:
            message += f" and app_name='{app_name}'"
        result = ActionResult(ok=False, action_type="focus_window", message=message)
        append_jsonl("actions", {**result.model_dump(), "title_query": title_query, "app_name": app_name})
        return result

    if dry_run:
        result = ActionResult(
            ok=True,
            action_type="focus_window",
            message=(
                f"[DRY RUN] Would focus window '{candidate.title}'"
                + (f" ({candidate.app_name})" if candidate.app_name else "")
            ),
        )
        append_jsonl(
            "actions",
            {
                **result.model_dump(),
                "title_query": title_query,
                "app_name": app_name,
                "window_id": candidate.window_id,
            },
        )
        return result

    try:
        activation = _run_xdotool("windowactivate", "--sync", candidate.window_id)
        if activation.returncode != 0:
            raise RuntimeError(activation.stderr.strip() or "xdotool windowactivate failed")
        result = ActionResult(
            ok=True,
            action_type="focus_window",
            message=(
                f"Focused window '{candidate.title}'"
                + (f" ({candidate.app_name})" if candidate.app_name else "")
            ),
        )
    except Exception as exc:
        result = ActionResult(ok=False, action_type="focus_window", message=f"Failed to focus window: {exc}")

    append_jsonl(
        "actions",
        {
            **result.model_dump(),
            "title_query": title_query,
            "app_name": app_name,
            "window_id": candidate.window_id,
        },
    )
    return result
