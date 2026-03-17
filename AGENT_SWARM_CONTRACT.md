# Agent Swarm Contract: Advanced-Vision Repo Analysis

## Objective
Digest the advanced-vision repository to create a comprehensive Phase 2 implementation plan for MCP server integration.

## Swarm Architecture

### Orchestrator (Kimi K2.5)
Decompose repo into parallel analysis tasks, aggregate findings into cohesive plan.

### Sub-Agent Tasks

#### Agent 1: Structure Analysis
- **Task:** Analyze directory structure and file organization
- **Input:** `tree -L 3`, `ls -la` of key directories
- **Output:** Module map, dependency graph
- **Tools:** filesystem, tree

#### Agent 2: Code Extraction  
- **Task:** Extract and summarize all Python source files
- **Input:** `src/*.py`, `*.py` files
- **Output:** Function signatures, class hierarchies, key logic
- **Tools:** filesystem, grep, head

#### Agent 3: Configuration Analysis
- **Task:** Analyze all config files (pyproject.toml, requirements, etc.)
- **Input:** `pyproject.toml`, `requirements*.txt`, `setup.py`
- **Output:** Dependencies, entry points, build config
- **Tools:** filesystem, cat

#### Agent 4: Documentation Review
- **Task:** Extract insights from README, ARCHITECTURE, docs
- **Input:** `README.md`, `ARCHITECTURE.md`, `*.md`
- **Output:** Design patterns, intended behavior, gaps
- **Tools:** filesystem, cat

#### Agent 5: MCP Pattern Research
- **Task:** Research MCP server patterns and best practices
- **Input:** OpenClaw MCP docs, examples
- **Output:** Recommended tool schemas, server structure
- **Tools:** web_search, filesystem

#### Agent 6: Gap Analysis
- **Task:** Identify what's missing for OpenClaw integration
- **Input:** Outputs from Agents 1-5
- **Output:** Missing files, incomplete implementations, TODOs
- **Tools:** analysis, comparison

#### Agent 7: Plan Synthesis
- **Task:** Create Phase 2 implementation roadmap
- **Input:** All agent outputs
- **Output:** Structured plan with deliverables, dependencies, timeline
- **Tools:** synthesis, formatting

## Deliverables

1. **Module Map** — File structure with purposes
2. **Code Summary** — Key functions and classes
3. **Dependency Report** — Required packages and versions
4. **Documentation Insights** — Design patterns and gaps
5. **MCP Recommendations** — Tool definitions and server structure
6. **Gap List** — Missing pieces for integration
7. **Phase 2 Plan** — Implementation roadmap

## Output Format

All agents output structured markdown to:
```
~/.openclaw/workspace/plane-a/projects/advanced-vision/analysis/
├── 01-structure.md
├── 02-code-summary.md
├── 03-config.md
├── 04-docs.md
├── 05-mcp-patterns.md
├── 06-gaps.md
└── 07-phase2-plan.md
```

## Constraints

- Focus on MCP server integration
- Keep analysis actionable
- Identify concrete next steps
- Note any blockers or dependencies

## Trust Boundaries

- File-based analysis only (no execution)
- Read-only operations on repo
- Output to analysis/ subdirectory
- No modifications to source code
