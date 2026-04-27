# Phase 8: Agent Swarm & Scheduled Automation — Research

**Researched:** 2026-04-27
**Status:** Ready for planning
**Source:** /gsd-plan-phase workflow (--research flag)

---

## Research Domain

Phase 8 transforms LuminaMind into an autonomous agent platform. Key architectural concerns:

1. **Task Queue & Persistence** — Redis-backed queue with retry logic
2. **Scheduler & Cron** — Time-based task triggering with cron expressions
3. **Agent Swarm** — Multi-agent coordination with emergent behavior
4. **Background Workers** — Long-running processes surviving restarts
5. **Monitoring** — Real-time dashboard and alerting
6. **API/CLI** — External control surface
7. **Enterprise** — Multi-tenancy, RBAC, audit
8. **Distribution** — Docker-based one-command install

---

## Validation Architecture

### Framework

- **Python testing:** pytest with pytest-asyncio for async tests
- **Test location:** `tests/unit/` per module + `tests/integration/` for API

### Quick run command

```bash
pytest tests/unit/ -v --tb=short
```

### Full suite command

```bash
pytest tests/ -v --tb=short
```

### Sampling Rate

- After every task: run unit tests for modified module
- After every wave: full suite
- Before gsd-verify-work: all tests must pass

### Manual-Only Verifications

| Behavior | Why Manual |
|----------|-----------|
| Docker container isolation | Requires Docker daemon |
| Cross-platform install scripts | Platform-specific testing |
| WebSocket real-time updates | Requires live server |
| Graceful worker shutdown | Timing-dependent |

---

## Architecture Patterns

### Task Queue (08-01)

**Pattern:** Redis-backed with in-memory fallback

Key files:
- `luminamind/queue/task_queue.py` — TaskQueue interface
- `luminamind/queue/redis_backend.py` — Redis implementation
- `luminamind/queue/memory_backend.py` — In-memory fallback

Redis patterns from roadmap:
- `Task.enqueue()` → LPUSH to list
- `Task.dequeue()` → BRPOP with timeout
- `Task.ack()` → LREM after success
- Dead letter queue: separate key with failed tasks

### Scheduler (08-02)

**Pattern:** Cron expression parsing + tick loop

Key files:
- `luminamind/scheduler/cron_parser.py` — CronExpression class
- `luminamind/scheduler/scheduler.py` — Scheduler tick loop

Cron parsing approach:
- Use `croniter` library for Python cron parsing (or implement 5-field parser)
- Tick loop: timer-based, calculate next fire time, trigger when due

### Swarm (08-03)

**Pattern:** Shared knowledge base + role-based specialization

Key files:
- `luminamind/swarm/swarm.py` — Swarm main class
- `luminamind/swarm/knowledge_base.py` — SharedKnowledge

Agent communication:
- Broadcast: pub/sub pattern
- Direct: message queue per agent
- Consensus: priority-based voting

---

## Dependencies

| Sub-plan | Dependencies |
|----------|--------------|
| 08-01 (Queue) | None — foundational |
| 08-02 (Scheduler) | 08-01 |
| 08-03 (Swarm) | 08-01, 08-02 |
| 08-04 (Workers) | 08-01, 08-02 |
| 08-05 (Monitoring) | 08-03, 08-04 |
| 08-06 (API) | 08-01, 08-02, 08-03 |
| 08-07 (Enterprise) | 08-06 |
| 08-08 (Install) | All above |

---

## Key Classes Reference

### TaskQueue API

```python
class TaskQueue:
    def enqueue(task: Task, delay_seconds: int = 0) -> str: ...
    def dequeue(timeout_seconds: int = 0) -> Task | None: ...
    def ack(task_id: str) -> None: ...
    def nack(task_id: str, error: str) -> None: ...
    def cancel(task_id: str) -> bool: ...
    def get_status(task_id: str) -> TaskStatus: ...
    def get_metrics() -> QueueMetrics: ...
```

### Scheduler API

```python
class Scheduler:
    def schedule(task: ScheduledTask) -> str: ...
    def unschedule(task_id: str) -> bool: ...
    def pause(task_id: str) -> bool: ...
    def resume(task_id: str) -> bool: ...
    def get_next_runs(count: int) -> list[datetime]: ...
    def tick() -> list[Task]: ...
```

### Swarm API

```python
class Swarm:
    def spawn(role: AgentRole, config: dict) -> str: ...
    def kill(agent_id: str) -> bool: ...
    def broadcast(message: SwarmMessage) -> None: ...
    def send_to(agent_id: str, message: SwarmMessage) -> None: ...
    def get_status() -> SwarmStatus: ...
    def wait_for_completion(timeout_seconds: int) -> SwarmResult: ...
```

---

## Testing Strategy

### Unit Tests

| Module | Test File | Coverage Target |
|--------|----------|----------------|
| queue | `tests/unit/test_task_queue.py` | 90%+ |
| scheduler | `tests/unit/test_scheduler.py` | 90%+ |
| swarm | `tests/unit/test_swarm.py` | 85%+ |
| worker | `tests/unit/test_worker.py` | 85%+ |
| monitoring | `tests/unit/test_monitoring.py` | 80%+ |
| api | `tests/integration/test_api.py` | 80%+ |

### Integration Tests

- API endpoints: `tests/integration/test_api.py`
- Queue + Scheduler + Swarm E2E: `tests/integration/test_swarm.py`

---

## Common Pitfalls

1. **Redis connection failures** — Use connection pooling, implement retry logic
2. **Scheduler tick drift** — Use monotonic clock, track drift
3. **Swarm consensus deadlocks** — Implement timeout on voting
4. **Worker crash recovery** — Re-queue in-flight tasks with proper state
5. **Docker image size** — Multi-stage build, minimize layers

---

## Threat Model Notes

- **T-08-01:** Queue injection (untrusted task payload) — validate all task fields
- **T-08-02:** Scheduler cron injection — validate cron expressions
- **T-08-03:** Swarm agent spoofing — authenticate agent communication
- **T-08-04:** Worker privilege escalation — sandbox worker processes
- **T-08-05:** Metrics tampering — read-only metric queries
- **T-08-06:** API auth bypass — require auth on all endpoints
- **T-08-07:** Tenant isolation breach — namespace per tenant

---
*Phase: 08-agent-swarm-automation*
*Researched: 2026-04-27*
