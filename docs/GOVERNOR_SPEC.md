# Governor Design Specification (Arbiter v1.0)

**Source:** Arbiter (Dad) — 2026-03-18
**Status:** Ready for Implementation

---

## 1. Core Doctrine

> Reviewer outputs are **advisory evidence**, not **executable authority**.

**Flow:**
```
Perception/Reviewer → Governor Evaluates → Governor Emits Decision → Execution Proceeds
```

**Hard Rule:** No reviewer result directly triggers execution.

---

## 2. Governor Output Structure

```python
{
  "verdict_id": "uuid",
  "timestamp": "iso8601",
  "risk_level": "none | low | medium | high | critical",
  "decision": "continue | warn | recheck | require_approval | block",
  "policy_class": "...",
  "rationale": "human-readable explanation",
  "lineage": {
    "source_event": "uuid",
    "reviewer": "eagle|qwen|aya",
    "trace_id": "uuid"
  },
  "tags": ["risk:high", "action:block", "mode:trading"],
  "overrides_applied": ["trading_execution_candidate"]
}
```

---

## 3. Policy Classes (9)

| Policy Class | Default Max | Minimum Gate | Notes |
|--------------|-------------|--------------|-------|
| `observe` | warn | — | Passive monitoring |
| `inform` | warn | — | Notifications only |
| `internal_state_update` | warn | — | Local state changes |
| `external_review` | warn | continue | Aya/Claude review |
| `trading_analysis` | recheck | — | Chart/ticket analysis |
| `trading_execution_candidate` | require_approval | require_approval | **Never auto-execute** |
| `ui_interaction_candidate` | recheck | recheck | Escalate if side effects |
| `sensitive_data_access` | recheck | recheck | Block if trust boundary unclear |
| `promotion_candidate` | require_approval | require_approval | **Never auto-promote** |

---

## 4. Risk Level Defaults

| Risk Level | Default Decision |
|------------|------------------|
| none | continue |
| low | continue |
| medium | warn |
| high | recheck |
| critical | block |

---

## 5. Override Conditions

Escalate to `require_approval` or `block` if:
- External side effects detected
- Trading execution candidate
- Sensitive data access + unclear trust boundary
- Promotion candidate

---

## 6. Artifact Policy

### SHA256
- **Always** enforce checksums

### Retention Tiers

**Trading Mode:**
- Raw captures: `short_term`
- Reviewed evidence: `long_term`
- Execution/governor records: `permanent`

**UI Mode:**
- Raw captures: `ephemeral` / `short_term`
- Incidents: `long_term`
- Promoted evidence: `permanent`

### Access Logging
Log:
- All writes
- All external reads
- All sensitive/decision-relevant reads

---

## 7. Tag Alignment

Map governor decisions to tags, but **structured fields remain primary**.

Example tag mapping:
- `risk:{level}`
- `action:{decision}`
- `policy_class:{class}`
- `mode:{trading|ui}`

---

## 8. Interface Contract

```python
class Governor:
    def evaluate(
        self,
        recommendation: ReviewerResult,
        context: PolicyContext,
        policy_class: str
    ) -> GovernorVerdict:
        """
        Evaluate reviewer recommendation and emit authoritative decision.
        """
        pass
```

---

## 9. Next Steps

1. Implement `Governor` class
2. Implement `GovernorVerdict` dataclass
3. Add policy engine with class-based rules
4. Integrate with TruthWriter for verdict logging
5. Block direct reviewer→execution paths
6. Add tests for all 9 policy classes

**Status:** Ready for implementation agent.
