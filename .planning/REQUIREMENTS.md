# Requirements

**Project:** LuminaMind Harness Engineering
**Version:** v0.0.1.1.3 → v1.0 (target)
**Date:** 2026-04-27

---

## Validated

(None yet — ship to validate)

---

## Active

### Memory & Context

- [ ] **MEM-01**: Two-layer memory architecture (FullTranscript + WorkingMemory) reduces token waste by 40%
- [ ] **MEM-02**: Session resumption persists and restores full conversation state across restarts
- [ ] **MEM-03**: Prompt prefix caching activates on stable workspace content
- [ ] **MEM-04**: Context compaction maintains quality under max-token budget with recent-biased compression

### Generator-Evaluator Pattern

- [ ] **GE-01**: Evaluator agent catches 90% of bugs that generator misses (benchmark-verified)
- [ ] **GE-02**: Iteration controller enforces max-iteration limits with configurable thresholds
- [ ] **GE-03**: Multi-round refinement pipeline converges on quality达标 with early termination
- [ ] **GE-04**: Grading criteria framework covers design, originality, craft, functionality domains
- [ ] **GE-05**: Frontend design evaluator produces specific actionable critique with visual quality scoring
- [ ] **GE-06**: Code quality evaluator scores correctness, maintainability, performance, security
- [ ] **GE-07**: Evaluator sandbox provides isolated environment with Playwright MCP integration
- [ ] **GE-08**: API endpoint testing and database state verification are integrated

### Planner & Sprint System

- [ ] **PLAN-01**: Planner agent produces spec in <5 min that evaluator approves
- [ ] **PLAN-02**: Spec generation creates structured output with feature decomposition into user stories
- [ ] **PLAN-03**: Sprint contract framework enables negotiation, persistence, and version control
- [ ] **PLAN-04**: Contract verification performs criterion-by-criterion checking with pass/fail determination
- [ ] **PLAN-05**: Sprint lifecycle manager orchestrates planning → execution → verification → handoff

### Multi-Agent Coordination

- [ ] **MULTI-01**: Bounded subagent system enforces context inheritance with boundaries and recursion limits
- [ ] **MULTI-02**: AgentMessageBus handles inter-agent communication with queuing and conflict resolution

### Live Verification

- [ ] **LIVE-01**: Playwright MCP bridge automates browser testing with screenshot capture and user flow simulation
- [ ] **LIVE-02**: Visual regression detection identifies layout changes via screenshot comparison
- [ ] **LIVE-03**: Live verification finds UI bugs without human testing (demo-verified)

### Tool & Prompt Optimization

- [ ] **TOOL-01**: Tool tiering (core/extended/specialist) reduces unnecessary tool exposure by 50%
- [ ] **TOOL-02**: Context-dependent tool loading auto-selects tools based on task type
- [ ] **TOOL-03**: Prompt library maps task types to presets with versioning and A/B testing
- [ ] **TOOL-04**: Dynamic prompt composition assembles context-aware prompts with personality variations
- [ ] **TOOL-05**: Lifecycle hooks fire on: on_init, on_start, on_step, on_complete, on_error, on_exit
- [ ] **TOOL-06**: Recovery framework implements exponential backoff, circuit breaker, and fallback chain

### Production Hardening

- [ ] **PROD-01**: Harness-specific metrics track iteration count, evaluator scores, tool usage efficiency
- [ ] **PROD-02**: Harness debugging tools enable trace viewing and step-by-step replay
- [ ] **PROD-03**: Safety systems sandbox generated code and validate output before evaluation
- [ ] **PROD-04**: Circuit breakers prevent infinite loops and dead letter queues capture failed tasks
- [ ] **PROD-05**: Token optimization achieves smart context window allocation with KV cache
- [ ] **PROD-06**: Parallelization enables concurrent subagent execution with result merging

### End-to-End Integration

- [ ] **E2E-01**: All Phase 1-6 components wire into unified harness with graceful degradation
- [ ] **E2E-02**: Demo applications (frontend design, full-stack app, code review) demonstrate quality
- [ ] **E2E-03**: Benchmark suite (100+ cases) enables automated scoring and regression detection
- [ ] **E2E-04**: Chaos testing validates resilience to network failure, LLM timeout, partial system failure
- [ ] **E2E-05**: End-to-end harness matches Claude Code quality (human evaluation survey)

### Security (Critical — must resolve before production)

- [ ] **SEC-01**: Resolve shell injection vulnerability (CVSS 9.8) — path allowlisting, command whitelist, dangerous pattern detection
- [ ] **SEC-02**: Remove hardcoded API keys (CVSS 8.5) — migrate to secrets manager (Vault/K8s secrets)
- [ ] **SEC-03**: Add TLS verification for HTTP client
- [ ] **SEC-04**: Implement rate limiting for all tool categories

---

## Out of Scope

- Switching away from LangChain/LangGraph stack — locked decision
- Using different LLM providers — current GLM-4.5-flash/Ollama stack is adequate
- Building mobile UI — desktop CLI is the target
- Non-Python support — Python 3.12 is the only target

---

## Traceability

| Requirement | Phase | Plan |
|-------------|-------|------|
| MEM-01 through MEM-04 | Phase 1 | 01-01 through 01-04 |
| GE-01 through GE-08 | Phase 2 | 02-01 through 02-08 |
| PLAN-01 through PLAN-05, MULTI-01, MULTI-02 | Phase 3 | 03-01 through 03-08 |
| LIVE-01 through LIVE-03 | Phase 4 | 04-01 through 04-05 |
| TOOL-01 through TOOL-06 | Phase 5 | 05-01 through 05-05 |
| PROD-01 through PROD-06 | Phase 6 | 06-01 through 06-06 |
| E2E-01 through E2E-05 | Phase 7 | 07-01 through 07-04 |
| SEC-01 through SEC-04 | Phase 6 (embedded) | 06-03 (safety) |
