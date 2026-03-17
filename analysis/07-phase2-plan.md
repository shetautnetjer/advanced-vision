# Advanced Vision - Phase 2 Implementation Roadmap

**Generated:** 2026-03-16  
**Synthesis of:** 01-structure.md, 02-code-summary.md, 03-config.md, 04-docs.md, 06-gaps.md  
**Purpose:** Comprehensive Phase 2 implementation plan with MCP server integration

---

## Overview

**Phase 2 Goal:** Basic runtime validation with full OpenClaw MCP integration  
**Current State:** MCP server exists, screenshots work, input blocked, no OpenClaw config  
**Target State:** Fully functional MCP server registered with OpenClaw, input tools working, governance foundation in place

---

## Phase 2 Deliverables

1. ✅ Working input tools (mouse/keyboard)
2. ✅ OpenClaw MCP server configuration
3. ✅ Policy envelope foundation
4. ✅ Artifact governance (retention, classification)
5. ✅ Enhanced logging with provenance
6. ✅ Comprehensive test coverage
7. ✅ Documentation updates

---

## Implementation Tasks

### Task 1: Fix Input Tools Blocker (P0 - Blocking)
**Estimated Time:** 2-4 hours  
**Depends On:** None  
**Blocks:** Tasks 4, 5, 6, 7

#### 1.1 Install System Dependencies
```bash
# Check current Python environment
which python3
python3 --version

# Install tkinter and dependencies
sudo apt-get update
sudo apt-get install -y python3-tk python3-dev scrot

# Verify installation
python3 -c "import tkinter; print(tkinter.Tcl().eval('info patchlevel'))"
```

#### 1.2 Validate in Dedicated Environment
```bash
# Activate the Python 3.11 computer-use environment
source .venv-computer-use/bin/activate

# Verify pyautogui can import without tkinter errors
python3 -c "import pyautogui; print('pyautogui OK')"

# Test basic mouse movement (moves to center of screen)
python3 -c "import pyautogui; pyautogui.moveTo(960, 540, duration=0.5)"
```

#### 1.3 Update Diagnostics Tool
**File:** `src/advanced_vision/diagnostics.py`

Add tkinter check:
```python
REQUIRED_MODULES = [
    "PIL", "pydantic", "mcp", "pyautogui", "pygetwindow",
    "tkinter"  # ADD THIS
]

# Add specific tkinter validation
def _check_tkinter() -> dict[str, Any]:
    try:
        import tkinter
        version = tkinter.Tcl().eval('info patchlevel')
        return {"ok": True, "version": version}
    except Exception as e:
        return {"ok": False, "error": str(e)}
```

#### 1.4 Verification
```bash
# Run diagnostics
advanced-vision-diagnostics | jq '.modules.tkinter'

# Expected output:
# {"ok": true, "version": "8.6.x"}
```

**Success Criteria:**
- [ ] `advanced-vision-diagnostics` shows tkinter as available
- [ ] Can import pyautogui without ImportError
- [ ] Mouse can be moved via Python

---

### Task 2: Create OpenClaw MCP Configuration (P1 - Blocking)
**Estimated Time:** 1-2 hours  
**Depends On:** None  
**Blocks:** Task 7

#### 2.1 Create MCP Server Config
**File:** `~/.openclaw/mcp.json` (or add to existing)

```json
{
  "servers": {
    "advanced-vision": {
      "type": "stdio",
      "command": "advanced-vision-server",
      "description": "Computer-use automation (screenshots, mouse, keyboard, window management)",
      "env": {
        "DISPLAY": "${DISPLAY:-:0}",
        "WAYLAND_DISPLAY": "${WAYLAND_DISPLAY}"
      }
    }
  }
}
```

#### 2.2 Update SKILL.md with mcporter Info
**File:** `SKILL.md`

Add section:
```markdown
## OpenClaw Integration

### Via mcporter

Add to `~/.openclaw/mcp.json`:

\`\`\`json
{
  "servers": {
    "advanced-vision": {
      "type": "stdio",
      "command": "advanced-vision-server"
    }
  }
}
\`\`\`

Then reload or run:
\`\`\`bash
openclaw mcp reload
\`\`\`

### Available Tools

| Tool | Description | Approval |
|------|-------------|----------|
| screenshot_full | Capture entire screen | Green |
| screenshot_active_window | Capture active window | Green |
| list_windows | List open windows | Green |
| move_mouse | Move cursor to coordinates | Yellow |
| click | Click at coordinates | Yellow |
| type_text | Type text | Yellow |
| press_keys | Press keys/combos | Yellow |
| scroll | Scroll mouse wheel | Yellow |
| verify_screen_change | Verify visual change | Green |
| analyze_screenshot | Analyze via vision adapter | Yellow |
```

#### 2.3 Test MCP Server Standalone
```bash
# Test server starts correctly
advanced-vision-server --help

# Test stdio mode (should start and listen)
echo '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}' | advanced-vision-server
```

#### 2.4 Verify mcporter Integration
```bash
# If using mcporter CLI
mcporter list
mcporter call advanced-vision screenshot_full
```

**Success Criteria:**
- [ ] MCP config file created and valid
- [ ] Server starts without errors
- [ ] Can call tools via mcporter/OpenClaw

---

### Task 3: Enhance Schemas for Governance (P1)
**Estimated Time:** 3-4 hours  
**Depends On:** None  
**Blocks:** Task 4

#### 3.1 Create Policy Envelope Schema
**File:** `src/advanced_vision/schemas.py` (add to existing)

```python
from typing import Literal

class RequestContext(BaseModel):
    """Request context for governed operations."""
    request_id: str | None = None
    task_id: str | None = None
    session_id: str | None = None
    
class RequesterInfo(BaseModel):
    """Information about who made the request."""
    agent_id: str | None = None
    user_id: str | None = None
    surface: str | None = None  # telegram, discord, cli, etc.

class PolicyContext(BaseModel):
    """Policy context for approval and classification."""
    approval_class: Literal["green", "yellow", "red"] = "green"
    approved: bool = True
    data_classification: Literal["public", "internal", "sensitive", "secret"] = "internal"
    dry_run: bool = False

class Provenance(BaseModel):
    """Provenance chain for audit trails."""
    parent_event_id: str | None = None
    trace_id: str | None = None
    actor: str | None = None

class PolicyEnvelope(BaseModel):
    """Common envelope for all governed requests."""
    request_context: RequestContext = Field(default_factory=RequestContext)
    requester: RequesterInfo = Field(default_factory=RequesterInfo)
    policy: PolicyContext = Field(default_factory=PolicyContext)
    provenance: Provenance = Field(default_factory=Provenance)
```

#### 3.2 Update Artifact Schemas
**File:** `src/advanced_vision/schemas.py`

```python
class ScreenshotArtifact(BaseModel):
    path: str
    width: int
    height: int
    timestamp: str
    classification: Literal["public", "internal", "sensitive", "secret"] = "internal"
    retention_ttl_seconds: int | None = None  # None = keep forever
    
class ActionResult(BaseModel):
    ok: bool
    action_type: str
    message: str
    artifact_path: str | None = None
    dry_run: bool = False  # ADD THIS
    would_execute: str | None = None  # Description of what would happen
```

#### 3.3 Update Config Schema
**File:** `src/advanced_vision/config.py`

```python
class Settings(BaseModel):
    artifacts_dir: Path = Path("artifacts")
    screens_dir_name: str = "screens"
    logs_dir_name: str = "logs"
    
    # ADD THESE:
    default_screenshot_ttl_seconds: int | None = 86400  # 24 hours
    default_log_ttl_seconds: int | None = 604800  # 7 days
    delete_screenshots_on_success: bool = False
    encryption_enabled: bool = False
    
    @property
    def screens_dir(self) -> Path:
        return self.artifacts_dir / self.screens_dir_name
    
    @property
    def logs_dir(self) -> Path:
        return self.artifacts_dir / self.logs_dir_name
```

#### 3.4 Update Example Config
**File:** `configs/settings.example.yaml`

```yaml
artifacts_dir: artifacts
screens_dir_name: screens
logs_dir_name: logs

# Retention policy
default_screenshot_ttl_seconds: 86400  # 24 hours
default_log_ttl_seconds: 604800  # 7 days
delete_screenshots_on_success: false
encryption_enabled: false
```

**Success Criteria:**
- [ ] All new schemas validate correctly
- [ ] Existing tests still pass
- [ ] New tests for policy envelope pass

---

### Task 4: Implement Policy Envelope in Tools (P1)
**Estimated Time:** 4-6 hours  
**Depends On:** Task 3  
**Blocks:** Task 5

#### 4.1 Update Screen Tools
**File:** `src/advanced_vision/tools/screen.py`

```python
from advanced_vision.schemas import PolicyEnvelope

def screenshot_full(
    envelope: PolicyEnvelope | None = None,
    persist: bool = True
) -> ScreenshotArtifact:
    """
    Capture full desktop screenshot.
    
    Args:
        envelope: Optional policy envelope for governance
        persist: Whether to save to disk (False = memory only)
    """
    # ... existing capture logic ...
    
    artifact = _save_image(image, "full")
    
    # Apply classification from envelope if provided
    if envelope:
        artifact.classification = envelope.policy.data_classification
        artifact.retention_ttl_seconds = settings.default_screenshot_ttl_seconds
    
    return artifact

def screenshot_active_window(
    envelope: PolicyEnvelope | None = None
) -> ScreenshotArtifact:
    """Capture active window with policy context."""
    # Similar pattern
    pass
```

#### 4.2 Update Input Tools with Dry-Run
**File:** `src/advanced_vision/tools/input.py`

```python
from advanced_vision.schemas import PolicyEnvelope

def move_mouse(
    x: int, 
    y: int, 
    envelope: PolicyEnvelope | None = None
) -> ActionResult:
    """
    Move mouse to coordinates.
    
    Args:
        x: X coordinate
        y: Y coordinate
        envelope: Optional policy envelope (includes dry_run)
    """
    dry_run = envelope.policy.dry_run if envelope else False
    
    if dry_run:
        return ActionResult(
            ok=True,
            action_type="move_mouse",
            message=f"[DRY RUN] Would move mouse to ({x}, {y})",
            dry_run=True,
            would_execute=f"pyautogui.moveTo({x}, {y})"
        )
    
    # ... existing execution logic ...

# Apply same pattern to click(), type_text(), press_keys(), scroll()
```

#### 4.3 Update MCP Server Endpoints
**File:** `src/advanced_vision/server.py`

Add envelope support to all tool wrappers:

```python
@mcp.tool()
def move_mouse_mcp(
    x: int, 
    y: int,
    dry_run: bool = False,
    approval_class: str = "yellow"
) -> dict:
    """Move mouse to coordinates."""
    from advanced_vision.schemas import PolicyEnvelope, PolicyContext
    
    envelope = PolicyEnvelope(
        policy=PolicyContext(dry_run=dry_run, approval_class=approval_class)
    ) if dry_run or approval_class != "green" else None
    
    result = move_mouse(x, y, envelope)
    return result.model_dump()

# Apply to all action tools: click, type_text, press_keys, scroll
```

**Success Criteria:**
- [ ] All tools accept optional PolicyEnvelope
- [ ] Dry-run mode works for all action tools
- [ ] Classification flows through to artifacts
- [ ] Tests updated and passing

---

### Task 5: Implement Artifact Governance (P2)
**Estimated Time:** 4-5 hours  
**Depends On:** Task 3, Task 4  
**Blocks:** None

#### 5.1 Create Cleanup Module
**File:** `src/advanced_vision/cleanup.py` (new)

```python
"""Artifact cleanup and retention management."""

import json
from datetime import datetime, timedelta
from pathlib import Path

from advanced_vision.config import get_settings
from advanced_vision.logging_utils import utc_now_iso

def cleanup_expired_artifacts(dry_run: bool = False) -> dict:
    """
    Remove expired artifacts based on TTL settings.
    
    Returns:
        Dict with counts of deleted/screens/logs and bytes freed
    """
    settings = get_settings()
    stats = {"screens_deleted": 0, "logs_deleted": 0, "bytes_freed": 0}
    
    now = datetime.utcnow()
    
    # Clean screenshots
    if settings.default_screenshot_ttl_seconds:
        cutoff = now - timedelta(seconds=settings.default_screenshot_ttl_seconds)
        for screen_file in settings.screens_dir.glob("*.png"):
            mtime = datetime.fromtimestamp(screen_file.stat().st_mtime)
            if mtime < cutoff:
                if not dry_run:
                    stats["bytes_freed"] += screen_file.stat().st_size
                    screen_file.unlink()
                stats["screens_deleted"] += 1
    
    # Clean logs
    if settings.default_log_ttl_seconds:
        cutoff = now - timedelta(seconds=settings.default_log_ttl_seconds)
        for log_file in settings.logs_dir.glob("*.jsonl"):
            mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
            if mtime < cutoff:
                if not dry_run:
                    stats["bytes_freed"] += log_file.stat().st_size
                    log_file.unlink()
                stats["logs_deleted"] += 1
    
    return stats

def classify_artifact(path: Path, classification: str) -> None:
    """Write classification metadata alongside artifact."""
    meta_path = path.with_suffix(path.suffix + ".meta.json")
    meta = {
        "classification": classification,
        "classified_at": utc_now_iso(),
        "path": str(path)
    }
    meta_path.write_text(json.dumps(meta, indent=2))
```

#### 5.2 Update Logging Utils
**File:** `src/advanced_vision/logging_utils.py`

```python
def append_jsonl(
    log_name: str, 
    payload: dict[str, Any],
    provenance: dict | None = None
) -> Path:
    """
    Append a JSON line to a log file with optional provenance.
    
    Args:
        log_name: Name of log file (without .jsonl)
        payload: Data to log
        provenance: Optional provenance metadata
    """
    settings = get_settings()
    log_file = settings.logs_dir / f"{log_name}.jsonl"
    
    entry = {
        "timestamp": utc_now_iso(),
        **payload
    }
    
    if provenance:
        entry["provenance"] = provenance
    
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, default=str) + "\n")
    
    return log_file
```

#### 5.3 Add Cleanup Command
**File:** `src/advanced_vision/server.py` or new CLI

```python
@mcp.tool()
def cleanup_artifacts(dry_run: bool = False) -> dict:
    """Clean up expired artifacts based on retention policy."""
    from advanced_vision.cleanup import cleanup_expired_artifacts
    stats = cleanup_expired_artifacts(dry_run=dry_run)
    return stats
```

**Success Criteria:**
- [ ] Cleanup function removes expired files
- [ ] Classification metadata written
- [ ] Dry-run mode previews deletions
- [ ] Bytes freed reported correctly

---

### Task 6: Expand Test Coverage (P2)
**Estimated Time:** 3-4 hours  
**Depends On:** Task 1, Task 4  
**Blocks:** None

#### 6.1 Add Input Tool Tests
**File:** `tests/test_input.py` (new)

```python
"""Tests for input tools with mocking."""

import pytest
from unittest.mock import patch, MagicMock

from advanced_vision.tools.input import move_mouse, click, type_text, press_keys
from advanced_vision.schemas import PolicyEnvelope, PolicyContext

class TestInputTools:
    """Test mouse and keyboard automation."""
    
    @patch("advanced_vision.tools.input._get_pyautogui")
    def test_move_mouse_executes(self, mock_get_pag):
        """Test mouse movement executes."""
        mock_pag = MagicMock()
        mock_get_pag.return_value = mock_pag
        
        result = move_mouse(100, 200)
        
        assert result.ok is True
        mock_pag.moveTo.assert_called_once_with(100, 200)
    
    @patch("advanced_vision.tools.input._get_pyautogui")
    def test_move_mouse_dry_run(self, mock_get_pag):
        """Test dry-run mode doesn't execute."""
        mock_pag = MagicMock()
        mock_get_pag.return_value = mock_pag
        
        envelope = PolicyEnvelope(policy=PolicyContext(dry_run=True))
        result = move_mouse(100, 200, envelope)
        
        assert result.ok is True
        assert result.dry_run is True
        mock_pag.moveTo.assert_not_called()
    
    @patch("advanced_vision.tools.input._get_pyautogui")
    def test_click_with_button(self, mock_get_pag):
        """Test click with different buttons."""
        mock_pag = MagicMock()
        mock_get_pag.return_value = mock_pag
        
        result = click(100, 200, button="right")
        
        assert result.ok is True
        mock_pag.click.assert_called_once_with(100, 200, button="right")
    
    @patch("advanced_vision.tools.input._get_pyautogui")
    def test_type_text_redacted(self, mock_get_pag):
        """Test text typing with redacted logging."""
        mock_pag = MagicMock()
        mock_get_pag.return_value = mock_pag
        
        result = type_text("secret password")
        
        assert result.ok is True
        # Message should not contain the actual text
        assert "secret" not in result.message.lower()
```

#### 6.2 Add Policy Envelope Tests
**File:** `tests/test_policy.py` (new)

```python
"""Tests for policy envelope and governance."""

from advanced_vision.schemas import (
    PolicyEnvelope, PolicyContext, RequestContext, 
    RequesterInfo, Provenance, ScreenshotArtifact
)

class TestPolicyEnvelope:
    """Test policy envelope functionality."""
    
    def test_default_envelope(self):
        """Test envelope with defaults."""
        envelope = PolicyEnvelope()
        
        assert envelope.policy.approval_class == "green"
        assert envelope.policy.approved is True
        assert envelope.policy.dry_run is False
        assert envelope.policy.data_classification == "internal"
    
    def test_custom_envelope(self):
        """Test envelope with custom values."""
        envelope = PolicyEnvelope(
            request_context=RequestContext(request_id="req-123"),
            policy=PolicyContext(
                approval_class="yellow",
                dry_run=True,
                data_classification="sensitive"
            )
        )
        
        assert envelope.request_context.request_id == "req-123"
        assert envelope.policy.approval_class == "yellow"
        assert envelope.policy.dry_run is True
        assert envelope.policy.data_classification == "sensitive"
    
    def test_artifact_classification_flow(self):
        """Test classification flows to artifacts."""
        envelope = PolicyEnvelope(
            policy=PolicyContext(data_classification="secret")
        )
        
        # Simulate screenshot with envelope
        artifact = ScreenshotArtifact(
            path="/tmp/test.png",
            width=1920,
            height=1080,
            timestamp="2026-03-16T00:00:00Z",
            classification=envelope.policy.data_classification
        )
        
        assert artifact.classification == "secret"
```

#### 6.3 Add Cleanup Tests
**File:** `tests/test_cleanup.py` (new)

```python
"""Tests for artifact cleanup."""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from advanced_vision.cleanup import cleanup_expired_artifacts

class TestCleanup:
    """Test artifact cleanup functionality."""
    
    def test_cleanup_dry_run(self, tmp_path):
        """Test dry-run doesn't delete."""
        # Create test file
        test_file = tmp_path / "test.png"
        test_file.write_text("test")
        
        # Modify mtime to be old
        old_time = (datetime.now() - timedelta(days=30)).timestamp()
        test_file.touch()
        
        # Should not delete in dry-run
        stats = cleanup_expired_artifacts(dry_run=True)
        
        assert test_file.exists()  # Still there
    
    def test_cleanup_deletes_expired(self, tmp_path):
        """Test cleanup removes expired files."""
        # Create old file
        old_file = tmp_path / "old.png"
        old_file.write_text("old")
        
        # Create new file
        new_file = tmp_path / "new.png"
        new_file.write_text("new")
        
        # Mock settings to use tmp_path
        # ... test implementation
```

#### 6.4 Update Existing Tests
**File:** `tests/test_smoke.py`

Add tests for dry-run mode:
```python
def test_flow_with_dry_run():
    """Test flow execution with dry_run flag."""
    from advanced_vision.schemas import PolicyEnvelope, PolicyContext
    
    envelope = PolicyEnvelope(policy=PolicyContext(dry_run=True))
    # Test that actions are not executed but reported
```

**Success Criteria:**
- [ ] Input tool tests pass with mocked pyautogui
- [ ] Policy envelope tests pass
- [ ] Cleanup tests pass
- [ ] Overall coverage > 80%

---

### Task 7: Update Documentation (P2)
**Estimated Time:** 2-3 hours  
**Depends On:** Task 2, Task 3, Task 4  
**Blocks:** None

#### 7.1 Update README.md
Add sections:
- OpenClaw integration instructions
- Policy envelope usage
- Dry-run mode examples
- Retention configuration

#### 7.2 Update SKILL.md
Already covered in Task 2.2

#### 7.3 Update ARCHITECTURE.md
Add:
- Policy envelope architecture diagram
- Artifact lifecycle documentation
- Trust boundary clarifications

#### 7.4 Create Configuration Guide
**File:** `docs/CONFIGURATION.md` (new)

```markdown
# Configuration Guide

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ADVANCED_VISION_ARTIFACTS_DIR` | Base artifacts directory | `artifacts` |
| `ADVANCED_VISION_SCREEN_TTL` | Screenshot retention (seconds) | `86400` |
| `ADVANCED_VISION_LOG_TTL` | Log retention (seconds) | `604800` |

## Settings File

Create `configs/settings.yaml`:

\`\`\`yaml
artifacts_dir: /secure/artifacts
default_screenshot_ttl_seconds: 3600  # 1 hour
delete_screenshots_on_success: true
encryption_enabled: true
\`\`\`

## OpenClaw Integration

See SKILL.md for mcporter configuration.
```

**Success Criteria:**
- [ ] README updated with new features
- [ ] Configuration guide complete
- [ ] All examples tested and working

---

## Implementation Order

```
Week 1 (Days 1-3):
  Task 1: Fix Input Tools Blocker
  Task 2: Create OpenClaw MCP Configuration

Week 1 (Days 4-5):
  Task 3: Enhance Schemas for Governance
  Task 4: Implement Policy Envelope in Tools

Week 2 (Days 6-8):
  Task 5: Implement Artifact Governance
  Task 6: Expand Test Coverage

Week 2 (Days 9-10):
  Task 7: Update Documentation
  Integration Testing & Bug Fixes
```

---

## Dependencies and Prerequisites

### System Dependencies
```bash
# Required for input tools
sudo apt-get install -y python3-tk python3-dev scrot

# Optional for testing
sudo apt-get install -y xvfb  # Virtual display for headless testing
```

### Python Dependencies
All already specified in `pyproject.toml`:
- pydantic >=2.7.0
- mcp >=1.0.0
- Pillow >=10.0.0
- pyautogui >=0.9.54
- pygetwindow >=0.0.9

### OpenClaw Integration
- mcporter CLI configured
- `~/.openclaw/mcp.json` writable
- Gateway running (if using remote)

---

## Testing Strategy

### Unit Tests
- Mock external dependencies (pyautogui, PIL)
- Test policy envelope validation
- Test schema serialization

### Integration Tests
- Test actual screenshot capture
- Test MCP server stdio communication
- Test with virtual display (Xvfb)

### End-to-End Tests
- Full flow: screenshot → analyze → act → verify
- OpenClaw integration via mcporter
- Cleanup and retention policies

### Test Environments
1. **Development:** Local with real GUI
2. **CI:** Headless with Xvfb
3. **Staging:** OpenClaw integration test

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| tkinter fix doesn't work | HIGH | Have fallback to Python 3.11 env |
| mcporter integration issues | MEDIUM | Test early, document workarounds |
| Policy envelope too complex | MEDIUM | Start simple, iterate |
| Test flakiness with GUI | MEDIUM | Use mocks + Xvfb combo |

---

## Success Criteria for Phase 2

- [ ] All P0 blockers resolved
- [ ] MCP server registered and functional in OpenClaw
- [ ] Input tools working (mouse, keyboard)
- [ ] Policy envelope implemented and tested
- [ ] Dry-run mode functional
- [ ] Artifact governance (cleanup, classification) working
- [ ] Test coverage > 80%
- [ ] Documentation complete and accurate

---

## Future Work (Phase 3+)

- **Phase 3:** Live tool-use validation, window management improvements
- **Phase 4:** Policy broker wrapper, full governance hardening
- **Phase 5:** Real vision adapter (Kimi/Claude/GPT-4V integration)
- **Phase 6:** GitHub service integration, multi-agent orchestration

---

*End of Phase 2 Implementation Roadmap*
