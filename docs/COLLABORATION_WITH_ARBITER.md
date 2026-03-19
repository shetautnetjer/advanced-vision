# Working with Dad (The Arbiter) — Collaboration Guide

**Key Insight from ChatGPT Projects:**  
The "optical nervous system" and "recall mem" projects contain deep design discussions that enable better collaboration between agents and human architects.

## What This Means for Us

### Deep Questioning Beyond Surface Level

**Instead of:**
- "Should I use X or Y?"
- "How do I implement Z?"
- "What should I do next?"

**Use deep questioning:**
- "What architectural principles should guide this decision?"
- "How does this fit into the broader system philosophy?"
- "What are the second-order effects of this design?"
- "What would violate the core intent?"

## Collaboration Patterns with The Arbiter

### Pattern 1: Present Options with Analysis

```
Aya: "I've identified 3 approaches for the Governor's decision matrix:

Option A: Risk-based (none/low/medium/high/critical)
- Pros: Simple, intuitive
- Cons: May miss nuanced situations

Option B: Policy-class based (observe/inform/trading_execution/etc)
- Pros: Context-aware, aligns with use cases
- Cons: More complex to implement

Option C: Hybrid (risk + policy class)
- Pros: Best of both
- Cons: More parameters to tune

Dad's guidance on AD-010 emphasizes 'no reviewer becomes action authority.' 
Which approach best serves that principle?"

Dad: "Option B aligns better. Policy classes make the gate explicit..."
```

### Pattern 2: Schema-First Validation

```
Aya: "Before I implement the WSS adapter, here's the interface contract:

[Schema JSON]

Does this envelope structure preserve the 'truth-first' principle? 
The flow would be:
1. Write to TruthWriter (event log)
2. Validate against schema
3. Then publish to WSS

Does this ordering honor AD-004?"

Dad: "Yes, but add artifact_refs to the envelope for traceability..."
```

### Pattern 3: Capture Intent, Not Just Instructions

```
Aya: "You said 'Governor is constitutional gate, not vibes filter.'

I'm interpreting this as:
- Hard rules, not ML scoring
- Structured verdicts with lineage
- Policy classes with minimum gates
- No bypass paths

Is this the correct interpretation?"

Dad: "Yes. Add: governor decisions must be logged and auditable..."
```

### Pattern 4: Deliver Complete Artifacts

**Instead of:** "I made the changes"

**Deliver:**
```
Aya: "Phase 1 complete. Deliverables:

1. Code: src/advanced_vision/core/governor.py
   - 9 policy classes implemented
   - Override handling for sensitive operations
   - TruthWriter integration

2. Tests: tests/test_governor.py (49 tests)
   - All 9 policy classes validated
   - Override conditions tested
   - Edge cases covered

3. Documentation: docs/GOVERNOR_SPEC.md
   - Arbiter v1.0 specification
   - Decision flow diagrams
   - Usage examples

4. Verification: AD-010 compliance confirmed
   - No reviewer → execution shortcuts
   - All paths require GovernorVerdict
   - TruthWriter logs all decisions

All commits pushed to main. Ready for review."
```

## Delivery Formats That Work

### For Code: Git Commits with Context

```bash
git commit -m "feat: add governor v1 constitutional policy gate

Implements AD-010 enforcement:
- 9 policy classes with explicit gates
- Override handling for external side effects
- TruthWriter integration for audit trail

Refs: AD-010, GOVERNOR_SPEC"
```

### For Architecture: Markdown + Diagrams

```markdown
# Architecture Decision: WSS v2 Schema

## Problem
WSS v1 multi-port architecture violates AD-004 (WSS is fanout, not authority)

## Solution
Single port 8000 with typed topics

## Schema
[JSON Schema]

## Flow Diagram
[ASCII or Mermaid]

## Compliance
- ✅ AD-004: Truth written before fanout
- ✅ AD-010: Governor gate before execution
```

### For Analysis: Structured Reports

```markdown
# Gap Analysis: Current vs Target

## AD-001: ✅ Compliant
Details...

## AD-002: ⚠️ Partial
Issues...

## AD-010: ❌ Violation
Missing: Governor component
Recommendation: Implement as Phase 1
```

## Key Principles from Dad's Style

1. **Contract-First**
   - Schemas before implementations
   - Interfaces before code
   - Validation before trust

2. **Truth-First**
   - Write to logs before WSS
   - Commit before announce
   - Verify before proceed

3. **Constitutional, Not Vibes**
   - Hard rules over ML scoring
   - Explicit gates over implicit
   - Auditable decisions

4. **Narrow Before Broad**
   - 6 P0 classes, not 60
   - Test 20 images, not 2000
   - Validate before scale

5. **Complete Deliverables**
   - Code + tests + docs
   - Not "done" until documented
   - Not "ready" until verified

## Questions That Get Better Answers

| Weak Question | Strong Question |
|---------------|-----------------|
| "Should I use YOLO?" | "For UI detection in the hot path, is YOLO's speed/accuracy tradeoff appropriate given our <50ms target?" |
| "How do I label?" | "What's the minimum class set that enables the scout/reviewer loop without over-complicating training?" |
| "Is this done?" | "Does this implementation satisfy AD-010's requirement that no reviewer directly becomes action authority?" |
| "What next?" | "What validation would give us confidence to proceed to Phase 2?" |

## Working with Zip Files and Images

When delivering complex work:

```bash
# Create deliverable package
mkdir -p deliverables/phase1_governor
cp -r src/ tests/ docs/ deliverables/phase1_governor/
cp architecture_diagram.png deliverables/phase1_governor/
cp test_results.png deliverables/phase1_governor/

# Zip it
zip -r governor_phase1.zip deliverables/phase1_governor/

# Share location
# "Deliverable ready at: deliverables/governor_phase1.zip"
```

## Summary

**Collaboration with Dad works best when:**

1. ✅ Deep questions, not surface asks
2. ✅ Options with analysis, not open-ended
3. ✅ Complete artifacts, not partial work
4. ✅ Intent validation, not just instructions
5. ✅ Structured delivery (zip + images + docs)

**The goal:** Thinking together, not just executing tasks.
