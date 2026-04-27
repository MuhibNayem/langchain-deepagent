# LuminaMind Harness Engineering Master Plan

**Objective**: Transform LuminaMind from basic autonomous agent to industry-leading coding harness  
**Baseline**: Current v0.0.1.1.3 with 12 critical/high/medium gaps identified  
**Target**: Claude Code-level harness engineering with GAN-inspired evaluator architecture

---

## PHASE 1: Context & Memory Infrastructure (Weeks 1-2)

### 1.1 Structured Session Memory System

**Task 1.1.1**: Implement two-layer memory architecture
- [ ] Create `SessionMemory` class with full transcript + working memory separation
- [ ] Implement `FullTranscript` store (JSONL persistence)
- [ ] Implement `WorkingMemory` store (distilled task state, current files, notes)
- [ ] Add automatic working memory compaction on each turn
- [ ] Write tests: test_memory_two_layer.py, test_compaction.py

**Task 1.1.2**: Add session resumption capability
- [ ] Implement `SessionStore` with save/load/resume functions
- [ ] Add session listing and cleanup utilities
- [ ] Integrate with checkpointer for unified state management
- [ ] Write tests: test_session_resume.py

### 1.2 Prompt Prefix Caching

**Task 1.2.1**: Build stable prompt prefix system
- [ ] Create `PromptPrefixBuilder` class
- [ ] Implement workspace summary generation (repo root, git status, project structure)
- [ ] Add tool description registry with versioning
- [ ] Implement prefix cache invalidation on workspace changes
- [ ] Write tests: test_prompt_prefix.py, test_cache_invalidation.py

**Task 1.2.2**: Implement context compaction
- [ ] Create `ContextCompactor` with clipping strategies
- [ ] Implement recent-biased compression (keep recent turns rich, compress older)
- [ ] Add file read deduplication (don't re-send same file content)
- [ ] Implement max-token budget enforcement
- [ ] Write tests: test_compaction.py, test_deduplication.py

### 1.3 Working Memory Maintenance

**Task 1.3.1**: Build distilled state management
- [ ] Create `WorkingMemoryManager` class
- [ ] Track: current task, important files, recent notes, pending actions
- [ ] Implement memory update on each agent turn
- [ ] Add memory merge for multi-agent scenarios
- [ ] Write tests: test_working_memory.py

---

## PHASE 2: Generator-Evaluator Architecture (Weeks 3-5)

### 2.1 Evaluator Agent System

**Task 2.1.1**: Create base evaluator agent class
- [ ] Create `EvaluatorAgent` with grading-focused prompt template
- [ ] Implement grading criteria framework (design, originality, craft, functionality)
- [ ] Add few-shot calibration examples system
- [ ] Create evaluator prompt library per domain
- [ ] Write tests: test_evaluator_agent.py

**Task 2.1.2**: Implement frontend design evaluator
- [ ] Create grading criteria: design quality, originality, craft, functionality
- [ ] Add visual quality scoring with tolerance calibration
- [ ] Implement evaluator feedback generation with specific actionable critique
- [ ] Add iteration guidance (refine direction vs pivot)
- [ ] Write tests: test_design_evaluator.py

**Task 2.1.3**: Implement code quality evaluator
- [ ] Create coding grading criteria: correctness, maintainability, performance, security
- [ ] Add test coverage analysis integration
- [ ] Implement bug severity classification
- [ ] Add code review feedback generation
- [ ] Write tests: test_code_evaluator.py

**Task 2.1.4**: Build evaluator sandbox
- [ ] Create isolated evaluation environment
- [ ] Implement Playwright MCP integration for live app testing
- [ ] Add API endpoint testing capability
- [ ] Implement database state verification
- [ ] Write tests: test_evaluator_sandbox.py

### 2.2 Generator-Evaluator Loop

**Task 2.2.1**: Build iteration controller
- [ ] Create `IterationController` class
- [ ] Implement max-iteration limits with configurable thresholds
- [ ] Add convergence detection (score plateau handling)
- [ ] Implement strategic decision engine (refine vs pivot)
- [ ] Write tests: test_iteration_controller.py

**Task 2.2.2**: Implement feedback bridge
- [ ] Create `FeedbackBridge` for generator-evaluator communication
- [ ] Implement file-based handoff system
- [ ] Add structured feedback format with severity levels
- [ ] Implement feedback prioritization
- [ ] Write tests: test_feedback_bridge.py

**Task 2.2.3**: Add multi-round refinement pipeline
- [ ] Create `RefinementPipeline` orchestrator
- [ ] Implement round trip: generate → evaluate → feedback → regenerate
- [ ] Add quality gate enforcement with configurable thresholds
- [ ] Implement early termination on quality达标
- [ ] Write tests: test_refinement_pipeline.py

### 2.3 Grading Criteria Engine

**Task 2.3.1**: Build criteria framework
- [ ] Create `GradingCriteria` base class
- [ ] Implement criteria registry with validation
- [ ] Add hard threshold vs soft weight distinction
- [ ] Implement criteria dependency resolution
- [ ] Write tests: test_criteria_framework.py

**Task 2.3.2**: Implement domain-specific criteria sets
- [ ] Create frontend design criteria set (4 criteria with weights)
- [ ] Create full-stack app criteria set (functionality, depth, design, code quality)
- [ ] Create code review criteria set
- [ ] Create document generation criteria set
- [ ] Write tests: test_domain_criteria.py

---

## PHASE 3: Planner & Sprint System (Weeks 6-8)

### 3.1 Planner Agent

**Task 3.1.1**: Build planner agent
- [ ] Create `PlannerAgent` class
- [ ] Implement spec expansion (1-4 sentences → full spec)
- [ ] Add product context extraction from existing project files
- [ ] Implement AI feature suggestion integration
- [ ] Add technical design high-level decomposition
- [ ] Write tests: test_planner_agent.py

**Task 3.1.2**: Implement spec generation
- [ ] Create `SpecGenerator` with structured output
- [ ] Implement feature decomposition into user stories
- [ ] Add acceptance criteria generation
- [ ] Implement visual design language creation
- [ ] Write tests: test_spec_generator.py

**Task 3.1.3**: Add planner-evaluator integration
- [ ] Implement spec review by evaluator before acceptance
- [ ] Add spec completeness scoring
- [ ] Implement spec revision loop
- [ ] Write tests: test_planner_evaluator_integration.py

### 3.2 Sprint Contract System

**Task 3.2.1**: Build sprint contract framework
- [ ] Create `SprintContract` class
- [ ] Implement contract negotiation protocol (generator proposes, evaluator reviews)
- [ ] Add contract modification loop until agreement
- [ ] Implement contract persistence and versioning
- [ ] Write tests: test_sprint_contract.py

**Task 3.2.2**: Implement contract verification
- [ ] Create `ContractVerifier` class
- [ ] Implement criterion-by-criterion checking
- [ ] Add testable behavior extraction from contracts
- [ ] Implement pass/fail determination with detailed reporting
- [ ] Write tests: test_contract_verifier.py

**Task 3.2.3**: Build sprint lifecycle manager
- [ ] Create `SprintManager` orchestrator
- [ ] Implement sprint planning → execution → verification → handoff flow
- [ ] Add sprint backlog management
- [ ] Implement sprint completion detection
- [ ] Write tests: test_sprint_manager.py

### 3.3 Multi-Agent Coordination

**Task 3.3.1**: Implement bounded subagent system
- [ ] Create `BoundedSubagent` with inheritance rules
- [ ] Implement context inheritance with boundaries
- [ ] Add recursion depth limiting
- [ ] Implement read-only mode option
- [ ] Write tests: test_bounded_subagent.py

**Task 3.3.2**: Build subagent communication layer
- [ ] Create `AgentMessageBus` for inter-agent communication
- [ ] Implement message queuing and delivery
- [ ] Add output merging logic
- [ ] Implement conflict resolution strategies
- [ ] Write tests: test_message_bus.py

---

## PHASE 4: Live Verification Infrastructure (Weeks 9-10)

### 4.1 Playwright MCP Integration

**Task 4.1.1**: Build Playwright MCP bridge
- [ ] Create `PlaywrightBridge` class
- [ ] Implement browser automation for live app testing
- [ ] Add screenshot capture capability
- [ ] Implement user flow simulation (click, type, navigate)
- [ ] Write tests: test_playwright_bridge.py

**Task 4.1.2**: Implement visual regression detection
- [ ] Create `VisualDiffChecker` class
- [ ] Implement screenshot comparison
- [ ] Add layout change detection
- [ ] Implement visual quality scoring
- [ ] Write tests: test_visual_diff.py

**Task 4.1.3**: Build API testing integration
- [ ] Create `APITester` class
- [ ] Implement endpoint discovery from running app
- [ ] Add request/response logging
- [ ] Implement assertion framework for API verification
- [ ] Write tests: test_api_tester.py

### 4.2 Database State Verification

**Task 4.2.1**: Build DB state checker
- [ ] Create `DatabaseVerifier` class
- [ ] Implement schema introspection
- [ ] Add state query capability
- [ ] Implement expected state assertions
- [ ] Write tests: test_database_verifier.py

**Task 4.2.2**: Implement integration with evaluator
- [ ] Connect DB verifier to evaluator agent
- [ ] Add DB state checks to sprint contract verification
- [ ] Implement bug-finding enhanced queries
- [ ] Write integration tests

---

## PHASE 5: Tool & Prompt Optimization (Weeks 11-12)

### 5.1 Tool Rationalization

**Task 5.1.1**: Audit current tool inventory
- [ ] Catalog all existing tools with usage metrics
- [ ] Identify redundant/rarely-used tools
- [ ] Analyze tool call patterns and dependencies
- [ ] Create tool utility scoring

**Task 5.1.2**: Implement tool tiering
- [ ] Create tool tier system (core, extended, specialist)
- [ ] Implement context-dependent tool loading
- [ ] Add tool auto-selection based on task type
- [ ] Implement tool unbundling for lightweight mode
- [ ] Write tests: test_tool_tiering.py

### 5.2 Prompt Library System

**Task 5.2.1**: Build prompt preset library
- [ ] Create `PromptLibrary` class with CRUD operations
- [ ] Implement task-type → prompt mapping
- [ ] Add prompt versioning and A/B testing capability
- [ ] Create preset for: code generation, code review, bug fix, refactoring, documentation
- [ ] Write tests: test_prompt_library.py

**Task 5.2.2**: Implement dynamic prompt composition
- [ ] Create `DynamicPromptBuilder` class
- [ ] Implement context-aware prompt assembly
- [ ] Add personality/style variations
- [ ] Implement prompt template inheritance
- [ ] Write tests: test_dynamic_prompts.py

### 5.3 Lifecycle Hooks

**Task 5.3.1**: Implement hook system
- [ ] Create `LifecycleHookManager` class
- [ ] Implement hook types: on_init, on_start, on_step, on_complete, on_error, on_exit
- [ ] Add hook registration and ordering
- [ ] Implement hook error isolation
- [ ] Write tests: test_lifecycle_hooks.py

**Task 5.3.2**: Add recovery and retry framework
- [ ] Create `RecoveryManager` class
- [ ] Implement retry strategies: exponential backoff, circuit breaker
- [ ] Add fallback chain (primary → secondary → human)
- [ ] Implement dead letter queue for failed tasks
- [ ] Write tests: test_recovery_manager.py

---

## PHASE 6: Production Hardening (Weeks 13-14)

### 6.1 Observability Enhancement

**Task 6.1.1**: Add harness-specific metrics
- [ ] Add iteration count, convergence metrics
- [ ] Add evaluator score tracking over time
- [ ] Implement tool usage efficiency metrics
- [ ] Add subagent coordination metrics
- [ ] Update Prometheus instrumentation

**Task 6.1.2**: Build harness debugging tools
- [ ] Create trace viewer for agent decisions
- [ ] Add step-by-step replay capability
- [ ] Implement decision point annotation
- [ ] Create harness audit log viewer
- [ ] Write tests: test_harness_debugging.py

### 6.2 Safety & Guardrails

**Task 6.2.1**: Enhance safety systems
- [ ] Add evaluator-specific safety checks
- [ ] Implement sandboxed code execution for generated code
- [ ] Add output validation before evaluation
- [ ] Implement circuit breakers for infinite loops
- [ ] Write tests: test_safety_enhancements.py

**Task 6.2.2**: Build approval workflow integration
- [ ] Connect evaluator findings to approval system
- [ ] Add automatic escalation for critical issues
- [ ] Implement approval timeout handling
- [ ] Add batch approval for minor issues
- [ ] Write tests: test_approval_workflow.py

### 6.3 Performance Optimization

**Task 6.3.1**: Optimize token usage
- [ ] Implement smart context window allocation
- [ ] Add compression for repeated structures
- [ ] Implement KV cache for embeddings
- [ ] Benchmark and optimize hot paths
- [ ] Write tests: test_token_optimization.py

**Task 6.3.2**: Parallelization
- [ ] Identify parallelizable subagent tasks
- [ ] Implement concurrent subagent execution
- [ ] Add result merging with conflict resolution
- [ ] Benchmark and validate speedup
- [ ] Write tests: test_parallelization.py

---

## PHASE 7: Integration & Testing (Weeks 15-16)

### 7.1 End-to-End Integration

**Task 7.1.1**: Integrate all components
- [ ] Wire Phase 1-6 components into unified harness
- [ ] Implement configuration management
- [ ] Add graceful degradation for missing components
- [ ] Create integration test suite

**Task 7.1.2**: Build demo applications
- [ ] Create frontend design demo (museum website)
- [ ] Create full-stack app demo (retro game maker)
- [ ] Create code review demo
- [ ] Document demo results and quality metrics

### 7.2 Regression Test Suite

**Task 7.2.1**: Build benchmark harness
- [ ] Create standardized benchmark suite (100+ cases)
- [ ] Implement automated scoring
- [ ] Add regression detection
- [ ] Create baseline metrics dashboard

**Task 7.2.2**: Add chaos testing
- [ ] Implement network failure simulation
- [ ] Add LLM timeout/failure simulation
- [ ] Implement partial system failure modes
- [ ] Create chaos test playbook

---

## Dependencies Map

```
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

---

## Success Criteria

| Phase | Deliverable | Verification |
|-------|-------------|--------------|
| 1 | Working memory system reduces token waste by 40% | Token usage benchmarks |
| 2 | Evaluator catches 90% of bugs that generator misses | Benchmark comparison |
| 3 | Planner produces spec in <5 min that evaluator approves | Automated acceptance rate |
| 4 | Live verification finds UI bugs without human testing | Demo app bug detection |
| 5 | Tool tiering reduces unnecessary tool exposure by 50% | Tool call count metrics |
| 6 | 99.9% task completion with no silent failures | Chaos test pass rate |
| 7 | End-to-end harness matches Claude Code quality | Human evaluation survey |

---

## Resource Estimate

| Role | Weeks | Tasks |
|------|-------|-------|
| Senior Backend/Python | 16 | Phases 1, 2, 3, 4 core |
| AI/Harness Engineer | 16 | Phases 2, 3 evaluator focus |
| Frontend/Testing | 8 | Phase 4, 7.2 |
| DevOps | 4 | Phase 6, deployment |

**Total Timeline**: 16 weeks (4 months)  
**Team**: 2-3 engineers  
**Infrastructure**: Redis cluster, Playwright cloud (optional), benchmark compute