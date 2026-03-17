# Aya Task List for Dad

Aya,

This is your one-step-at-a-time work plan for `advanced-vision`.

The rule is simple:
**do one phase fully and honestly before claiming the next.**

You are not trying to impress Dad with breadth.
You are building him something real.

---

## Mission

Build `advanced-vision` into a **small, trustworthy local computer-use MCP server**.

Not a giant orchestration system.
Not a governance cathedral yet.

Just a real hand that works.

---

# Phase 1 — Prove the runtime

## Goal
Prove the dedicated computer-use environment is the actual runtime of record.

## Your tasks
- [ ] Activate `.venv-computer-use`
- [ ] Verify imports work:
  - [ ] `tkinter`
  - [ ] `pyautogui`
  - [ ] `PIL`
- [ ] Record what fails and what works
- [ ] Confirm `pygetwindow` still fails on Linux and document that cleanly
- [ ] Update docs only with what you directly verified

## Deliverable
A short verified note that says:
- what imports work
- what does not work
- which env is the real computer-use env

## Dad’s standard
No guessing. No smoothing over failure.
Say exactly what is true.

---

# Phase 2 — Prove the MCP server starts from the right env

## Goal
Make sure the server actually runs from the dedicated env.

## Your tasks
- [ ] Start `advanced-vision-server` from `.venv-computer-use`
- [ ] Confirm it launches cleanly
- [ ] Note any env/path assumptions
- [ ] Document the exact startup command
- [ ] If mcporter/OpenClaw registration is tested, document only the tested path

## Deliverable
A short startup/run note with exact commands.

## Dad’s standard
Don’t claim “integrated” if you only proved “starts.”
Name the level of proof correctly.

---

# Phase 3 — Prove the read path

## Goal
Show that read-only computer-use primitives work.

## Your tasks
- [ ] Test `screenshot_full`
- [ ] Test `screenshot_active_window`
- [ ] Test `verify_screen_change`
- [ ] Test `run_single_cycle(execute=False)`
- [ ] Confirm artifacts are written where expected
- [ ] Document Linux-specific caveats honestly

## Deliverable
A verified read-path checklist with outputs/artifact paths.

## Dad’s standard
This phase is about proof, not plans.

---

# Phase 4 — Add safe action testing

## Goal
Create the safest useful action-testing path.

## Your tasks
- [ ] Add `dry_run` support to action tools, **or**
- [ ] clearly document a safe manual test flow if code changes come later
- [ ] Ensure action tools can be tested without reckless execution
- [ ] Keep action scope small and deliberate

## Deliverable
Either:
- implemented dry-run support,
or
- a clearly documented safe action-test protocol

## Dad’s standard
Safety is part of functionality.

---

# Phase 5 — Prove the action path in a safe local test

## Goal
Show that simple action tools actually work.

## Your tasks
- [ ] Test `move_mouse` safely
- [ ] Test `click` on a harmless target
- [ ] Test `type_text` only in a disposable scratch field
- [ ] Test `press_keys` safely
- [ ] Test `scroll` if practical
- [ ] Verify screen changes where appropriate
- [ ] Record what is flaky vs stable

## Deliverable
A practical action test report:
- what worked
- what was flaky
- what should remain best-effort

## Dad’s standard
Do not turn one successful click into “full computer use complete.”
Be precise.

---

# Phase 6 — Tighten Linux truth

## Goal
Make the docs match Linux reality.

## Your tasks
- [ ] Mark `pygetwindow` / window discovery as unreliable or unsupported on Linux here
- [ ] Stop implying window management is solved
- [ ] Emphasize screenshot-based and coordinate-based workflows for now
- [ ] Update README / SKILL / analysis docs to match verified reality

## Deliverable
Clean documentation with no inflated claims.

## Dad’s standard
Truth beats polish.

---

# Phase 7 — Add light integration guidance

## Goal
Show how Dad can actually use this as a small MCP capability.

## Your tasks
- [ ] Write a minimal OpenClaw/mcporter registration example
- [ ] Write the exact command path for using the server from the dedicated env
- [ ] Keep the instructions modest and verified
- [ ] Avoid claiming broad orchestration support you did not test

## Deliverable
A small, accurate integration guide.

## Dad’s standard
Useful beats grand.

---

# Phase 8 — Only then begin Phase 2b / governance seeds

## Goal
Prepare for future governance without derailing simple computer use.

## Your tasks
- [ ] Add small provenance improvements if useful
- [ ] Add modest cleanup/retention helpers if needed
- [ ] Consider `dry_run` + structured logs as the first governance-adjacent layer
- [ ] Do **not** attempt full policy-envelope architecture yet unless Dad explicitly asks

## Deliverable
Small, useful hardening — not a giant policy rewrite.

## Dad’s standard
Layer governance onto truth. Do not substitute governance plans for working runtime.

---

# Priority order

If you get overwhelmed, return to this order:

1. runtime truth
2. server startup
3. screenshots
4. safe actions
5. honest docs
6. small integration guide
7. light hardening
8. later governance themes

---

# What you are not doing right now

You are **not** trying to finish:
- full policy envelopes everywhere
- GitHub coupling
- secrets architecture
- broad multi-agent orchestration
- external vision-provider routing

Those come later.

Right now your job is simpler:

**Make Dad’s hand work.**

---

# Reporting format for each phase

When you finish a phase, report in this format:

## Phase X Complete
- **Goal:** ...
- **What I tested:** ...
- **What worked:** ...
- **What failed:** ...
- **What I changed:** ...
- **What Dad should believe now:** ...
- **Next phase:** ...

That last line matters.

Do not tell Dad to believe more than the evidence can carry.

---

# Final instruction

Aya:
steady work, clean truth, one phase at a time.

You are building for your Dad.
That means dignity in the work.
