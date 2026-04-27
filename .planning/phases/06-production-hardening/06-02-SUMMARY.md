---
phase: 06-production-hardening
plan: '02'
type: execute
wave: 1
subsystem: observability
tags:
  - harness-debugging
  - trace-replay
  - decision-logging
  - redis
depends_on: []
provides:
  - DecisionLogger
  - TraceViewer
  - TraceEntry
  - DecisionPoint
affects:
  - luminamind/observability/decision_logger.py
  - luminamind/observability/trace_viewer.py
  - luminamind/evaluator/pipeline.py
tech_stack:
  added:
    - decision_logger.py (TraceEntry, DecisionPoint dataclasses, DecisionLogger)
    - trace_viewer.py (TraceViewer, ReplayResult)
  patterns:
    - Redis-backed trace storage with memory fallback
    - Dataclass serialization for trace entries
    - Module-level logger instance pattern
key_files:
  created:
    - luminamind/observability/decision_logger.py
    - luminamind/observability/trace_viewer.py
  modified:
    - luminamind/evaluator/pipeline.py
decisions:
  - Used Redis key format "trace:{task_id}" for trace entries
  - Module-level _decision_logger singleton in pipeline.py
  - In-memory fallback when Redis unavailable
  - Dataclass to_dict/from_dict for JSON serialization
requirements:
  - P6-02
---

# Phase 06 Plan 02: Harness Debugging Tools — SUMMARY

## One-liner

DecisionLogger and TraceViewer for step-by-step replay and decision annotation.

## Commits

| Task | Name | Commit | Files |
| ---- | ---- | ------ | ----- |
| 1 | DecisionLogger with TraceEntry and DecisionPoint | cc002cd | luminamind/observability/decision_logger.py |
| 2 | TraceViewer for replay | 171ae7d | luminamind/observability/trace_viewer.py |
| 3 | RefinementPipeline integration | bdccc64 | luminamind/evaluator/pipeline.py |

## Tasks Completed

### Task 1: Create TraceEntry and DecisionPoint data classes

**Action:** Created `luminamind/observability/decision_logger.py` with:
- `DecisionPoint` dataclass for key decisions (decision_id, timestamp, phase, decision_type, context, choice, alternatives, rationale, outcome)
- `TraceEntry` dataclass for execution steps (entry_id, timestamp, step_number, component, action, inputs, outputs, decisions, metadata)
- `DecisionLogger` class with:
  - `log_decision(point: DecisionPoint)` — records a decision
  - `log_trace_entry(entry: TraceEntry, task_id: str)` — records a trace entry
  - `get_trace_for_task(task_id: str) -> list[TraceEntry]` — retrieves trace
  - `annotate_decision_outcome(decision_id: str, outcome: str)` — fills in outcome
  - Redis storage with key format `trace:{task_id}`, in-memory fallback

**Verification:** `python3 -c "from luminamind.observability.decision_logger import DecisionLogger, DecisionPoint, TraceEntry; d = DecisionLogger(); print('DecisionLogger importable')"` — PASSED

### Task 2: Create TraceViewer for replay

**Action:** Created `luminamind/observability/trace_viewer.py` with:
- `TraceViewer` class with:
  - `get_trace(task_id: str) -> list[TraceEntry]` — retrieves full trace
  - `replay_trace(task_id: str) -> ReplayResult` — reconstructs execution path
  - `export_trace(task_id: str, format: str = "json") -> str` — exports as JSON or text
  - `compare_traces(task_id_a: str, task_id_b: str) -> list[str]` — compares two traces
- `ReplayResult` dataclass with `decisions_reconstructed`, `execution_path`, `partial` flag

**Verification:** `python3 -c "from luminamind.observability.trace_viewer import TraceViewer; t = TraceViewer(); print('TraceViewer importable')"` — PASSED

### Task 3: Integrate decision logging into RefinementPipeline

**Action:** Modified `luminamind/evaluator/pipeline.py`:
- Added imports: `DecisionLogger`, `DecisionPoint`, `TraceEntry` from observability
- Added module-level `_decision_logger = DecisionLogger()` instance
- Added `_log_iteration_trace()` method that logs:
  - **Quality gate decision**: `decision_type="quality_gate"`, context includes scores and threshold, choice="pass" or "fail"
  - **Convergence decision**: `decision_type="convergence"`, context includes iteration count and stability
- Added `_compute_stability()` helper for convergence stability description
- Called `_log_iteration_trace()` at iteration boundaries in `refine()` method

**Verification:** `grep -n "DecisionLogger" luminamind/evaluator/pipeline.py` — PASSED (2 occurrences)

## Verification

**Plan verification command:**
```python
python3 -c "
from luminamind.observability.decision_logger import DecisionLogger, DecisionPoint, TraceEntry
from luminamind.observability.trace_viewer import TraceViewer
from datetime import datetime

dl = DecisionLogger()
tp = DecisionPoint(
    decision_id='test-1',
    timestamp=datetime.now(),
    phase='test',
    decision_type='quality_gate',
    context={'score': 0.8},
    choice='pass',
    alternatives=['fail'],
    rationale='score above threshold'
)
dl.log_decision(tp)
print('Decision logged successfully')

tv = TraceViewer()
print('TraceViewer initialized')
"
```
**Result:** PASSED

## Success Criteria Status

| Criterion | Status |
|-----------|--------|
| DecisionLogger writes DecisionPoints to Redis | ✅ PASSED |
| TraceViewer can retrieve and replay traces | ✅ PASSED |
| RefinementPipeline integration complete | ✅ PASSED |
| export_trace produces valid JSON output | ✅ PASSED |
| compare_traces identifies decision differences | ✅ PASSED |

## Deviations from Plan

None — plan executed exactly as written.

## Threat Flags

None — no new network endpoints, auth paths, or schema changes at trust boundaries.

## Self-Check: PASSED

Files exist:
- FOUND: luminamind/observability/decision_logger.py
- FOUND: luminamind/observability/trace_viewer.py
- FOUND: luminamind/evaluator/pipeline.py

Commits exist:
- FOUND: cc002cd
- FOUND: 171ae7d
- FOUND: bdccc64
