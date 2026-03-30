# Troubleshooting

## `.venv-computer-use` vs `.venv`

Use `.venv-computer-use` for local computer-use work.

Treat `.venv` as secondary unless you are intentionally working outside the GUI
and computer-use path.

If behavior differs between the two envs, trust `.venv-computer-use` for:

- `pyautogui`
- screenshot capture
- `pywinctl`
- `ultralytics`
- `cv2`

## `mcporter` issues

### `advanced-vision` missing from `mcporter list`

Check:

1. current working directory is `/home/netjer/Projects/AI Frame/optical.nerves`
2. [`config/mcporter.json`](/home/netjer/Projects/AI%20Frame/optical.nerves/config/mcporter.json) exists
3. `mcporter config doctor` passes

### `advanced-vision` unhealthy in `mcporter list`

Check:

1. `.venv-computer-use/bin/python` exists
2. `PYTHONPATH=.../advanced-vision/src` is present in the entry
3. direct Python diagnostics still pass

## Stale server entry point

The current `.venv-computer-use/bin/advanced-vision-server` console script is
stale and points at an older shebang path. Until it is rebuilt, prefer:

```bash
PYTHONPATH=/home/netjer/Projects/AI\ Frame/optical.nerves/advanced-vision/src \
/home/netjer/Projects/AI\ Frame/optical.nerves/advanced-vision/.venv-computer-use/bin/python \
-m advanced_vision.server
```

## Screenshot problems

### Blank or placeholder screenshots

Check:

- `DISPLAY`
- `WAYLAND_DISPLAY`
- `XDG_SESSION_TYPE`
- `python -m advanced_vision.diagnostics`

If diagnostics say GUI-ready is false, fix the desktop session before blaming
the MCP layer.

## Window listing problems

On Linux, `pywinctl` is preferred over `pygetwindow`.

If `list_windows` is empty or unstable:

1. run diagnostics
2. confirm GUI session is real
3. treat Wayland/back-end limits as a platform issue before rewriting code

## Safety rule

If screenshot capture works but input actions are uncertain, keep moving with:

1. `dry_run`
2. screenshots
3. verification

Do not escalate straight to live clicking just because the MCP server is reachable.
