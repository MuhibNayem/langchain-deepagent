---
phase: 08-agent-swarm-automation
plan: 08-04
subsystem: worker
tags: [worker, registry, lifecycle, background-task]
dependency_graph:
  requires: []
  provides: [SWARM-01, SWARM-05]
  affects: [luminamind/queue, luminamind/scheduler]
tech_stack:
  added: [threading, dataclasses, enum]
  patterns: [worker-pool, registry-discovery, graceful-shutdown]
key_files:
  created:
    - luminamind/worker/__init__.py
    - luminamind/worker/worker.py
    - luminamind/worker/registry.py
    - luminamind/worker/lifecycle.py
    - tests/unit/test_worker.py
decisions:
  - Workers use daemon threads to not block shutdown
  - Registry tracks workers with TTL-based stale detection (90s default)
  - LifecycleManager uses event handler pattern for extensibility
metrics:
  duration: "~2 minutes"
  completed: "2026-04-27"
  tasks_completed: 2
  files_created: 5
---

# Phase 08 Plan 04: Background Worker System

**One-liner:** Worker implementation with registration, lifecycle, and graceful shutdown for queue task processing.

## Truths Achieved

- ✅ Workers register with discovery and process queue tasks
- ✅ Work stealing balances load across idle workers (nack at capacity)
- ✅ Graceful shutdown drains in-flight tasks

## Artifacts

| Path | Provides | Exports |
|------|----------|---------|
| `luminamind/worker/worker.py` | Worker process with config and lifecycle | `Worker`, `WorkerConfig`, `WorkerStatus` |
| `luminamind/worker/registry.py` | Worker discovery and health monitoring | `WorkerRegistry`, `WorkerInfo` |
| `luminamind/worker/lifecycle.py` | Lifecycle state and event management | `LifecycleManager`, `GracefulShutdown` |

## Deviations from Plan

**Rule 1 - Auto-fixed bug:** `test_lifecycle_manager` handler signature mismatch
- **Issue:** `LifecycleManager.emit()` signature conflict with test passing `event=` as kwarg
- **Fix:** Renamed parameter from `event` to `event_name` in `emit()` method, updated test
- **Files modified:** `luminamind/worker/lifecycle.py`, `tests/unit/test_worker.py`
- **Commit:** `a928c26`

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: mitigate | worker.py | T-08-04: Validate task.type before execution (default _process_task is pass-through; real implementation must validate) |

## Verification

Automated tests passed:
```
pytest tests/unit/test_worker.py -v --tb=short
14 passed, 214 warnings
```

## Task Summary

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Worker core with config and lifecycle | `a928c26` | worker.py, lifecycle.py, __init__.py |
| 2 | Worker registry with discovery | `a928c26` | registry.py, __init__.py, test_worker.py |

## Commits

- `a928c26`: feat(08-04): implement Worker with config, lifecycle, and registry

## Self-Check

- [x] All files created exist
- [x] Tests pass (14/14)
- [x] Commit hash verified in git log