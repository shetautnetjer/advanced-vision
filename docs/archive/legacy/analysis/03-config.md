# Configuration Analysis Report

**Project:** advanced-vision  
**Analysis Date:** 2026-03-16  
**Analyzed By:** Config Analyzer Subagent

---

## 1. pyproject.toml

### Build System
| Setting | Value |
|---------|-------|
| Build Backend | `setuptools.build_meta` |
| Requires | `setuptools>=68`, `wheel` |

### Project Metadata
| Setting | Value |
|---------|-------|
| Name | `advanced-vision` |
| Version | `0.1.0` |
| Description | Standalone minimal MCP-based local computer-use capability layer |
| Python Requires | `>=3.10` |
| README | `README.md` |

### Core Dependencies
| Package | Version Constraint |
|---------|-------------------|
| pydantic | `>=2.7.0` |
| mcp | `>=1.0.0` |
| Pillow | `>=10.0.0` |
| pyautogui | `>=0.9.54` |
| pygetwindow | `>=0.0.9` |

### Optional Dependencies (dev)
| Package | Version Constraint |
|---------|-------------------|
| pytest | `>=8.0.0` |

### Entry Points (Console Scripts)
| Command | Module Path | Purpose |
|---------|-------------|---------|
| `advanced-vision-server` | `advanced_vision.server:run` | MCP server runner |
| `advanced-vision-diagnostics` | `advanced_vision.diagnostics:main` | Environment diagnostics tool |

### Setuptools Configuration
| Setting | Value |
|---------|-------|
| Package Directory | `src` |
| Package Discovery | `where = ["src"]` |

### pytest Configuration
| Setting | Value |
|---------|-------|
| Python Path | `["src"]` |

---

## 2. requirements.txt / setup.py / setup.cfg

**Status:** Not present. The project uses modern `pyproject.toml` exclusively (PEP 621).

No `requirements.txt`, `setup.py`, or `setup.cfg` files were found in the repository.

---

## 3. Application Configuration

### Settings Schema (YAML Config)
**File:** `configs/settings.example.yaml`

```yaml
artifacts_dir: artifacts
screens_dir_name: screens
logs_dir_name: logs
```

### Configuration Model (Python)
**File:** `src/advanced_vision/config.py`

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `artifacts_dir` | Path | `artifacts` | Base directory for all artifacts |
| `screens_dir_name` | str | `screens` | Subdirectory for screenshots |
| `logs_dir_name` | str | `logs` | Subdirectory for log files |

**Computed Properties:**
- `screens_dir` → `artifacts_dir / screens_dir_name`
- `logs_dir` → `artifacts_dir / logs_dir_name`

---

## 4. MCP Configuration

### MCP Server Details
| Setting | Value |
|---------|-------|
| Server Name | `advanced-vision` |
| Framework | `mcp.server.fastmcp.FastMCP` |
| Import Guard | Graceful fallback if MCP unavailable |

### MCP Tools Exposed
| Tool Name | Function | Description |
|-----------|----------|-------------|
| `screenshot_full` | `screenshot_full_mcp()` | Capture full screen screenshot |
| `screenshot_active_window` | `screenshot_active_window_mcp()` | Capture active window screenshot |
| `list_windows` | `list_windows_mcp()` | List available windows |
| `move_mouse` | `move_mouse_mcp(x, y)` | Move mouse cursor |
| `click` | `click_mcp(x, y, button)` | Mouse click at coordinates |
| `type_text` | `type_text_mcp(text)` | Type text input |
| `press_keys` | `press_keys_mcp(keys)` | Press key combinations |
| `scroll` | `scroll_mcp(vertical, horizontal)` | Scroll in directions |
| `verify_screen_change` | `verify_screen_change_mcp(path, threshold)` | Verify visual changes |
| `analyze_screenshot` | `analyze_screenshot_mcp(path, task)` | Analyze screenshot content |

### MCP Installation
The MCP dependency is specified in `pyproject.toml`:
```toml
dependencies = [
  "mcp>=1.0.0",
  ...
]
```

---

## 5. Other Configuration Files

### .gitignore
**Patterns:**
- `__pycache__/` - Python cache
- `*.py[cod]` - Compiled Python
- `.venv/` - Virtual environment
- `.pytest_cache/` - pytest cache
- `artifacts/screens/*.png` - Generated screenshots
- `artifacts/logs/*.jsonl` - Generated logs
- `.venv-computer-use/` - Secondary virtual environment

### work_log_*.json
**Purpose:** Work session logging (auto-generated)

---

## 6. Build/Installation Requirements

### Python Version
- **Minimum:** Python 3.10+

### Installation Commands
```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install with development dependencies
python3 -m pip install -e .[dev]

# Or install without dev dependencies
python3 -m pip install -e .
```

### Package Installation Location
- Installed as editable package (`-e .`)
- Package location: `src/advanced_vision/`
- Egg-info: `src/advanced_vision.egg-info/`

---

## 7. OpenClaw Integration Assessment

### ✅ Available Entry Points
| Command | Status | Notes |
|---------|--------|-------|
| `advanced-vision-server` | ✅ Ready | MCP server with stdio/SSE transport |
| `advanced-vision-diagnostics` | ✅ Ready | Diagnostic check tool |

### ✅ Configuration Status
| Item | Status | Notes |
|------|--------|-------|
| pyproject.toml | ✅ Present | Modern Python packaging |
| MCP Tools | ✅ Defined | 10 tools exposed via FastMCP |
| Settings Schema | ✅ Present | YAML + Pydantic models |

### ⚠️ Missing/Recommended for OpenClaw
| Item | Status | Recommendation |
|------|--------|----------------|
| MCP Server Config File | ❌ Missing | Consider `mcp.json` or `mcp.yaml` for mcporter integration |
| Environment Variables | ⚠️ Partial | Only `DISPLAY`, `WAYLAND_DISPLAY`, `XDG_SESSION_TYPE` checked |
| .env.example | ❌ Missing | Add template for API keys (future vision adapter) |
| OpenClaw Skill Manifest | ❌ Missing | Consider creating `SKILL.md` for mcporter |

### 🔧 OpenClaw Integration Notes

1. **MCP Server Mode:** The server uses FastMCP which supports stdio (default) and SSE transports.
   - For OpenClaw mcporter integration, add to `~/.openclaw/mcp.json`:
   ```json
   {
     "servers": {
       "advanced-vision": {
         "type": "stdio",
         "command": "advanced-vision-server"
       }
     }
   }
   ```

2. **GUI Environment:** This tool requires GUI access (X11/Wayland).
   - Ensure `DISPLAY` or `WAYLAND_DISPLAY` env vars are set
   - May not work in headless/container environments without virtual display

3. **Python Path:** Package uses `src/` layout - ensure PYTHONPATH includes `src/` when running directly.

---

## 8. Dependency Summary

### Production Dependencies (5)
1. **pydantic** >=2.7.0 - Data validation and serialization
2. **mcp** >=1.0.0 - Model Context Protocol server framework
3. **Pillow** >=10.0.0 - Image processing for screenshots
4. **pyautogui** >=0.9.54 - GUI automation (mouse, keyboard)
5. **pygetwindow** >=0.0.9 - Window management

### Development Dependencies (1)
1. **pytest** >=8.0.0 - Testing framework

### System Dependencies
- Python 3.10+
- GUI backend (X11 on Linux, native on macOS/Windows)
- Optional: Virtual display for headless environments

---

## 9. Directory Structure

```
advanced-vision/
├── pyproject.toml              # Main project config ✅
├── configs/
│   └── settings.example.yaml   # Config template ✅
├── src/
│   └── advanced_vision/
│       ├── __init__.py
│       ├── server.py           # MCP server entry ✅
│       ├── config.py           # Settings model ✅
│       ├── diagnostics.py      # Diagnostics entry ✅
│       └── ...
├── tests/                      # Test suite
├── artifacts/                  # Generated artifacts
│   ├── screens/               # Screenshots
│   └── logs/                  # JSONL logs
└── analysis/                   # This analysis
    └── 03-config.md           # ✅ This file
```

---

## Summary

The `advanced-vision` project uses modern Python packaging with `pyproject.toml`. It exposes an MCP server with 10 tools for computer-use automation (screenshots, input control, window management). The project is ready for OpenClaw integration via mcporter with the addition of an MCP server configuration file.

**Key Integration Points:**
- Entry point: `advanced-vision-server` command
- Transport: stdio (default) or SSE
- Config: Optional YAML in `configs/settings.yaml`
- Requirements: Python 3.10+, GUI environment
