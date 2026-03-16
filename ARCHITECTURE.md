# Advanced Vision Architecture

## Purpose

This document describes a safe integration architecture for `advanced-vision` inside a larger governed system that also needs:

- GitHub access
- MCP-based service composition
- future computer-use workflows
- strong data-boundary protection

The central design principle is simple:

**Do not collapse planning, secrets, code access, and desktop control into one trust domain.**

`advanced-vision` should remain a narrow capability service: a hand, not a sovereign mind.

---

## Architectural goals

1. Enable local computer-use primitives safely.
2. Allow GitHub-based development workflows.
3. Support MCP composition across multiple services.
4. Prevent sensitive data from leaking across trust zones.
5. Preserve auditability, provenance, and policy enforcement.
6. Allow gradual evolution from local-only vision to external-model-backed vision.

---

## Current repository role

`advanced-vision` is currently a **local MCP server** exposing narrowly scoped computer-use primitives:

- screenshots
- active-window capture
- window listing
- mouse movement
- clicks
- typing
- keypress combos
- scrolling
- screen-change verification
- screenshot analysis via adapter abstraction

This is a strong foundation because it is already:

- local-first
- minimal
- composable
- not overloaded with unrelated powers

That separation should be preserved.

---

## Recommended system model

Use a **three-plane architecture**.

### 1. Control plane

The control plane is the governed executive layer.

Responsibilities:
- planning
- policy evaluation
- task decomposition
- approval routing
- trust-boundary enforcement
- provenance recording
- deciding which MCP/service may be called

The control plane should not directly own unrestricted desktop control, GitHub write authority, or raw secret storage.

### 2. Capability plane

The capability plane contains specialized MCP services.

Examples:
- `advanced-vision` MCP
- GitHub MCP
- workspace/file MCP
- browser MCP
- secrets broker MCP

Each capability service should be narrow, testable, and independently revocable.

### 3. Data / secret plane

The data plane contains sensitive assets and durable state.

Examples:
- GitHub credentials
- personal data
- private repositories
- canonical memory
- internal configs
- secret material
- logs requiring retention policy

Access to this plane should occur only through explicit, policy-enforced interfaces.

---

## High-level topology

```text
                          ┌──────────────────────────┐
                          │      Control Plane       │
                          │  Arbiter / Policy Brain  │
                          │                          │
                          │ - plan                   │
                          │ - approve                │
                          │ - route                  │
                          │ - enforce policy         │
                          └─────────────┬────────────┘
                                        │
                                        │ brokered calls
                                        ▼
                          ┌──────────────────────────┐
                          │      Policy Broker       │
                          │                          │
                          │ - tool allowlists        │
                          │ - approval classes       │
                          │ - redaction rules        │
                          │ - audit envelopes        │
                          └──────┬─────────┬─────────┘
                                 │         │
                    ┌────────────┘         └────────────┐
                    ▼                                   ▼
      ┌────────────────────────┐          ┌────────────────────────┐
      │ Advanced-Vision MCP    │          │ GitHub MCP / Worker    │
      │                        │          │                        │
      │ - screenshots          │          │ - issues / PRs         │
      │ - mouse/keyboard       │          │ - branches             │
      │ - verify screen        │          │ - commits / PR drafts  │
      │ - local UI actions     │          │ - scoped repo access   │
      └───────────┬────────────┘          └───────────┬────────────┘
                  │                                   │
                  ▼                                   ▼
      ┌────────────────────────┐          ┌────────────────────────┐
      │ Local Desktop Session  │          │ Isolated Repo Worker   │
      │ / GUI Environment      │          │ / Sandbox Clone        │
      └────────────────────────┘          └────────────────────────┘

                                 ┌────────────────────────┐
                                 │   Secrets / Data Plane │
                                 │                        │
                                 │ - tokens               │
                                 │ - canonical data       │
                                 │ - protected memory     │
                                 └────────────────────────┘
```

---

## Core design rule

### Separate powers by trust domain

Do not let one service simultaneously have:

- screen visibility
- keyboard/mouse control
- broad filesystem reach
- GitHub write credentials
- secret enumeration ability
- autonomous multi-step authority

Those powers should be distributed.

This reduces blast radius if any one service misbehaves or is compromised.

---

## Recommended service boundaries

### A. `advanced-vision` MCP

Purpose:
- local computer-use primitives only

Allowed responsibilities:
- capture screenshots
- inspect windows
- move mouse
- click
- type text
- press keys
- scroll
- verify visual change
- request screenshot analysis through an adapter

Should not own:
- GitHub credentials
- shell execution
- arbitrary file reads outside its artifact boundary
- browser automation logic beyond primitive UI actions
- long-horizon planning
- unrestricted network exfiltration

### B. GitHub MCP / worker

Purpose:
- safe source-control and issue workflow operations

Allowed responsibilities:
- read repository metadata
- read code from allowlisted repositories
- create branches
- stage changes
- create draft PRs
- comment on issues/PRs

Should not own:
- desktop control
- screenshot artifacts by default
- personal private data
- broad secret inventory access

### C. Secrets broker

Purpose:
- narrow release of credential material

Allowed responsibilities:
- return a specific token for a specific approved operation
- provide short-lived credentials where possible
- deny secret listing/browsing by default

Should not own:
- planning
- UI control
- repo manipulation

### D. Workspace / file MCP

Purpose:
- scoped project file access

Allowed responsibilities:
- operate only on allowlisted project roots
- enforce read/write policy by path
- return structured metadata on file provenance

Should not own:
- desktop control
- secret inventory
- unrestricted shell access

---

## Data protection strategy

### 1. Treat screenshots as potentially sensitive

Screenshots may contain:
- tokens
- private DMs
- browser sessions
- code
- internal dashboards
- family/personal data

Therefore screenshots should be classified, not treated as harmless artifacts.

Recommended classes:
- `public`
- `internal`
- `sensitive`
- `secret`

Suggested handling:
- `public`: standard retention allowed
- `internal`: retain briefly with local-only storage
- `sensitive`: short TTL and restricted access
- `secret`: avoid persistence where possible; if persisted, encrypt and expire quickly

### 2. Add retention policy

Current artifact storage is useful for debugging, but production architecture should add:
- screenshot TTL
- log TTL
- optional encrypted storage
- delete-on-success mode
- keep hashes/metadata longer than raw images

Recommended practice:
- keep structured action logs longer
- keep raw screenshots briefly
- allow explicit retention only when needed for debugging or audit

### 3. Redact before external analysis

If a real model-backed adapter is added later:
- do not send full desktop captures by default
- crop to task-relevant regions when possible
- redact known sensitive UI regions
- attach provenance metadata to each outbound request
- require policy approval for sending `sensitive` or `secret` screenshots off-host

---

## Approval model

Use action classes.

### Green actions
Low-risk actions that can be auto-approved:
- screenshot capture
- list windows
- verify screen change
- read GitHub issue metadata
- read allowlisted repository metadata

### Yellow actions
Useful but should be policy-checked and often logged prominently:
- click
- type text
- key combos
- branch creation
- draft PR creation
- reading selected code from private repos

### Red actions
High-risk actions requiring explicit approval:
- secret retrieval for write operations
- destructive git actions
- credential rotation
- broad repository writes
- sending sensitive screenshots to external providers
- multi-step autonomous UI execution beyond bounded scope

---

## GitHub integration model

### Principle

GitHub should be treated as a **code/task surface**, not as the place where trust boundaries disappear.

### Recommended GitHub pattern

Use one of:
- GitHub App installation tokens, or
- fine-grained PATs

Prefer:
- repo-specific scopes
- separate read-only and write credentials
- short-lived tokens where possible

### Split GitHub privileges

#### Read-only GitHub credential
Use for:
- issues
- pull requests
- commit metadata
- repository contents read
- labels / milestones read

#### Write-scoped GitHub credential
Use for:
- branch creation
- pushing approved changes
- opening draft PRs
- comments / status updates

Avoid granting by default:
- org admin
- repo admin
- secrets admin
- webhook admin
- package admin

---

## Computer-use integration model

### Keep `advanced-vision` local-first

`advanced-vision` should remain a local MCP server that:
- acts on the local desktop
- stores only bounded artifacts
- returns structured outputs
- does not directly decide long workflows

### Use proposal-before-execution

The preferred pattern is:
1. capture current screenshot
2. produce action proposal
3. run policy evaluation
4. optionally require human approval
5. execute action
6. verify visual change
7. log provenance

This preserves inspectability.

---

## MCP composition model

Do not build one mega-server.

Build one MCP per trust domain.

Recommended services:
- `advanced-vision`
- `github`
- `workspace`
- `secrets-broker`
- `browser` (later, if needed)
- `policy-broker` or equivalent orchestrator wrapper

Benefits:
- revocable capabilities
- easier auditing
- simpler testing
- clear blast-radius boundaries
- future compatibility with multi-agent orchestration

---

## Recommended workflow examples

### Example 1: Read a GitHub issue and inspect a local app

1. Control plane reads issue through GitHub MCP.
2. Policy broker determines local UI inspection is needed.
3. Broker calls `advanced-vision.screenshot_full`.
4. Screenshot is analyzed locally or through an approved adapter.
5. Broker returns a proposal to click/type if needed.
6. Human approval or yellow-policy autoapproval decides whether to act.
7. Action and before/after evidence are logged.

### Example 2: Open a PR after safe local validation

1. GitHub MCP reads issue and repo state.
2. Isolated repo worker prepares changes.
3. If a local app must be exercised, broker calls `advanced-vision`.
4. UI evidence is stored under retention policy.
5. Broker requests write credential from secrets broker only for PR creation.
6. GitHub MCP creates branch and draft PR.
7. Control plane records provenance and policy decision.

---

## Evolution roadmap

### Phase 1: Local-only safe baseline
- keep `advanced-vision` local
- no external vision provider
- read-only GitHub integration
- artifact retention policy
- structured logs

### Phase 2: Brokered multi-service architecture
- add policy broker
- add secrets broker
- split GitHub read/write credentials
- add repo allowlists and path allowlists

### Phase 3: Model-backed screenshot analysis
- replace stub adapter with pluggable real adapter
- redaction/cropping before external calls
- explicit approval classes for off-host image analysis
- provider-specific policy rules

### Phase 4: Bounded semi-autonomous workflows
- limited multi-step UI tasks
- checkpointing between steps
- rollback policy where possible
- human approval at risk boundaries

---

## Recommended changes to this repository over time

### Add policy envelope metadata
Each MCP tool invocation should be able to carry:
- requester
- session id
- task id
- sensitivity classification
- approval state
- provenance id

### Add artifact policy config
Expand settings to support:
- screenshot retention TTL
- log retention TTL
- screenshot persistence on/off
- redaction configuration
- encryption mode
- delete-on-success behavior

### Add proposal-only mode for action tools
Support returning a proposed action without executing it.
This should be the default integration mode for higher-risk environments.

### Add provenance logging
For every action cycle, store:
- before screenshot hash
- proposal
- execution status
- after screenshot hash
- verification result
- actor and session metadata

### Add capability toggles
Allow runtime disabling of:
- typing
- key combos
- right click
- scroll
- active-window capture
- external vision adapter use

---

## Bottom line

`advanced-vision` should stay small, local, and capability-focused.

The right architecture is not:
- one giant autonomous agent with GitHub, secrets, and mouse control

The right architecture is:
- governed control plane
- brokered policy enforcement
- separate MCP services by trust domain
- minimal scoped credentials
- explicit retention/redaction rules
- auditable provenance around every sensitive action

That approach protects data without blocking progress.
