# Roadmap

**Project:** LuminaMind Harness Engineering
**Phases:** 7 | **Status:** Pre-execution

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
- [ ] 02-01: Evaluator agent system (EvaluatorAgent, grading criteria framework)
- [ ] 02-02: Frontend design evaluator (visual quality scoring, actionable critique)
- [ ] 02-03: Code quality evaluator (correctness, maintainability, performance, security)
- [ ] 02-04: Evaluator sandbox (Playwright MCP, API testing, DB state verification)
- [ ] 02-05: Iteration controller (max-iteration limits, convergence detection)
- [ ] 02-06: Feedback bridge (generator-evaluator communication)
- [ ] 02-07: Multi-round refinement pipeline (quality gate enforcement)
- [ ] 02-08: Grading criteria engine (domain-specific criteria sets)

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
- [ ] 03-01: Planner agent (spec expansion, feature decomposition, AI suggestion integration)
- [ ] 03-02: Spec generation (structured output, user stories, acceptance criteria)
- [ ] 03-03: Planner-evaluator integration (spec review loop)
- [ ] 03-04: Sprint contract framework (negotiation protocol, persistence)
- [ ] 03-05: Contract verification (criterion-by-criterion checking)
- [ ] 03-06: Sprint lifecycle manager (planning → execution → verification → handoff)
- [ ] 03-07: Bounded subagent system (context inheritance, recursion depth limiting)
- [ ] 03-08: Subagent communication layer (AgentMessageBus, output merging)

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
- [ ] 04-01: Playwright MCP bridge (browser automation, screenshot capture, user flow simulation)
- [ ] 04-02: Visual regression detection (screenshot comparison, layout change detection)
- [ ] 04-03: API testing integration (endpoint discovery, request/response logging)
- [ ] 04-04: Database state verifier (schema introspection, state query, expected assertions)
- [ ] 04-05: Evaluator integration (connect DB verifier to evaluator agent)

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
```
