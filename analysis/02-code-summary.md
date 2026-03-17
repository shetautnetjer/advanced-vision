# Advanced Vision - Code Summary

## Overview
This document provides a comprehensive summary of all Python source code in the advanced-vision repository. The project is a minimal MCP (Model Context Protocol) based local computer-use capability layer that provides screenshot capture, vision-based analysis, and GUI automation tools.

---

## Project Structure

```
src/advanced_vision/
├── __init__.py          # Package exports
├── config.py            # Configuration management
├── diagnostics.py       # Environment diagnostics
├── flow.py              # Main workflow cycle
├── logging_utils.py     # JSONL logging utilities
├── schemas.py           # Pydantic data models
├── server.py            # MCP server implementation
├── vision_adapter.py    # Vision analysis abstraction
└── tools/
    ├── __init__.py      # Tools package marker
    ├── input.py         # Mouse/keyboard control
    ├── screen.py        # Screenshot capture
    ├── verify.py        # Screen change verification
    └── windows.py       # Window listing

tests/
├── test_schemas.py      # Schema validation tests
└── test_smoke.py        # Integration smoke tests
```

---

## Configuration (config.py)

### Class: `Settings` (Pydantic BaseModel)
Configuration management using Pydantic models with computed properties.

**Attributes:**
- `artifacts_dir: Path` - Base directory for artifacts (default: "artifacts")
- `screens_dir_name: str` - Screenshot subdirectory name (default: "screens")
- `logs_dir_name: str` - Logs subdirectory name (default: "logs")

**Properties:**
- `screens_dir: Path` - Computed path to screenshots directory
- `logs_dir: Path` - Computed path to logs directory

### Function: `get_settings() -> Settings`
Factory function that:
- Creates Settings instance
- Ensures directories exist (mkdir with parents=True, exist_ok=True)
- Returns configured settings

---

## Diagnostics (diagnostics.py)

### Module Constants
```python
REQUIRED_MODULES = ["PIL", "pydantic", "mcp", "pyautogui", "pygetwindow"]
```

### Function: `_module_status(name: str) -> dict[str, Any]`
Attempts to import a module and returns status information.

**Returns:**
- `name`: Module name
- `ok`: Boolean indicating successful import
- `version`: Module version if available
- `error`: Error message if import failed

### Function: `collect_diagnostics() -> dict[str, Any]`
Comprehensive environment diagnostics collector.

**Collects:**
- Python info: executable path, version, python/python3/pip availability
- Platform info: system, release, full platform string
- Environment: DISPLAY, WAYLAND_DISPLAY, XDG_SESSION_TYPE
- Module status for all REQUIRED_MODULES
- Summary: all_required_modules_ok, gui_hint (based on DISPLAY/WAYLAND_DISPLAY)

### Function: `main() -> None`
Entry point that prints JSON-formatted diagnostics.

**CLI Entry Point:** `advanced-vision-diagnostics`

---

## Schemas (schemas.py)

All data models using Pydantic BaseModel.

### Class: `ScreenshotArtifact`
Represents a captured screenshot.

**Fields:**
- `path: str` - File path to screenshot
- `width: int` - Image width in pixels
- `height: int` - Image height in pixels
- `timestamp: str` - ISO timestamp

### Class: `WindowInfo`
Represents a window on the desktop.

**Fields:**
- `title: str` - Window title
- `app_name: str | None` - Application name (optional)
- `is_active: bool | None` - Whether window is active (optional)

### Class: `ActionProposal`
Represents a proposed GUI action from vision analysis.

**Fields:**
- `action_type: str` - Type of action (move_mouse, click, type_text, press_keys, scroll, noop)
- `x: int | None` - X coordinate (for mouse actions)
- `y: int | None` - Y coordinate (for mouse actions)
- `text: str | None` - Text to type (for type_text)
- `keys: list[str] | None` - Keys to press (for press_keys)
- `confidence: float | None` - Confidence score (optional)
- `rationale: str | None` - Explanation for the action (optional)

### Class: `ActionResult`
Result of executing an action.

**Fields:**
- `ok: bool` - Success indicator
- `action_type: str` - Type of action performed
- `message: str` - Human-readable result message
- `artifact_path: str | None` - Path to any output artifact (optional)

### Class: `VerificationResult`
Result of screen change verification.

**Fields:**
- `changed: bool` - Whether screen changed significantly
- `similarity: float | None` - Similarity score (0-1, higher is more similar)
- `message: str` - Detailed verification message

---

## Logging Utilities (logging_utils.py)

### Function: `utc_now_iso() -> str`
Returns current UTC time in ISO format.

### Function: `append_jsonl(log_name: str, payload: dict[str, Any]) -> Path`
Appends a JSON line to a log file.

**Behavior:**
- Creates log file in `logs_dir` with `.jsonl` extension
- Prepends timestamp to payload
- Opens in append mode with UTF-8 encoding
- Returns path to log file

---

## Vision Adapter (vision_adapter.py)

### Class: `VisionAdapter` (Abstract)
Base interface for screenshot analysis.

**Method:**
```python
def analyze_screenshot(self, image_path: str, task: str) -> ActionProposal
```

### Class: `StubVisionAdapter` (VisionAdapter)
Default no-op implementation that returns conservative noop proposals.

**Implementation:**
- Returns `ActionProposal` with `action_type="noop"`
- Low confidence (0.1)
- Rationale explains this is a stub and suggests integrating a real vision model

### Function: `analyze_screenshot(image_path: str, task: str) -> ActionProposal`
Convenience function using the default stub adapter.

**TODO/Future Work:**
- Integrate a real vision model (Kimi or similar)
- Add model-backed implementation

---

## Tools: Input (tools/input.py)

Mouse and keyboard automation using pyautogui.

### Function: `_get_pyautogui()`
Internal helper that imports pyautogui with FAILSAFE enabled.

### Function: `move_mouse(x: int, y: int) -> ActionResult`
Moves mouse cursor to coordinates.
- Logs to `actions.jsonl`
- Returns ActionResult with success/failure message

### Function: `click(x: int, y: int, button: str = "left") -> ActionResult`
Clicks at specified coordinates.
- Supports left/right/middle buttons
- Logs to `actions.jsonl`

### Function: `type_text(text: str) -> ActionResult`
Types text using pyautogui.write().
- Logs to `actions.jsonl` with text redacted (only length stored)

### Function: `press_keys(keys: list[str]) -> ActionResult`
Presses keyboard keys.
- Single key: uses `pag.press()`
- Multiple keys: uses `pag.hotkey()` for combinations
- Logs pressed keys to `actions.jsonl`

### Function: `scroll(vertical: int = 0, horizontal: int = 0) -> ActionResult`
Scrolls the mouse wheel.
- Supports vertical and horizontal scrolling
- Uses `hscroll` for horizontal if available
- Logs scroll amounts to `actions.jsonl`

---

## Tools: Screen (tools/screen.py)

Screenshot capture using PIL/Pillow.

### Function: `_save_image(image: Image.Image, prefix: str) -> ScreenshotArtifact`
Internal helper to save image and create artifact.

**Behavior:**
- Generates timestamped filename with colon-replaced timestamp
- Saves to `screens_dir`
- Logs to `screenshots.jsonl`
- Returns ScreenshotArtifact

### Function: `_safe_grab(bbox=None, retry_fullscreen=False) -> Image.Image`
Robust screenshot capture with fallback.

**Features:**
- Attempts ImageGrab.grab() with optional bounding box
- Retries fullscreen if bbox fails (when retry_fullscreen=True)
- Fallback for headless: returns blank 1280x720 RGB image

### Function: `screenshot_full() -> ScreenshotArtifact`
Captures full desktop screenshot.

### Function: `_active_window_bbox() -> tuple[int, int, int, int] | None`
Returns bounding box of active window using pygetwindow.

**Returns:** (left, top, right, bottom) or None if unavailable

### Function: `screenshot_active_window() -> ScreenshotArtifact`
Captures active window or falls back to full screenshot.

---

## Tools: Verify (tools/verify.py)

Screen change detection using image comparison.

### Function: `_compare_images(previous_path, current_path, threshold) -> VerificationResult`
Internal comparison logic using PIL.

**Algorithm:**
1. Opens both images and converts to RGB
2. Resizes current to match previous if sizes differ
3. Computes pixel-wise difference using ImageChops.difference()
4. Calculates global similarity: `1 - (mean_diff / 255)`
5. Calculates localized change ratio:
   - Thresholds pixel luminance difference at 16
   - Counts changed pixels
   - Computes ratio of changed pixels
6. Determines change: `similarity < threshold OR changed_ratio >= 0.0005`

**Returns:** VerificationResult with changed flag, similarity score, and detailed message

### Function: `verify_screen_change(previous_screenshot_path: str, threshold: float = 0.99) -> VerificationResult`
Takes new screenshot and compares with previous.

**Flow:**
1. Captures new screenshot
2. Compares with previous
3. Logs to `verification.jsonl`
4. Returns result

### Function: `verify_screen_change_between(previous_path, current_path, threshold=0.99) -> VerificationResult`
Compares two existing screenshots without capturing new one.

---

## Tools: Windows (tools/windows.py)

Window enumeration using pygetwindow.

### Function: `list_windows() -> list[WindowInfo]`
Returns list of visible top-level windows.

**Implementation:**
- Uses pygetwindow to get all windows
- Filters out windows with empty titles
- Marks active window with `is_active=True`
- Best-effort fallback: returns empty list on exception
- Logs count to `actions.jsonl`

---

## Flow (flow.py)

### Function: `_execute_proposed_action(proposal: ActionProposal) -> dict[str, Any]`
Executes an ActionProposal by dispatching to appropriate tool.

**Dispatch Table:**
| action_type | Requirements | Tool Called |
|-------------|--------------|-------------|
| move_mouse | x, y | move_mouse(x, y) |
| click | x, y | click(x, y) |
| type_text | text | type_text(text) |
| press_keys | keys | press_keys(keys) |
| scroll | - | scroll(vertical=y or 0, horizontal=x or 0) |
| default | - | noop response |

### Function: `run_single_cycle(task: str, execute: bool = False) -> dict[str, Any]`
Main workflow for screenshot → analyze → act → verify.

**Flow:**
1. Capture `before` screenshot
2. Analyze screenshot with vision adapter for given task
3. If `execute=True`: execute proposed action, else skip
4. Capture `after` screenshot
5. Verify screen change between before/after
6. Return complete cycle results

**Returns:**
```python
{
    "before": ScreenshotArtifact dict,
    "proposal": ActionProposal dict,
    "action_result": ActionResult dict or skip message,
    "after": ScreenshotArtifact dict,
    "verification": VerificationResult dict
}
```

---

## Server (server.py)

MCP (Model Context Protocol) server exposing tools.

### Conditional Import Pattern
```python
try:
    from mcp.server.fastmcp import FastMCP
except Exception as exc:
    FastMCP = None
    _IMPORT_ERROR = exc
```

### MCP Tools Exposed

| Tool Name | Function | Parameters |
|-----------|----------|------------|
| screenshot_full | screenshot_full_mcp | none |
| screenshot_active_window | screenshot_active_window_mcp | none |
| list_windows | list_windows_mcp | none |
| move_mouse | move_mouse_mcp | x: int, y: int |
| click | click_mcp | x: int, y: int, button: str = "left" |
| type_text | type_text_mcp | text: str |
| press_keys | press_keys_mcp | keys: list[str] |
| scroll | scroll_mcp | vertical: int = 0, horizontal: int = 0 |
| verify_screen_change | verify_screen_change_mcp | previous_screenshot_path: str, threshold: float = 0.99 |
| analyze_screenshot | analyze_screenshot_mcp | screenshot_path: str, task: str |

### Function: `run() -> None`
Entry point that starts the MCP server.

**Raises:** RuntimeError if MCP dependency unavailable

**CLI Entry Point:** `advanced-vision-server`

---

## Tests

### test_schemas.py

**Function: `test_schema_instantiation()`**
Validates all schema classes can be instantiated with minimal data.
- Tests ScreenshotArtifact, WindowInfo, ActionProposal, ActionResult, VerificationResult
- Verifies field access works correctly

### test_smoke.py

**Function: `test_smoke_capture_and_analyze()`**
- Captures screenshot and verifies file exists
- Analyzes screenshot and expects noop action (stub adapter)

**Function: `test_smoke_flow()`**
- Runs `run_single_cycle()` with execute=False
- Verifies result contains expected keys

**Function: `test_verification_executes()`**
- Takes screenshot, runs verification
- Checks similarity is None or in valid range [0,1]

**Function: `test_verification_between_executes()`**
- Takes two screenshots, compares them
- Validates similarity range

**Function: `test_verification_detects_localized_change(tmp_path: Path)`**
- Creates two synthetic images: white canvas and white canvas with small black rectangle
- Verifies change detection works for small localized changes
- Uses high threshold (0.9999) to test sensitivity

---

## Package Exports (__init__.py)

```python
__all__ = [
    "config",
    "flow",
    "schemas",
    "server",
    "vision_adapter",
]
```

---

## Entry Points (pyproject.toml)

```toml
[project.scripts]
advanced-vision-server = "advanced_vision.server:run"
advanced-vision-diagnostics = "advanced_vision.diagnostics:main"
```

---

## Dependencies (pyproject.toml)

**Required:**
- pydantic>=2.7.0
- mcp>=1.0.0
- Pillow>=10.0.0
- pyautogui>=0.9.54
- pygetwindow>=0.0.9

**Development:**
- pytest>=8.0.0

---

## Key Logic and Algorithms

### Image Comparison Algorithm (verify.py)
The verification system uses a two-pronged approach:

1. **Global Similarity**: Mean pixel difference across entire image
   - `similarity = 1 - (mean_diff / 255.0)`
   - Range: 0.0 to 1.0

2. **Localized Change Detection**: Per-pixel threshold counting
   - Pixels with diff >= 16 considered "changed"
   - Changed ratio = changed_pixels / total_pixels
   - Trigger: changed_ratio >= 0.0005 (0.05% of pixels)

**Change Detection Logic:**
```python
changed = similarity < threshold or changed_ratio >= 0.0005
```

### Fail-Safe Patterns
- pyautogui.FAILSAFE = True (corner escape)
- Headless fallback: returns blank image instead of crashing
- Exception handling: logs failures, returns empty lists/fallbacks
- JSONL logging: append-only, never blocks main flow

### Asynchronous Safety
- All tools are synchronous/blocking
- Designed for single-threaded use
- Logging is synchronous file append

---

## TODO Comments and Unfinished Implementations

1. **Vision Adapter** (`vision_adapter.py`):
   - Current: StubVisionAdapter returns noop with explanation
   - TODO: Integrate real vision model (Kimi suggested)
   - Design: Adapter pattern allows swapping implementations

2. **WindowInfo.app_name** (`schemas.py`):
   - Field exists but is not populated by `list_windows()`
   - Currently always None

3. **Horizontal Scroll** (`tools/input.py`):
   - Conditional: `if horizontal and hasattr(pag, "hscroll")`
   - Not all platforms support horizontal scroll

4. **Image Comparison Optimization** (`tools/verify.py`):
   - Resizes images to match if sizes differ
   - Could be optimized to compare at smaller resolution first

---

## Architecture Notes

- **Separation of Concerns**: Tools are independent, flow orchestrates
- **Schema-First**: All data structures use Pydantic for validation
- **Logging**: Everything is logged to JSONL for audit/debugging
- **MCP Native**: Designed as MCP tool server from ground up
- **Headless Safe**: Graceful degradation without GUI
- **Extensible**: Vision adapter pattern allows model swapping
