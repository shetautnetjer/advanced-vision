# Audit of Analysis Set

**Date:** 2026-03-16
**Purpose:** correct overstatements, mark verified facts, and tighten the Phase 2 direction.

## Executive summary

The analysis set is useful, but it should be treated as a **planning draft**, not canon.

Main strengths:
- good repo decomposition
- good gap identification
- strong instinct toward a dedicated computer-use environment

Main weaknesses:
- some documents overstate verification
- a few claims are stale or inaccurate
- the Phase 2 plan mixes runtime enablement and governance hardening too early

---

## Verified facts from direct checks

### Verified in dedicated computer-use env
Using `.venv-computer-use`:
- `tkinter` imports successfully
- `pyautogui` imports successfully
- `PIL` imports successfully

### Verified limitation
- `pygetwindow` still fails on Linux in this environment with:
  - `NotImplementedError: PyGetWindow currently does not support Linux`

### Implication
The dedicated env improves input-stack viability, but **window management should not be treated as solved**.

---

## Corrections to existing analysis

### 1. `analysis/01-structure.md`
Issue:
- describes `analysis/` as empty

Correction:
- the folder is not empty and already contains generated analysis files

### 2. `analysis/04-docs.md`
Issue:
- frames MCP server as not yet implemented because `src/mcp_server.py` is missing

Correction:
- the MCP server already exists at `src/advanced_vision/server.py`
- the real gap is OpenClaw integration/registration clarity, not server absence

### 3. `COMPUTER_USE_ENV.md`
Issue:
- presents several runtime capabilities as fully operational

Correction:
- imports for `tkinter` and `pyautogui` are now directly confirmed
- `pygetwindow` support is **not** confirmed; in fact it fails on Linux here
- window management should be marked partial/unreliable, not complete

### 4. `analysis/07-phase2-plan.md`
Issue:
- Phase 2 scope is too broad

Correction:
- Phase 2 should focus on simple computer use and MCP runtime proof
- governance-heavy themes should come later once the substrate is verified

---

## Better framing for Phase 2

### Phase 2 should prove
- dedicated env works
- MCP server runs from intended env
- screenshot tools work
- input tools work in safe tests
- verification loop works
- Linux limitations are documented honestly

### Phase 2 should not try to finish
- full governance envelope design
- secrets/policy-broker integration
- GitHub service coupling
- comprehensive retention/classification framework

Those belong later.

---

## Updated reality-based priorities

### P0
- verify input actions in `.venv-computer-use`
- verify MCP server startup from that env
- document Linux `pygetwindow` limitation

### P1
- add simple `dry_run` support for input tools
- add a minimal OpenClaw/mcporter registration example
- add a small safe test plan for local computer use

### P2
- improve logging/provenance a bit
- add cleanup/retention utilities if needed
- begin governance layering only after runtime confidence increases

---

## Recommendation

Treat the new Phase 2 architecture/spec as the working guide:
- simple computer use first
- governance themes later
- verify more, speculate less

That will keep the project honest and moving.
