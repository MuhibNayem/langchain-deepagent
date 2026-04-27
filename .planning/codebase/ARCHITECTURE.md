# Architecture

**Analysis Date:** 2026-04-27

## Pattern Overview

**Overall:** Multi-agent orchestration with LangGraph

**Key Characteristics:**
- Graph-based agent architecture using LangGraph's `create_deep_agent`
- Subagent delegation pattern (web-researcher, code-executor, greeting-responder)
- Human-in-the-loop (HITL) interrupts for sensitive operations
- State persistence via checkpointers (Redis/in-memory/file)
- Tool registry pattern for extensibility

## Layers

**CLI Layer:**
- Purpose: User interaction and command routing
- Location: `luminamind/main.py`
- Contains: Typer CLI, interactive prompts, Rich UI rendering, session management
- Depends on: deep_agent, observability, config
- Used by: End users via CLI commands

**Agent Core Layer:**
- Purpose: Agent orchestration and state machine
- Location: `luminamind/deep_agent.py`
- Contains: `get_llm()`, `build_subagents()`, `create_deep_agent()` call
- Depends on: LangGraph, LangChain, all tools
- Used by: CLI layer, LangGraph platform

**Tool Ecosystem Layer:**
- Purpose: Reusable tool implementations
- Location: `luminamind/py_tools/` (10 tools)
- Contains: web_search, web_markdown, weather, shell, grep, tree, read_many, multi_replace, patch, os_info, safety
- Depends on: LangChain tools, external APIs, utils
- Used by: Agent core via registry

**Utilities Layer:**
- Purpose: Cross-cutting concerns
- Location: `luminamind/utils/`
- Contains: http_client (retry, TLS), rate_limit (token bucket)
- Used by: Tools and agent

**Observability Layer:**
- Purpose: Logging, metrics, tracing
- Location: `luminamind/observability/`
- Contains: setup_logging(), start_metrics_server(), monitor_tool decorator
- Used by: All layers

**Configuration Layer:**
- Purpose: Environment and settings management
- Location: `luminamind/config/`
- Contains: checkpointer (Redis/file/memory), env loading
- Used by: All layers

## Data Flow

**User Input → Agent Response:**
1. User input via `main.py:chat()` → `_stream_agent_response()`
2. `app.astream()` processes with LLM + tools
3. Tool calls rendered via `_render_tool_start()` / `_render_tool_end()`
4. HITL interrupts pause agent for approval via `_prompt_for_approval()`
5. `Command(resume={...})` resumes after user decision
6. Final response rendered via `_render_agent_reply()`

**State Persistence Flow:**
1. `create_checkpointer()` factory creates appropriate checkpointer
2. `RedisBackedMemorySaver` persists to Redis (production)
3. `FileBackedMemorySaver` persists to disk (development fallback)
4. Thread ID (`configurable.thread_id`) scopes conversation state

**Tool Execution Flow:**
1. Agent calls tool → `@monitor_tool` decorator starts timing
2. `enforce_rate_limit()` checks limits (Redis or memory)
3. Tool execution with error handling
4. Metrics recorded (TOOL_INVOCATIONS, TOOL_DURATION, TOOL_ERRORS)
5. Result returned to agent

## Key Abstractions

**DeepAgent (via deepagents library):**
- Purpose: Build autonomous agent with subagents
- Pattern: `create_deep_agent(model, tools, system_prompt, subagents, interrupt_on)`
- Examples: `luminamind/deep_agent.py:212`

**Tool Registry:**
- Purpose: Centralized tool lookup
- Pattern: `PY_TOOL_REGISTRY` dict in `luminamind/py_tools/registry.py`
- Usage: `registry_tool(name)` helper function

**Checkpointer:**
- Purpose: Conversation state persistence
- Pattern: Factory method `create_checkpointer()` returns MemorySaver variant

**Rate Limiter:**
- Purpose: Prevent API/function abuse
- Pattern: Token bucket with Redis backend, in-memory fallback

## Entry Points

**CLI Entry:**
- Location: `luminamind/main.py:cli` (Typer app)
- Triggers: `luminamind` command or `python -m luminamind`
- Responsibilities: Mode selection, chat loop, LangGraph dev server

**Programmatic Entry:**
- Location: `luminamind/deep_agent.py:app`
- Triggers: Import of `app` or `agent_kwargs` from `deep_agent`
- Responsibilities: Agent initialization, tool setup, subagent configuration

## Error Handling

**Strategy:** Graceful degradation with structured error responses

**Patterns:**
- Tools return `{"error": True, "message": "...", ...}` on failure
- Validation via Pydantic models (e.g., `ShellInput`)
- Rate limit errors raised as `RateLimitError` exception
- HTTP errors handled with retries and fallback chains

## Cross-Cutting Concerns

**Logging:** Structlog with JSON/console output, configurable via `LOG_LEVEL`/`LOG_FORMAT`

**Validation:** Pydantic BaseModel for all tool inputs

**Rate Limiting:** Per-tool limits (web_search: 10/min, shell: 30/min, etc.)

**Metrics:** Prometheus counters/histograms for tool execution

**Security:** Path allowlisting, command whitelist, dangerous pattern detection

---

*Architecture analysis: 2026-04-27*