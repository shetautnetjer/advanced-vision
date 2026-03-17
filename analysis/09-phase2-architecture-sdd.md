# Phase 2 Architecture SDD

**Project:** advanced-vision  
**Phase:** 2  
**Focus:** simple computer use first, governance later

---

## 1. Intent

Phase 2 exists to prove that `advanced-vision` can serve as a **small local MCP capability layer for computer use**.

This phase is not about building the entire governed architecture.
It is about making a narrow slice real.

### Core objective
Make the following loop work reliably enough for local testing:

1. capture screen
2. inspect screen
3. perform a simple action
4. verify visual change

If this loop is not stable, later governance layers will be mostly paperwork.

---

## 2. Scope

## In scope
- dedicated computer-use runtime
- MCP server startup and local registration path
- screenshot tools
- input tools
- verify tools
- simple dry-run support for input tools
- honest platform notes for Linux
- basic safe test workflow

## Out of scope
- full governance/policy envelopes everywhere
- secrets broker
- GitHub integration coupling
- external vision-provider policy system
- broad provenance architecture
- long-horizon orchestration

---

## 3. Functional target

At the end of Phase 2, the system should support:

### Read tools
- `screenshot_full`
- `screenshot_active_window` (best effort)
- `verify_screen_change`
- `analyze_screenshot` (still stub is acceptable)

### Action tools
- `move_mouse`
- `click`
- `type_text`
- `press_keys`
- `scroll`

### Runtime behavior
- MCP server starts from the intended env
- screenshots are written to artifacts
- actions can be tested safely
- verification loop can observe whether action changed the UI

---

## 4. Reality constraints on this host

### Confirmed
- dedicated Python 3.11 computer-use env exists
- `tkinter` imports there
- `pyautogui` imports there
- `PIL` imports there

### Confirmed limitation
- `pygetwindow` does not support Linux in this environment

### Design consequence
Window discovery should not be treated as a core dependency for Phase 2.

Instead, Phase 2 should rely on:
- screenshots
- coordinates
- visual verification
- simple safe local tests

---

## 5. Architecture for Phase 2

```text
        ┌─────────────────────────────┐
        │  Calling agent / host tool  │
        └──────────────┬──────────────┘
                       │ MCP/stdio
                       ▼
        ┌─────────────────────────────┐
        │   advanced-vision server    │
        │   src/advanced_vision/      │
        │   server.py                 │
        └───────┬───────────┬─────────┘
                │           │
                │           │
                ▼           ▼
      ┌────────────────┐  ┌─────────────────┐
      │ screen tools   │  │ input tools     │
      │ verify tools   │  │ action tools    │
      └────────────────┘  └─────────────────┘
                │           │
                └─────┬─────┘
                      ▼
          ┌─────────────────────────┐
          │ local desktop session   │
          │ X11 / GUI environment   │
          └─────────────────────────┘
                      │
                      ▼
          ┌─────────────────────────┐
          │ artifacts/              │
          │ - screens/              │
          │ - logs/                 │
          └─────────────────────────┘
```

---

## 6. Recommended implementation order

### Step 1 — prove runtime
- activate `.venv-computer-use`
- run diagnostics from that env
- start MCP server from that env
- confirm imports and tool startup

### Step 2 — prove read path
- run `screenshot_full`
- run `screenshot_active_window`
- run `verify_screen_change`
- run `run_single_cycle(execute=False)`

### Step 3 — prove action path carefully
- add/confirm `dry_run` for action tools
- test `move_mouse` in dry-run mode
- test `move_mouse` live in a safe context
- test `click` live in a harmless context
- test `type_text` only in a deliberate safe input field
- verify results visually

### Step 4 — document Linux limitations
- mark `list_windows` as best effort only
- explicitly note that `pygetwindow` is not reliable/usable on Linux here
- recommend screenshot-based interaction instead of window-discovery dependence

### Step 5 — package integration notes
- add simple OpenClaw/mcporter registration example
- document exact environment activation assumptions
- keep the integration notes modest and verified

---

## 7. Minimal Phase 2 design changes

### A. Add `dry_run` to action tools
Why:
- safer testing
- easier demos
- useful without heavy governance machinery

### B. Improve diagnostics to reflect dedicated env reality
Diagnostics should explicitly report:
- tkinter import status
- pyautogui import status
- pygetwindow Linux limitation

### C. Keep `analyze_screenshot` stubbed if needed
That is acceptable in Phase 2.
The purpose is infrastructure proof, not model sophistication.

### D. Do not let `list_windows` gate progress
Keep it exposed as best effort if helpful, but do not architect around it.

---

## 8. Testing strategy

### Safe manual tests
Use harmless contexts only:
- empty desktop region
- text editor scratch buffer
- disposable text field

### Recommended test progression
1. `screenshot_full`
2. `move_mouse` dry-run
3. `move_mouse` live
4. `click` live on safe target
5. `type_text` into scratch pad
6. `verify_screen_change`

### Automated tests
Continue using unit/smoke tests for:
- schemas
- screenshot capture
- verification logic
- dry-run behavior

Avoid pretending full GUI automation can be comprehensively proven by CI alone.

---

## 9. Deferred governance themes

These matter, but they are **later-phase work**:
- policy envelopes on every tool
- classification and retention system
- provenance chain expansion
- secret-aware external vision routing
- GitHub plus desktop combined orchestration

Phase 2 should leave room for them without implementing all of them now.

A small concession to the future is fine:
- preserve clean schemas
- keep logs structured
- design APIs that can later accept policy context

But do not let future governance complexity block current runtime truth.

---

## 10. Phase 2 success criteria

A successful Phase 2 means:
- dedicated env is the documented runtime of record for computer use
- MCP server runs from that env
- screenshot tools work
- at least basic input actions work in safe tests
- verification loop works
- docs clearly state Linux window-management limitations
- dry-run exists for action tools or is explicitly next-up

It does **not** require:
- real model vision
- full governance architecture
- GitHub-integrated orchestration

---

## 11. Bottom line

Phase 2 should answer one question clearly:

**Can this repo act as a simple, local, testable computer-use MCP server?**

If yes, then later phases can add:
- governance
- policy
- secrets discipline
- richer orchestration

But first the hand has to work.
