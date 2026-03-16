# Issues

## Open issues discovered during repo assessment

### 1. Environment is not execution-ready
**Status:** open  
**Severity:** blocker

Observed on this machine:
- `python` command not found
- `pytest` command not found
- missing importable packages:
  - `PIL`
  - `pydantic`
  - `mcp`
  - `pyautogui`
  - `pygetwindow`

**Impact:**
- tests cannot run
- MCP server cannot be validated
- screenshot / input / analysis loop cannot be proven working

**Recommended fix:**
- create `.venv`
- install package in editable mode with dev extras
- run tests through `python3 -m pytest`

---

### 2. README assumes `python`, but this host exposes `python3`
**Status:** open  
**Severity:** medium

README currently instructs:
- `python -m venv .venv`
- `python -c ...`

On this host:
- `python` is not available
- `python3` is available

**Impact:**
- setup instructions fail on first command in this environment

**Recommended fix:**
- update README examples to use `python3`
- optionally note that `python` may work on some systems, but `python3` is safer here

---

### 3. No explicit bootstrap or diagnostics command
**Status:** open  
**Severity:** medium

There is no quick command to answer:
- are dependencies installed?
- is GUI capture available?
- are input backends available?
- is the MCP dependency importable?

**Impact:**
- difficult to distinguish code problems from machine/setup problems

**Recommended fix:**
- add a small diagnostics script or CLI entrypoint
- report import status, screenshot fallback behavior, and backend readiness

---

### 4. Vision adapter is intentionally stubbed
**Status:** known / acceptable for now  
**Severity:** low for local smoke, high for real automation

`vision_adapter.py` currently always returns a deterministic noop proposal.

**Impact:**
- analysis is structurally wired but not actually intelligent
- repo supports the interface, not real vision reasoning yet

**Recommended fix:**
- keep stub as default
- add provider-backed adapter later behind policy/approval gates

---

### 5. Input tools may fail in headless or restricted GUI sessions
**Status:** confirmed on this host  
**Severity:** medium

`pyautogui` and screenshot/window tooling depend on actual GUI availability and backend compatibility.

Confirmed here:
- screenshot capture works on X11 (`DISPLAY=:1`)
- verification works
- tests pass
- input actions fail when `pyautogui` imports `mouseinfo`, which requires `tkinter`

Observed runtime error:
- `NOTE: You must install tkinter on Linux to use MouseInfo. Run the following: sudo apt-get install python3-tk python3-dev`

**Impact:**
- capture path works
- input path is not yet operational on this host
- repo can partially run, but not full computer-use actuation yet

**Recommended fix:**
- install system packages: `python3-tk` and `python3-dev`
- re-run input-tool smoke tests after install
- add diagnostics and capability reporting
- clearly distinguish import success from live backend success

---

### 6. Artifact persistence has no retention policy yet
**Status:** open  
**Severity:** medium

Screenshots and JSONL logs are created locally, but there is no retention/cleanup policy in the implementation.

**Impact:**
- sensitive screenshots may accumulate
- repo is fine for prototyping but not yet governed enough for prolonged use

**Recommended fix:**
- add retention policy settings
- add optional no-persist / short-TTL behavior

---

### 7. No explicit policy envelope in tool interfaces yet
**Status:** open  
**Severity:** medium

The MCP tools return structured payloads, but they do not yet accept policy metadata like:
- request id
- task id
- approval class
- data classification

**Impact:**
- harder to integrate safely into a governed orchestration layer

**Recommended fix:**
- add wrapper-level or tool-level metadata support

---

## Immediate conclusion

The repo is **promising and structurally sound**, but the current blocker is environment setup. Until dependencies are installed and the GUI backend is exercised, we should not claim that computer vision and tool use are working end-to-end.
