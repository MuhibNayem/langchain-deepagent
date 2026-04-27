# Project

**Project:** LuminaMind — Autonomous Coding Agent Harness
**Goal:** Transform LuminaMind from basic autonomous agent to industry-leading coding harness using Generator-Evaluator pattern, live verification, planner/sprint system, and modern LangGraph/LangChain patterns
**Baseline:** v0.0.1.1.3 with 12 critical/high/medium gaps identified
**Target:** Claude Code-level harness engineering quality
**Timeline:** 16-week execution
**Team:** 2-3 engineers

---

## What This Is

LuminaMind is an AI-powered autonomous coding agent built on LangChain/LangGraph. It uses a multi-agent orchestration pattern with subagent delegation, human-in-the-loop interrupts for sensitive operations, and state persistence via checkpointers.

## Core Value

A coding harness that produces working code — not broken stubs. The harness engineering matters more than the model choice.

## Constraints

- Must use existing LangChain/LangGraph stack (already in pyproject.toml)
- Target Claude Code-level harness engineering quality
- 16-week execution timeline
- 2-3 engineering team
- Security CVEs must be resolved before production

## Tech Stack

- **Language:** Python 3.12
- **Agent Framework:** LangChain 1.0.8 + LangGraph 1.0.3
- **Agent Builder:** deepagents 0.2.7 (create_deep_agent pattern)
- **LLM:** GLM-4.5-flash (OpenAI-compatible) or Ollama local
- **State:** Redis-backed checkpointers
- **CLI:** Typer + Rich + Questionary
- **Observability:** structlog + Prometheus

## Key Decisions

| Decision | Rationale | Status |
|----------|-----------|--------|
| Generator-Evaluator pattern first | Anthropic showed 20x better output quality vs solo agent | Locked |
| Two-layer memory architecture | Token optimization for full transcript + working memory | Locked |
| GAN-inspired dual-agent | Iterative refinement loops for quality | Locked |
| LangGraph conditional edges | Iteration control via state schema | Locked |
| Playwright MCP for live verification | Click-through UI testing without human testers | Locked |
| Tool reduction validated | Vercel cut 80% of tools → better results | Locked |

## Known Gaps (v0.0.1.1.3)

1. No Generator-Evaluator pattern
2. No live verification infrastructure
3. No planner/sprint contract system
4. No context compaction / prompt caching
5. No bounded subagent system
6. No tool tiering
7. No lifecycle hooks
8. No grading criteria framework
9. No prompt library
10. No stable memory architecture
11. Security: shell injection (CVSS 9.8), hardcoded API keys (CVSS 8.5)
12. No rate limiting

## Out of Scope

- Switching away from LangChain/LangGraph
- Using different LLM providers (current stack is adequate)
- Building mobile UI
- Non-Python support

---

*Last updated: 2026-04-27 after project import from plan.md*
