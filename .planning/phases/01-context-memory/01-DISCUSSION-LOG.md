# Phase 01: Context & Memory Infrastructure - Discussion Log

**Phase:** 01 - context-memory
**Date:** 2026-04-27
**Mode:** --auto (recommended defaults auto-selected)

---

## Areas Discussed

### Two-Layer Memory Architecture
- **Q:** How to implement two-layer memory (FullTranscript + WorkingMemory)?
- **Options:** Layer on checkpointer (Recommended) | Independent stores
- **Selected:** Layer on checkpointer (Recommended)
- **Rationale:** Build on existing MemorySaver. FullTranscript = JSONL files + in-memory index. WorkingMemory = structured fields in checkpointer state. Cleaner integration with LangGraph.

### Session Resumption
- **Q:** Session resumption approach?
- **Selected:** Session index store + checkpointer per-thread (recommended default)
- **Rationale:** SessionStore factory mirrors create_checkpointer pattern (Redis → File → in-memory fallback). Session index tracks thread_id, created_at, last_accessed, summary.

### Prompt Prefix Caching
- **Q:** Prompt caching approach?
- **Selected:** Workspace summary builder with mtime-based invalidation (recommended default)
- **Rationale:** PromptPrefixBuilder generates workspace summary (repo root, git status, project structure). Cache invalidation on mtime changes.

### Context Compaction
- **Q:** Context compaction strategy?
- **Selected:** Recent-biased compression with file read deduplication (recommended default)
- **Rationale:** Keep recent turns rich, compress older turns. Same file content not re-sent in same session. Max-token budget enforcement with quality fallback.

---

## Decisions Summary

| Decision | Choice |
|----------|--------|
| Two-layer memory approach | Layer on checkpointer |
| Session resumption | Session index + checkpointer per-thread |
| Prompt caching | Workspace summary + mtime invalidation |
| Context compaction | Recent-biased + file deduplication |

## Deferred Ideas

None — all Phase 1 topics covered in defaults.

---

*Discussion log — not consumed by downstream agents*
