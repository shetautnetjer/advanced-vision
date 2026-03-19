# Antigravity Meta-Agenting Capability

**Powerful Feature:** Ask Antigravity's agent about agent design

## What This Means

**Meta-agenting** — Using Claude Opus 4.0 (in Antigravity) to:
- Discuss agent architecture
- Review agent implementations
- Get feedback on design decisions
- Brainstorm approaches
- Debug agent behavior

## Use Cases

### 1. Architecture Review
```
You (in Antigravity agent panel):
"Review my agent swarm design. I have:
- audit-current-state agent
- fix-model-roles agent  
- activate-wss-v2 agent

Is this the right decomposition?"

Antigravity Agent:
"Consider these improvements..."
```

### 2. Implementation Feedback
```
You:
"Here's my Governor implementation. Does the 
precondition check order make sense?"

Agent:
"The freshness check should come before structure 
validation to fail fast..."
```

### 3. Debugging Agent Behavior
```
You:
"My subagent isn't returning results. What should 
I check?"

Agent:
"Verify: 1) Task clarity, 2) File paths exist, 
3) Dependencies installed, 4) Timeout settings..."
```

### 4. Design Patterns
```
You:
"When should I spawn 5 agents vs 1 agent with 
5 tasks?"

Agent:
"Parallel when: independent tasks, different skills, 
time critical. Sequential when: dependencies, shared 
state, need coherence..."
```

## How to Use

1. **Open Antigravity** (already running)
2. **Click Agent panel** (right side)
3. **Type questions** about your agents
4. **Get feedback** from Claude Opus 4.0

## Example Session

```
User: I'm building a YOLO training pipeline. Should 
I use schema-first or capture-first?

Agent: Schema-first is generally better because:
1. Contracts clarify requirements
2. Validation catches errors early
3. Agents work against stable interfaces
4. Easier to parallelize

However, if your data is messy and requirements 
are unclear, capture-first with iterative schema 
refinement might work better.

Recommendation: Start with minimal schema, capture 
some samples, refine schema, then scale.
```

## Benefits

| Benefit | Description |
|---------|-------------|
| **Second opinion** | Get feedback before committing |
| **Pattern library** | Learn common agent patterns |
| **Error prevention** | Catch design flaws early |
| **Learning** | Understand why approaches work |
| **Confidence** | Validate decisions |

## When to Use

✅ **Good for:**
- Architecture decisions
- Design reviews
- Debugging stuck agents
- Learning best practices
- Refactoring guidance

❌ **Not for:**
- Simple syntax errors (use linter)
- File operations (use tools directly)
- Execution (agents do this)

## Integration with Workflow

```
1. Design phase     → Ask Antigravity agent
2. Implementation   → Code in Antigravity
3. Testing          → Run in terminal
4. Debugging        → Ask agent again
5. Deployment       → Git push from Antigravity
```

## Summary

**Antigravity = IDE + Agent Peer Review**

Use it as a thinking partner for agent design. Not just code editor — architectural sounding board.

**Next time you're unsure:** Ask the agent in Antigravity before spawning subagents.
