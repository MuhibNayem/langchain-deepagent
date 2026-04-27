---
phase: 8
slug: agent-swarm-automation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-27
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x with pytest-asyncio |
| **Config file** | pytest.ini or pyproject.toml (TBD by executor) |
| **Quick run command** | `pytest tests/unit/ -v --tb=short -x` |
| **Full suite command** | `pytest tests/ -v --tb=short` |
| **Estimated runtime** | ~120 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/unit/<module>/ -v --tb=short`
- **After every plan wave:** Run `pytest tests/ -v --tb=short`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 08-01-01 | 08-01 | 1 | Queue architecture | T-08-01 | Input validation on all task fields | unit | `pytest tests/unit/test_task_queue.py::test_enqueue -v` | ✅ W0 | ⬜ pending |
| 08-01-02 | 08-01 | 1 | Redis persistence | T-08-01 | Redis connection uses TLS | unit | `pytest tests/unit/test_task_queue.py::test_redis_backend -v` | ✅ W0 | ⬜ pending |
| 08-02-01 | 08-02 | 2 | Cron parsing | T-08-02 | Cron expressions validated before parsing | unit | `pytest tests/unit/test_scheduler.py::test_cron_parse -v` | ✅ W0 | ⬜ pending |
| 08-03-01 | 08-03 | 3 | Swarm spawn | T-08-03 | Agent identity verified on spawn | unit | `pytest tests/unit/test_swarm.py::test_spawn -v` | ✅ W0 | ⬜ pending |
| 08-03-02 | 08-03 | 3 | Swarm consensus | T-08-03 | Voting timeout prevents deadlock | unit | `pytest tests/unit/test_swarm.py::test_consensus -v` | ✅ W0 | ⬜ pending |
| 08-04-01 | 08-04 | 3 | Worker lifecycle | T-08-04 | Worker runs in sandboxed context | unit | `pytest tests/unit/test_worker.py::test_worker_start -v` | ✅ W0 | ⬜ pending |
| 08-05-01 | 08-05 | 4 | Alert rules | T-08-05 | Alert conditions sanitized | unit | `pytest tests/unit/test_monitoring.py::test_alert_rule -v` | ✅ W0 | ⬜ pending |
| 08-06-01 | 08-06 | 4 | API auth | T-08-06 | All endpoints require valid API key | integration | `pytest tests/integration/test_api.py::test_auth_required -v` | ✅ W0 | ⬜ pending |
| 08-07-01 | 08-07 | 5 | Tenant isolation | T-08-07 | Namespace enforced on all queries | unit | `pytest tests/unit/test_enterprise.py::test_tenant_isolation -v` | ✅ W0 | ⬜ pending |
| 08-08-01 | 08-08 | 6 | Docker build | — | Multi-stage build produces image | manual | `docker build -t luminamind:test .` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/test_task_queue.py` — stubs for TaskQueue, Task, TaskStatus, Priority
- [ ] `tests/unit/test_scheduler.py` — stubs for CronExpression, Scheduler
- [ ] `tests/unit/test_swarm.py` — stubs for Swarm, AgentRole, SwarmConfig
- [ ] `tests/unit/test_worker.py` — stubs for Worker, WorkerConfig
- [ ] `tests/unit/test_monitoring.py` — stubs for AlertRule, AlertEngine
- [ ] `tests/integration/test_api.py` — stubs for API endpoints
- [ ] `pytest` and `pytest-asyncio` installed in environment

*If none: "Wave 0 will create test infrastructure as needed."*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Docker container isolation | T-08-04 | Requires Docker daemon running | `docker run --rm luminamind:test pytest tests/` |
| Cross-platform install scripts | 08-08-04 | Platform-specific execution | Test on macOS/Linux/Windows respectively |
| WebSocket real-time updates | 08-06-04 | Requires live server + browser | Open dashboard, trigger event, observe WebSocket |
| Graceful worker shutdown | 08-04-05 | Timing-dependent race conditions | Send SIGTERM, verify drain completes |

*If none: "All phase behaviors have automated verification."*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
