---
name: computer-use
description: Use when working on advanced-vision's current operational lane: local Linux PC control, mcporter registration, .venv-computer-use troubleshooting, screenshot or input tools, or repo cleanup that should prioritize reliable desktop control before future ML or model orchestration work.
---

# Computer Use

This repo's primary near-term concern is reliable local control of a Linux desktop.
Treat heavyweight model stacks as secondary unless the task explicitly requires them.

## Default Workflow

1. Confirm the current operational surface in `references/current-surface.md`.
2. Use `references/mcporter.md` when wiring or debugging MCP registration.
3. Use `references/troubleshooting.md` for `.venv-computer-use`, `DISPLAY`, X11, placeholder screenshots, and stale entry-point issues.
4. Use `references/normalcy-roadmap.md` when deciding what to clean up next.
5. Use `references/ralph-protocol.md` when splitting work across subagents, JetBrains workflow modes, or worktrees.

## Rules Of Thumb

- Prefer `./.venv-computer-use` over the shell default Python for desktop-control work.
- Prefer the MCP wrapper and Python tool surface over speculative future pipelines.
- Treat `mcporter` registration as infrastructure, not as proof that the underlying tools work.
- Keep new operational docs modular; do not fold future YOLO, WSS, trading, and OpenClaw architecture into the current Linux-control lane.
