# Service Contracts

This document is a forward-looking integration reference.

The repo's current first-class operating lane is still local Linux computer use
via MCP. Use `README.md` and `COMPUTER_USE_ENV.md` first for day-to-day setup and
runtime truth, then come here when the task is specifically about cross-service
integration boundaries.

This document defines recommended service contracts for integrating `advanced-vision` into a larger governed system.

The goal is to enable:
- safe computer use
- GitHub-connected workflows
- MCP composition
- policy enforcement
- durable provenance

The contracts below are intentionally operational rather than theoretical.

---

## Design principles

1. **One service per trust domain.**
2. **Structured I/O over implicit behavior.**
3. **Policy metadata travels with every request.**
4. **Secrets are requested, not ambiently available.**
5. **Write authority is narrower than read authority.**
6. **Artifacts are classified and retained intentionally.**
7. **Every sensitive action should leave evidence.**

---

## Common envelope

All service calls should support a common envelope, whether implemented directly in MCP arguments, wrapper middleware, or broker-managed metadata.

### Request envelope

```json
{
  "request_id": "req_123",
  "task_id": "task_456",
  "session_id": "sess_789",
  "requester": {
    "agent_id": "arbiter",
    "user_id": "1302555752",
    "surface": "telegram"
  },
  "policy": {
    "approval_class": "yellow",
    "approved": false,
    "data_classification": "internal"
  },
  "provenance": {
    "parent_event_id": "evt_001",
    "trace_id": "trace_abc"
  }
}
```

### Response envelope

```json
{
  "request_id": "req_123",
  "ok": true,
  "result": {},
  "audit": {
    "service": "advanced-vision",
    "action": "screenshot_full",
    "timestamp": "2026-03-16T18:00:00Z"
  },
  "artifacts": [],
  "warnings": []
}
```

### Envelope fields

#### Required
- `request_id`
- `task_id`
- `session_id`
- `requester.agent_id`
- `policy.approval_class`
- `policy.data_classification`

#### Strongly recommended
- `provenance.trace_id`
- `provenance.parent_event_id`
- `requester.user_id`
- `requester.surface`

---

## 1. Advanced-Vision service contract

### Purpose

Provide narrowly scoped local computer-use primitives.

### Trust boundary

This service controls the local GUI and can observe the local display.
It should **not** have ambient GitHub credentials or broad secret access.

### Allowed responsibilities
- screenshot capture
- window listing
- pointer movement
- click execution
- text entry
- keypress combos
- scroll
- visual verification
- screenshot analysis through an adapter

### Forbidden by default
- secret retrieval
- arbitrary shell execution
- unrestricted filesystem traversal
- GitHub operations
- network exfiltration of screenshots unless policy-approved

### Recommended tool contract shape

#### `screenshot_full`

Request:
```json
{
  "request_id": "req_1",
  "task_id": "task_ui_1",
  "session_id": "sess_1",
  "policy": {
    "approval_class": "green",
    "data_classification": "internal"
  },
  "persist": true,
  "retention_ttl_seconds": 3600
}
```

Response:
```json
{
  "ok": true,
  "result": {
    "path": "artifacts/screens/screen-001.png",
    "width": 1920,
    "height": 1080,
    "sha256": "...",
    "classification": "internal"
  },
  "artifacts": [
    {
      "type": "screenshot",
      "path": "artifacts/screens/screen-001.png",
      "retention_ttl_seconds": 3600
    }
  ]
}
```

#### `analyze_screenshot`

Request:
```json
{
  "request_id": "req_2",
  "task_id": "task_ui_1",
  "session_id": "sess_1",
  "policy": {
    "approval_class": "green",
    "data_classification": "internal",
    "allow_external_model": false
  },
  "screenshot_path": "artifacts/screens/screen-001.png",
  "task": "Identify whether the login dialog is visible"
}
```

Response:
```json
{
  "ok": true,
  "result": {
    "action_type": "noop",
    "confidence": 0.82,
    "rationale": "Login dialog detected. No UI action requested."
  }
}
```

#### `click`

Request:
```json
{
  "request_id": "req_3",
  "task_id": "task_ui_1",
  "session_id": "sess_1",
  "policy": {
    "approval_class": "yellow",
    "approved": true,
    "data_classification": "internal"
  },
  "x": 812,
  "y": 644,
  "button": "left",
  "dry_run": false
}
```

Response:
```json
{
  "ok": true,
  "result": {
    "action": "click",
    "x": 812,
    "y": 644,
    "button": "left",
    "executed": true
  }
}
```

### Recommended extensions for this repo

Add support for:
- `dry_run`
- `persist`
- `retention_ttl_seconds`
- `classification`
- `allow_external_model`
- `trace_id`
- before/after screenshot hash recording

### Audit requirements

Every action should capture:
- request metadata
- before-state artifact hash when relevant
- proposed or executed action
- after-state artifact hash when relevant
- verification result
- warnings/failures

---

## 2. GitHub service contract

### Purpose

Provide narrow, policy-governed access to GitHub repos and workflows.

### Trust boundary

This service touches source code and repository state.
It should not control the desktop and should not have broad personal-memory access.

### Credential split

Use distinct credentials for:
- read operations
- write operations

### Allowed read operations
- list repositories
- get issue/PR metadata
- read file contents from allowlisted repos
- inspect branches and commits
- read CI status

### Allowed write operations
- create branch
- commit approved changes
- open draft PR
- comment on issue/PR

### Forbidden by default
- org-wide admin
- secret management
- webhook management
- repo deletion
- forced pushes
- broad write across all repos

### Contract examples

#### `get_issue`

Request:
```json
{
  "request_id": "req_10",
  "task_id": "task_repo_1",
  "session_id": "sess_1",
  "policy": {
    "approval_class": "green",
    "data_classification": "internal"
  },
  "repo": "shetautnetjer/advanced-vision",
  "issue_number": 12
}
```

Response:
```json
{
  "ok": true,
  "result": {
    "repo": "shetautnetjer/advanced-vision",
    "issue_number": 12,
    "title": "Add policy envelope support",
    "state": "open",
    "labels": ["enhancement"]
  }
}
```

#### `read_file`

Request:
```json
{
  "request_id": "req_11",
  "task_id": "task_repo_1",
  "session_id": "sess_1",
  "policy": {
    "approval_class": "green",
    "data_classification": "internal"
  },
  "repo": "shetautnetjer/advanced-vision",
  "ref": "main",
  "path": "src/advanced_vision/server.py"
}
```

#### `create_branch`

Request:
```json
{
  "request_id": "req_12",
  "task_id": "task_repo_write_1",
  "session_id": "sess_1",
  "policy": {
    "approval_class": "yellow",
    "approved": true,
    "data_classification": "internal"
  },
  "repo": "shetautnetjer/advanced-vision",
  "base": "main",
  "branch": "feat/policy-envelope"
}
```

#### `open_draft_pr`

Request:
```json
{
  "request_id": "req_13",
  "task_id": "task_repo_write_1",
  "session_id": "sess_1",
  "policy": {
    "approval_class": "yellow",
    "approved": true,
    "data_classification": "internal"
  },
  "repo": "shetautnetjer/advanced-vision",
  "head": "feat/policy-envelope",
  "base": "main",
  "title": "Add policy envelope support",
  "body": "This PR adds request envelope metadata..."
}
```

### Required policy controls

- repo allowlist
- operation allowlist
- scope separation between read and write
- audit log for all writes
- optional branch naming policy

---

## 3. Policy broker contract

### Purpose

Act as the enforcement layer between planning/orchestration and capability services.

### Responsibilities
- authorize or deny requests
- classify risk
- attach approval state
- enforce repo/path/provider allowlists
- apply screenshot/data redaction policy
- record decisions for audit

### Input
The broker should accept a normalized action request like:

```json
{
  "request_id": "req_20",
  "task_id": "task_1",
  "session_id": "sess_1",
  "actor": "arbiter",
  "target_service": "advanced-vision",
  "target_action": "click",
  "payload": {
    "x": 500,
    "y": 300,
    "button": "left"
  },
  "context": {
    "data_classification": "internal",
    "repo": null,
    "requires_external_model": false
  }
}
```

### Output
```json
{
  "ok": true,
  "decision": "allow",
  "approval_class": "yellow",
  "approved": true,
  "constraints": {
    "persist_artifacts": true,
    "retention_ttl_seconds": 1800,
    "allow_external_model": false
  },
  "reason": "Bounded local UI click in internal desktop context"
}
```

### Deny example
```json
{
  "ok": true,
  "decision": "deny",
  "approval_class": "red",
  "approved": false,
  "reason": "Sensitive screenshot cannot be sent to external vision provider without explicit approval"
}
```

### Required policy dimensions

- service name
- action name
- data classification
- external egress yes/no
- repo target
- path target
- write vs read
- requester identity
- explicit approval presence

---

## 4. Secrets broker contract

### Purpose

Release only the credential needed for a specific approved action.

### Responsibilities
- no ambient secret listing
- narrow retrieval by name and purpose
- optional short-lived tokens
- audit all releases

### Request
```json
{
  "request_id": "req_30",
  "task_id": "task_repo_write_1",
  "session_id": "sess_1",
  "requester": {
    "agent_id": "arbiter"
  },
  "policy": {
    "approval_class": "red",
    "approved": true,
    "data_classification": "secret"
  },
  "secret_ref": "github/write/advanced-vision",
  "purpose": "open_draft_pr",
  "ttl_seconds": 600
}
```

### Response
```json
{
  "ok": true,
  "result": {
    "secret_type": "token",
    "value": "<redacted-runtime-only>",
    "expires_at": "2026-03-16T18:10:00Z"
  },
  "audit": {
    "secret_ref": "github/write/advanced-vision",
    "purpose": "open_draft_pr"
  }
}
```

### Hard rules

- no `list_all_secrets`
- no wildcard retrieval
- every retrieval tied to a purpose
- every retrieval tied to approval state
- every retrieval logged

---

## 5. Workspace / file service contract

### Purpose

Provide scoped file access to approved project roots.

### Responsibilities
- read/write within allowlisted roots
- enforce path normalization
- reject path traversal
- optionally classify files by sensitivity

### Request
```json
{
  "request_id": "req_40",
  "task_id": "task_repo_2",
  "session_id": "sess_1",
  "policy": {
    "approval_class": "green",
    "data_classification": "internal"
  },
  "workspace_root": "/projects/advanced-vision",
  "path": "src/advanced_vision/server.py"
}
```

### Controls
- path must resolve inside declared root
- root must be allowlisted
- writes may require higher approval than reads
- protected files may need elevated approval

---

## 6. Vision adapter contract

### Purpose

Allow `advanced-vision` to use either:
- a local adapter, or
- an external model-backed adapter

without changing the rest of the system.

### Interface

Input:
- image reference
- task prompt
- classification
- external egress permission
- redaction metadata

Output:
- structured `ActionProposal`
- confidence
- rationale
- model/provider metadata
- whether any data left host boundaries

### Request example
```json
{
  "request_id": "req_50",
  "task": "Find the browser address bar",
  "image_path": "artifacts/screens/screen-001.png",
  "classification": "internal",
  "allow_external_model": false,
  "redaction_profile": "default-internal"
}
```

### Response example
```json
{
  "ok": true,
  "result": {
    "action_type": "click",
    "x": 423,
    "y": 51,
    "confidence": 0.88,
    "rationale": "Address bar detected at top center of browser window"
  },
  "audit": {
    "provider": "local-stub",
    "external_egress": false
  }
}
```

---

## Contract-level security requirements

### For all services
- request ids mandatory
- structured responses only
- no silent side effects
- audit record on every write or secret touch
- explicit classification for artifacts
- deny-by-default when policy metadata is missing

### For all write-capable services
- require `approved: true` for yellow/red actions
- record actor + session + task
- attach provenance reference to each action

### For any external egress
- require explicit allow flag
- classify outgoing data
- log destination provider/service
- log whether payload was redacted or cropped

---

## Suggested implementation order

### Stage 1
- define common request/response envelope
- keep `advanced-vision` local-only
- add dry-run support
- add artifact classification and TTL

### Stage 2
- introduce policy broker wrapper
- add GitHub service with read-only credential
- add audit records around all service calls

### Stage 3
- add write-scoped GitHub operations
- add secrets broker
- add external vision adapter support behind policy gate

### Stage 4
- support bounded multi-step task flows
- checkpoint approvals at risk boundaries
- add stronger provenance chain linking all events

---

## Bottom line

These contracts are meant to preserve one key property:

**the system can become more capable without becoming flatly overtrusted.**

That means:
- `advanced-vision` stays a local capability server
- GitHub access stays scoped and brokered
- secrets are released narrowly
- policy decisions are explicit
- artifacts are retained intentionally
- provenance remains legible
