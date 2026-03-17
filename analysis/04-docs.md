# Documentation Analysis: advanced-vision Repository

## Document Inventory

| Document | Purpose | Key Focus |
|----------|---------|-----------|
| README.md | Project overview, quick start, features | Current capabilities and non-goals |
| ARCHITECTURE.md | Three-plane system design | Trust boundaries and security architecture |
| SKILL.md | Skill documentation for agent context | Phase tracking and implementation status |
| COMPUTER_USE_ENV.md | Environment setup validation | Python 3.11 + GUI stack configuration |
| AGENT_SWARM_CONTRACT.md | Swarm task decomposition | Parallel analysis strategy for Phase 2 planning |
| SERVICE_CONTRACTS.md | Service interface specifications | Request/response envelopes and contracts |
| brain/README.md | Engineering notebook intro | Working principles and file organization |
| brain/PHASES.md | Implementation roadmap | 6-phase progression plan |
| brain/TASKS.md | Actionable checklist | Completed and pending tasks |
| brain/ISSUES.md | Discovered blockers | Environment and runtime issues |
| brain/FIXES.md | Changes made | Documentation and diagnostics additions |
| brain/WORKLOG.md | Chronological notes | Daily progress and findings |

---

## 1. Design Patterns and Architecture Decisions

### Three-Plane Architecture
The core architectural pattern is a **three-plane separation of concerns**:

1. **Control Plane** - The governed executive layer
   - Planning, policy evaluation, task decomposition
   - Approval routing, trust-boundary enforcement
   - Provenance recording, service orchestration

2. **Capability Plane** - Specialized MCP services
   - `advanced-vision` (computer-use primitives)
   - GitHub MCP (repo operations)
   - Workspace/file MCP (scoped file access)
   - Secrets broker MCP (credential management)

3. **Data/Secret Plane** - Sensitive assets and durable state
   - GitHub credentials, personal data, private repos
   - Canonical memory, internal configs
   - Protected through explicit policy-enforced interfaces

### Trust Domain Separation
**Core design rule**: Do not collapse planning, secrets, code access, and desktop control into one trust domain.

Powers are distributed to reduce blast radius:
- Screen visibility + keyboard/mouse control ≠ filesystem reach
- GitHub write credentials ≠ desktop control
- Secret enumeration ≠ autonomous multi-step authority

### MCP Composition Model
- **One MCP per trust domain** (not one mega-server)
- Revocable capabilities, easier auditing, simpler testing
- Clear blast-radius boundaries
- Future compatibility with multi-agent orchestration

### Proposal-Before-Execution Pattern
Preferred workflow for UI actions:
1. Capture current screenshot
2. Produce action proposal
3. Run policy evaluation
4. Optionally require human approval
5. Execute action
6. Verify visual change
7. Log provenance

---

## 2. Intended Behavior and Capabilities

### Current Implemented Tools (MCP Server)

| Tool | Function | Status |
|------|----------|--------|
| `screenshot_full` | Capture entire screen | ✅ Working |
| `screenshot_active_window` | Capture focused window | ✅ Working (fallback to full) |
| `list_windows` | List open windows | ⚠️ Returns 0 on this host |
| `move_mouse` | Move cursor to coordinates | 📋 Planned |
| `click` | Mouse click (left/right) | 📋 Planned |
| `type_text` | Type text | 📋 Planned |
| `press_keys` | Key combinations | 📋 Planned |
| `scroll` | Vertical/horizontal scroll | 📋 Planned |
| `verify_screen_change` | Verify visual change | ✅ Working |
| `analyze_screenshot` | Vision analysis via adapter | ⚠️ Stub only |

### Environment Configuration
- **Runtime**: Python 3.11 (dedicated venv: `.venv-computer-use`)
- **Protocol**: MCP (Model Context Protocol)
- **Host**: Local only (no external APIs by default)
- **Artifacts**: Screenshots → `artifacts/screens/`, Logs → `artifacts/logs/`

### Stubbed by Design
- `vision_adapter.py` returns deterministic noop `ActionProposal`
- No external vision API calls (no secrets/API keys)
- Allows infrastructure testing without intelligence dependencies

### Approval Classes

| Class | Actions | Approval |
|-------|---------|----------|
| **Green** | screenshot, list windows, verify change, read issue metadata | Auto-approve |
| **Yellow** | click, type, key combos, create branch, draft PR | Policy-checked, logged |
| **Red** | secret retrieval, destructive git, credential rotation, sensitive screenshot external analysis | Explicit approval required |

---

## 3. Current Limitations and Gaps

### Environment Blockers (Identified in brain/ISSUES.md)

1. **Input tools blocked on tkinter**
   - `pyautogui` → `mouseinfo` requires `python3-tk`, `python3-dev`, `scrot`
   - Screenshot path works, input path not yet operational
   - Linuxbrew Python 3.14 may need different strategy than system packages

2. **Window listing returns empty**
   - `list_windows()` returns 0 windows on this host
   - Headless/minimal desktop environment limitation

3. **Vision adapter is stub only**
   - Returns deterministic noop, no real analysis
   - Infrastructure ready, intelligence not connected

### Governance Gaps

| Gap | Impact | Recommended Fix |
|-----|--------|-----------------|
| No retention policy | Sensitive screenshots accumulate | Add TTL settings, delete-on-success mode |
| No policy envelope in tools | Harder to integrate into governed orchestration | Add request_id, task_id, approval_class, classification params |
| No dry-run mode | Cannot preview actions before execution | Add dry_run flag to action tools |
| No artifact classification | All screenshots treated equally | Add public/internal/sensitive/secret classes |
| Limited provenance logging | Missing actor/session metadata | Expand logging_utils with full provenance chain |

### Integration Gaps

| Gap | Status |
|-----|--------|
| MCP server integration with OpenClaw | 📋 Pending (Phase 2) |
| Real vision adapter implementation | 📋 Pending (Phase 5) |
| Policy broker wrapper | 📋 Pending (Phase 4) |
| GitHub service integration | 📋 Pending (Phase 6) |
| Secrets broker | 📋 Pending (Phase 4+) |

---

## 4. Integration Requirements

### For OpenClaw Integration

**From SKILL.md:**
- MCP server entry point
- Tool definitions for OpenClaw
- Screenshot, mouse/keyboard, window management tools

**Required files:**
- `src/mcp_server.py` - MCP server entry point (pending)
- Tool schemas matching OpenClaw expectations

### Service Contract Requirements

From SERVICE_CONTRACTS.md, all services should support:

**Common Envelope Fields:**
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

**Required Controls:**
- Service name + action name validation
- Data classification enforcement
- External egress approval for screenshots
- Write vs read scope separation
- Explicit approval for yellow/red actions

### Recommended Extensions

**Add to advanced-vision:**
- `dry_run` parameter for action tools
- `persist` and `retention_ttl_seconds` for screenshots
- `classification` metadata (public/internal/sensitive/secret)
- `allow_external_model` flag for vision adapter
- Capability toggles (disable typing, key combos, etc.)

**Artifact Policy Config:**
- Screenshot retention TTL
- Log retention TTL
- Encrypted storage option
- Delete-on-success behavior
- Keep hashes/metadata longer than raw images

---

## 5. Implementation Phases (from brain/PHASES.md)

| Phase | Goal | Status |
|-------|------|--------|
| Phase 0 | Repo intake, blockers documented | ✅ Complete |
| Phase 1 | Local execution readiness | ✅ Complete |
| Phase 2 | Basic runtime validation | ✅ Partial (screenshots work, input blocked) |
| Phase 3 | Live tool-use validation | 📋 Pending (needs tkinter fix) |
| Phase 4 | Governance hardening | 📋 Pending |
| Phase 5 | Real vision integration | 📋 Pending |
| Phase 6 | GitHub + MCP orchestration | 📋 Pending |

---

## 6. Key Architectural Principles Summary

1. **Narrow capability services** - `advanced-vision` is a hand, not a sovereign mind
2. **Explicit trust boundaries** - Never combine desktop control + GitHub write + secrets
3. **Policy-gated actions** - Green/Yellow/Red approval classes with audit trails
4. **Local-first default** - No external vision API calls without explicit policy approval
5. **Structured I/O** - Pydantic schemas, common envelopes, provenance metadata
6. **Intentional retention** - Artifacts classified and TTL-managed

---

## 7. Documentation Quality Assessment

| Strength | Evidence |
|----------|----------|
| Comprehensive architecture docs | ARCHITECTURE.md, SERVICE_CONTRACTS.md define clear patterns |
| Honest status tracking | SKILL.md, brain/ files show real progress vs. planned |
| Security-first design | Trust boundaries, approval classes, data classification throughout |
| Actionable task breakdown | brain/TASKS.md, brain/PHASES.md provide clear roadmap |

| Gap | Evidence |
|-----|----------|
| MCP server not yet implemented | SKILL.md lists as "pending", no src/mcp_server.py |
| Input tools not validated | brain/ISSUES.md #5 documents tkinter blocker |
| No OpenClaw-specific integration guide | Missing: how to register with OpenClaw gateway |

---

*Analysis Date: 2026-03-16*
*Documents Reviewed: 12 markdown files*
