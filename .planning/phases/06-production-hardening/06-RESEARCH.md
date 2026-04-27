# Phase 6: Production Hardening - Research

**Phase:** 06-production-hardening
**Date:** 2026-04-27
**Status:** Ready for Planning

---

## Domain Analysis

Phase 6 focuses on hardening the LuminaMind harness for production use with observability, safety guardrails, and performance optimization. The phase builds on all prior phases (1-5) and must integrate with the existing evaluator sandbox, planner sprint system, tool tiering, and live verification infrastructure.

---

## Existing Foundation

### Already Implemented (Phases 1-5)

| Component | Location | Notes |
|-----------|----------|-------|
| Basic metrics | `luminamind/observability/metrics.py` | Prometheus counters/histograms for tool invocations |
| Basic logging | `luminamind/observability/logging.py` | Structured logging setup |
| Safety checks | `luminamind/py_tools/safety.py` | Path boundary enforcement (ALLOWED_ROOT) |
| Checkpointing | `luminamind/config/checkpointer.py` | Redis-backed MemorySaver for state persistence |
| Retry framework | `luminamind/utils/retry.py` | Exponential backoff retry logic |
| Rate limiting | `luminamind/utils/rate_limit.py` | HTTP client rate limiting |
| Evaluator sandbox | `luminamind/evaluator/sandbox.py` | Context manager for isolated evaluation |
| Feedback bridge | `luminamind/evaluator/feedback_bridge.py` | File-based generator-evaluator communication |
| Iteration controller | `luminamind/evaluator/iteration.py` | Convergence detection with sliding window |
| Refinement pipeline | `luminamind/evaluator/pipeline.py` | GAN-inspired generator-evaluator loop |

### What's Missing for Production

| Gap | Impact |
|-----|--------|
| No harness-specific metrics (iteration count, evaluator scores, tool efficiency) | Can't measure harness health |
| No debugging tools (trace viewer, step replay) | Hard to diagnose harness failures |
| No circuit breakers on LLM calls | Cascading failures possible |
| No sandbox for generated code execution | Safety risk |
| No approval workflow integration | Can't require human sign-off for sensitive ops |
| No token optimization | Wasting context window allocation |

---

## Technical Approach

### 1. Harness Metrics (`06-01`)

**Goal:** Track harness-specific metrics beyond basic tool metrics.

**Design:**
- `HarnessMetrics` class in `luminamind/observability/harness_metrics.py`
- Iteration-level metrics: iteration count, evaluator scores per round, convergence status
- Tool usage efficiency: calls per task, avg duration, error rate
- Agent-level metrics: planner calls, executor calls, evaluator calls
- Sprint metrics: contract negotiation duration, spec generation time

**Integration:** Metrics should be additive to existing `metrics.py` (prometheus_client registry shared).

**File:** `luminamind/observability/harness_metrics.py`

### 2. Harness Debugging Tools (`06-02`)

**Goal:** Enable step-by-step replay of harness execution.

**Design:**
- `TraceViewer` class in `luminamind/observability/trace_viewer.py`
- Checkpoint-based trace recording (leverages existing `checkpointer.py`)
- Decision annotation: log key decisions at each iteration with context
- Step replay: reconstruct execution path from checkpoints
- Session replay: re-run a harness session with same inputs

**Key insight:** The `checkpointer.py` already has Redis-backed state persistence. Extend it to record decision points.

**Files:**
- `luminamind/observability/trace_viewer.py`
- `luminamind/observability/decision_logger.py`

### 3. Safety Enhancements (`06-03`)

**Goal:** Sandbox generated code and add circuit breakers.

**Design:**
- Circuit breaker pattern for LLM calls (extend `retry.py` with failure threshold)
- Code execution sandbox (temporary directory with restricted permissions)
- Output validation before returning to agent
- Resource limits (max execution time, max output size)

**Existing patterns:**
- `luminamind/py_tools/safety.py` already has path boundary enforcement
- `luminamind/evaluator/sandbox.py` has evaluator sandbox context manager

**Files:**
- `luminamind/safety/circuit_breaker.py`
- `luminamind/safety/code_sandbox.py`
- `luminamind/safety/output_validator.py`

### 4. Approval Workflow (`06-04`)

**Goal:** Human-in-the-loop for sensitive operations.

**Design:**
- `ApprovalQueue` for operations requiring sign-off
- Integration with evaluator pipeline (escalation on low scores)
- Batch approval for bulk operations
- CLI/API for approval management

**Note:** This is framework-level, not UI-level (dashboard comes in Phase 8).

**Files:**
- `luminamind/approval/queue.py`
- `luminamind/approval/policies.py`
- `luminamind/approval/cli.py`

### 5. Token Optimization (`06-05`)

**Goal:** Smart context window allocation.

**Design:**
- Context budget calculator based on task complexity
- Dynamic allocation: more tokens for complex tasks
- KV cache optimization (identify stable prompt segments)
- Compression strategy selection based on remaining budget

**Existing work:**
- `luminamind/config/context_compactor.py` has compaction logic from Phase 1
- `luminamind/config/prompt_prefix.py` has prefix caching from Phase 1

**Files:**
- `luminamind/optimization/token_budget.py`
- `luminamind/optimization/cache_optimizer.py`

### 6. Parallelization (`06-06`)

**Goal:** Concurrent subagent execution with result merging.

**Design:**
- Task pool for parallel subagent spawning
- Result aggregator with conflict resolution
- Dependency graph for ordered execution where required
- Context inheritance boundaries (from Phase 3 subagent system)

**Existing:**
- `luminamind/planner/bounded_subagent.py` has subagent context inheritance
- `luminamind/planner/agent_message_bus.py` has inter-agent communication

**Files:**
- `luminamind/execution/task_pool.py`
- `luminamind/execution/result_aggregator.py`
- `luminamind/execution/dependency_graph.py`

---

## Key Decisions Required During Planning

1. **Trace storage:** Redis-backed (leverages existing infrastructure) vs. file-based (simpler)
2. **Circuit breaker thresholds:** What failure count triggers open state? What retry interval?
3. **Sandbox implementation:** subprocess with restricted permissions vs. containerized (Phase 9 has Docker sandbox)
4. **Approval persistence:** Redis-backed queue vs. file-based (leverages checkpointer)
5. **Token budget strategy:** Fixed allocation per role vs. dynamic based on task complexity scoring

---

## Dependencies

| Phase | Dependency | Usage |
|-------|------------|-------|
| Phase 1 | Context compaction, prompt prefix | Token optimization builds on these |
| Phase 2 | Evaluator sandbox, feedback bridge | Debugging traces evaluator execution |
| Phase 3 | Bounded subagent, agent message bus | Parallelization extends subagent system |
| Phase 4 | Live verification | Debugging traces include verification runs |
| Phase 5 | Tool tiering, lifecycle hooks | Metrics track tool usage efficiency |

---

## Patterns to Follow

- **Prometheus metrics:** Already in use (`metrics.py`) — extend, don't replace
- **Context manager for sandbox:** Already used in `evaluator/sandbox.py`
- **Redis-backed persistence:** Already in `checkpointer.py` — extend for trace storage
- **Dataclass-based config:** Used throughout for configuration objects
- **Registry pattern:** Used in `criteria_engine.py`, `py_tools/registry.py`

---

## Common Pitfalls

1. **Metrics explosion:** Too many unique label combinations → cardinality issues
2. **Trace storage growth:** Unbounded trace history → Redis memory pressure
3. **Circuit breaker flapping:** Too-low thresholds → premature opens
4. **Sandbox security:** Path traversal in generated code → use `safety.py` path validation
5. **Token overallocation:** Aggressive compression → quality degradation

---

## Verification Architecture

For each plan, the verification approach:

| Plan | Verification Method |
|------|---------------------|
| 06-01 | Prometheus metrics scrapeable at `/metrics` endpoint |
| 06-02 | Trace replay produces same decisions as original execution |
| 06-03 | Circuit opens after N failures, closes after recovery interval |
| 06-04 | Approval queue persists across restarts (Redis-backed) |
| 06-05 | Token usage reduced by measured amount vs. baseline |
| 06-06 | Parallel tasks complete within theoretical minimum time |

---

## Out of Scope

- UI dashboard (Phase 8)
- Docker sandbox (Phase 9.3)
- Multi-tenancy RBAC (Phase 8.7)
- Plugin system (Phase 9.8)
