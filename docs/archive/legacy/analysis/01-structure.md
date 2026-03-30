# Advanced-Vision Repository Structure Analysis

**Generated:** 2026-03-16  
**Repository:** ~/.openclaw/workspace/plane-a/projects/advanced-vision  
**Purpose:** Comprehensive module map for Phase 2 MCP integration planning

---

## 1. Directory Structure (tree -L 4)

```
~/.openclaw/workspace/plane-a/projects/advanced-vision/
├── .git/                              # Git repository metadata
│   ├── objects/                       # Git object storage
│   ├── refs/                          # Git references (branches, tags)
│   └── hooks/                         # Git hooks
├── .venv/                             # Main Python 3.14 virtual environment
│   ├── bin/                           # Virtualenv executables
│   ├── lib/python3.14/site-packages/  # Python packages
│   └── pyvenv.cfg                     # Virtualenv configuration
├── .venv-computer-use/                # Dedicated Python 3.11 environment for GUI
│   ├── bin/                           # Virtualenv executables
│   ├── lib/python3.11/site-packages/  # Python packages
│   └── pyvenv.cfg                     # Virtualenv configuration
├── analysis/                          # Analysis output directory (empty, for swarm)
├── artifacts/                         # Runtime artifacts storage
│   ├── .gitkeep                       # Preserve directory in git
│   ├── logs/                          # JSONL log files
│   └── screens/                       # Screenshot PNG files
├── brain/                             # Engineering notebook for development
│   ├── README.md                      # Brain folder overview
│   ├── PHASES.md                      # Implementation roadmap
│   ├── TASKS.md                       # Actionable checklist
│   ├── ISSUES.md                      # Discovered problems and blockers
│   ├── FIXES.md                       # Changes made
│   └── WORKLOG.md                     # Chronological notes
├── configs/                           # Configuration templates
│   └── settings.example.yaml          # Example settings file
├── src/                               # Source code
│   ├── advanced_vision/               # Main Python package
│   │   ├── __init__.py                # Package initialization
│   │   ├── __pycache__/               # Compiled Python bytecode
│   │   ├── config.py                  # Settings and configuration
│   │   ├── diagnostics.py             # Environment diagnostics
│   │   ├── flow.py                    # Screenshot->analyze->act->verify flow
│   │   ├── logging_utils.py           # JSONL logging utilities
│   │   ├── schemas.py                 # Pydantic data models
│   │   ├── server.py                  # MCP server entry point
│   │   ├── vision_adapter.py          # Vision analysis adapter (stub)
│   │   └── tools/                     # Tool implementations
│   │       ├── __init__.py            # Tools package init
│   │       ├── __pycache__/           # Compiled bytecode
│   │       ├── input.py               # Mouse/keyboard input tools
│   │       ├── screen.py              # Screenshot capture tools
│   │       ├── verify.py              # Screen change verification
│   │       └── windows.py             # Window management tools
│   └── advanced_vision.egg-info/      # Package metadata
│       ├── PKG-INFO                   # Package information
│       ├── SOURCES.txt                # Source file list
│       ├── dependency_links.txt       # Dependency links
│       ├── entry_points.txt           # Console scripts
│       ├── requires.txt               # Dependencies
│       └── top_level.txt              # Top-level packages
├── tests/                             # Test suite
│   ├── __pycache__/                   # Compiled bytecode
│   ├── test_schemas.py                # Schema instantiation tests
│   └── test_smoke.py                  # Smoke/integration tests
└── .pytest_cache/                     # Pytest cache directory
    └── v/cache/
```

---

## 2. Python Source Files

### Core Package (`src/advanced_vision/`)

| File | Lines | Purpose |
|------|-------|---------|
| `__init__.py` | ~10 | Package initialization, exports main modules (config, flow, schemas, server, vision_adapter) |
| `config.py` | ~25 | Settings management with Pydantic; defines artifact directories (screens, logs) |
| `diagnostics.py` | ~75 | Environment diagnostics - checks Python version, platform, required modules (PIL, pydantic, mcp, pyautogui, pygetwindow), GUI environment variables (DISPLAY, WAYLAND_DISPLAY) |
| `flow.py` | ~50 | Reusable workflow: screenshot → analyze → optional act → verify; `run_single_cycle()` helper |
| `logging_utils.py` | ~25 | JSONL artifact logging with UTC timestamps; `append_jsonl()` for structured logging |
| `schemas.py` | ~35 | Pydantic data models: ScreenshotArtifact, WindowInfo, ActionProposal, ActionResult, VerificationResult |
| `server.py` | ~80 | MCP server using FastMCP; exposes 10 tools as MCP endpoints (screenshots, input, verification, analysis) |
| `vision_adapter.py` | ~35 | Vision adapter abstraction; includes StubVisionAdapter that returns noop proposals (placeholder for real vision model) |

### Tools Submodule (`src/advanced_vision/tools/`)

| File | Lines | Purpose |
|------|-------|---------|
| `__init__.py` | ~3 | Tools package marker (empty docstring) |
| `screen.py` | ~65 | Screenshot capture tools: `screenshot_full()`, `screenshot_active_window()`; uses PIL.ImageGrab with fallbacks |
| `input.py` | ~75 | Mouse/keyboard control: `move_mouse()`, `click()`, `type_text()`, `press_keys()`, `scroll()`; wraps pyautogui |
| `verify.py` | ~70 | Screen change verification: `verify_screen_change()`, `verify_screen_change_between()`; uses PIL image comparison |
| `windows.py` | ~35 | Window listing: `list_windows()`; uses pygetwindow with graceful fallback |

### Test Files (`tests/`)

| File | Lines | Purpose |
|------|-------|---------|
| `test_schemas.py` | ~25 | Unit tests for schema instantiation (ScreenshotArtifact, WindowInfo, ActionProposal, ActionResult, VerificationResult) |
| `test_smoke.py` | ~60 | Integration/smoke tests: screenshot capture, flow execution, verification, vision adapter stub behavior |

---

## 3. Configuration Files

### Build & Package Configuration

| File | Purpose |
|------|---------|
| `pyproject.toml` | Main Python project configuration. Defines build system (setuptools), dependencies (pydantic, mcp, Pillow, pyautogui, pygetwindow), optional dev dependencies (pytest), console scripts (advanced-vision-server, advanced-vision-diagnostics), and pytest configuration |
| `src/advanced_vision.egg-info/PKG-INFO` | Generated package metadata (duplicate of README) |
| `src/advanced_vision.egg-info/SOURCES.txt` | List of source files in distribution |
| `src/advanced_vision.egg-info/requires.txt` | Resolved dependencies |
| `src/advanced_vision.egg-info/entry_points.txt` | Console script definitions |
| `src/advanced_vision.egg-info/dependency_links.txt` | External dependency links (empty) |
| `src/advanced_vision.egg-info/top_level.txt` | Top-level package names |

### Runtime Configuration

| File | Purpose |
|------|---------|
| `configs/settings.example.yaml` | Example configuration file showing artifacts_dir, screens_dir_name, logs_dir_name settings |

### Virtual Environment Configs

| File | Purpose |
|------|---------|
| `.venv/pyvenv.cfg` | Main virtual environment configuration (Python 3.14) |
| `.venv/.gitignore` | Gitignore for venv (ignores entire directory) |
| `.venv-computer-use/pyvenv.cfg` | Dedicated GUI environment configuration (Python 3.11) |

### Git Configuration

| File | Purpose |
|------|---------|
| `.gitignore` | Project gitignore: excludes `__pycache__/`, `*.py[cod]`, `.venv/`, `.pytest_cache/`, screenshots, logs, `.venv-computer-use/` |

---

## 4. Documentation Files

### Primary Documentation (Root Level)

| File | Size | Purpose |
|------|------|---------|
| `README.md` | ~2.6KB | Main project documentation: overview, scope, installation, usage examples, repository layout |
| `ARCHITECTURE.md` | ~15KB | Comprehensive architecture document: three-plane architecture (control/capability/data), trust boundaries, service boundaries, data protection strategy, approval model (green/yellow/red actions), evolution roadmap through 6 phases |
| `SERVICE_CONTRACTS.md` | ~13KB | Service contract definitions: common envelope format, advanced-vision contract, GitHub contract, policy broker contract, secrets broker contract, workspace contract, vision adapter contract |
| `SKILL.md` | ~2.8KB | Skill documentation for OpenClaw integration: status, quick start, planned tools, architecture notes, work log |
| `AGENT_SWARM_CONTRACT.md` | ~3KB | Contract for multi-agent analysis: defines 7 sub-agent tasks (structure, code, config, docs, MCP patterns, gaps, plan synthesis) and deliverable format |
| `COMPUTER_USE_ENV.md` | ~2.3KB | Environment setup documentation: Python 3.11 dedicated environment status, installed packages, validation commands, trust boundaries |

### Engineering Notebook (`brain/`)

| File | Size | Purpose |
|------|------|---------|
| `brain/README.md` | ~1KB | Overview of brain folder purpose: track what's true, broken, fixed, blocked |
| `brain/PHASES.md` | ~3KB | 6-phase implementation roadmap: Phase 0 (reality check) through Phase 6 (GitHub + MCP orchestration) |
| `brain/TASKS.md` | ~1.5KB | Actionable checklist: immediate tasks, runtime validation, governance improvements, vision improvements |
| `brain/ISSUES.md` | ~4KB | Discovered issues: environment readiness, README assumptions, missing diagnostics, stub adapter, GUI backend limitations, retention policy, policy envelope |
| `brain/FIXES.md` | ~2KB | Changes made: architecture docs added, brain folder added, diagnostics module added, README updates |
| `brain/WORKLOG.md` | ~2KB | Chronological development notes from 2026-03-16 |

### Cache/Generated Documentation

| File | Purpose |
|------|---------|
| `.pytest_cache/README.md` | Pytest cache directory readme |

---

## 5. Key Dependencies

### Runtime Dependencies (from pyproject.toml)

| Package | Version | Purpose |
|---------|---------|---------|
| pydantic | >=2.7.0 | Data validation and serialization |
| mcp | >=1.0.0 | Model Context Protocol server framework |
| Pillow | >=10.0.0 | Image processing (PIL) |
| pyautogui | >=0.9.54 | Cross-platform GUI automation |
| pygetwindow | >=0.0.9 | Window management |

### Development Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| pytest | >=8.0.0 | Testing framework |

### System Dependencies (Linux)

| Package | Purpose |
|---------|---------|
| python3.11-tk | Tkinter for MouseInfo/pyautogui |
| python3-dev | Python development headers |
| scrot | Screenshot utility for Linux |

---

## 6. Console Scripts (Entry Points)

| Script | Module:Function | Purpose |
|--------|-----------------|---------|
| `advanced-vision-server` | `advanced_vision.server:run` | Start the MCP server |
| `advanced-vision-diagnostics` | `advanced_vision.diagnostics:main` | Run environment diagnostics |

---

## 7. MCP Tools Exposed

The MCP server (`server.py`) exposes these 10 tools:

| Tool Name | Function | Category |
|-----------|----------|----------|
| `screenshot_full` | Capture entire desktop | Screen |
| `screenshot_active_window` | Capture active window (with fallback) | Screen |
| `list_windows` | List visible top-level windows | Window |
| `move_mouse` | Move mouse to coordinates | Input |
| `click` | Mouse click (left/right button) | Input |
| `type_text` | Type text string | Input |
| `press_keys` | Press keys or combinations | Input |
| `scroll` | Scroll vertically/horizontally | Input |
| `verify_screen_change` | Compare screenshots for visual change | Verification |
| `analyze_screenshot` | Analyze screenshot via vision adapter | Analysis |

---

## 8. Schema Summary

### Data Models (from `schemas.py`)

| Model | Fields | Purpose |
|-------|--------|---------|
| `ScreenshotArtifact` | path, width, height, timestamp | Screenshot result metadata |
| `WindowInfo` | title, app_name, is_active | Window information |
| `ActionProposal` | action_type, x, y, text, keys, confidence, rationale | Proposed UI action from vision analysis |
| `ActionResult` | ok, action_type, message, artifact_path | Action execution result |
| `VerificationResult` | changed, similarity, message | Screen change verification result |

---

## 9. Artifact Storage Structure

```
artifacts/
├── screens/           # PNG screenshots with timestamps
│   └── full_2026-03-16T12-00-00.png
└── logs/              # JSONL structured logs
    ├── screenshots.jsonl
    ├── actions.jsonl
    └── verification.jsonl
```

---

## 10. Current Status Summary

**Working:**
- ✅ MCP server structure implemented
- ✅ Screenshot capture (full and active window)
- ✅ Window listing (best-effort)
- ✅ Screen change verification
- ✅ All tests passing (6 passed)
- ✅ Pydantic schemas validated
- ✅ Artifact logging functional

**Partial/Blocked:**
- ⚠️ Input tools (mouse/keyboard) blocked on tkinter availability in current environment
- ⚠️ Vision adapter is stubbed (returns noop proposals)
- ⚠️ `list_windows()` returns 0 windows on headless/minimal environments

**Not Yet Implemented:**
- ❌ Real vision model integration
- ❌ Policy envelope support in tool interfaces
- ❌ Artifact retention/cleanup policies
- ❌ Dry-run mode for action tools
- ❌ GitHub service integration

---

*End of Structure Analysis*
