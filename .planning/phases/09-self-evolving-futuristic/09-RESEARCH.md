# Phase 9: Self-Evolving & Futuristic Capabilities — Research

**Phase:** 09
**Researched:** 2026-04-27
**Status:** Ready for planning

---

## Phase Goal

Transform LuminaMind into a true modern futuristic harness with self-improvement, real-time visualization, isolated sandboxing, and autonomous adaptation.

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

## Standard Stack

Based on Phase 9 roadmap requirements:

| Component | Technology | Notes |
|-----------|------------|-------|
| Event Streaming | SSE (Server-Sent Events), WebSocket | For real-time dashboards |
| Sandbox Isolation | Docker SDK | `docker-py`, per-task containers |
| Memory OS | Filesystem-based hierarchy | Not flat vector store |
| Plugin System | PluginManifest (YAML) | Sandboxed execution |
| Model Routing | Multi-provider middleware | OpenAI, Anthropic, Ollama, Groq, MiniMax, Zhipu, Moonshot |
| Meta-Reasoning | Self-review agent pattern | Post-task analysis |

### Existing Stack to Leverage

- **Registry pattern** (from CriteriaEngine) → Plugin registry, model registry
- **Context manager pattern** (from EvaluatorSandbox) → Sandbox lifecycle
- **Polling approach** (from async evaluation) → Event buffering
- **FallbackChain** → Model fallback chains
- **Lifecycle hooks** → Plugin lifecycle events

---

## Architecture Patterns

### 9.1 Self-Improving Memory System
- Closed-loop feedback: Judge → reward → skill update
- AtomicSkill with trigger_conditions for context-aware invocation
- SKILL.md file format for persistent lessons
- Skill versioning and rollback

### 9.2 Agent Event Stream API
- Event schema registry with versioning
- SSE + WebSocket dual support
- Event buffering for replay capability
- Subscription/filtering per agent or task

### 9.3 Docker Sandbox Runtime
- Per-task container lifecycle
- Network isolation + egress control
- Resource limits (CPU, memory, disk, time)
- Multi-language runtime support (Python, Node, Java, Go)

### 9.4 Real-Time Token Streaming
- Token-by-token streaming to client
- Reasoning trace visualization (think → act → observe)
- Tool call timeline with latency tracking
- Branching visualization for subagent spawn

### 9.5 Hierarchical Memory OS
- Filesystem-based hierarchy: global → project → task → session
- Context hierarchy over flat vector store
- Cross-task knowledge distillation
- Memory TTL/eviction policies (LRU, time-based, importance-based)

### 9.6 Recursive Meta-Reasoning
- Post-task self-review phase
- Step count analysis (actual vs. optimal)
- Token efficiency scoring
- Redundancy detection + strategy suggestion

### 9.7 Model Cost Arbitrage
- Dynamic model selection middleware
- Task complexity classifier
- Mid-task model switching
- Cost budget enforcement

### 9.8 Plugin & Extension System
- PluginManifest YAML format
- Sandboxed plugin execution
- Evaluator, tool, prompt plugin interfaces
- Plugin marketplace metadata

### 9.9 Per-Role Model Selection
- Role → model mapping (planner, executor, evaluator, critic)
- Provider configurations (MiniMax, Zhipu GLM, Moonshot Kimi, OpenAI, Anthropic)
- Preset profiles (free_optimal, balanced, quality, fast)
- CLI model picker

### 9.10 Agent Customization System
- AgentConfig per role (prompt, criteria, tools, params)
- File-based prompt storage
- Interactive config wizard
- Config validation on load

---

## Don't Hand-Roll

| Problem | Use Instead |
|---------|-------------|
| Cron parsing | `croniter` library |
| SSE/WebSocket | `sse-starlette`, `websockets` |
| Docker SDK | `docker-py` |
| Plugin sandboxing | ` subprocess` with timeout + namespace |
| Model routing | Custom middleware (don't build from scratch) |
| Event schema versioning | Follow established patterns |

---

## Common Pitfalls

1. **Memory OS**: Don't use flat vector store — filesystem hierarchy is explicitly required
2. **Sandbox**: Must have network isolation — simple subprocess is insufficient
3. **Model arbitrage**: Quality threshold must be measurable, not subjective
4. **Plugin system**: Signature verification needed before execution
5. **Event streaming**: Need buffering for replay — raw stream can't be rewound
6. **Meta-reasoning**: Self-patch integration requires safety guardrails

---

## Validation Architecture

For each component:

### Self-Improving Memory
- Unit tests: SkillAcquisition, SkillLibrary, LessonsLearned
- Integration: Closed-loop feedback cycle
- Benchmark: Skill suggestion accuracy

### Event Stream API
- Unit tests: Event schema, buffer replay
- Integration: SSE client connect/disconnect
- Benchmark: Event throughput

### Docker Sandbox
- Unit tests: Container provisioning, resource limits
- Integration: Untrusted code execution
- Security: Network isolation verification

### Real-Time Streaming
- Unit tests: Token streaming, reasoning trace
- Integration: Dashboard visualization
- Benchmark: Latency under load

---

## Key Decisions Required During Planning

1. **Memory OS backend**: Filesystem + SQLite index vs. pure filesystem
2. **Event buffer size**: How many events to retain for replay
3. **Sandbox base images**: Which language runtimes to support initially
4. **Model providers**: Which providers to support beyond existing stack
5. **Plugin sandbox approach**: Firejail vs. namespace vs. seccomp
