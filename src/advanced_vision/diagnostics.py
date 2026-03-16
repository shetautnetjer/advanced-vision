"""Environment diagnostics for advanced_vision.

Keeps dependency and GUI-readiness checks lightweight so users can quickly tell
whether failures are caused by setup, missing packages, or desktop backend issues.
"""

from __future__ import annotations

import importlib
import json
import os
import platform
import shutil
import sys
from typing import Any

REQUIRED_MODULES = [
    "PIL",
    "pydantic",
    "mcp",
    "pyautogui",
    "pygetwindow",
]


def _module_status(name: str) -> dict[str, Any]:
    try:
        module = importlib.import_module(name)
        return {
            "name": name,
            "ok": True,
            "version": getattr(module, "__version__", None),
            "error": None,
        }
    except Exception as exc:
        return {
            "name": name,
            "ok": False,
            "version": None,
            "error": f"{type(exc).__name__}: {exc}",
        }


def collect_diagnostics() -> dict[str, Any]:
    module_results = [_module_status(name) for name in REQUIRED_MODULES]
    all_modules_ok = all(item["ok"] for item in module_results)

    return {
        "python": {
            "executable": sys.executable,
            "version": sys.version,
            "python_on_path": shutil.which("python"),
            "python3_on_path": shutil.which("python3"),
            "pip_on_path": shutil.which("pip"),
            "pip3_on_path": shutil.which("pip3"),
        },
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "platform": platform.platform(),
        },
        "environment": {
            "DISPLAY": os.environ.get("DISPLAY"),
            "WAYLAND_DISPLAY": os.environ.get("WAYLAND_DISPLAY"),
            "XDG_SESSION_TYPE": os.environ.get("XDG_SESSION_TYPE"),
        },
        "modules": module_results,
        "summary": {
            "all_required_modules_ok": all_modules_ok,
            "gui_hint": bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")),
        },
    }


def main() -> None:
    print(json.dumps(collect_diagnostics(), indent=2))


if __name__ == "__main__":
    main()
