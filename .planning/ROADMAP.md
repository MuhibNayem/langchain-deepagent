# Roadmap

**Project:** LuminaMind Harness Engineering
**Phases:** 9 | **Status:** Pre-execution

---

## Phase 1 — Context & Memory Infrastructure

**Goal:** Implement structured session memory with two-layer architecture (full transcript + working memory), prompt prefix caching, and context compaction to reduce token waste by 40%

**Requirements:** [All new — no existing map]

**Success Criteria:**
1. Working memory reduces token waste by 40% (benchmarked)
2. Session resumption works across restarts
3. Prompt prefix caching active on stable content
4. Context compaction maintains quality under max-token budget with recent-biased compression

**Plans:**
- [x] 01-01: Two-layer memory architecture (SessionMemory, FullTranscript, WorkingMemory) — `.planning/phases/01-context-memory/01-01-PLAN.md`
- [x] 01-02: Session resumption capability (SessionStore) — `.planning/phases/01-context-memory/01-02-PLAN.md`
- [x] 01-03: Prompt prefix caching system (PromptPrefixBuilder) — `.planning/phases/01-context-memory/01-03-PLAN.md`
- [x] 01-04: Context compaction (ContextCompactor with recent-biased compression) — `.planning/phases/01-context-memory/01-04-PLAN.md`

---

## Phase 2 — Generator-Evaluator Architecture

**Goal:** Build GAN-inspired dual-agent system with evaluator agent catching 90% of bugs that generator misses

**Requirements:** [All new — no existing map]

**Success Criteria:**
1. Evaluator catches 90% of bugs that generator misses (benchmark comparison)
2. Iterative refinement loop converges on quality code
3. Grading criteria framework covers design, originality, craft, functionality
4. Sandbox environment for isolated evaluation

**Plans:**
- [x] 02-01: Evaluator agent system (EvaluatorAgent, grading criteria framework)
- [x] 02-02: Frontend design evaluator (visual quality scoring, actionable critique)
- [x] 02-03: Code quality evaluator (correctness, maintainability, performance, security)
- [x] 02-04: Evaluator sandbox (Playwright MCP, API testing, DB state verification)
- [x] 02-05: Iteration controller (max-iteration limits, convergence detection)
- [x] 02-06: Feedback bridge (generator-evaluator communication)
- [x] 02-07: Multi-round refinement pipeline (quality gate enforcement)
- [x] 02-08: Grading criteria engine (domain-specific criteria sets)

---

## Phase 3 — Planner & Sprint System

**Goal:** Enable AI feature suggestion, spec generation, sprint contracts, and bounded subagents for coordinated multi-agent execution

**Requirements:** [All new — no existing map]

**Success Criteria:**
1. Planner produces spec in <5 min that evaluator approves
2. Sprint contract negotiation produces signed agreements
3. Bounded subagents respect context inheritance boundaries
4. Multi-agent coordination handles message queuing and conflict resolution

**Plans:**
- [x] 03-01: Planner agent (spec expansion, feature decomposition, AI suggestion integration)
- [x] 03-02: Spec generation (structured output, user stories, acceptance criteria)
- [x] 03-03: Planner-evaluator integration (spec review loop)
- [x] 03-04: Sprint contract framework (negotiation protocol, persistence)
- [x] 03-05: Contract verification (criterion-by-criterion checking)
- [x] 03-06: Sprint lifecycle manager (planning → execution → verification → handoff)
- [x] 03-07: Bounded subagent system (context inheritance, recursion depth limiting)
- [x] 03-08: Subagent communication layer (AgentMessageBus, output merging)

---

## Phase 4 — Live Verification Infrastructure

**Goal:** Implement Playwright MCP integration and database state verification for automated UI/API testing

**Requirements:** [All new — no existing map]

**Success Criteria:**
1. Live verification finds UI bugs without human testing
2. Visual regression detection identifies layout changes
3. API endpoint testing validates backend contracts
4. Database state verification confirms expected state assertions

**Plans:**
- [x] 04-01: Playwright MCP bridge (browser automation, screenshot capture, user flow simulation) — `.planning/phases/04-live-verification/04-01-PLAN.md`
- [x] 04-02: Visual regression detection (screenshot comparison, layout change detection) — `.planning/phases/04-live-verification/04-02-PLAN.md`
- [x] 04-03: API testing integration (endpoint discovery, request/response logging) — `.planning/phases/04-live-verification/04-03-PLAN.md`
- [x] 04-04: Database state verifier (schema introspection, state query, expected assertions) — `.planning/phases/04-live-verification/04-04-PLAN.md`
- [x] 04-05: Evaluator integration (connect DB verifier to evaluator agent) — `.planning/phases/04-live-verification/04-05-PLAN.md`

---

## Phase 5 — Tool & Prompt Optimization

**Goal:** Implement tool tiering, prompt library, and lifecycle hooks for maintainability and extensibility

**Requirements:** [All new — no existing map]

**Success Criteria:**
1. Tool tiering reduces unnecessary tool exposure by 50% (tool call count metrics)
2. Prompt library maps task types to presets with versioning
3. Lifecycle hooks fire on all agent lifecycle events
4. Recovery framework handles retries with exponential backoff

**Plans:**
- [ ] 05-01: Tool audit and tiering (core, extended, specialist tiers, context-dependent loading)
- [ ] 05-02: Prompt preset library (CRUD, task-type mapping, A/B testing)
- [ ] 05-03: Dynamic prompt composition (context-aware assembly, personality variations)
- [ ] 05-04: Lifecycle hook system (on_init, on_start, on_step, on_complete, on_error, on_exit)
- [ ] 05-05: Recovery and retry framework (exponential backoff, circuit breaker, fallback chain)

---

## Phase 6 — Production Hardening

**Goal:** Add harness-specific observability, safety guardrails, and performance optimization

**Requirements:** [All new — no existing map]

**Success Criteria:**
1. 99.9% task completion with no silent failures (chaos test pass rate)
2. Harness debugging tools enable step-by-step replay
3. Safety systems sandbox generated code and validate output
4. Token optimization achieves 40% reduction in context window allocation

**Plans:**
- [ ] 06-01: Harness-specific metrics (iteration count, evaluator score tracking, tool usage efficiency)
- [ ] 06-02: Harness debugging tools (trace viewer, step-by-step replay, decision annotation)
- [ ] 06-03: Safety enhancements (evaluator-specific checks, sandboxed code execution, circuit breakers)
- [ ] 06-04: Approval workflow integration (automatic escalation, batch approval)
- [ ] 06-05: Token usage optimization (smart context window allocation, compression, KV cache)
- [ ] 06-06: Parallelization (concurrent subagent execution, result merging)

---

## Phase 7 — Integration & Testing

**Goal:** Wire all components into unified harness and establish regression test suite

**Requirements:** [All new — no existing map]

**Success Criteria:**
1. End-to-end harness matches Claude Code quality (human evaluation survey)
2. Benchmark suite (100+ cases) enables automated scoring
3. Chaos testing validates resilience to network/LLM failures

**Plans:**
- [ ] 07-01: End-to-end integration (wire Phase 1-6 components, configuration management)
- [ ] 07-02: Demo applications (frontend design demo, full-stack app demo, code review demo)
- [ ] 07-03: Benchmark harness (100+ test cases, automated scoring, regression detection)
- [ ] 07-04: Chaos testing (network failure simulation, LLM timeout/failure simulation)

---

## Phase 7 — Integration & Testing

**Goal:** Wire all components into unified harness and establish regression test suite

**Requirements:** [All new — no existing map]

**Success Criteria:**
1. End-to-end harness matches Claude Code quality (human evaluation survey)
2. Benchmark suite (100+ cases) enables automated scoring
3. Chaos testing validates resilience to network/LLM failures

**Plans:**
- [ ] 07-01: End-to-end integration (wire Phase 1-6 components, configuration management)
- [ ] 07-02: Demo applications (frontend design demo, full-stack app demo, code review demo)
- [ ] 07-03: Benchmark harness (100+ test cases, automated scoring, regression detection)
- [ ] 07-04: Chaos testing (network failure simulation, LLM timeout/failure simulation)

---

## Phase 8 — Agent Swarm & Scheduled Automation

**Goal:** Transform LuminaMind from single-task harness to autonomous agent platform with swarm intelligence, scheduled task execution, and multi-agent coordination

**Requirements:** [All new — no existing map]

**Success Criteria:**
1. Agent swarm coordinates 5+ agents on a single task without conflicts
2. Scheduled tasks trigger agent execution on cron-like schedule
3. Background tasks persist across process restarts
4. Swarm achieves emergent behavior through agent specialization
5. Task queue handles 100+ concurrent tasks with retry logic
6. Monitoring dashboard shows swarm health, task status, resource usage
7. Alert system notifies on task failure, convergence issues, resource exhaustion

---

### Phase 8.1 — Task Queue & Persistence

**Goal:** Persistent task queue with retry logic, priority handling, and dead-letter queue

**Subtasks:**
- [ ] 08-01-01: Task queue architecture (FIFO, priority, delayed execution)
- [ ] 08-01-02: Task persistence to Redis (serialization, deserialization)
- [ ] 08-01-03: Retry logic with exponential backoff (max_attempts, backoff_multiplier)
- [ ] 08-01-04: Dead-letter queue for failed tasks after max retries
- [ ] 08-01-05: Task cancellation (user-initiated abort)
- [ ] 08-01-06: Task priority escalation (tasks promoted after waiting threshold)
- [ ] 08-01-07: Task deduplication (idempotency key per task type)
- [ ] 08-01-08: Task rate limiting (max concurrent tasks per namespace)

**Files:**
- `luminamind/queue/task_queue.py` — TaskQueue, Task, TaskStatus, Priority enum
- `luminamind/queue/redis_backend.py` — Redis-backed queue implementation
- `luminamind/queue/memory_backend.py` — In-memory fallback
- `luminamind/queue/retry_policy.py` — RetryPolicy dataclass
- `tests/unit/test_task_queue.py` — Unit tests

**Key Classes:**
```python
class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DEAD_LETTER = "dead_letter"

class Task:
    id: str
    type: str  # "planner", "generator", "evaluator", "sprint"
    payload: dict
    priority: Priority  # LOW, NORMAL, HIGH, CRITICAL
    status: TaskStatus
    created_at: datetime
    scheduled_at: datetime | None  # For delayed tasks
    started_at: datetime | None
    completed_at: datetime | None
    attempts: int
    max_attempts: int
    error: str | None
    idempotency_key: str | None

class TaskQueue:
    def enqueue(task: Task, delay_seconds: int = 0) -> str: ...
    def dequeue(timeout_seconds: int = 0) -> Task | None: ...
    def ack(task_id: str) -> None: ...
    def nack(task_id: str, error: str) -> None: ...
    def cancel(task_id: str) -> bool: ...
    def get_status(task_id: str) -> TaskStatus: ...
    def get_metrics() -> QueueMetrics: ...
```

---

### Phase 8.2 — Scheduler & Cron System

**Goal:** Time-based task scheduling with cron expressions, one-shot tasks, and recurring task management

**Subtasks:**
- [ ] 08-02-01: Cron expression parser (standard cron format: minute, hour, day, month, weekday)
- [ ] 08-02-02: One-shot scheduled tasks (run once at specific datetime)
- [ ] 08-02-03: Recurring task registration (daily, weekly, monthly, custom cron)
- [ ] 08-02-04: Scheduler engine (tick loop, next-fire calculation)
- [ ] 08-02-05: Timezone support (UTC, local, named timezones)
- [ ] 08-02-06: Missed task handling (run_missed, skip_missed, run_once)
- [ ] 08-02-07: Task persistence across restarts (scheduler state serialization)
- [ ] 08-02-08: Calendar-based scheduling (exclude holidays, business days only)

**Files:**
- `luminamind/scheduler/cron_parser.py` — CronExpression, CronField
- `luminamind/scheduler/scheduler.py` — Scheduler, ScheduledTask
- `luminamind/scheduler/timezone.py` — TimezoneConfig
- `luminamind/scheduler/calendar.py` — BusinessCalendar
- `tests/unit/test_scheduler.py` — Unit tests

**Key Classes:**
```python
class CronExpression:
    minute: str  # 0-59, */5, etc.
    hour: str    # 0-23, */2, etc.
    day_of_month: str  # 1-31, */3, etc.
    month: str   # 1-12, */2, etc.
    day_of_week: str  # 0-6, mon-fri, etc.

    def next_fire_time(from_time: datetime) -> datetime: ...
    def validate() -> bool: ...

class ScheduledTask:
    id: str
    name: str
    cron: CronExpression | None  # None = one-shot
    task_type: str  # References TaskQueue task type
    payload: dict
    timezone: str  # "UTC", "America/New_York", etc.
    run_missed: bool
    enabled: bool
    last_run: datetime | None
    next_run: datetime | None
    total_runs: int

class Scheduler:
    def schedule(task: ScheduledTask) -> str: ...
    def unschedule(task_id: str) -> bool: ...
    def pause(task_id: str) -> bool: ...
    def resume(task_id: str) -> bool: ...
    def get_next_runs(count: int) -> list[datetime]: ...
    def tick() -> list[Task]: ...  # Returns tasks due to run
```

---

### Phase 8.3 — Agent Swarm Orchestration

**Goal:** Coordinate multiple agents as a swarm with shared context, role specialization, and emergent coordination

**Subtasks:**
- [ ] 08-03-01: Swarm architecture (Swarm, AgentRole, SwarmConfig)
- [ ] 08-03-02: Role-based agent specialization (planner_role, generator_role, reviewer_role)
- [ ] 08-03-03: Shared knowledge base (vector store, graph store for agent memory)
- [ ] 08-03-04: Agent heartbeat and health monitoring
- [ ] 08-03-05: Swarm consensus mechanism (voting, priority-based conflict resolution)
- [ ] 08-03-06: Emergent task decomposition (swarm auto-splits large tasks)
- [ ] 08-03-07: Agent spawning and lifecycle management
- [ ] 08-03-08: Cross-agent communication (broadcast, direct, pub/sub)
- [ ] 08-03-09: Swarm termination conditions (all agents idle, timeout, goal achieved)
- [ ] 08-03-10: Inter-agent dependency graph and topological execution

**Files:**
- `luminamind/swarm/swarm.py` — Swarm, AgentRole, SwarmConfig
- `luminamind/swarm/roles.py` — RoleSpecialization, RoleRegistry
- `luminamind/swarm/knowledge_base.py` — SharedKnowledge, VectorStore, GraphStore
- `luminamind/swarm/health.py` — AgentHeartbeat, SwarmHealth
- `luminamind/swarm/consensus.py` — ConsensusMechanism, VotingProtocol
- `luminamind/swarm/spawner.py` — AgentSpawner, LifecycleManager
- `luminamind/swarm/dependency.py` — DependencyGraph, TopologicalExecutor
- `tests/unit/test_swarm.py` — Unit tests

**Key Classes:**
```python
class AgentRole(Enum):
    PLANNER = "planner"
    GENERATOR = "generator"
    REVIEWER = "reviewer"
    COORDINATOR = "coordinator"
    SPECIALIST = "specialist"

class SwarmConfig:
    max_agents: int
    idle_timeout_seconds: int
    consensus_threshold: float
    heartbeat_interval_seconds: int
    auto_spawn: bool
    shared_knowledge_enabled: bool

class Swarm:
    def spawn(role: AgentRole, config: dict) -> str: ...  # Returns agent_id
    def kill(agent_id: str) -> bool: ...
    def broadcast(message: SwarmMessage) -> None: ...
    def send_to(agent_id: str, message: SwarmMessage) -> None: ...
    def get_status() -> SwarmStatus: ...
    def wait_for_completion(timeout_seconds: int) -> SwarmResult: ...

class SharedKnowledge:
    def store(key: str, value: Any, ttl_seconds: int | None = None) -> None: ...
    def retrieve(key: str) -> Any | None: ...
    def query(embedding: list[float], top_k: int) -> list[KnowledgeItem]: ...
    def graph_store(triple: tuple[str, str, str]) -> None: ...  # (subject, predicate, object)
```

---

### Phase 8.4 — Background Worker System

**Goal:** Long-running background workers that process queue tasks, survive restarts, and report health

**Subtasks:**
- [ ] 08-04-01: Worker process architecture (Worker, WorkerConfig)
- [ ] 08-04-02: Worker registration with discovery (Consul, etcd, or Redis-based)
- [ ] 08-04-03: Worker pools (multiple workers per queue)
- [ ] 08-04-04: Work stealing (idle workers grab tasks from busy workers)
- [ ] 08-04-05: Graceful shutdown (drain tasks before exit)
- [ ] 08-04-06: Worker health checks (heartbeat, CPU/memory monitoring)
- [ ] 08-04-07: Crash recovery (restart worker, re-queue in-flight tasks)
- [ ] 08-04-08: Worker scaling (auto-scale based on queue depth)

**Files:**
- `luminamind/worker/worker.py` — Worker, WorkerConfig, WorkerStatus
- `luminamind/worker/registry.py` — WorkerRegistry, DiscoveryBackend
- `luminamind/worker/pool.py` — WorkerPool, WorkStealingStrategy
- `luminamind/worker/lifecycle.py` — LifecycleManager, GracefulShutdown
- `luminamind/worker/scaling.py` — AutoScaler, ScalingPolicy
- `tests/unit/test_worker.py` — Unit tests

---

### Phase 8.5 — Monitoring & Alerting Dashboard

**Goal:** Real-time dashboard for swarm health, task metrics, and proactive alerting on failures

**Subtasks:**
- [ ] 08-05-01: Dashboard web UI (FastAPI + React or static HTML)
- [ ] 08-05-02: Task metrics (queued, running, completed, failed, rate per minute)
- [ ] 08-05-03: Swarm metrics (active agents, idle agents, tasks per agent)
- [ ] 08-05-04: Queue depth over time (chart, alerts on backlog threshold)
- [ ] 08-05-05: Alert rules engine (conditions, severity, notification targets)
- [ ] 08-05-06: Notification channels (email, Slack, PagerDuty, webhooks)
- [ ] 08-05-07: Alert history and acknowledgment
- [ ] 08-05-08: Prometheus exporter for external scraping
- [ ] 08-05-09: Grafana dashboard templates
- [ ] 08-05-10: SLA tracking (task completion time percentiles)

**Files:**
- `luminamind/monitoring/dashboard.py` — FastAPI app, routes
- `luminamind/monitoring/metrics.py` — TaskMetrics, SwarmMetrics
- `luminamind/monitoring/alerts.py` — AlertRule, AlertEngine, NotificationChannel
- `luminamind/monitoring/prometheus.py` — PrometheusExporter
- `luminamind/monitoring/grafana.py` — GrafanaDashboard
- `luminamind/monitoring/templates/` — Dashboard HTML templates
- `tests/unit/test_monitoring.py` — Unit tests

**Alert Rules Examples:**
```python
ALERT_TASK_BACKLOG = AlertRule(
    name="task_backlog",
    condition="queue_depth > 100 and queue_depth_increasing_for(minutes=5)",
    severity=AlertSeverity.WARNING,
    channels=["slack"],
)

ALERT_SWARM_STALLED = AlertRule(
    name="swarm_stalled",
    condition="no_tasks_completed_for(minutes=30) and active_agents > 0",
    severity=AlertSeverity.CRITICAL,
    channels=["slack", "pagerduty"],
)

ALERT_TASK_FAILED = AlertRule(
    name="task_failed",
    condition="task_status == FAILED",
    severity=AlertSeverity.ERROR,
    channels=["email"],
)
```

---

### Phase 8.6 — API & CLI for Swarm Control

**Goal:** External-facing API and CLI to interact with swarm, schedule tasks, and monitor execution

**Subtasks:**
- [ ] 08-06-01: REST API for queue operations (enqueue, dequeue, status, cancel)
- [ ] 08-06-02: REST API for scheduler (schedule, unschedule, pause, resume)
- [ ] 08-06-03: REST API for swarm (spawn, kill, status, broadcast)
- [ ] 08-06-04: WebSocket support for real-time dashboard updates
- [ ] 08-06-05: CLI commands for all API operations
- [ ] 08-06-06: Authentication (API key, JWT for admin operations)
- [ ] 08-06-07: Rate limiting on API endpoints
- [ ] 08-06-08: OpenAPI spec generation
- [ ] 08-06-09: API versioning (v1, v2)
- [ ] 08-06-10: Usage metering and quotas

**Files:**
- `luminamind/api/app.py` — FastAPI application
- `luminamind/api/routes/queue.py` — Queue endpoints
- `luminamind/api/routes/scheduler.py` — Scheduler endpoints
- `luminamind/api/routes/swarm.py` — Swarm endpoints
- `luminamind/api/routes/tasks.py` — Task management endpoints
- `luminamind/api/auth.py` — APIKeyAuth, JWTAuth
- `luminamind/api/middleware.py` — RateLimitMiddleware
- `luminamind/cli/swarm.py` — CLI group for swarm commands
- `tests/integration/test_api.py` — Integration tests

**API Endpoints:**
```
# Queue
POST   /api/v1/queue/enqueue
GET    /api/v1/queue/status/{task_id}
DELETE /api/v1/queue/cancel/{task_id}
GET    /api/v1/queue/metrics

# Scheduler
POST   /api/v1/scheduler/schedule
GET    /api/v1/scheduler/list
DELETE /api/v1/scheduler/unschedule/{task_id}
PUT     /api/v1/scheduler/pause/{task_id}
PUT     /api/v1/scheduler/resume/{task_id}

# Swarm
POST   /api/v1/swarm/spawn
DELETE /api/v1/swarm/kill/{agent_id}
GET    /api/v1/swarm/status
POST   /api/v1/swarm/broadcast
GET    /api/v1/swarm/agents

# Tasks
GET    /api/v1/tasks
GET    /api/v1/tasks/{task_id}
```

---

### Phase 8.7 — Enterprise Features

**Goal:** Multi-tenancy, RBAC, audit logging, and compliance features for enterprise deployment

**Subtasks:**
- [ ] 08-07-01: Multi-tenant isolation (namespace per tenant)
- [ ] 08-07-02: Role-based access control (RBAC: admin, operator, viewer)
- [ ] 08-07-03: Audit logging (all admin actions logged)
- [ ] 08-07-04: SAML/OAuth SSO integration
- [ ] 08-07-05: Data residency (tenant-specific storage location)
- [ ] 08-07-06: Compliance exports (SOC2, HIPAA, GDPR report generation)
- [ ] 08-07-07: SLA configuration per tenant
- [ ] 08-07-08: Billing metering (task counts, agent hours)

**Files:**
- `luminamind/enterprise/tenancy.py` — Tenant, Namespace
- `luminamind/enterprise/rbac.py` — Role, Permission, RBACEngine
- `luminamind/enterprise/audit.py` — AuditLog, AuditEntry
- `luminamind/enterprise/sso.py` — SSOProvider, SAMLConfig
- `luminamind/enterprise/compliance.py` — ComplianceReport
- `luminamind/enterprise/billing.py` — UsageMeter, BillingReport

---

## Phase 8 Summary

| Plan | Focus | Plans | Dependencies |
|------|-------|-------|--------------|
| 08-01 | Task Queue & Persistence | 8 subtasks | Phase 4 complete |
| 08-02 | Scheduler & Cron | 8 subtasks | 08-01 |
| 08-03 | Agent Swarm Orchestration | 10 subtasks | 08-01, 08-02 |
| 08-04 | Background Workers | 8 subtasks | 08-01, 08-02 |
| 08-05 | Monitoring & Alerting | 10 subtasks | 08-03, 08-04 |
| 08-06 | API & CLI | 10 subtasks | 08-01, 08-02, 08-03 |
| 08-07 | Enterprise Features | 8 subtasks | 08-06 |

**Total Phase 8:** 7 plans, 62 subtasks

---

## Phase 9 — Self-Evolving & Futuristic Capabilities

**Goal:** Transform LuminaMind into a true modern futuristic harness with self-improvement, real-time visualization, isolated sandboxing, and autonomous adaptation

**Requirements:** [All new — emerging research from self-evolving agents, agent harnesses, OpenHands]

**Success Criteria:**
1. Harness learns from each run → permanent skill improvement (SKILL.md files)
2. Real-time token streaming and agent reasoning visualization
3. Docker sandbox isolation for untrusted code execution
4. Agent event stream API for custom dashboards and visualizers
5. Hierarchical memory OS for cross-task knowledge transfer
6. Recursive meta-reasoning: self-review and optimization suggestions
7. Model cost arbitrage: auto-select cheapest LLM meeting quality threshold
8. Plugin system: third-party evaluators, custom tools, community templates

---

### Phase 9.1 — Self-Improving Memory System

**Goal:** Closed-loop learning where successful executions are distilled into permanent skill modules, and failures become lessons injected into global reasoning

**Subtasks:**
- [ ] 09-01-01: Skill acquisition framework (atomic skill modules vs. whole-model changes)
- [ ] 09-01-02: SKILL.md file format and persistence (structured lessons from successes)
- [ ] 09-01-03: Structured failure lessons (AutoResearchClaw-style permanent injection)
- [ ] 09-01-04: Closed-loop feedback integration (Judge → reward → skill update)
- [ ] 09-01-05: Lessons Learned library (searchable, versioned skill catalog)
- [ ] 09-01-06: Workflow template extraction (pattern-based reuse from successful runs)
- [ ] 09-01-07: Skill versioning and rollback (mutable skill history)
- [ ] 09-01-08: Cross-task skill suggestion (context-aware skill recommendations)

**Files:**
- `luminamind/learning/skill_acquirer.py` — SkillAcquisition, AtomicSkill
- `luminamind/learning/skill_library.py` — SkillLibrary, SKILL.md format
- `luminamind/learning/lessons.py` — LessonsLearned, FailureLesson
- `luminamind/learning/workflow_template.py` — WorkflowTemplate, PatternExtractor
- `luminamind/learning/feedback_loop.py` — ClosedLoopFeedback, RewardSignal
- `tests/unit/test_learning.py` — Unit tests

**Key Classes:**
```python
class AtomicSkill:
    id: str
    name: str
    description: str
    trigger_conditions: list[str]  # task patterns that invoke this skill
    actions: list[str]             # code/commands to execute
    success_rate: float
    avg_tokens_saved: float
    version: int
    created_at: datetime
    last_used: datetime

class SkillLibrary:
    def register(skill: AtomicSkill) -> str: ...
    def suggest(context: TaskContext) -> list[AtomicSkill]: ...
    def improve(skill_id: str, feedback: FeedbackSignal) -> None: ...
    def search(query: str) -> list[AtomicSkill]: ...

class LessonsLearned:
    def distill(task_result: TaskResult) -> StructuredLesson: ...
    def inject(failure: Failure) -> void: ...  # Permanent improvement
    def retrieve(task_type: str) -> list[StructuredLesson]: ...
```

---

### Phase 9.2 — Agent Event Stream API

**Goal:** Lightweight event-stream API enabling real-time dashboards, custom visualizers, and external integrations

**Subtasks:**
- [ ] 09-02-01: Event schema definition (AgentEvent, ToolEvent, TokenEvent, ErrorEvent)
- [ ] 09-02-02: SSE (Server-Sent Events) streaming endpoint
- [ ] 09-02-03: WebSocket support for bidirectional communication
- [ ] 09-02-04: Event buffering and replay capability
- [ ] 09-02-05: Event filtering and subscription (subscribe to specific agent/task)
- [ ] 09-02-06: Authentication and authorization for event stream
- [ ] 09-02-07: Event schema registry and versioning
- [ ] 09-02-08: Benchmark mode: record event sequences for replay testing

**Files:**
- `luminamind/events/stream.py` — EventStream, SSEHandler, WebSocketHandler
- `luminamind/events/schema.py` — EventSchema, AgentEvent, ToolEvent
- `luminamind/events/buffer.py` — EventBuffer, EventReplay
- `luminamind/events/subscription.py` — EventSubscription, EventFilter
- `luminamind/api/routes/events.py` — /events endpoint
- `tests/unit/test_events.py` — Unit tests

**Event Schema:**
```python
class AgentEventType(Enum):
    AGENT_SPAWN = "agent_spawn"
    AGENT_COMPLETE = "agent_complete"
    AGENT_ERROR = "agent_error"
    TOOL_START = "tool_start"
    TOOL_END = "tool_end"
    TOKEN_STREAM = "token_stream"
    STATE_UPDATE = "state_update"
    INTERRUPT = "interrupt"
    RESUME = "resume"

@dataclass
class AgentEvent:
    event_id: str
    event_type: AgentEventType
    agent_id: str
    timestamp: datetime
    data: dict  # event-specific payload
    session_id: str

class EventStream:
    def publish(event: AgentEvent) -> None: ...
    def subscribe(filter: EventFilter) -> AsyncIterator[AgentEvent]: ...
    def replay(session_id: str, from_event_id: str | None) -> list[AgentEvent]: ...
```

---

### Phase 9.3 — Docker Sandbox Runtime

**Goal:** Isolated containerized execution environment for untrusted code, mimicking OpenHands sandbox architecture

**Subtasks:**
- [ ] 09-03-01: Sandbox architecture (Sandbox, SandboxConfig, SandboxBackend)
- [ ] 09-03-02: Docker container provisioning (per-task container lifecycle)
- [ ] 09-03-03: Container image management (base images, custom tool images)
- [ ] 09-03-04: Network isolation and egress control
- [ ] 09-03-05: Filesystem sandboxing (overlayfs, tmpfs for /tmp)
- [ ] 09-03-06: Resource limits (CPU, memory, disk, time)
- [ ] 09-03-07: Container registry integration (push/pull custom images)
- [ ] 09-03-08: Sandbox cleanup and resource reclamation
- [ ] 09-03-09: Pre-execution validation (static analysis before sandbox run)
- [ ] 09-03-10: Multi-language runtime support (Python, Node, Java, Go)

**Files:**
- `luminamind/sandbox/sandbox.py` — Sandbox, SandboxConfig
- `luminamind/sandbox/docker_backend.py` — DockerBackend, ContainerManager
- `luminamind/sandbox/image.py` — ContainerImage, ImageRegistry
- `luminamind/sandbox/network.py` — NetworkIsolation, EgressControl
- `luminamind/sandbox/filesystem.py` — FilesystemSandbox, OverlayFS
- `luminamind/sandbox/limits.py` — ResourceLimits, ContainerResources
- `luminamind/sandbox/validator.py` — PreExecutionValidator
- `luminamind/sandbox/runtime.py` — RuntimeRegistry
- `tests/unit/test_sandbox.py` — Unit tests

---

### Phase 9.4 — Real-Time Token Streaming & Visualization

**Goal:** Live token-by-token streaming to dashboard, showing agent reasoning and tool execution in real-time

**Subtasks:**
- [ ] 09-04-01: Token streaming architecture (streaming LLM response to client)
- [ ] 09-04-02: Reasoning trace visualization (think → act → observe chain)
- [ ] 09-04-03: Tool call timeline (each tool with latency, input, output preview)
- [ ] 09-04-04: Branching visualization (subagent spawn, parallel execution branches)
- [ ] 09-04-05: Token consumption tracker (per-task, per-session, per-agent)
- [ ] 09-04-06: Live progress indicators (spinner, step counter, ETA)
- [ ] 09-04-07: Streaming interruption support (pause/resume mid-generation)
- [ ] 09-04-08: Streaming transcript export (save streamed session for replay)
- [ ] 09-04-09: Interactive visualization (click tool call to expand details)
- [ ] 09-04-10: Mobile-friendly dashboard (responsive streaming view)

**Files:**
- `luminamind/streaming/token_stream.py` — TokenStream, StreamingConfig
- `luminamind/streaming/reasoning_trace.py` — ReasoningTrace, ThinkActObserve
- `luminamind/streaming/tool_timeline.py` — ToolTimeline, ToolCallNode
- `luminamind/streaming/branching.py` — BranchingVisualizer, ExecutionTree
- `luminamind/streaming/consumption.py` — TokenConsumptionTracker
- `luminamind/streaming/interactive.py` — InteractiveVisualization
- `luminamind/monitoring/dashboard_templates/streaming.html` — Dashboard HTML
- `tests/unit/test_streaming.py` — Unit tests

---

### Phase 9.5 — Hierarchical Memory OS

**Goal:** Filesystem-based hierarchical context (not flat vector store) for cross-task knowledge transfer and long-term memory

**Subtasks:**
- [ ] 09-05-01: Memory OS architecture (MemoryOS, filesystem-based namespace)
- [ ] 09-05-02: Context hierarchy (global → project → task → session)
- [ ] 09-05-03: Memory indexing and search (full-text + semantic)
- [ ] 09-05-04: Cross-task knowledge distillation (extract reusable patterns)
- [ ] 09-05-05: Memory TTL and eviction policies (LRU, time-based, importance-based)
- [ ] 09-05-06: Memory compression and summarization (long-term → dense format)
- [ ] 09-05-07: Memory sharing across agents (shared knowledge base in swarm)
- [ ] 09-05-08: Memory versioning and diff (track how knowledge evolves)
- [ ] 09-05-09: Import/export memory snapshots (backup, migration)
- [ ] 09-05-10: Memory analytics (what's learned, what's stale, what's conflicting)

**Files:**
- `luminamind/memoryos/memory_os.py` — MemoryOS, ContextHierarchy
- `luminamind/memoryos/namespace.py` — MemoryNamespace
- `luminamind/memoryos/index.py` — MemoryIndex, SemanticSearch
- `luminamind/memoryos/distillation.py` — KnowledgeDistiller
- `luminamind/memoryos/eviction.py` — MemoryEvictionPolicy
- `luminamind/memoryos/compression.py` — MemoryCompressor
- `luminamind/memoryos/versioning.py` — MemoryVersion, MemoryDiff
- `luminamind/memoryos/shared.py` — SharedMemory
- `tests/unit/test_memoryos.py` — Unit tests

---

### Phase 9.6 — Recursive Meta-Reasoning

**Goal:** Agent self-review after task completion asking "how could this be solved with 50% fewer steps?" and proposing optimizations

**Subtasks:**
- [ ] 09-06-01: Meta-reasoning trigger (post-task review phase)
- [ ] 09-06-02: Step count analysis (compare actual vs. optimal path)
- [ ] 09-06-03: Token efficiency scoring (tokens used vs. theoretical minimum)
- [ ] 09-06-04: Redundant action detection (repeated attempts, unnecessary tools)
- [ ] 09-06-05: Strategy suggestion engine (propose alternative approaches)
- [ ] 09-06-06: Self-patch integration (agent modifies own strategy)
- [ ] 09-06-07: Meta-learner persistence (store meta-reasoning across sessions)
- [ ] 09-06-08: Convergence metrics (track meta-reasoning improvements over time)

**Files:**
- `luminamind/meta/meta_reasoner.py` — MetaReasoner, SelfReview
- `luminamind/meta/step_analyzer.py` — StepAnalyzer, PathComparison
- `luminamind/meta/efficiency.py` — TokenEfficiency, RedundancyDetector
- `luminamind/meta/strategy.py` — StrategySuggestion, AlternativePath
- `luminamind/meta/patcher.py` — SelfPatcher, StrategyModification
- `luminamind/meta/metrics.py` — MetaMetrics, ConvergenceTracker
- `tests/unit/test_meta.py` — Unit tests

---

### Phase 9.7 — Model Cost Arbitrage

**Goal:** Auto-select cheapest LLM that meets quality threshold per task complexity, switching mid-task when needed

**Subtasks:**
- [ ] 09-07-01: Model cost/rquality registry (price per 1K tokens, capability scores)
- [ ] 09-07-02: Task complexity classifier (simple/medium/complex automatic routing)
- [ ] 09-07-03: Dynamic model selection middleware (transparent to agent)
- [ ] 09-07-04: Mid-task model switching (when complexity underestimated)
- [ ] 09-07-05: Cost budget enforcement (max cost per task, per sprint)
- [ ] 09-07-06: Cost analytics and reporting (cost breakdown by task/agent/phase)
- [ ] 09-07-07: Model capability benchmarking (track actual vs. stated capability)
- [ ] 09-07-08: Multi-provider support (OpenAI, Anthropic, Ollama, Groq, etc.)
- [ ] 09-07-09: Fallback chain with cost ranking (cheapest first, escalate on failure)
- [ ] 09-07-10: Cost prediction before execution (estimate before committing)

**Files:**
- `luminamind/orbit/cost_registry.py` — ModelCostRegistry, ProviderConfig
- `luminamind/orbit/classifier.py` — TaskComplexityClassifier
- `luminamind/orbit/selector.py` — DynamicModelSelector
- `luminamind/orbit/switcher.py` — MidTaskSwitcher
- `luminamind/orbit/budget.py` — CostBudget, BudgetEnforcement
- `luminamind/orbit/analytics.py` — CostAnalytics, CostReport
- `luminamind/orbit/benchmark.py` — ModelBenchmark
- `luminamind/orbit/fallback.py` — FallbackChain
- `luminamind/orbit/predictor.py` — CostPredictor
- `tests/unit/test_orbit.py` — Unit tests

---

### Phase 9.8 — Plugin & Extension System

**Goal:** Third-party extensibility for evaluators, tools, prompts, and notification channels with sandboxed execution

**Subtasks:**
- [ ] 09-08-01: Plugin architecture (Plugin, PluginManifest, PluginRegistry)
- [ ] 09-08-02: Plugin manifest format (plugin.yaml with dependencies, permissions)
- [ ] 09-08-03: Plugin installation and lifecycle (install, enable, disable, uninstall)
- [ ] 09-08-04: Sandboxed plugin execution (plugins run in isolated context)
- [ ] 09-08-05: Custom evaluator interface (third-party quality criteria)
- [ ] 09-08-06: Custom tool interface (vendor-specific API integrations)
- [ ] 09-08-07: Custom prompt template interface (community prompt packs)
- [ ] 09-08-08: Plugin marketplace metadata (registry, search, star/rating)
- [ ] 09-08-09: Plugin signature verification (cryptographic integrity check)
- [ ] 09-08-10: Plugin dependency resolution (plugin A requires plugin B version)

**Files:**
- `luminamind/plugins/plugin.py` — Plugin, PluginManifest
- `luminamind/plugins/registry.py` — PluginRegistry, PluginStore
- `luminamind/plugins/lifecycle.py` — PluginLifecycle
- `luminamind/plugins/sandbox.py` — PluginSandbox
- `luminamind/plugins/evaluator_iface.py` — EvaluatorPluginInterface
- `luminamind/plugins/tool_iface.py` — ToolPluginInterface
- `luminamind/plugins/prompt_iface.py` — PromptPluginInterface
- `luminamind/plugins/marketplace.py` — PluginMarketplace
- `luminamind/plugins/signature.py` — PluginSignature
- `luminamind/plugins/resolver.py` — DependencyResolver
- `tests/unit/test_plugins.py` — Unit tests

---

## Phase 9 Summary

| Plan | Focus | Subtasks | Dependencies |
|------|-------|---------|--------------|
| 09-01 | Self-Improving Memory | 8 | Phase 2 (evaluator), Phase 3 (planner) |
| 09-02 | Agent Event Stream API | 8 | Phase 8-06 (API) |
| 09-03 | Docker Sandbox Runtime | 10 | Phase 2-04 (evaluator sandbox) |
| 09-04 | Real-Time Token Streaming | 10 | Phase 9-02 (event stream) |
| 09-05 | Hierarchical Memory OS | 10 | Phase 1 (memory), Phase 9-01 |
| 09-06 | Recursive Meta-Reasoning | 8 | Phase 2 (evaluator), Phase 9-01 |
| 09-07 | Model Cost Arbitrage | 10 | Phase 8 (API) |
| 09-08 | Plugin & Extension System | 10 | Phase 7 (integration), Phase 9-03 |

**Total Phase 9:** 8 plans, 64 subtasks

---

## Phase 9 — Futuristic Vision

```
After Phase 9, LuminaMind becomes:

┌─────────────────────────────────────────────────────────────┐
│                    LUMINAMIND HARNESS                       │
│                                                              │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐ │
│  │ Self-    │   │ Real-Time│   │ Docker   │   │ Plugin   │ │
│  │ Improving│   │ Token    │   │ Sandbox  │   │ Ecosystem│ │
│  │ Memory   │   │ Streaming│   │ Runtime  │   │          │ │
│  └────┬─────┘   └────┬─────┘   └────┬─────┘   └────┬─────┘ │
│       │               │               │               │        │
│  ┌────┴───────────────┴───────────────┴───────────────┴────┐ │
│  │              Hierarchical Memory OS                     │ │
│  │         (Filesystem-based cross-task knowledge)       │ │
│  └────────────────────────┬────────────────────────────────┘ │
│                           │                                   │
│  ┌────────────────────────┴────────────────────────────────┐ │
│  │            Recursive Meta-Reasoning                       │ │
│  │    "How could this be solved with 50% fewer steps?"      │ │
│  └────────────────────────┬────────────────────────────────┘ │
│                           │                                   │
│  ┌────────────────────────┴────────────────────────────────┐ │
│  │              Model Cost Arbitrage                         │ │
│  │      Cheapest LLM meeting quality threshold               │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

**Total Phases 1-9:** 9 phases, 69+ plans, 400+ subtasks

**What makes it "futuristic":**
- **Self-improving**: Learns from every run → permanent skill growth
- **Transparent**: Real-time token streaming, agent reasoning visible
- **Isolated**: Docker sandbox for any code, any language
- **Extensible**: Plugin ecosystem for community contributions
- **Efficient**: Model arbitrage cuts costs 10x
- **Self-aware**: Meta-reasoning optimizes own strategies

---

## Backlog

(Deferred items will appear here)
PHASE 1 (Context & Memory)
├── 1.1 Structured Session Memory ──┐
├── 1.2 Prompt Prefix Caching ───────┤
└── 1.3 Working Memory ──────────────┘
         │
         ▼
PHASE 2 (Generator-Evaluator) ←── (requires Phase 1)
├── 2.1 Evaluator Agent ──────────────┐
├── 2.2 Generator-Evaluator Loop ─────┤
└── 2.3 Grading Criteria Engine ──────┘
         │
         ▼
PHASE 3 (Planner & Sprint) ←── (requires Phase 2)
├── 3.1 Planner Agent ────────────────┐
├── 3.2 Sprint Contract System ───────┤
└── 3.3 Multi-Agent Coordination ─────┘
         │
         ▼
PHASE 4 (Live Verification) ←── (requires Phase 2)
├── 4.1 Playwright MCP Integration ───┐
└── 4.2 Database State Verification ─┘
         │
         ▼
PHASE 5 (Tool & Prompt Optimization) ←── (independent, can run parallel)
├── 5.1 Tool Rationalization ──────────┐
├── 5.2 Prompt Library System ─────────┤
└── 5.3 Lifecycle Hooks ──────────────┘
         │
         ▼
PHASE 6 (Production Hardening) ←── (requires Phases 1-5)
├── 6.1 Observability Enhancement ────┐
├── 6.2 Safety & Guardrails ──────────┤
└── 6.3 Performance Optimization ─────┘
         │
         ▼
PHASE 7 (Integration & Testing) ←── (final)
├── 7.1 End-to-End Integration ───────┐
└── 7.2 Regression Test Suite ────────┘
         │
         ▼
PHASE 8 (Agent Swarm & Scheduled Automation) ←── (ultimate autonomous platform)
├── 8.1 Task Queue & Persistence ─────┐
├── 8.2 Scheduler & Cron ───────────────┤
├── 8.3 Agent Swarm Orchestration ─────┤
├── 8.4 Background Workers ────────────┤
├── 8.5 Monitoring & Alerting ─────────┤
├── 8.6 API & CLI ─────────────────────┤
└── 8.7 Enterprise Features ──────────┘
         │
         ▼
PHASE 9 (Self-Evolving & Futuristic) ←── (true modern harness)
├── 9.1 Self-Improving Memory ─────────┐
├── 9.2 Agent Event Stream API ──────────┤
├── 9.3 Docker Sandbox Runtime ──────────┤
├── 9.4 Real-Time Token Streaming ───────┤
├── 9.5 Hierarchical Memory OS ──────────┤
├── 9.6 Recursive Meta-Reasoning ────────┤
├── 9.7 Model Cost Arbitrage ─────────────┤
└── 9.8 Plugin & Extension System ───────┘
```
