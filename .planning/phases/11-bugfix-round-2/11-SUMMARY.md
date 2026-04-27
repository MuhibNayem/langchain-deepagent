# Phase 11: Bug Fixes Round 2 — COMPLETED

**Duration:** ~15 minutes (all plans)
**Plans:** 13/13 complete
**Commits:** 26 total

---

## Summary

| Plan | Fix | Status |
|------|-----|--------|
| 11-01 | datetime import in RefinementPipeline | ✅ |
| 11-02 | Pillow get_flattened_data() → getdata() | ✅ (pre-existing fix) |
| 11-03 | pytest configuration for test collection | ✅ |
| 11-04 | aiofiles moved to main dependencies | ✅ |
| 11-05 | API auth enforcement on all endpoints | ✅ |
| 11-06 | SQL injection prevention in DB verifier | ✅ |
| 11-07 | Memory queue delay (datetime.now() + timedelta) | ✅ |
| 11-08 | TaskPool signal.alarm → cross-platform timeout | ✅ |
| 11-09 | TaskPool execute_with_dependencies batch ordering | ✅ |
| 11-10 | EventBuffer index corruption on deque rotation | ✅ |
| 11-11 | PluginSandbox uses DockerBackend (not abstract Sandbox) | ✅ |
| 11-12 | Swarm send_to() edge case validation | ✅ |
| 11-13 | Events router included in FastAPI app | ✅ |

---

## Key Fixes

### Critical
- **RefinementPipeline datetime**: Added `from datetime import datetime` at pipeline.py:15
- **DB verifier SQL injection**: Added `_is_safe_identifier()`, parameterized queries, identifier allowlist validation

### High
- **Memory queue delay**: `enqueue` now uses `datetime.now() + timedelta(seconds=delay_seconds)` instead of `datetime.utcnow()`
- **TaskPool signal safety**: Replaced `signal.alarm()` with executor-based cross-platform timeout
- **EventBuffer index corruption**: `_index` dict now decrements remaining indices by 1 after `popleft()`
- **PluginSandbox**: Changed `Sandbox(config)` → `DockerBackend(config)` to avoid abstract instantiation

### Medium
- **API auth**: All 16 endpoints now require `verify_api_key` dependency
- **Events router**: Added `include_router(events_router.router)` to app.py
- **send_to() edge cases**: Validates agent_id not empty, message not None, no self-messaging

---

## Remaining Open Items

- Missing source module imports (5 test files): `py_tools.edit`, `replace_in_file`, `web_crawl`, `deep_agent.app`, `_search_ollama` — require new source files, not dependency fixes
- API route mutable dict defaults (queue.py, scheduler.py, swarm.py)
- EventSchema.validate()/migrate() stubs returning None
- Model role middleware stub returning None at line 35
- Memory namespace export/import stubs
- Sandbox network policy export stub
- Weather tool module-level _SESSION patching issue