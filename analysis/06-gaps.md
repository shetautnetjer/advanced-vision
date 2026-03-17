# Advanced Vision - Gaps Analysis

**Generated:** 2026-03-16  
**Synthesis of:** 01-structure.md, 02-code-summary.md, 03-config.md, 04-docs.md  
**Purpose:** Identify all missing pieces, blockers, and incomplete implementations for Phase 2 planning

---

## Critical Blockers (Must Fix First)

### 1. Input Tools Blocked on tkinter
**File:** `src/advanced_vision/tools/input.py`  
**Status:** ⚠️ Non-functional  
**Impact:** HIGH - Core computer-use capability unavailable

**Problem:**
- `pyautogui` → `mouseinfo` requires `python3-tk`, `python3-dev`, `scrot`
- Linuxbrew Python 3.14 may need different strategy than system packages
- All mouse/keyboard actions fail without this

**Evidence from analysis:**
> "Input tools (mouse/keyboard) blocked on tkinter availability in current environment" (01-structure.md)

> "pyautogui → mouseinfo requires python3-tk, python3-dev, scrot. Screenshot path works, input path not yet operational" (04-docs.md)

**Resolution Options:**
1. Install system packages: `sudo apt-get install python3-tk python3-dev scrot`
2. Use dedicated Python 3.11 environment (`.venv-computer-use/`) which may have better compatibility
3. Switch to alternative input library (lower priority)

---

### 2. Window Listing Returns Empty
**File:** `src/advanced_vision/tools/windows.py`  
**Status:** ⚠️ Degraded  
**Impact:** MEDIUM - Reduces UI automation accuracy

**Problem:**
- `list_windows()` returns 0 windows on headless/minimal desktop environments
- `pygetwindow` has limited Linux/Wayland support
- Fallback returns empty list gracefully but provides no window context

**Evidence:**
> "`list_windows()` returns 0 windows on headless/minimal environments" (01-structure.md)

---

## Architecture Gaps

### 3. Vision Adapter is Stub Only
**File:** `src/advanced_vision/vision_adapter.py`  
**Status:** ❌ Not Implemented  
**Impact:** HIGH - No intelligence without this

**Current State:**
```python
class StubVisionAdapter(VisionAdapter):
    def analyze_screenshot(self, image_path: str, task: str) -> ActionProposal:
        return ActionProposal(
            action_type="noop",
            confidence=0.1,
            rationale="Stub adapter - no real vision model integrated"
        )
```

**Missing:**
- Real vision model integration (Kimi, Claude, GPT-4V, etc.)
- API key management for vision providers
- Image preprocessing (resize, format conversion)
- Error handling for API failures
- Rate limiting and retry logic

**Evidence:**
> "Vision adapter is stubbed (returns noop proposals)" (01-structure.md)

> "Returns deterministic noop, no real analysis. Infrastructure ready, intelligence not connected" (04-docs.md)

---

### 4. No Policy Envelope Support
**Files:** All tool files in `src/advanced_vision/tools/`  
**Status:** ❌ Not Implemented  
**Impact:** HIGH - Cannot integrate with governed orchestration

**Missing:**
- `request_id`, `task_id`, `session_id` parameters
- `approval_class` parameter (green/yellow/red)
- `data_classification` parameter (public/internal/sensitive/secret)
- `provenance` chain tracking
- Requester metadata (agent_id, user_id, surface)

**Required per SERVICE_CONTRACTS.md:**
```json
{
  "request_id": "req_123",
  "task_id": "task_456",
  "session_id": "sess_789",
  "requester": {"agent_id": "...", "user_id": "...", "surface": "..."},
  "policy": {"approval_class": "...", "approved": true/false, "data_classification": "..."},
  "provenance": {"parent_event_id": "...", "trace_id": "..."}
}
```

**Evidence:**
> "No policy envelope in tools - Harder to integrate into governed orchestration" (04-docs.md)

---

### 5. No Dry-Run Mode for Actions
**Files:** `src/advanced_vision/tools/input.py`  
**Status:** ❌ Not Implemented  
**Impact:** MEDIUM - Cannot preview actions before execution

**Missing:**
- `dry_run: bool = False` parameter on all action tools
- Action preview/description without execution
- Validation-only mode for testing workflows

**Evidence:**
> "No dry-run mode - Cannot preview actions before execution" (04-docs.md)

---

## Governance & Security Gaps

### 6. No Artifact Retention Policy
**Files:** `src/advanced_vision/config.py`, `src/advanced_vision/tools/screen.py`  
**Status:** ❌ Not Implemented  
**Impact:** MEDIUM - Sensitive screenshots accumulate indefinitely

**Missing:**
- TTL settings for screenshots and logs
- Delete-on-success behavior option
- Automatic cleanup jobs
- Encrypted storage option
- Configurable retention per artifact type

**Evidence:**
> "No retention policy - Sensitive screenshots accumulate" (04-docs.md)

> "Artifact retention/cleanup policies" marked as "Not Yet Implemented" (01-structure.md)

---

### 7. No Artifact Classification
**Files:** `src/advanced_vision/schemas.py`, `src/advanced_vision/tools/screen.py`  
**Status:** ❌ Not Implemented  
**Impact:** MEDIUM - Cannot apply differentiated policies

**Missing:**
- `classification` field on ScreenshotArtifact (public/internal/sensitive/secret)
- Classification inference from content
- Different handling per classification level
- Classification-based retention policies

**Evidence:**
> "No artifact classification - All screenshots treated equally" (04-docs.md)

---

### 8. Limited Provenance Logging
**File:** `src/advanced_vision/logging_utils.py`  
**Status:** ⚠️ Partial  
**Impact:** MEDIUM - Incomplete audit trail

**Current State:**
- Basic timestamp + payload logging
- Missing: actor/session metadata, parent events, trace IDs

**Missing:**
- Full provenance chain (parent_event_id, trace_id)
- Actor identification (agent_id, user_id)
- Session context
- Policy context at time of action

**Evidence:**
> "Limited provenance logging - Missing actor/session metadata" (04-docs.md)

---

## Integration Gaps

### 9. Missing OpenClaw MCP Configuration
**Status:** ❌ Not Implemented  
**Impact:** HIGH - Cannot be discovered by mcporter

**Missing:**
- `mcp.json` or `mcp.yaml` configuration file
- OpenClaw skill manifest updates
- Registration with OpenClaw gateway

**Required for mcporter integration:**
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

**Evidence:**
> "MCP Server Config File - Missing - Consider mcp.json or mcp.yaml for mcporter integration" (03-config.md)

> "OpenClaw Skill Manifest - Missing - Consider creating SKILL.md for mcporter" (03-config.md)

---

### 10. WindowInfo.app_name Not Populated
**File:** `src/advanced_vision/tools/windows.py`  
**Status:** ⚠️ Partial  
**Impact:** LOW - Missing context but non-blocking

**Problem:**
- Field exists in schema but is never populated by `list_windows()`
- Always returns None

**Evidence:**
> "WindowInfo.app_name - Field exists but is not populated by list_windows() - Currently always None" (02-code-summary.md)

---

## Testing Gaps

### 11. No Integration Tests for Input Tools
**File:** `tests/test_smoke.py`  
**Status:** ❌ Not Implemented  
**Impact:** MEDIUM - Cannot validate input tools

**Missing:**
- Tests for `move_mouse`, `click`, `type_text`, `press_keys`, `scroll`
- Mock-based unit tests for pyautogui calls
- Integration tests with virtual display

---

### 12. No Vision Adapter Tests
**File:** Tests directory  
**Status:** ❌ Not Implemented  
**Impact:** MEDIUM - No validation of vision integration

**Missing:**
- Tests for real vision adapter (once implemented)
- Mock vision provider for testing
- Image preprocessing tests

---

## Configuration Gaps

### 13. Missing Environment Variable Configuration
**Status:** ⚠️ Partial  
**Impact:** LOW - Limited runtime configuration

**Missing:**
- `.env.example` file
- Environment variable overrides for settings
- API key configuration for vision providers
- Runtime feature toggles

**Evidence:**
> ".env.example - Missing - Add template for API keys (future vision adapter)" (03-config.md)

---

### 14. Horizontal Scroll Not Universally Supported
**File:** `src/advanced_vision/tools/input.py`  
**Status:** ⚠️ Platform-dependent  
**Impact:** LOW - Limited functionality on some platforms

**Problem:**
```python
if horizontal and hasattr(pag, "hscroll"):
    pag.hscroll(horizontal)
```
- Conditional check means horizontal scroll silently fails on unsupported platforms

**Evidence:**
> "Horizontal Scroll - Conditional: if horizontal and hasattr(pag, 'hscroll') - Not all platforms support horizontal scroll" (02-code-summary.md)

---

## Summary Table

| Gap | Priority | Category | Blocking Phase 2? |
|-----|----------|----------|-------------------|
| 1. Input tools blocked on tkinter | P0 | Blocker | YES |
| 2. Window listing empty | P1 | Degradation | NO |
| 3. Vision adapter stub | P1 | Feature | NO |
| 4. No policy envelope | P1 | Architecture | NO |
| 5. No dry-run mode | P2 | Feature | NO |
| 6. No retention policy | P2 | Governance | NO |
| 7. No artifact classification | P2 | Governance | NO |
| 8. Limited provenance logging | P2 | Governance | NO |
| 9. Missing OpenClaw MCP config | P1 | Integration | YES |
| 10. app_name not populated | P3 | Polish | NO |
| 11. No input tool tests | P2 | Testing | NO |
| 12. No vision adapter tests | P2 | Testing | NO |
| 13. Missing env config | P3 | Configuration | NO |
| 14. Horizontal scroll platform issues | P3 | Platform | NO |

---

## Dependencies for Phase 2

### Must Have (Blocking)
1. Fix tkinter for input tools
2. Create OpenClaw MCP configuration

### Should Have (Enables Full Capability)
3. Real vision adapter implementation
4. Policy envelope support in tools
5. Artifact retention and classification

### Nice to Have (Polish)
6. Dry-run mode
7. Enhanced provenance logging
8. Complete test coverage

---

*End of Gaps Analysis*
