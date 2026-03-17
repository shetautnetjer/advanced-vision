# Gap Fill: Simple Computer Use First

This file fills the practical gap between the original analysis set and a reality-based implementation path.

## Missing before
The earlier analysis identified many worthwhile future themes, but it did not cleanly separate:
- what must work now
- what should wait until later

That separation matters.

---

## What must work now

### Runtime
- dedicated computer-use env
- working imports for GUI automation stack
- MCP server startup from the intended env

### Read path
- screenshot capture
- verification logic
- inspect-only flow

### Action path
- basic mouse/keyboard actions in safe tests
- dry-run or equivalent low-risk testing path

### Documentation
- exact commands that match reality
- explicit Linux limitations

---

## What should wait

### Governance later
- approval-class plumbing everywhere
- data classification and retention framework
- provenance-chain design
- secrets-aware outbound analysis routing

### Integration later
- GitHub coupling
- broad orchestration contracts
- bigger multi-agent protocol ideas

Those are worth doing, but only after the substrate is truthful and stable.

---

## Specific corrected priorities

### Priority 0
- verify `.venv-computer-use` as the runtime of record
- prove server startup from that env
- prove action tools work at least minimally

### Priority 1
- add `dry_run` for input tools
- update diagnostics
- tighten README/SKILL wording so it reflects verified reality

### Priority 2
- add lightweight cleanup
- add modest provenance improvements
- improve integration docs for OpenClaw/mcporter

### Priority 3
- begin governance layering after runtime confidence is established

---

## Practical engineering rule

If a change does not improve one of these immediately:
- runtime truth
- local safety
- testability
- documentation accuracy

then it is probably not Phase 2 work.

---

## Conclusion

The right move is not to abandon governance themes.
The right move is to **sequence them correctly**.

Simple computer use first.
Governed computer use second.
