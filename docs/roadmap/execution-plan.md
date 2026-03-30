# Advanced Vision — Execution Plan

**Status:** ✅ COMPLETED - All phases E0-E5 finished  
**Date:** 2026-03-17  
**Purpose:** Define the grounded implementation path for `advanced-vision`

---

## 1. Intent

This execution plan deliberately narrows scope.

The immediate goal is **not** to finish the full `advanced-vision` dream.
The immediate goal is to prove that this repo can serve as a:

**small, local, testable computer-use and visual-analysis substrate**

That means the first body of work is:
- runtime
- capture
- safe action
- verification
- optional recording experiment

Everything else depends on that truth.

---

## 2. Success definition

This plan succeeds if, by the end, the repo can honestly claim:

- the dedicated env is the runtime of record
- the MCP server starts from that env
- screenshot tools work reliably
- basic input actions work in safe local tests
- action results can be verified visually
- Linux limitations are documented clearly
- a recording-analysis experiment path is identified and bounded

It does **not** require:
- full trading intelligence
- policy/governor framework
- Lobster integration
- LangGraph state machine
- broad multi-model orchestration

---

## 3. Constraints already known

### Verified repo reality
- tests pass in the current repo env
- screenshot path works
- verification path works
- `run_single_cycle(execute=False)` works
- a dedicated `.venv-computer-use` exists
- `tkinter`, `pyautogui`, and `PIL` import there
- `pygetwindow` still fails on Linux here

### Design consequence
The substrate should remain:
- screenshot-based
- coordinate-based
- verification-based

Do not architect the near-term plan around window enumeration.

---

## 4. Execution phases

## Phase E0 — Clean runtime and repo boundaries

### Goal
Make the dedicated env and current repo state unambiguous.

### Tasks
- document `.venv-computer-use` as the intended computer-use runtime
- verify exact activation/start commands
- record known Linux limitations in one place
- ensure `.venv*`, `artifacts/`, and other generated paths are ignored appropriately if needed
- keep third-party/site-packages modifications out of commits

### Deliverables
- verified startup instructions
- clean `.gitignore` hygiene if needed
- short runtime note

### Exit criteria
A new contributor can tell which env is real and what Linux does/doesn’t support here.

---

## Phase E1 — Read path hardening

### Goal
Make the visual read path real and documented.

### Tasks
- confirm `screenshot_full`
- confirm `screenshot_active_window` behavior and document whether it falls back
- confirm `verify_screen_change`
- confirm artifact output paths
- tighten diagnostics to report:
  - `tkinter`
  - `pyautogui`
  - `pygetwindow` limitation
  - GUI session hints

### Deliverables
- stronger diagnostics
- read-path notes
- small smoke-test procedure

### Exit criteria
Read-only computer-use primitives are stable enough to rely on during development.

---

## Phase E2 — Safe action path

### Goal
Make local action primitives testable without recklessness.

### Tasks
- add `dry_run` support for action tools where practical:
  - `move_mouse`
  - `click`
  - `type_text`
  - `press_keys`
  - `scroll`
- if code-level `dry_run` is not added immediately, document a safe manual protocol clearly
- ensure action tools return structured results suitable for later governance layering

### Deliverables
- dry-run action path or clearly documented safe protocol
- structured action-test notes

### Exit criteria
Action testing is possible without pretending the system is already safe by default.

---

## Phase E3 — Live action verification

### Goal
Prove that the body can act and then verify its own effect.

### Tasks
- test `move_mouse` in a safe context
- test `click` on a harmless target
- test `type_text` in a disposable scratch field only
- test `press_keys` in a safe context
- test `scroll` if practical
- run `action -> wait -> verify_screen_change -> log`
- record what is stable vs flaky

### Deliverables
- action-verification report
- known-flaky behaviors list
- minimal local demo scenario

### Exit criteria
At least one small end-to-end local loop works:
- see
- act
- verify
- log

---

## Phase E4 — Recording/video experiment

### Goal
Decide how recordings should fit into `advanced-vision` without distorting the repo.

### Research-backed premise
Kimi K2.5 appears to support image and video input, but video is described as **experimental** and associated with the **official API path** rather than all third-party/self-hosted compatibility routes.

### Tasks
- create a small `VIDEO_SUPPORT.md` or equivalent note
- define the candidate paths:
  1. direct official Moonshot video API
  2. local frame extraction + image analysis
  3. hybrid summarization path
- select one tiny test case (short MP4)
- document the exact request path and assumptions before implementing
- do not block the rest of the repo on this phase

### Deliverables
- bounded video-support design note
- one test plan for a short recording

### Exit criteria
The repo has an honest, narrow path for recording analysis experimentation.

---

## Phase E5 — Lightweight integration guidance

### Goal
Make the current substrate actually usable by Dad and future agents.

### Tasks
- document exact server-start path
- document exact runtime assumptions
- add a minimal OpenClaw/mcporter registration example if verified
- keep wording modest: “tested” vs “planned”

### Deliverables
- concise integration guide
- no inflated claims

### Exit criteria
The repo is easy to run and understand in its current truthful state.

---

## 5. Explicitly deferred

Do **not** treat these as part of the current execution ladder:
- trading-watch stack
- Chronos-2 integration
- Nemotron/Cosmos integration
- stock-pattern detector integration
- governor/policy engine
- LangGraph workflow engine
- message bus
- Lobster integration
- Ralph human-simulation protocol

Those belong to the roadmap, not this execution plan.

---

## 6. Research notes that influenced this plan

### Kimi K2.5 / recording support
Research consistently suggests:
- K2.5 is natively multimodal
- image and video input are supported in official examples
- video input is experimental
- official API and third-party/self-hosted paths differ, especially for video and thinking-mode parameters

### Ultralytics / tracking
Research confirms:
- BoT-SORT is built into Ultralytics tracking mode
- it should be treated as an available tracker path, not a separate heavyweight model program

### Linux computer-use reality
Direct local testing still matters more than speculative architecture:
- `pygetwindow` limitation remains real here
- action reliability must be demonstrated, not assumed from imports alone

---

## 7. Ordered task checklist

### Immediate ✅ DONE
- [x] document runtime-of-record clearly
- [x] clean commit boundaries / ignore generated churn if needed
- [x] strengthen diagnostics
- [x] verify and document read-path behavior

### Next ✅ DONE
- [x] add `dry_run` support or safe protocol
- [x] test action tools safely
- [x] produce an action-verification report

### Then ✅ DONE
- [x] write bounded video-support note
- [x] choose one recording-analysis experiment path
- [x] add small integration guide

---

## 8. Decision standard

A near-term change is approved only if it improves one of:
- runtime truth
- local capability
- safe testing
- documentation accuracy
- current integration usability

If it mainly serves future governance, future trading intelligence, or future orchestration, it is roadmap work and should wait.

---

## 9. Bottom line

This repo does not need to become a full governed swarm platform in the next breath.
It needs to become a real hand.

This execution plan protects that truth.
