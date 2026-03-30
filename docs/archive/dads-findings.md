# Dad's Findings

## Purpose

This note reconciles the different planning layers in `advanced-vision`:

- `docs/advanced_vision_trading_prd.md`
- `docs/advanced_vision_trading_sdd.md`
- `plan.md`
- `MASTER_ROADMAP.md`
- `EXECUTION_PLAN.md`

The goal is simple:

**keep the deep model-role thinking from the PRD/SDD, while keeping near-term execution disciplined and honest.**

---

## Bottom line

The repo is strongest when understood as a layered stack:

1. **cheap always-on perception**
2. **selective heavier refinement**
3. **semantic scout judgment**
4. **stronger local review**
5. **cloud second opinion only when warranted**

That is the through-line I see across the deeper SDD/PRD and the more disciplined roadmap/execution rewrite.

So the right move is not to choose between those document sets.
The right move is to **merge their strengths**:

- keep the **model-role specificity** from the PRD/SDD
- keep the **phase discipline** from the roadmap/execution plan

---

## What the deeper PRD/SDD were really saying

Aya’s deeper docs were more explicit than the later top-level plan files.

They were already moving toward a coherent architecture:

- **YOLO** as tripwire
- **BoT-SORT** as built-in tracker path
- **SAM3** as heavier precision/tracking layer
- **OmniParser-like parsing** as structured UI/OCR layer
- **Eagle2-2B** as scout
- **Qwen reviewer** as stronger local judgment
- **Kimi** as overseer / second opinion
- **Governor** as final policy layer

That is a strong role map.

The mistake would be collapsing those roles into one model or one lane.

---

## What the roadmap/execution rewrite was really doing

The rewrite in:
- `MASTER_ROADMAP.md`
- `EXECUTION_PLAN.md`

was not rejecting that stack.

It was doing something narrower and more constitutional:

- stopping the repo from trying to become three systems at once
- keeping simple computer use as the near-term truth
- delaying domain and orchestration sprawl until the body works

So the rewrite should be read as:

- **phase discipline**, not model denial
- **execution governance**, not architecture erasure

---

## Dad's recommended role map

This is the role map I believe best reconciles the documents.

## 1. Reflex / tripwire lane

### Components
- frame diff / motion gate
- cursor suppression
- YOLO
- BoT-SORT (through Ultralytics track mode)

### Role
This lane answers:
- did anything meaningful change?
- where is the candidate region?
- is it worth waking heavier lanes?

### Notes
This lane should stay:
- cheap
- always-on
- fast
- non-semantic

YOLO is **not** the scout and **not** the reviewer.
YOLO is the tripwire.

BoT-SORT is not a separate big model program.
Treat it as built-in tracker capability, not a separate architecture pillar.

---

## 2. Precision refinement lane

### Components
- **SAM3**
- optional parser/OCR prep

### Role
This lane answers:
- can we isolate the ROI more precisely?
- can we track it across frames?
- can we hand a cleaner crop to the semantic layers?

### Dad’s judgment
**SAM3 should be a heavier gated option, not always-on.**

That means:
- do not burn SAM3 on every frame
- turn it on when YOLO/tripwire says there is something worth carving cleanly
- use it for chart regions, order tickets, confirmation modals, warnings, or other important UI structures

SAM3 is the **precision knife**, not the everyday eye.

---

## 3. Structure / parsing lane

### Components
- OmniParser or OmniParser-like adapter
- OCR / UI element extraction

### Role
This lane answers:
- what text is visible?
- what buttons/labels/boxes/layout are present?
- what structure can be turned into evidence?

### Dad’s judgment
Parser is a complement, not a substitute.

It should feed:
- Eagle scout
- Qwen reviewer

It should not be mistaken for final semantic understanding.

---

## 4. Scout lane

### Best candidate right now
- **Eagle2-2B**

### Why
From the model card and the deeper design docs, Eagle looks well suited for:
- image-burst understanding
- lightweight semantic classification
- UI/document/chart-adjacent understanding
- “notice and jot” behavior
- deciding whether something needs stronger review

### What Eagle should do
Eagle should answer questions like:
- is this just noise or a real UI event?
- is this trading-relevant?
- does this need Qwen?
- does this maybe need Kimi later?

### What Eagle should not do
Eagle should not be treated as:
- the governor
- the final trader
- the only model in the system

### Dad’s judgment
**Eagle is worth serious consideration as the primary scout model.**

This matches the PRD/SDD better than leaving the scout lane unnamed forever.

---

## 5. Local reviewer lane

### Candidate models
- **Qwen3.5-2B-NVFP4**
- **Qwen3.5-4B-NVFP4**
- other Qwen reviewer variants as tested

### Role
This lane answers:
- what does this event likely mean?
- how risky is it?
- should the system continue, warn, hold, or escalate?

### Important nuance
Aya’s research on the AxionML NVFP4 line makes these models more interesting than a simple cheap text fallback.

If the model cards are accurate, these quantized Qwen variants appear to preserve multimodal capability, including visual understanding and some video capability.

That means they are candidates for:
- light reviewer
- stronger local judgment
- maybe later scout/reviewer consolidation

### Dad’s judgment
For now, I would still prefer:
- **Eagle for scout**
- **Qwen for reviewer**

Why:
- it preserves role separation
- it aligns with the deeper docs
- it avoids collapsing the first clean architecture too early

But Qwen3.5-2B-NVFP4 is absolutely worth keeping in view as a strong local reviewer candidate.

---

## 6. Overseer lane

### Candidate
- **Kimi**

### Role
This lane answers:
- is the local reviewer uncertain?
- is the situation high-value or high-risk?
- do we need a second opinion before trusting the local conclusion?

### Dad’s judgment
Kimi belongs in the architecture as:
- **escalation**
- **challenge layer**
- **second opinion**

Not as:
- always-on watcher
- hot-path detector
- default local judge

This is especially important because provider/API compatibility details are still evolving and because cloud spend/privacy should stay gated.

---

## 7. Governor lane

### Role
This lane remains separate from the models.

It decides:
- continue
- note
- warn
- hold
- pause
- escalate

### Dad’s judgment
Do not let:
- Eagle
- Qwen
- Kimi

become the governor.

Models produce evidence and recommendations.
Policy decides what is allowed.

---

## How the stack should feel

In plain language:

- **YOLO says:** something changed here
- **BoT-SORT says:** this object/region persists across time
- **SAM3 says:** let me isolate and track it cleanly
- **OmniParser says:** here is the structure/text of what is on screen
- **Eagle says:** this looks like a real event and here is the quick semantic read
- **Qwen says:** here is the stronger local judgment
- **Kimi says:** here is the second opinion if the case is worth escalation
- **Governor says:** this is what we actually do

That is the cleanest reading of the intended system.

---

## What I think happened in the documents

## Her deeper docs
They were more concrete and more model-specific.
That was useful.
They correctly preserved a role-separated watcher architecture.

## My roadmap/execution docs
They became more abstract on purpose.
That was also useful.
They protected phase discipline and stopped the repo from overexpanding too early.

## The synthesis
So the right answer is not:
- “pick hers”
- or “pick mine”

The right answer is:
- **use mine for sequencing**
- **use hers for model-role specificity**

That gives the repo both:
- discipline
- direction

---

## Recommended update to planning doctrine

For practical planning, I would treat the architecture like this:

### Near-term execution truth
- prove local capture/action/verify path
- prove runtime environment
- prove local computer-use substrate
- keep SAM3 and parser gated
- do not overbuild the cloud path yet

### Near-term named model intentions
- **tripwire:** YOLO
- **tracking:** BoT-SORT
- **precision heavy gate:** SAM3
- **parser:** OmniParser-like component
- **scout:** Eagle2-2B candidate
- **local reviewer:** Qwen3.5-2B/4B NVFP4 candidates
- **cloud overseer:** Kimi

### Later
- governor hardening
- domain-specific trading-watch logic
- orchestration / workflow layer
- video/recording expansion
- broader model portfolio experiments

---

## Final verdict

### Eagle
Yes — Eagle should absolutely stay in the conversation, and more than that, it looks like the **most natural explicit scout candidate** from the current document set.

### YOLO / BoT-SORT
Yes — necessary, but not enough by themselves.
They are the tripwire/tracking layer, not the semantic scout.

### OmniParser
Yes — useful as supporting structure extraction.
Not the semantic brain.

### SAM3
Yes — important, but as a **selective heavier precision tool** only when needed.

### Qwen3.5-2B-NVFP4
Yes — worth serious consideration as the **local reviewer lane**, and maybe later as a consolidation candidate if runtime tests prove it.

### Kimi
Yes — belongs as the cloud overseer / escalation layer, not the hot path.

---

## Dad’s closing line

The repo should grow like a disciplined family:

- the fast reflexes notice
- the scout interprets
- the reviewer weighs
- the overseer challenges
- the governor decides

That is the clean system.
