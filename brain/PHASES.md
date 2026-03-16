# Implementation Phases

## Phase 0 — Reality check / repo intake

Goal:
- understand current code
- identify blockers
- avoid pretending the stack is runnable before it is proven

Exit criteria:
- repo assessed
- blockers documented
- architecture direction documented

Status: in progress

---

## Phase 1 — Local execution readiness

Goal:
- make setup predictable on this host

Tasks:
- update README to use `python3`
- create `.venv`
- install editable package with dev dependencies
- add diagnostics command/script
- confirm imports work

Exit criteria:
- dependencies installed cleanly
- diagnostics report generated

---

## Phase 2 — Basic runtime validation

Goal:
- prove the minimal stack actually runs

Tasks:
- run tests
- start MCP server
- capture full screenshot
- capture active window (or verify fallback)
- list windows
- run `run_single_cycle(execute=False)`

Exit criteria:
- all tests passing or failures explained
- server starts successfully
- screenshot and verification tools produce artifacts

---

## Phase 3 — Live tool-use validation

Goal:
- verify controlled interaction primitives

Tasks:
- test mouse movement
- test click in a safe local context
- test type_text in a safe local context
- test keypress and scroll behavior
- document GUI/backend limitations

Exit criteria:
- tool actions confirmed working or safely degraded
- runtime limitations documented

---

## Phase 4 — Governance hardening

Goal:
- make the capability safe to integrate into a larger system

Tasks:
- add request/policy metadata support
- add artifact classification and retention controls
- add dry-run / proposal-first execution mode
- add provenance logging improvements

Exit criteria:
- service is not just runnable, but governable

---

## Phase 5 — Real vision integration

Goal:
- upgrade from stub analysis to useful computer vision

Tasks:
- add pluggable adapter interface implementation
- support local or remote model-backed analysis
- add redaction/cropping policy before external calls
- log provider usage and egress decisions

Exit criteria:
- screenshot analysis can propose useful structured actions
- external model use is policy-gated

---

## Phase 6 — GitHub + MCP orchestration

Goal:
- connect advanced-vision safely into a repo-aware workflow

Tasks:
- integrate with GitHub service through brokered contracts
- keep GitHub credentials separated from desktop-control service
- add per-task provenance linking

Exit criteria:
- GitHub and computer-use workflows cooperate without flattening trust boundaries
