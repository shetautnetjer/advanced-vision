# Ralph Protocol

Use this when the repo needs several loops to become more normal, modular, and
operable.

This is a repo-local adaptation of the broader Ralph-style workflow pattern:
multi-phase execution, separate review passes, bounded agent roles, and
worktree-friendly parallelism. It is not treated here as a rigid external spec.

## Core idea

Run narrow loops with clear roles instead of one giant mixed pass.

## Suggested loop

1. **Orient**
   Use JetBrains workflow habits first: reviewer for risk, debugger for failure
   surface, coder or refactorer for the change lane.
2. **Mine context with spark sidecars**
   Use Codex Spark subagents for repo mining, doc discovery, or second-pass risk
   scans. Keep their scope narrow.
3. **Patch the smallest stable layer**
   Prefer config, docs, tests, and routing cleanup before architecture churn.
4. **Validate immediately**
   Use the cheapest proving command that answers the question.
5. **Only then widen scope**
   Move to refactor, modularization, or new abstractions after the local loop is stable.

## Good subagent roles

- explorer
  Use for finding the best existing docs, commands, and code paths
- reviewer
  Use for “what could break if we change this?”
- second explorer
  Use for separation-of-concerns suggestions, not for duplicate implementation work

## JetBrains role mapping

When using JetBrains workflow skills, think in modes:

- reviewer
  Defects, regressions, missing tests
- debugger
  Reproduce and narrow the failure
- coder
  Small direct implementation
- refactorer
  Structure cleanup after behavior is stable
- test-fixer
  Make validation trustworthy before broadening scope

## When to use a Git worktree

Use a worktree when:

- a refactor will touch many unrelated areas
- you need a parallel cleanup branch while preserving the current stable path
- you want to compare two alternative cleanup strategies without polluting one branch

Do not reach for a worktree when:

- the change is a focused config or doc fix
- the task is still in the reproduction stage
- you have not yet stabilized the primary local-control path

## Repo priority rule

For this repo, every loop should ask:

“Did this make Linux local control more normal and less confusing?”

If not, the loop is probably drifting into future-model work too early.
