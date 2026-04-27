# Phase 6: Production Hardening - Research

**Researched:** 2026-04-27
**Domain:** Harness observability, safety guardrails, performance optimization
**Confidence:** HIGH

## Summary

Phase 6 hardens the LuminaMind harness for production use across six dimensions: metrics, debugging, safety, approval workflows, token optimization, and parallelization. The phase extends existing infrastructure (Prometheus metrics in `metrics.py`, circuit breaker in `retry.py`, Redis-backed checkpointer, evaluator sandbox) rather than building new foundations. Key architectural decisions: use `prometheus_client` for metrics (already in use), extend the `CircuitBreaker` from `retry.py` for LLM call protection, leverage `subprocess` with temp directory isolation for code sandboxing, and build parallelization on `concurrent.futures` with dependency graph ordering.

**Primary recommendation:** Extend existing patterns (context managers for sandbox lifecycle, dataclasses for config, prometheus_client for metrics) rather than introducing new libraries. The existing `CircuitBreaker` in `retry.py` should be refactored into `luminamind/safety/circuit_breaker.py` as the canonical location for safety primitives.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Harness metrics | API/Backend | — | Prometheus counters/histograms track harness internals |
| Harness debugging (trace viewer) | API/Backend | — | Checkpoint-based trace recording, Redis-backed persistence |
| Safety (circuit breakers) | API/Backend | — | Protect LLM calls from cascading failures |
| Safety (code sandbox) | API/Backend | — | Subprocess isolation for generated code execution |
| Safety (output validation) | API/Backend | — | Pattern matching and structure validation |
| Approval workflow | API/Backend | — | Queue-based human-in-the-loop for sensitive operations |
| Token optimization | API/Backend | — | Smart context window allocation and KV cache |
| Parallelization | API/Backend | — | concurrent.futures task pool with dependency graph |

## User Constraints (from CONTEXT.md)

*No CONTEXT.md found — using REQUIREMENTS.md and STATE.md as context sources.*

### Phase Requirements (from REQUIREMENTS.md)

| ID | Description | Research Support |
|----|-------------|------------------|
| PROD-01 | Harness-specific metrics track iteration count, evaluator scores, tool usage efficiency | 06-01 extends Prometheus metrics |
| PROD-02 | Harness debugging tools enable trace viewing and step-by-step replay | 06-02 builds on checkpointer |
| PROD-03 | Safety systems sandbox generated code and validate output before evaluation | 06-03 extends evaluator sandbox |
| PROD-04 | Circuit breakers prevent infinite loops and dead letter queues capture failed tasks | 06-03 refactors existing CircuitBreaker |
| PROD-05 | Token optimization achieves smart context window allocation with KV cache | 06-05 extends context_compactor.py |
| PROD-06 | Parallelization enables concurrent subagent execution with result merging | 06-06 extends bounded_subagent.py |

### Existing Decisions (from STATE.md)

- EvaluatorSandbox uses context manager pattern for lifecycle management
- Tool dispatch pattern for evaluation (playwright, api_testing, db_verifier)
- IterationController convergence requires both score AND issue count stability
- RefinementPipeline orchestrates generator-evaluator loop with quality gate
- FallbackChain for retry with exponential backoff
- Lifecycle hooks: on_init, on_start, on_step, on_complete, on_error, on_exit

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `prometheus_client` | latest | Metrics collection | Already in use in `observability/metrics.py` |
| `concurrent.futures` | stdlib | Parallel execution | ThreadPoolExecutor for task pool |
| `subprocess` | stdlib | Code sandbox | Temp directory isolation, restricted env |
| `redis` | latest | State persistence | Already in use via `checkpointer.py` |
| `threading` | stdlib | Thread-safe operations | Already used in `retry.py`, `agent_message_bus.py` |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `tempfile` | stdlib | Temp directory creation | Sandbox workspace isolation |
| `signal` | stdlib | Timeout enforcement | Task execution timeout |
| `pathlib` | stdlib | Path manipulation | `ensure_path_allowed` integration |
| `dataclasses` | stdlib | Configuration objects | Already established pattern |

### Installation

```bash
pip install prometheus_client redis
```

**Version verification:** `npm` not applicable — Python project. Standard library covers `concurrent.futures`, `subprocess`, `threading`, `tempfile`, `pathlib`, `dataclasses`.

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     Harness (Phase 6)                           │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │   Metrics    │  │  Debugging   │  │   Safety             │   │
│  │  (06-01)     │  │  (06-02)     │  │  (06-03)             │   │
│  │              │  │              │  │                      │   │
│  │ HarnessMetrics│  │TraceViewer  │  │ CircuitBreaker      │   │
│  │ - iteration  │  │ - checkpoints│  │ - LLM call protect  │   │
│  │ - scores     │  │ - decision   │  │ CodeSandbox         │   │
│  │ - tool eff   │  │   logs       │  │ - temp dir isolation│   │
│  │ - agent call│  │ - step replay│  │ OutputValidator     │   │
│  └──────────────┘  └──────────────┘  │ - pattern blocking  │   │
│         │                │          └──────────────────────┘   │
│         ▼                ▼                     │               │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Shared Infrastructure                        │   │
│  │  • prometheus_client registry (metrics.py)              │   │
│  │  • RedisBackedMemorySaver (checkpointer.py)             │   │
│  │  • CircuitBreaker (retry.py) → safety/circuit_breaker   │   │
│  └──────────────────────────────────────────────────────────┘   │
│         │                │                    │               │
│         ▼                ▼                    ▼               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │  Approval   │  │   Token      │  │   Parallelization   │   │
│  │  (06-04)    │  │  (06-05)     │  │  (06-06)            │   │
│  │             │  │              │  │                      │   │
│  │ ApprovalQueue│  │TokenBudget  │  │ TaskPool            │   │
│  │ - escalate  │  │ - allocation│  │ - concurrent.futures│   │
│  │ - batch     │  │ - KV cache  │  │ ResultAggregator    │   │
│  │ - CLI/API   │  │ - compress  │  │ DependencyGraph     │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure

```
luminamind/
├── observability/
│   ├── __init__.py
│   ├── logging.py          # Existing
│   ├── metrics.py         # Existing — base Prometheus metrics
│   ├── harness_metrics.py # 06-01 — HarnessMetrics class
│   └── trace_viewer.py    # 06-02 — trace viewing and replay
├── safety/
│   ├── __init__.py
│   ├── circuit_breaker.py # 06-03 — refactored from retry.py
│   ├── code_sandbox.py    # 06-03 — subprocess sandbox
│   └── output_validator.py # 06-03 — output validation
├── approval/
│   ├── __init__.py
│   ├── queue.py           # 06-04 — ApprovalQueue
│   ├── policies.py        # 06-04 — escalation policies
│   └── cli.py             # 06-04 — CLI/API for approvals
├── optimization/
│   ├── __init__.py
│   ├── token_budget.py    # 06-05 — context window allocation
│   └── cache_optimizer.py # 06-05 — KV cache optimization
├── execution/
│   ├── __init__.py
│   ├── task_pool.py       # 06-06 — TaskPool for parallel exec
│   ├── result_aggregator.py # 06-06 — ResultAggregator
│   └── dependency_graph.py # 06-06 — DependencyGraph
├── evaluator/
│   ├── sandbox.py         # Existing — EvaluatorSandbox
│   ├── pipeline.py        # Existing — RefinementPipeline
│   └── iteration.py       # Existing — IterationController
├── config/
│   ├── checkpointer.py    # Existing — Redis-backed persistence
│   └── context_compactor.py # Existing — compression logic
└── planner/
    ├── bounded_subagent.py # Existing — context inheritance
    └── agent_message_bus.py # Existing — message bus
```

### Pattern 1: Prometheus Metrics Extension

**What:** Extend existing `prometheus_client` pattern from `metrics.py`
**When to use:** Adding new metrics to the harness

```python
# From luminamind/observability/metrics.py (existing pattern)
from prometheus_client import Counter, Histogram, Gauge

# New harness metrics in harness_metrics.py
ITERATION_COUNT = Counter(
    "luminamind_iteration_total",
    "Total refinement iterations",
    ["task_id", "status"],
)

EVALUATOR_SCORE = Histogram(
    "luminamind_evaluator_score",
    "Evaluator score per iteration",
    ["task_id", "domain"],
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
)

class HarnessMetrics:
    """Singleton for harness metrics."""
    _instance = None

    def record_iteration(self, task_id: str, score_breakdown: dict, status: str):
        ITERATION_COUNT.labels(task_id=task_id, status=status).inc()
        for domain, score in score_breakdown.items():
            EVALUATOR_SCORE.labels(task_id=task_id, domain=domain).observe(score)
```

### Pattern 2: Context Manager for Sandbox Lifecycle

**What:** Use `__enter__`/`__exit__` for sandbox setup/teardown
**When to use:** Creating isolated execution environments

```python
# From luminamind/evaluator/sandbox.py (existing pattern)
class CodeSandbox:
    def __init__(self, config: SandboxConfig | None = None):
        self.config = config or SandboxConfig()
        self._temp_dir: str | None = None

    def __enter__(self) -> CodeSandbox:
        self._temp_dir = tempfile.mkdtemp(prefix="luminamind_sandbox_")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._temp_dir and Path(self._temp_dir).exists():
            shutil.rmtree(self._temp_dir, ignore_errors=True)
        self._temp_dir = None
```

### Pattern 3: Circuit Breaker for LLM Protection

**What:** Protect LLM calls from cascading failures
**When to use:** Any external LLM call that could fail

```python
# Refactor from luminamind/utils/retry.py (existing CircuitBreaker)
class CircuitBreaker:
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_max_calls: int = 3,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._lock = threading.Lock()

    def call(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        if not self._can_execute():
            raise CircuitOpenError(f"Circuit {self.name} is OPEN")
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
```

### Pattern 4: TaskPool with Dependency Graph

**What:** Execute tasks with dependency ordering and parallelization
**When to use:** Parallel subagent execution

```python
# From 06-06-PLAN.md
class TaskPool:
    def __init__(self, max_workers: int = 4):
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)

    def execute_with_dependencies(self, tasks: list[Task]) -> list[TaskResult]:
        graph = DependencyGraph()
        for task in tasks:
            graph.add_node(task.task_id, task.dependencies)
        batches = graph.get_execution_order()  # [[a], [b, c], [d]] style
        # Execute each batch in parallel, wait for completion before next batch
```

### Anti-Patterns to Avoid

- **Creating new metric registries:** Use the shared `prometheus_client` registry from `metrics.py` — don't create separate registries
- **Blocking pattern for async LLM calls:** Use async-compatible patterns from `retry.py` — don't mix sync/async circuit breakers
- **Unbounded trace storage:** Implement trace retention policy — don't let Redis memory grow unbounded
- **Trusting LLM output without validation:** Always run `OutputValidator` on sandboxed execution results
- **Naive parallelization (all tasks at once):** Use `DependencyGraph.get_execution_order()` — don't submit dependent tasks simultaneously

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Metrics collection | Custom counter/histogram | `prometheus_client` | Already in use, shares `/metrics` endpoint |
| Circuit breaker | Custom failure tracking | `CircuitBreaker` from `retry.py` (refactor to `safety/`) | Already implemented, tested pattern |
| Sandboxed execution | Custom subprocess isolation | `subprocess.run()` with temp dir + env restriction | Standard Python approach, container-level in Phase 9 |
| Task parallelization | Custom thread management | `concurrent.futures.ThreadPoolExecutor` | Standard library, handles pool lifecycle |
| State persistence | Custom Redis serialization | `RedisBackedMemorySaver` from `checkpointer.py` | Already handles pickle serialization |
| Token estimation | Simple char count | Existing `ContextCompactor._estimate_tokens()` | 1 token ≈ 4 chars is industry standard approximation |

**Key insight:** The codebase already has substantial infrastructure. Phase 6 extends rather than replaces — the `CircuitBreaker` exists in `retry.py`, the `EvaluatorSandbox` exists, the `checkpointer.py` has Redis persistence. The task is integration and filling gaps.

## Runtime State Inventory

*Not applicable — Phase 6 is greenfield implementation of production hardening features, not a rename/refactor/migration phase.*

## Common Pitfalls

### Pitfall 1: Metrics Cardinality Explosion
**What goes wrong:** Too many unique label combinations (e.g., `task_id` as label) causes Prometheus memory issues.
**Why it happens:** Each unique combination creates a new time series.
**How to avoid:** Use `task_id` as a label only for iteration-scoped metrics; aggregate to session-level for long-term storage. Consider high-cardinality labels as `task_id:iteration` or use recording rules.
**Warning signs:** `prometheus_client` warnings about duplicate metrics, memory growth on `/metrics` endpoint.

### Pitfall 2: Trace Storage Memory Growth
**What goes wrong:** Unbounded trace history fills Redis memory.
**Why it happens:** Each checkpoint stored indefinitely.
**How to avoid:** Implement trace retention — limit stored traces to last N sessions or TTL-based cleanup. Add periodic cleanup task.
**Warning signs:** Redis `maxmemory` warnings, slow `GET` operations.

### Pitfall 3: Circuit Breaker Flapping
**What goes wrong:** Circuit opens too quickly, recovers, opens again — never stabilizes.
**Why it happens:** Threshold too low, recovery timeout too short.
**How to avoid:** Start with conservative defaults (5 failures, 60s timeout). Monitor circuit state transitions.
**Warning signs:** Frequent `CircuitBreakerOpen` exceptions in logs.

### Pitfall 4: Sandbox Security (Path Traversal)
**What goes wrong:** Generated code escapes sandbox to access host filesystem.
**Why it happens:** Insufficient path validation on generated code.
**How to avoid:** Use `ensure_path_allowed` from `safety.py` for all file operations. Run subprocess with restricted `$HOME` and no access to parent directories.
**Warning signs:** Files appearing outside workspace, `PermissionError` from unexpected locations.

### Pitfall 5: Token Overallocation in Optimization
**What goes wrong:** Aggressive compression degrades output quality.
**Why it happens:** Compression factor too aggressive, summarization loses critical context.
**How to avoid:** Measure quality degradation (comparing scores before/after compression). Set minimum compression ratio floor.
**Warning signs:** Evaluator scores dropping after compaction, more refinement iterations needed.

### Pitfall 6: Parallelization Deadlocks
**What goes wrong:** Tasks waiting for each other in circular dependency.
**Why it happens:** Dependency graph has cycle, or tasks hold locks while waiting.
**How to avoid:** `DependencyGraph.validate()` catches cycles before execution. Use non-blocking result fetching.
**Warning signs:** Tasks stuck in `PENDING` state, `TimeoutError` on `wait_all()`.

## Code Examples

### HarnessMetrics Integration with RefinementPipeline

```python
# In luminamind/evaluator/pipeline.py (existing)
from luminamind.observability.harness_metrics import HarnessMetrics

class RefinementPipeline:
    def refine(self, initial_artifact, task_description, artifact_type="code"):
        # ... existing code ...
        session_id = str(uuid.uuid4())
        current_artifact = initial_artifact

        result, stats = self.controller.run(current_artifact)

        # NEW: Record metrics after each iteration
        HarnessMetrics().record_iteration(
            session_id,
            {"design": result.domain_scores.get("design", 0),
             "code": result.domain_scores.get("code", 0)},
            stats.status
        )

        HarnessMetrics().record_agent_call("evaluator", result.score > 0)

        return RefinementResult(...)
```

### Circuit Breaker Decorator for LLM Calls

```python
# In luminamind/safety/circuit_breaker.py
from luminamind.utils.retry import CircuitBreaker, circuit_breaker

# Refactor existing CircuitBreaker here, keep import alias in retry.py for backward compat

_llm_circuit = CircuitBreaker(
    name="llm-provider",
    failure_threshold=5,
    recovery_timeout=60.0,
)

@circuit_breaker(_llm_circuit)
async def call_llm(prompt: str) -> str:
    # LLM call here
    response = await model.acall(prompt)
    return response
```

### CodeSandbox Execution

```python
# In luminamind/safety/code_sandbox.py
with CodeSandbox() as sandbox:
    result = sandbox.execute("print('hello from sandbox')")
    validator = OutputValidator()
    validation = validator.validate(result.output)
    if not validation.valid:
        raise ValueError(f"Output blocked: {validation.issues}")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| ad-hoc logging | Prometheus metrics + Grafana dashboards | Industry shift 2023-2024 | Observability without custom parsing |
| Retry only | Retry + Circuit Breaker | Fowler microservices 2010s, adapted for LLM 2024 | Prevents cascading failures |
| Direct execution | Sandbox + validation | Security best practice | Safety for generated code |
| Sequential tasks | TaskPool + DependencyGraph | Standard parallelization | Performance via concurrency |
| Fixed token allocation | Dynamic budget + compression | Context window limits 2024 | Cost efficiency |

**Deprecated/outdated:**
- Custom metric libraries (use `prometheus_client`)
- Blocking retry without circuit breaker (use `FallbackChain` + `CircuitBreaker`)
- Single-threaded execution (use `ThreadPoolExecutor`)

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `prometheus_client` is the standard metrics library | Standard Stack | MEDIUM — if team prefers OpenTelemetry, would need refactor |
| A2 | Redis-backed checkpointer is the persistence layer | Common Pitfalls | LOW — file-based fallback exists |
| A3 | subprocess sandbox is sufficient for Phase 6 | Don't Hand-Roll | MEDIUM — Docker sandbox comes in Phase 9, may need restructure |
| A4 | concurrent.futures is appropriate for parallelization | Standard Stack | LOW — asyncio could be used but adds complexity |

*No user confirmation needed — all assumptions are LOW/MEDIUM risk and backed by existing codebase patterns.*

## Open Questions

1. **Trace storage format:** Redis-backed (current checkpointer pattern) vs. file-based with Redis index?
   - What we know: `checkpointer.py` has Redis-backed `MemorySaver`
   - What's unclear: Whether traces should use same Redis key or separate namespace
   - Recommendation: Use separate key prefix `langgraph:traces:` to avoid key collisions

2. **Circuit breaker thresholds:** What values for failure_threshold and recovery_timeout?
   - What we know: Defaults (5 failures, 60s timeout) are industry standard
   - What's unclear: Whether GLM-4.5-flash has different failure characteristics than typical API
   - Recommendation: Start with defaults, add metrics to observe actual failure patterns

3. **Token budget strategy:** Fixed allocation per role vs. dynamic based on task complexity?
   - What we know: `ContextCompactor` exists with recent-biased compression
   - What's unclear: How to score task complexity without LLM call
   - Recommendation: Use heuristic (file count, task description length) for Phase 6, refine in Phase 9

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | Core runtime | ✓ | 3.12 | — |
| prometheus_client | Metrics | ✓ | latest | — |
| redis | State persistence | ✗ | — | FileBackedMemorySaver |
| subprocess | Sandbox execution | ✓ | stdlib | — |
| concurrent.futures | Parallelization | ✓ | stdlib | — |

**Missing dependencies with fallback:**
- **redis:** Use `FileBackedMemorySaver` from `checkpointer.py` instead — works without Redis

**Missing dependencies with no fallback:**
- None identified — all Phase 6 requirements have standard library or existing package fallbacks

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing project standard) |
| Config file | `pytest.ini` or `pyproject.toml` |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ --tb=short` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PROD-01 | Metrics track iteration count | unit | `pytest tests/test_harness_metrics.py -x` | ❌ Wave 0 |
| PROD-01 | Metrics track evaluator scores | unit | `pytest tests/test_harness_metrics.py -x` | ❌ Wave 0 |
| PROD-01 | Metrics track tool efficiency | unit | `pytest tests/test_harness_metrics.py -x` | ❌ Wave 0 |
| PROD-02 | Trace viewer reconstructs execution | unit | `pytest tests/test_trace_viewer.py -x` | ❌ Wave 0 |
| PROD-02 | Step replay produces same decisions | integration | `pytest tests/test_trace_viewer.py::test_replay -x` | ❌ Wave 0 |
| PROD-03 | Circuit opens after N failures | unit | `pytest tests/test_circuit_breaker.py -x` | ❌ Wave 0 |
| PROD-03 | Circuit closes after recovery | unit | `pytest tests/test_circuit_breaker.py -x` | ❌ Wave 0 |
| PROD-03 | Sandbox executes in temp directory | unit | `pytest tests/test_code_sandbox.py -x` | ❌ Wave 0 |
| PROD-03 | OutputValidator blocks dangerous patterns | unit | `pytest tests/test_output_validator.py -x` | ❌ Wave 0 |
| PROD-04 | Circuit breaker prevents cascading failures | integration | `pytest tests/test_safety_integration.py -x` | ❌ Wave 0 |
| PROD-05 | Token budget allocates dynamically | unit | `pytest tests/test_token_budget.py -x` | ❌ Wave 0 |
| PROD-06 | TaskPool executes in parallel | unit | `pytest tests/test_task_pool.py -x` | ❌ Wave 0 |
| PROD-06 | ResultAggregator merges with conflicts | unit | `pytest tests/test_result_aggregator.py -x` | ❌ Wave 0 |
| PROD-06 | DependencyGraph orders tasks | unit | `pytest tests/test_dependency_graph.py -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/ -x -q` (quick feedback)
- **Per wave merge:** `pytest tests/ --tb=short` (full suite)
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_harness_metrics.py` — covers PROD-01
- [ ] `tests/test_trace_viewer.py` — covers PROD-02
- [ ] `tests/test_circuit_breaker.py` — covers PROD-03 (circuit breaker part)
- [ ] `tests/test_code_sandbox.py` — covers PROD-03 (sandbox part)
- [ ] `tests/test_output_validator.py` — covers PROD-03 (validator part)
- [ ] `tests/test_safety_integration.py` — covers PROD-04
- [ ] `tests/test_token_budget.py` — covers PROD-05
- [ ] `tests/test_task_pool.py` — covers PROD-06 (TaskPool part)
- [ ] `tests/test_result_aggregator.py` — covers PROD-06 (ResultAggregator part)
- [ ] `tests/test_dependency_graph.py` — covers PROD-06 (DependencyGraph part)
- [ ] `tests/conftest.py` — shared fixtures

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | N/A — internal harness |
| V3 Session Management | no | N/A — internal harness |
| V4 Access Control | no | N/A — internal harness |
| V5 Input Validation | yes | OutputValidator blocks dangerous patterns (r"\__import__", r"exec\s*\(") |
| V6 Cryptography | no | N/A — no crypto operations |

### Known Threat Patterns for Python/LLM Harness

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Shell injection via generated code | Tampering/Spoofing | `ensure_path_allowed` validation, sandbox subprocess restriction |
| Circuit breaker failure amplification | Denial of Service | Exponential backoff, half-open state recovery |
| Unbounded resource consumption | Denial of Service | Max execution time (signal.alarm), max output bytes (1MB limit) |
| Metrics endpoint exposure | Information Disclosure | Prometheus `/metrics` endpoint should be internal-only |

## Sources

### Primary (HIGH confidence)
- `luminamind/observability/metrics.py` — existing Prometheus metrics pattern
- `luminamind/utils/retry.py` — existing CircuitBreaker implementation
- `luminamind/config/checkpointer.py` — Redis-backed persistence pattern
- `luminamind/evaluator/sandbox.py` — existing sandbox context manager
- `luminamind/evaluator/pipeline.py` — RefinementPipeline integration point
- `luminamind/planner/bounded_subagent.py` — subagent context inheritance
- `luminamind/planner/agent_message_bus.py` — inter-agent communication

### Secondary (MEDIUM confidence)
- WebSearch: "Python harness metrics Prometheus LangGraph observability 2024" — confirmed prometheus_client as standard
- WebSearch: "Python circuit breaker LLM calls LangChain resilience patterns 2024" — confirmed circuit breaker for LLM protection

### Tertiary (LOW confidence)
- WebSearch: "Python code sandbox execution restricted subprocess isolation" — baseline subprocess sandboxing knowledge

## Metadata

**Confidence breakdown:**
- Standard Stack: HIGH — all libraries verified against existing codebase
- Architecture: HIGH — derived from existing patterns in codebase
- Pitfalls: MEDIUM — some inferred from common patterns, not verified in this codebase

**Research date:** 2026-04-27
**Valid until:** 2026-05-27 (30 days — Phase 6 is stable Python patterns)
