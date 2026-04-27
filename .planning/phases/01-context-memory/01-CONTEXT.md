# Phase 01: Context & Memory Infrastructure - Context

**Gathered:** 2026-04-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement structured session memory with two-layer architecture (full transcript + working memory), prompt prefix caching, and context compaction to reduce token waste by 40%.
</domain>

<decisions>
## Implementation Decisions

### Two-Layer Memory Architecture
- **D-01:** Layer on existing checkpointer infrastructure. FullTranscript = JSONL file persistence + in-memory index. WorkingMemory = structured fields in checkpointer state.
- **D-02:** SessionStore factory mirrors create_checkpointer pattern (Redis → File → in-memory fallback)
- **D-03:** Session resumption via thread_id lookup in session index + checkpointer state restoration
- **D-04:** Working memory compaction runs on each agent turn (automatic)

### Prompt Prefix Caching
- **D-05:** PromptPrefixBuilder generates workspace summary (repo root, git status, project structure)
- **D-06:** Cache invalidation on mtime changes (file modifications bust the cache)
- **D-07:** Stable content cached; dynamic content (tool results, user input) excluded

### Context Compaction
- **D-08:** Recent-biased compression: keep recent turns rich, compress older turns
- **D-09:** File read deduplication: same file content not re-sent in same session
- **D-10:** Max-token budget enforcement with quality fallback

### Session Persistence
- **D-11:** Session index tracks: thread_id, created_at, last_accessed, summary
- **D-12:** Session listing and cleanup utilities exposed via SessionStore API

### agent Discretion
- **D-13:** Exact compaction ratio (e.g., 50% reduction for turns older than N) — agent tunes based on benchmark results
- **D-14:** File read deduplication window (same file within N turns) — agent decides based on typical session length
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Core Architecture
- `luminamind/deep_agent.py` — Agent factory, existing checkpointer integration
- `luminamind/config/checkpointer.py` — Existing checkpointer classes (MemorySaver, RedisBackedMemorySaver, FileBackedMemorySaver)
- `luminamind/py_tools/registry.py` — Tool registry (PY_TOOL_REGISTRY) for tool metadata
- `luminamind/observability/logging.py` — Structured logging setup

### Codebase Structure
- `.planning/codebase/STRUCTURE.md` — Directory layout, naming conventions, where to add new code
- `.planning/codebase/ARCHITECTURE.md` — Layer overview, data flow, key abstractions
- `.planning/codebase/STACK.md` — Technology stack (LangChain, LangGraph, deepagents versions)

### Requirements & Roadmap
- `.planning/PROJECT.md` — Project constraints, tech stack locked decisions
- `.planning/REQUIREMENTS.md` — MEM-01 through MEM-04 as success criteria
- `.planning/ROADMAP.md` — Phase 1 structure, plan items 01-01 through 01-04

No external specs — requirements fully captured in decisions above.
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `MemorySaver`, `RedisBackedMemorySaver`, `FileBackedMemorySaver`: Extend, don't replace
- `create_checkpointer()` factory: Mirror for SessionStore factory
- LangGraph checkpointer protocol: Compatible with two-layer memory design
- Tool registry (`PY_TOOL_REGISTRY`): Source of tool descriptions for PromptPrefixBuilder

### Established Patterns
- Factory pattern with Redis → File → in-memory fallback for checkpointer
- Pickle serialization for checkpointer state
- Thread-ID scoped conversation state

### Integration Points
- Agent initialization in `deep_agent.py:app` — checkpointer passed at construction
- Session state flows through `configurable.thread_id`
- Tools access via `PY_TOOL_REGISTRY` — could feed into prompt prefix builder
</code_context>

<specifics>
## Specific Ideas

- JSONL format for FullTranscript: one JSON object per message, file per session
- WorkingMemory fields: current_task, important_files[], recent_notes[], pending_actions[]
- Session index: lightweight SQLite or JSON file (per-workspace)
- Cache key: hash of (workspace_summary, mtimes) — invalidation via mtime compare
</specifics>

<deferred>
## Deferred Ideas

None — all Phase 1 topics covered.
</deferred>

---

*Phase: 01-context-memory*
*Context gathered: 2026-04-27*
