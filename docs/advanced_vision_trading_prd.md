# Product Requirements Document (PRD)
## Advanced Vision Watcher for Desktop Scout + Trading Watch Modes

**Project scope:** advanced-vision capability slice for local computer watching, UI change understanding, and governed escalation into stronger local/cloud reasoning.

**Primary repos affected:**
- `advanced-vision` — primary implementation surface
- `OpenClaw` — future orchestration/runtime integration
- `Brain-harness` — doctrine, schemas, promotion, memory, and governance alignment

**Document status:** Draft PRD v1
**Primary plane:** Plane A working/operational system with governed escalation and selective promotion into Plane B artifacts

---

## 1. Executive summary

This product adds a local-first visual attention system that behaves more like a careful human sitting at the PC than a single giant model staring at every pixel. The system continuously watches a desktop or app stream, ignores obvious noise such as cursor-only motion, notices meaningful UI changes, tracks targeted regions over time, classifies those changes, and escalates only when warranted.

The product has two main operating modes:

1. **Desktop Scout Mode**
   - Lightweight continuous awareness for normal computer use.
   - Goal: notice meaningful changes, classify what happened, and avoid unnecessary pauses.
   - Typical output: structured notes, event logs, candidate UI changes, optional notifications.

2. **Trading Watch Mode**
   - Higher-sensitivity monitoring for charting and order-entry workflows.
   - Goal: detect trading-relevant UI changes, anomalies, warnings, and execution-risk states.
   - Typical output: structured evidence, local reviewer judgment, Kimi second-opinion escalation, governed pause/warn/hold recommendations.

This PRD formalizes the product goals, user outcomes, requirements, constraints, metrics, risks, and phased delivery plan. It builds directly on the existing watcher architecture and doctrine: local-first perception, specialized model roles, append-only event history, replayable episodes, safe escalation, and strict separation between working evidence and canonical truth. fileciteturn2file2 fileciteturn2file0

---

## 2. Problem statement

Current computer-use and vision-agent patterns often fail because they overuse expensive models, treat every visual change as equally important, and blur the line between observation and authority. That causes:

- needless pauses and latency
- hallucinated UI understanding
- poor responsiveness during active computer use
- brittle behavior in chart-heavy or high-risk workflows
- weak replay/debuggability after failures
- unsafe escalation of raw sensitive imagery to stronger cloud models

For trading specifically, the cost of false positives, missed warnings, or laggy screen reasoning is high. The system must distinguish between harmless motion and meaningful state changes, while preserving a structured evidence trail and routing higher-stakes judgments through stronger review and governance.

---

## 3. Product vision

Build a local-first visual watcher that:

- behaves like a human attention stack rather than a monolithic all-seeing model
- uses cheap reflexes first, targeted visual analysis second, and deliberate judgment last
- treats model outputs as advisory evidence rather than transport truth or autonomous authority
- supports both everyday desktop awareness and high-sensitivity trading workflows
- records replayable events and curated artifacts for debugging, retrieval, and coaching
- escalates to stronger models only with minimal, sanitized, structured evidence bundles

The product should feel like:

**observe → filter noise → classify change → track ROI → summarize evidence → escalate if needed → review → govern → continue/resume**

This aligns with the broader doctrine of trust-aware retrieval, governed learning, replayable event history, and validation-before-promotion. fileciteturn2file0

---

## 4. Goals

### 4.1 Primary goals

1. Provide continuous local screen monitoring without making the PC feel sluggish.
2. Ignore non-meaningful motion such as pointer-only movement, animations, and transient visual clutter whenever possible.
3. Detect and classify meaningful UI changes such as modals, warnings, chart-area changes, tickets, confirmation dialogs, and stateful panels.
4. Support a lightweight scout model for fast image-burst classification and evidence jotting.
5. Support a stronger reviewer model for higher-stakes interpretation in trading workflows.
6. Escalate selected evidence to Kimi for second-opinion review when needed.
7. Keep event history append-only, replayable, and inspectable.
8. Preserve governance boundaries between working evidence and promoted canonical knowledge.

### 4.2 Secondary goals

1. Support future retrieval and episode-learning from captured ROI evidence.
2. Create a reusable watcher stack that can later integrate with OpenClaw and Brain-harness without redesigning subsystem boundaries.
3. Allow mode-specific tuning for desktop use vs trading use.
4. Produce structured, machine-readable artifacts that later components can consume safely.

---

## 5. Non-goals

The following are explicitly out of scope for the initial product release:

1. Fully autonomous trading execution with no human or policy gate.
2. Treating vector stores as the source of truth.
3. Uploading raw unredacted desktop footage to cloud models by default.
4. Replacing Brain-harness governance with ad hoc model-only policy.
5. Designing the final full watcher ecosystem in one step.
6. Using one giant multimodal model as the only perception, tracking, reading, and judgment system.
7. Turning notifier outputs into authoritative delivery truth.

These non-goals preserve repo boundaries and doctrine. `advanced-vision` remains the capability surface; governance and promotion continue to belong to the harness layer. fileciteturn2file0 fileciteturn2file1

---

## 6. Users and use cases

### 6.1 Primary user

The primary user is a technically ambitious local-first operator who wants the computer to feel like an attentive assistant that can watch, notice, interpret, and escalate important visual events on the desktop, especially in trading contexts.

### 6.2 Primary use cases

#### A. Desktop Scout Mode

The user is browsing, coding, managing windows, or generally working at the PC. They want the system to:

- ignore the cursor or small incidental motion
- notice meaningful popups, dialogs, notifications, and window changes
- recognize that a detected object is “just the mouse,” “just a tooltip,” or “a real UI element that changed”
- continue normal operation without freezing or overreacting
- jot structured notes about important changes

#### B. Trading Watch Mode

The user is actively trading or reviewing markets. They want the system to:

- watch chart panels, order tickets, confirm modals, alerts, and risk widgets
- notice spread changes, slippage warnings, symbol mismatches, route warnings, or unexpected confirmation dialogs
- produce a local assessment of what changed and why it matters
- ask for a second opinion from Kimi when uncertainty or risk is high
- behave as if a careful human were sitting at the machine and checking the workflow

#### C. Review and replay

After an incident or suspicious event, the user wants to:

- replay what happened
- inspect the exact ROI crops and event timeline
- see why the scout/reviewer escalated or failed to escalate
- store labeled evidence for later learning and retrieval

---

## 7. Product principles

### 7.1 Local-first operation

The product must prioritize local capture, local filtering, local tracking, and local judgment before cloud escalation.

### 7.2 Specialized model roles

Each model has a constrained role:

- reflex/change detection
- detection/tripwire
- tracking/segmentation
- UI reading/structure extraction
- scout summarization
- reviewer judgment
- cloud overseer

This follows the existing watcher doctrine that watcher, embedder, reranker, and escalation models are separate roles. fileciteturn2file2

### 7.3 Evidence before conclusion

The system should prefer:

- ROI crops
- tracked regions
- structured event JSON
- timelines
- clip/keyframe bundles

over freeform narrative conclusions.

### 7.4 Governance is real

All learning and promotion paths must remain governed. Raw captured evidence lives in Plane A unless explicitly sanitized, verified, and promoted. fileciteturn2file0

### 7.5 Replayability matters

The product must generate append-only event records and replayable artifacts wherever possible.

---

## 8. Product modes

### 8.1 Desktop Scout Mode

**Purpose:** continuous lightweight visual awareness for everyday computer use.

**Behavioral requirements:**
- prioritize responsiveness and low interruption
- aggressively ignore pointer-only motion and non-meaningful change
- log meaningful UI change events without pausing normal workflows unless configured
- support low-cost scout classification for grouped screenshots or short sampled visual bursts

**Typical actions:**
- ignore
- note
- continue
- notify
- capture short evidence bundle

### 8.2 Trading Watch Mode

**Purpose:** high-sensitivity mode for charting, order-entry, and execution-risk review.

**Behavioral requirements:**
- track specific trading-relevant ROIs
- classify potential anomalies and risk states
- engage stronger local reviewer when change is trading-relevant
- escalate to Kimi for second-opinion review on uncertain/high-risk states
- support pause/warn/hold recommendations routed through a governor/policy gate

**Typical actions:**
- continue watching
- increase tracking intensity
- request local reviewer assessment
- request Kimi second opinion
- recommend pause / warn / do-not-proceed

### 8.3 Deep Review Mode

**Purpose:** offline or slower forensic review of a committed clip, sequence, or incident.

**Behavioral requirements:**
- higher-quality analysis acceptable
- can use heavier local or cloud review
- optimized for postmortem explanation, coaching, and dataset curation rather than real-time latency

---

## 9. Core user stories

### Desktop Scout stories

1. As a user, I want the system to ignore the mouse cursor flying across the screen so it does not waste attention on irrelevant motion.
2. As a user, I want the system to detect when a real UI element changes, such as a modal or alert, so it can note meaningful events.
3. As a user, I want the system to keep going during normal computer activity unless something important actually changed.
4. As a user, I want structured notes of what changed so another model or service can review them later.

### Trading Watch stories

5. As a trader, I want the system to recognize changes in chart panels, tickets, and confirmation dialogs so it can surface trading-relevant state.
6. As a trader, I want a local reviewer to interpret the evidence and tell me what it thinks is happening.
7. As a trader, I want Kimi to give a second opinion before risky trade actions are allowed to proceed.
8. As a trader, I want the system to feel like a careful human is watching the PC with me.
9. As a trader, I want suspicious or failed episodes captured into replayable clips and structured artifacts for later review.

### Governance and learning stories

10. As a system owner, I want model observations stored as advisory evidence, not treated as canonical truth.
11. As a system owner, I want learning artifacts promoted only through governed validation.
12. As a system owner, I want append-only event history so failures can be replayed and audited. fileciteturn2file0 fileciteturn2file1

---

## 10. Functional requirements

### 10.1 Capture and reflex filtering

The system shall:

1. Capture desktop frames locally.
2. Support a rolling ring buffer.
3. Apply a cursor suppressor or equivalent low-cost reflex filter before invoking expensive models.
4. Support frame-diff or equivalent cheap motion gating.
5. Support a configurable minimum change threshold before escalation to detection/tracking lanes.

### 10.2 Tripwire and detection

The system shall:

1. Support YOLO or equivalent detector as a tripwire lane.
2. Detect candidate UI changes such as modals, buttons, warnings, chart regions, or custom application-specific objects.
3. Allow class-based filtering so pointer/noise classes can be ignored and specific UI classes can be promoted.

### 10.3 Tracking and structure extraction

The system shall:

1. Support SAM3 tracking of triggered regions.
2. Maintain stable track IDs across short temporal windows when possible.
3. Support ROI extraction for chart panels, order tickets, confirmation modals, P&L widgets, and other configured UI elements.
4. Support optional OmniParser-style UI structure extraction for text/layout grounding.

### 10.4 Scout inference

The system shall:

1. Support a lightweight scout model such as Eagle2-2B for fast image-burst or short sampled clip understanding.
2. Allow the scout to classify candidate events into categories like `noise`, `ui_change`, `warning`, `trading_relevant`, or `unknown`.
3. Require scout outputs to be structured JSON, not long narrative prose.
4. Allow scout outputs to nominate whether stronger local or cloud review is warranted.

### 10.5 Reviewer inference

The system shall:

1. Support a stronger reviewer model such as Qwen3-VL/Qwen3.5 in trading mode.
2. Allow the reviewer to consume ROI crops, parser structure, and scout notes.
3. Produce structured judgment outputs including confidence, reasons, evidence links, and recommended next actions.
4. Treat reviewer outputs as advisory evidence, not automatic execution commands. fileciteturn2file0

### 10.6 Kimi overseer escalation

The system shall:

1. Support escalation bundles to Kimi containing minimal, sanitized evidence.
2. Support second-opinion review for uncertain or high-risk states.
3. Record whether Kimi review was requested, completed, or declined.
4. Support a later comparison between local reviewer judgment and Kimi overseer judgment.

### 10.7 Event history and artifacts

The system shall:

1. Write append-only event history for observations and escalations.
2. Produce replayable artifacts including clips, keyframes, ROI crops, and event slices.
3. Store watcher/scout/reviewer outputs with timestamps and source references.
4. Allow linkage between event history and downstream work/task identities.

### 10.8 Governance and trust

The system shall:

1. Distinguish Plane A working evidence from Plane B promoted/canonical artifacts.
2. Keep vector storage as retrieval/index support only, never authored truth.
3. Require validation-before-promotion for any learned prompts, rules, or promoted summaries.
4. Prevent raw unredacted cloud escalation by default.

---

## 11. Non-functional requirements

### 11.1 Performance

1. Desktop Scout Mode should feel responsive and not noticeably degrade normal PC interaction.
2. Capture must avoid blocking on disk I/O in the hot path.
3. Expensive model inference should run only on trigger or on scheduled review windows.
4. The system should support a human-smooth capture baseline aligned with the existing ring buffer plan. fileciteturn2file2

### 11.2 Reliability

1. Event logging must be append-only.
2. Failure modes should degrade gracefully into note/log/review rather than silent loss.
3. Trigger decisions must be inspectable after the fact.
4. Missed or failed escalations should be diagnosable from event history.

### 11.3 Security and privacy

1. Sensitive visual data must stay local by default.
2. Cloud escalation must use redaction and minimal artifact packaging.
3. Credentials, wallet addresses, API keys, browser URLs, notifications, and similar sensitive content must be masked when configured.
4. The system must avoid accidentally promoting third-party raw content into trusted instruction surfaces. fileciteturn2file2

### 11.4 Maintainability

1. The implementation must preserve repo boundaries.
2. Outputs must remain inspectable and schema-driven.
3. The product should favor additive evolution over giant rewrites.
4. Hot-path components should leave room for later Rust optimization.

---

## 12. Success metrics

### 12.1 Product metrics

1. Reduction in false pauses caused by pointer-only or trivial motion.
2. Detection rate for meaningful UI changes.
3. Precision of scout classification on triggered events.
4. Precision and recall of trading-relevant warnings/anomalies.
5. Time from meaningful UI change to structured event creation.
6. Time from escalation trigger to Kimi review request.
7. Percentage of high-risk events with replayable evidence bundles.

### 12.2 User experience metrics

1. User-perceived responsiveness during normal desktop use.
2. User trust in event summaries and escalation decisions.
3. Reduced need to manually reconstruct what happened after incidents.
4. User confidence that the system behaves more like a careful human than a brittle automation.

### 12.3 Governance metrics

1. Percentage of promoted learnings that passed explicit validation.
2. Percentage of escalations that were redacted before cloud upload.
3. Rate of doctrine violations such as ungoverned promotion or treating model outputs as authoritative truth.

---

## 13. Risks and mitigations

### Risk 1: Over-triggering on noise

**Mitigation:**
- cursor suppression
- frame-diff thresholds
- class filtering
- scout `noise` category

### Risk 2: VLM hallucinating UI state

**Mitigation:**
- feed isolated ROIs instead of full desktop when possible
- parser-assisted structure extraction
- evidence-first prompts
- Kimi second-opinion escalation

### Risk 3: VRAM pressure and latency

**Mitigation:**
- trigger-based inference only
- downsample clips for tracking
- use lightweight scout for hot path
- keep heavier reviewer optional/conditional

### Risk 4: Unsafe cloud escalation

**Mitigation:**
- local redaction step
- minimal evidence bundles
- explicit approval/gating path

### Risk 5: Architecture drift across repos

**Mitigation:**
- keep advanced-vision focused on perception/runtime only
- keep governance and promotion in Brain-harness
- integrate with OpenClaw via stable contracts later

### Risk 6: Model role confusion

**Mitigation:**
- formal role map: reflex, tripwire, tracker, scout, reviewer, overseer, governor
- no single model becomes the whole system

---

## 14. Requirements by mode

### 14.1 Desktop Scout Mode requirements

- Must ignore cursor-only movement whenever technically feasible.
- Must continue without pausing on non-relevant motion.
- Must support lightweight grouped-image or short sequence review.
- Must generate concise structured notes for downstream analysis.
- May notify or log without interrupting active workflows.

### 14.2 Trading Watch Mode requirements

- Must support tracked ROIs for chart/ticket/modal workflows.
- Must classify trading-relevant warnings and unexpected state changes.
- Must support stronger local review before cloud escalation.
- Must support Kimi second opinion for uncertain/high-risk states.
- Must never convert raw model output directly into ungoverned trade execution.

### 14.3 Deep Review Mode requirements

- Must support replay and postmortem analysis from committed evidence bundles.
- Must support side-by-side analysis of scout/reviewer/Kimi outputs.
- Must support learning extraction under governance.

---

## 15. Proposed product behavior

### 15.1 Simplified behavioral flow

1. Capture screen frame.
2. Apply cursor/noise suppression.
3. Apply cheap motion/change detection.
4. If no meaningful change, continue.
5. If meaningful change, run tripwire detection.
6. If relevant object/change detected, track ROI with SAM3.
7. Extract ROI crops and optional UI structure.
8. Run scout model for fast classification.
9. If desktop mode and low risk, note and continue.
10. If trading mode and relevant/uncertain, run stronger local reviewer.
11. If reviewer indicates uncertainty or risk, escalate sanitized bundle to Kimi.
12. Route resulting recommendation through governor/policy gate.
13. Log append-only events and preserve replayable evidence.

### 15.2 Human-like behavior goals

The product should emulate these human behaviors:

- ignore harmless motion
- notice salient UI changes
- look closer only when necessary
- think harder when money/risk is involved
- ask for a second opinion when uncertain
- remember what happened well enough to explain it later

---

## 16. Release phases

### Phase 0 — PRD and mode definition

Deliver:
- product scope
- user modes
- role map
- initial success metrics

### Phase 1 — Desktop Scout MVP

Deliver:
- local capture
- cursor/noise suppression
- frame-diff gate
- YOLO tripwire
- lightweight scout notes
- append-only logs

Success looks like:
- pointer-only motion mostly ignored
- meaningful UI changes logged without heavy interruption

### Phase 2 — Trading Watch MVP

Deliver:
- trading ROI definitions
- SAM3 tracking
- optional parser structure extraction
- stronger local reviewer
- Kimi escalation bundle
- policy gate hooks

Success looks like:
- system can recognize and summarize trading-relevant UI changes
- uncertain cases can escalate cleanly to Kimi

### Phase 3 — Replay and evidence pipeline

Deliver:
- clip/keyframe/ROI commits
- replay support
- manifest linkage
- incident review workflow

### Phase 4 — Retrieval and governed learning

Deliver:
- ROI embeddings
- retrieval/rerank support
- lesson extraction under validation-before-promotion

---

## 17. Open decisions

1. Which scout model is default for Desktop Scout Mode.
2. Which reviewer model is default for Trading Watch Mode.
3. How aggressive cursor suppression should be by default.
4. Which UI classes are globally relevant vs app-specific.
5. Default escalation threshold for Kimi review.
6. Whether pause recommendations require human confirmation in all trading cases.
7. Which evidence bundle schema is the stable cross-repo contract.
8. How much of the reviewer stack should run through vLLM vs direct Transformers runtimes.

---

## 18. Acceptance criteria for PRD signoff

This PRD is ready for signoff when:

1. Mode boundaries are accepted: Desktop Scout, Trading Watch, Deep Review.
2. Model role boundaries are accepted: reflex, tripwire, tracker, scout, reviewer, overseer, governor.
3. Governance constraints are preserved: no ungoverned promotion, no vector-store-as-truth, no raw model output as execution authority. fileciteturn2file0
4. Replayable event history and evidence artifacts are accepted as product requirements. fileciteturn2file1
5. The next implementation step can proceed without redesigning the entire architecture.

---

## 19. Appendix: doctrinal alignment

This PRD aligns with the following settled ideas already present in your system documents:

- perception is a distinct layer
- event history should be append-only and replayable
- judgment outputs are advisory
- retrieval is trust-aware and vector indexes are not authored truth
- validation-before-promotion is mandatory
- communications history and receipts/acks are distinct from hints/notifiers
- watcher pipelines should generate inspectable artifacts rather than opaque behavior. fileciteturn2file0 fileciteturn2file1 fileciteturn2file2
