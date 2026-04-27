---
phase: 11
plan: 09
subsystem: execution
tags: [task-pool, batch-ordering, bugfix]
dependency_graph:
  requires: []
  provides: []
  affects: [luminamind/execution/dependency_graph.py]
tech_stack:
  added: []
  patterns: [result-map-ordering]
key_files:
  created: []
  modified:
    - luminamind/execution/task_pool.py
decisions: []
metrics:
  duration: ""
  completed: "2026-04-28"
---

# Phase 11 Plan 09: TaskPool execute_with_dependencies Batch Fix

## One-liner

Fixed batch result ordering in TaskPool.execute_with_dependencies to return results in same order as input tasks list.

## Objective

Fix `execute_with_dependencies` batch bug where `wait_all()` returns results in submission/futures order instead of matching the input `tasks` list order.

## Tasks Completed

| # | Name | Commit | Files |
|---|------|--------|-------|
| 1 | Fix batch result ordering in execute_with_dependencies | `a85e95c` | `luminamind/execution/task_pool.py` |

## Changes

**File:** `luminamind/execution/task_pool.py` (lines 153-158)

### Before:
```python
batch_results = self.wait_all()
all_results.extend(batch_results)  # Wrong order - futures dict order
```

### After:
```python
batch_results = self.wait_all()
result_map = {r.task_id: r for r in batch_results}
for task_id in batch:
    all_results.append(result_map[task_id])  # Correct order - batch order
```

## Verification

- Import verification passed: `from luminamind.execution.task_pool import TaskPool, Task`

## Success Criteria

✅ `execute_with_dependencies` returns results in task list order, not arbitrary futures order.

## Deviations from Plan

None — fix applied exactly as specified.

## Commits

- `a85e95c`: fix(11-09): fix batch result ordering in execute_with_dependencies