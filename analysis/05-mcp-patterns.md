# MCP Patterns for Advanced Vision

**Purpose:** define the simplest useful MCP pattern for `advanced-vision` right now.

## Principle

Do not design this repo as a full governed automation framework yet.
Design it first as a **small, dependable MCP server for local computer-use primitives**.

That means the immediate pattern is:
- expose narrow tools
- keep request/response shapes simple
- prefer real working primitives over speculative governance surface
- layer governance later, after runtime behavior is proven

---

## Recommended Phase 2 MCP pattern

### Server role
`advanced-vision` should act as a **local capability server**.

It should provide:
- screen capture
- visual verification
- basic input primitives
- simple screenshot analysis hook

It should not yet try to be:
- a planner
- a secrets broker
- a browser automation framework
- a governance engine
- a full task orchestrator

---

## Tool categories

### 1. Read-only visual tools
Low-risk tools that inspect the local UI.

Recommended:
- `screenshot_full`
- `screenshot_active_window` (best effort)
- `list_windows` (best effort, but currently unreliable on Linux)
- `verify_screen_change`
- `analyze_screenshot`

These are the easiest tools to stabilize first.

### 2. Input/action tools
Higher-risk but still primitive local actions.

Recommended:
- `move_mouse`
- `click`
- `type_text`
- `press_keys`
- `scroll`

These should be treated as **simple imperative actions**, not autonomous behaviors.

---

## Response pattern

For Phase 2, keep tool outputs close to current schemas:
- `ScreenshotArtifact`
- `WindowInfo`
- `ActionResult`
- `VerificationResult`
- `ActionProposal`

That is enough for:
- local testing
- MCP integration
- orchestration by a higher layer later

Do not overcomplicate the MCP interface yet with a full policy envelope unless the calling system actually needs it immediately.

---

## Dry-run pattern

The one governance-adjacent addition worth doing early is `dry_run` for input tools.

Why:
- helps testing
- helps demos
- reduces risk
- does not require full governance infrastructure

Recommended Phase 2 behavior:
- read-only tools ignore `dry_run`
- input tools accept optional `dry_run: bool = false`
- when `dry_run=true`, return what would happen without executing

---

## Artifact pattern

Keep artifact handling simple for now:
- screenshots go to `artifacts/screens/`
- logs go to `artifacts/logs/`
- structured outputs remain JSON serializable

Recommended small improvement:
- add optional cleanup tooling later in Phase 2b or Phase 3
- do not block runtime validation on a full retention system yet

---

## Linux reality pattern

On Linux, separate tools by practical reliability:

### reliable enough now
- screenshot capture
- verification
- pyautogui import in dedicated env

### unreliable or host-dependent
- window discovery via `pygetwindow`
- input behavior across different display/session setups

So Phase 2 should not depend heavily on window enumeration.

Prefer:
- screenshot-based interaction
- coordinate-based safe testing
- verification after action

---

## Best immediate orchestration loop

The simplest useful loop remains:

1. `screenshot_full`
2. `analyze_screenshot` (stub or later real adapter)
3. optionally `move_mouse` / `click` / `type_text`
4. `verify_screen_change`

That is enough to prove the substrate.

---

## What to postpone

Postpone until later phases:
- full policy envelope everywhere
- secrets integration
- GitHub coupling
- external model egress policy
- broad provenance chain design
- approval-class plumbing in every tool

Those are important, but they should be layered onto a working substrate.

---

## Bottom line

The right MCP pattern for this repo **right now** is:
- small
- local
- capability-first
- dry-run-aware for actions
- honest about Linux window-management limitations

Build the hand first.
Govern the hand more deeply after it reliably moves.
