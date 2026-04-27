# Phase 05: Tool & Prompt Optimization - Context

**Gathered:** 2026-04-27
**Status:** Ready for planning
**Source:** Requirements analysis (no discuss-phase held)

<domain>
## Phase Boundary

Implement tool tiering, prompt library, and lifecycle hooks for maintainability and extensibility. This phase reduces unnecessary tool exposure, enables dynamic prompt composition, and provides recovery mechanisms.
</domain>

<decisions>
## Implementation Decisions

### Tool Tiering (TOOL-01, TOOL-02)
- **D-01:** Tool tiers defined as: core (always available), extended (task-dependent), specialist (role-specific)
- **D-02:** Tool selection is context-aware based on task type and current phase
- **D-03:** Tier assignment stored in PY_TOOL_REGISTRY metadata

### Prompt Library (TOOL-03, TOOL-04)
- **D-04:** Prompt presets stored as versioned documents with task-type mapping
- **D-05:** Dynamic composition assembles prompts from base + context + personality modules
- **D-06:** A/B testing support via prompt variant assignment

### Lifecycle Hooks (TOOL-05)
- **D-07:** Hook events: on_init, on_start, on_step, on_complete, on_error, on_exit
- **D-08:** Hooks implemented as async callbacks registered with the agent

### Recovery Framework (TOOL-06)
- **D-09:** Exponential backoff for transient failures (base=2, max_delay=60s, max_attempts=5)
- **D-10:** Circuit breaker pattern prevents repeated calls to failing services
- **D-11:** Fallback chain: primary → secondary → tertiary → error

### agent Discretion
- **D-12:** Specific tier thresholds and tool counts per tier — agent tunes based on metrics
- **D-13:** Which tools belong in which tier — agent decides based on usage patterns
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Core Architecture
- `luminamind/deep_agent.py` — Agent factory, existing tool integration, subagent definitions
- `luminamind/py_tools/registry.py` — PY_TOOL_REGISTRY holding all tool implementations
- `luminamind/config/checkpointer.py` — Existing factory pattern (create_checkpointer)

### Codebase Structure
- `.planning/codebase/STRUCTURE.md` — Directory layout, naming conventions
- `.planning/codebase/STACK.md` — Technology stack (LangChain, LangGraph, deepagents)
- `.planning/codebase/ARCHITECTURE.md` — Layer overview, data flow

### Requirements & Roadmap
- `.planning/REQUIREMENTS.md` — TOOL-01 through TOOL-06
- `.planning/ROADMAP.md` — Phase 5 structure, plan items 05-01 through 05-05

No external specs — requirements fully captured in decisions above.
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `PY_TOOL_REGISTRY`: Source of truth for tool definitions — extend with tier metadata
- `create_deep_agent()`: Entry point for tool and hook integration
- `deepagents` library: Already supports subagents and tool configurations

### Established Patterns
- Factory pattern with fallback (see create_checkpointer)
- Pydantic models for configuration
- Environment variable configuration via config/env.py

### Integration Points
- Tool tiering: Modify `PY_TOOL_REGISTRY` structure, update `deep_agent.py` tool selection
- Lifecycle hooks: Integrate with `create_deep_agent()` call
- Recovery: Apply to HTTP client in `utils/http_client.py`
</code_context>

<specifics>
## Specific Ideas

- Tool tier metadata structure: `{"tier": "core|extended|specialist", "task_types": [], "min_score": 0.0}`
- Prompt preset structure: `{id, name, task_type, base_prompt, variations: [], version, created_at}`
- Hook callback signature: `async def on_event(event_type: str, context: dict) -> None`
- Circuit breaker states: CLOSED (normal), OPEN (failing), HALF_OPEN (testing)
</specifics>

<deferred>
## Deferred Ideas

None — all Phase 5 topics covered.
</deferred>

---

*Phase: 05-tool-prompt-optimization*
*Context gathered: 2026-04-27*
