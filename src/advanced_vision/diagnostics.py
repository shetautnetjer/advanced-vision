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

CORE_MODULES = [
    "PIL",
    "pydantic",
    "mcp",
    "pyautogui",
]
WINDOW_BACKENDS = [
    "pywinctl",
    "pygetwindow",
]
ALL_MODULES = CORE_MODULES + WINDOW_BACKENDS


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


def _tkinter_status() -> dict[str, Any]:
    """Check tkinter availability - required for pyautogui on some platforms."""
    try:
        import tkinter
        return {
            "name": "tkinter",
            "ok": True,
            "version": tkinter.Tcl().eval("info patchlevel"),
            "error": None,
            "note": "Required for pyautogui screenshots on some platforms",
        }
    except Exception as exc:
        return {
            "name": "tkinter",
            "ok": False,
            "version": None,
            "error": f"{type(exc).__name__}: {exc}",
            "note": "May be needed for pyautogui screenshots; install with 'apt-get install python3-tk' on Debian/Ubuntu",
        }


def _screenshot_test() -> dict[str, Any]:
    """Test if screenshot capture actually works."""
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab()
        return {
            "name": "screenshot_capture",
            "ok": True,
            "size": img.size,
            "mode": img.mode,
            "error": None,
            "note": "Screenshot capture is functional",
        }
    except Exception as exc:
        return {
            "name": "screenshot_capture",
            "ok": False,
            "size": None,
            "mode": None,
            "error": f"{type(exc).__name__}: {exc}",
            "note": "Screenshot capture failed - check DISPLAY/X11/Wayland configuration",
        }


def _gui_session_hints() -> dict[str, Any]:
    """Collect GUI session hints for troubleshooting."""
    hints = {}
    
    # Display environment
    display = os.environ.get("DISPLAY")
    wayland = os.environ.get("WAYLAND_DISPLAY")
    session_type = os.environ.get("XDG_SESSION_TYPE")
    
    hints["display_env"] = display
    hints["wayland_display"] = wayland
    hints["xdg_session_type"] = session_type
    
    # Linux-specific checks
    is_linux = platform.system() == "Linux"
    hints["platform"] = platform.system()
    hints["is_linux"] = is_linux
    
    if is_linux:
        # Check for common GUI session indicators
        hints["has_display"] = bool(display)
        hints["has_wayland"] = bool(wayland)
        hints["gui_session_detected"] = bool(display or wayland)
        
        # X11-specific
        if display:
            hints["x11_display"] = display
            # Check for X authority
            xauth = os.environ.get("XAUTHORITY")
            hints["xauthority"] = xauth
            if xauth and os.path.exists(xauth):
                hints["xauthority_exists"] = True
            elif xauth:
                hints["xauthority_exists"] = False
                hints["xauthority_warning"] = "XAUTHORITY path does not exist"
        
        # Common issues
        if not display and not wayland:
            hints["warning"] = "No DISPLAY or WAYLAND_DISPLAY detected - screenshots will likely fail or produce blank images"
        
        # Check for xvfb (virtual framebuffer - common in headless/CI)
        xvfb_running = shutil.which("Xvfb") is not None
        hints["xvfb_available"] = xvfb_running
        
    return hints


def collect_diagnostics() -> dict[str, Any]:
    module_results = [_module_status(name) for name in ALL_MODULES]
    module_map = {item["name"]: item for item in module_results}
    core_modules_ok = all(module_map[name]["ok"] for name in CORE_MODULES)
    any_window_backend_ok = any(module_map[name]["ok"] for name in WINDOW_BACKENDS)

    preferred_backend = None
    if module_map.get("pywinctl", {}).get("ok"):
        preferred_backend = "pywinctl"
    elif module_map.get("pygetwindow", {}).get("ok"):
        preferred_backend = "pygetwindow"

    # Additional diagnostics
    tkinter_status = _tkinter_status()
    screenshot_test = _screenshot_test()
    gui_hints = _gui_session_hints()
    
    # Overall GUI readiness
    gui_ready = (
        core_modules_ok and 
        screenshot_test["ok"] and 
        bool(gui_hints.get("gui_session_detected") or gui_hints.get("has_display"))
    )

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
            "XAUTHORITY": os.environ.get("XAUTHORITY"),
        },
        "modules": module_results,
        "gui": {
            "tkinter": tkinter_status,
            "screenshot_test": screenshot_test,
            "session_hints": gui_hints,
        },
        "summary": {
            "core_modules_ok": core_modules_ok,
            "any_window_backend_ok": any_window_backend_ok,
            "environment_ready": core_modules_ok and any_window_backend_ok,
            "gui_ready": gui_ready,
            "gui_hint": bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")),
            "window_backend_preference": preferred_backend,
            "linux_window_note": (
                "pygetwindow may import but still not support Linux window enumeration; pywinctl is preferred on Linux. "
                "On headless systems, consider using Xvfb for virtual display."
                if platform.system() == "Linux"
                else None
            ),
        },
    }


def print_diagnostics_report() -> None:
    """Print a human-readable diagnostics report."""
    diag = collect_diagnostics()
    
    print("=" * 60)
    print("Advanced Vision - Environment Diagnostics Report")
    print("=" * 60)
    
    # Platform info
    print(f"\n📍 Platform: {diag['platform']['system']} ({diag['platform']['release']})")
    print(f"🐍 Python: {diag['python']['executable']}")
    
    # Environment
    print("\n🖥️  Environment:")
    env = diag['environment']
    print(f"   DISPLAY: {env.get('DISPLAY') or 'not set'}")
    print(f"   WAYLAND_DISPLAY: {env.get('WAYLAND_DISPLAY') or 'not set'}")
    print(f"   XDG_SESSION_TYPE: {env.get('XDG_SESSION_TYPE') or 'not set'}")
    
    # Core modules
    print("\n📦 Core Modules:")
    for mod in diag['modules']:
        status = "✅" if mod['ok'] else "❌"
        ver = f"v{mod['version']}" if mod['version'] else "version unknown"
        print(f"   {status} {mod['name']} ({ver})")
        if not mod['ok'] and mod['error']:
            print(f"      Error: {mod['error']}")
    
    # GUI diagnostics
    print("\n🎨 GUI Diagnostics:")
    tk = diag['gui']['tkinter']
    print(f"   {'✅' if tk['ok'] else '❌'} tkinter: {tk['version'] or 'not available'}")
    if tk.get('note') and not tk['ok']:
        print(f"      Note: {tk['note']}")
    
    scr = diag['gui']['screenshot_test']
    print(f"   {'✅' if scr['ok'] else '❌'} Screenshot capture")
    if scr['ok']:
        print(f"      Test capture size: {scr['size']}")
    else:
        print(f"      Error: {scr.get('error', 'Unknown')}")
        if scr.get('note'):
            print(f"      Note: {scr['note']}")
    
    # Summary
    print("\n📊 Summary:")
    summary = diag['summary']
    print(f"   Core modules: {'✅ OK' if summary['core_modules_ok'] else '❌ FAILED'}")
    print(f"   Window backend: {'✅ OK' if summary['any_window_backend_ok'] else '❌ FAILED'}")
    print(f"   GUI ready: {'✅ YES' if summary['gui_ready'] else '❌ NO'}")
    if summary.get('linux_window_note'):
        print(f"\n📝 Note: {summary['linux_window_note']}")
    
    print("\n" + "=" * 60)


def main() -> None:
    print_diagnostics_report()


if __name__ == "__main__":
    main()
