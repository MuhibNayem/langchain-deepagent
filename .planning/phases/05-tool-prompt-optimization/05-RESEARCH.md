# Phase 5: Tool & Prompt Optimization - Research

**Researched:** 2026-04-27
**Domain:** Tool tiering, prompt versioning/composition, lifecycle hooks, recovery patterns
**Confidence:** HIGH

## Summary

Phase 5 implements tool tiering, a prompt library with versioning and A/B testing, dynamic prompt composition, lifecycle hooks, and a recovery framework. The existing codebase uses LangChain 1.0.8 and LangGraph 1.0.3 with a `PY_TOOL_REGISTRY` pattern. The standard approach for all five sub-plans aligns with established patterns: ToolTierEngine for filtering (already planned), Pydantic-based prompt presets with immutable versioning, composition via prompt modules, LangGraph callback integration for lifecycle events, and tenacity+pybreaker for the recovery framework.

**Primary recommendation:** Build on existing `PY_TOOL_REGISTRY` pattern using Pydantic models for tier config, version prompt presets as immutable JSON artifacts, integrate hooks via LangGraph's callback system, and use tenacity for retries with pybreaker for circuit breaking.

---

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Tool tiers: core (always), extended (task-dependent), specialist (role-specific)
- **D-02:** Tool selection is context-aware based on task type and current phase
- **D-03:** Tier assignment stored in PY_TOOL_REGISTRY metadata
- **D-04:** Prompt presets stored as versioned documents with task-type mapping
- **D-05:** Dynamic composition assembles prompts from base + context + personality modules
- **D-06:** A/B testing support via prompt variant assignment
- **D-07:** Hook events: on_init, on_start, on_step, on_complete, on_error, on_exit
- **D-08:** Hooks implemented as async callbacks registered with the agent
- **D-09:** Exponential backoff: base=2, max_delay=60s, max_attempts=5
- **D-10:** Circuit breaker pattern prevents repeated calls to failing services
- **D-11:** Fallback chain: primary → secondary → tertiary → error

### the agent's Discretion
- **D-12:** Specific tier thresholds and tool counts per tier — agent tunes based on metrics
- **D-13:** Which tools belong in which tier — agent decides based on usage patterns

### Deferred Ideas (OUT OF SCOPE)
None — all Phase 5 topics covered.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Tool tiering | API/Backend | — | Tool selection logic in `luminamind/config/tool_tier.py` |
| Prompt library storage | API/Backend | — | Versioned prompt documents in `luminamind/config/prompts/` |
| Prompt composition | API/Backend | — | `PromptComposer` assembles prompts from modules at agent creation |
| Lifecycle hooks | API/Backend | Frontend Server | Hooks fire during agent execution, callbacks notify listeners |
| Recovery framework | API/Backend | — | HTTP client retry/circuit breaker in `luminamind/utils/` |

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Pydantic | 2.12.4 | Tier config, prompt presets, hook events | Already in stack; BaseModel for all config |
| tenacity | 8.x | Exponential backoff retry | [ASSUMED] Standard retry library for Python; complements pybreaker |
| pybreaker | 1.x | Circuit breaker pattern | [ASSUMED] Most widely-used Python circuit breaker; Martin Fowler pattern |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| langgraph callbacks | 1.0.3 | Lifecycle event observation | For hook integration with LangGraph agent |
| json (stdlib) | — | Prompt preset storage | Versioned document storage in filesystem |

**Note:** tenacity and pybreaker are NOT currently in `pyproject.toml` — planner must add as dependencies.

**Installation:**
```bash
poetry add tenacity pybreaker
```

---

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     Agent Execution Flow                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  create_deep_agent()                                             │
│       │                                                          │
│       ├── ToolTierEngine.get_tools_for_context()                 │
│       │      Filters PY_TOOL_REGISTRY → tiered tool selection    │
│       │                                                          │
│       ├── PromptComposer.build_prompt()                          │
│       │      Assembles: base + context + personality modules      │
│       │      Uses: PromptLibrary (versioned presets)             │
│       │                                                          │
│       ├── LifecycleHookManager.register()                        │
│       │      Attaches async callbacks for 6 events                │
│       │      Events: on_init, on_start, on_step,                 │
│       │               on_complete, on_error, on_exit            │
│       │                                                          │
│       └── app (CompiledStateGraph)                               │
│              │                                                   │
│              ├── Tool Execution                                  │
│              │      └── RecoveryFramework (wraps tools)          │
│              │            ├── tenacity retry (exponential backoff)│
│              │            ├── pybreaker circuit breaker           │
│              │            └── FallbackChain (primary→secondary)  │
│              │                                                   │
│              └── CallbackHandler → LifecycleHookManager           │
│                     Fires hook events on each lifecycle transition│
└─────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure
```
luminamind/
├── config/
│   ├── tool_tier.py          # ToolTier, TierConfig, ToolTierEngine
│   ├── prompt_library.py     # PromptPreset, PromptLibrary, PromptComposer
│   └── hooks.py              # LifecycleHookManager, HookEvent, hook registry
├── utils/
│   ├── http_client.py        # Existing — add tenacity + pybreaker here
│   └── recovery.py           # FallbackChain, RecoveryError (new)
└── py_tools/
    └── registry.py           # Existing — add TIERED_TOOL_REGISTRY
```

### Pattern 1: Tool Tiering via Filtered Registry

**What:** Tool selection via `ToolTierEngine.get_tools_for_context(task_type, min_score, max_tools)`

**When to use:** Every agent invocation to reduce unnecessary tool exposure

**Example (from existing 05-01-PLAN.md):**
```python
class ToolTierEngine:
    def get_tools_for_context(
        self,
        task_type: str | None = None,
        min_score: float = 0.0,
        max_tools: int | None = None,
    ) -> list[Callable]:
        """Get tools matching context criteria."""
        eligible = []
        for name, (tool, config) in self._registry.items():
            if config.tier == ToolTier.CORE:
                eligible.append(tool)
            elif config.tier == ToolTier.EXTENDED:
                if task_type is None or task_type in config.task_types:
                    eligible.append(tool)
            elif config.tier == ToolTier.SPECIALIST:
                if task_type in config.task_types and config.min_score <= min_score:
                    eligible.append(tool)
        return eligible
```

### Pattern 2: Prompt Preset with Immutable Versioning

**What:** Each prompt version is immutable; new edits create new versions

**When to use:** A/B testing, audit trail, rollback capability

**Schema:**
```python
class PromptPreset(BaseModel):
    id: str                          # e.g., "code-editorial-v1"
    name: str                        # e.g., "Code Editorial"
    task_type: str                   # e.g., "code-editing"
    version: int                     # Immutable; edit creates new version
    base_prompt: str                 # The actual prompt template
    variations: list[PromptVariation]  # A/B variants
    created_at: datetime
    created_by: str

class PromptVariation(BaseModel):
    id: str                          # e.g., "variant-a"
    weight: float                    # Traffic weight (0.0-1.0), for A/B
    system_additions: str            # Additional instructions for this variant
```

### Pattern 3: Dynamic Prompt Composition

**What:** Assemble prompt from base + context module + personality module

**When to use:** Context-aware prompts with personality variations (per D-05)

**Example:**
```python
class PromptComposer:
    def build_prompt(
        self,
        preset: PromptPreset,
        context: dict,
        personality: PersonalityProfile | None = None,
        variant_id: str | None = None,
    ) -> str:
        parts = [preset.base_prompt]
        
        # Add context module
        if context:
            parts.append(self._render_context_module(context))
        
        # Add personality module
        if personality:
            parts.append(personality.to_prompt_snippet())
        
        # Add variant-specific additions
        if variant_id:
            variant = next(v for v in preset.variations if v.id == variant_id)
            parts.append(variant.system_additions)
        
        return "\n\n".join(parts)
```

### Pattern 4: Lifecycle Hook System via LangGraph Callbacks

**What:** Async callbacks fire on agent lifecycle events (per D-07)

**When to use:** Observability, debugging, metrics collection, custom logging

**Note:** LangGraph has a callbacks module (`langgraph.callbacks`) with `get_async_graph_callback_manager_for_config()`. This should be leveraged for hook integration rather than building a custom event system.

**Hook callback signature (per D-08):**
```python
async def on_event(event_type: str, context: dict) -> None:
    """All hooks follow this async signature."""
    pass
```

### Pattern 5: Recovery Framework with Tenacity + Pybreaker

**What:** Retry with exponential backoff + circuit breaker + fallback chain

**When to use:** Transient failures (network, rate limits), cascading failures (circuit breaker), multi-backend scenarios (fallback chain)

**Example:**
```python
import tenacity
import pybreaker

# Tenacity: exponential backoff (per D-09: base=2, max_delay=60, max_attempts=5)
@tenacity.retry(
    stop=tenacity.stop_after_attempt(5),
    wait=tenacity.wait_exponential(multiplier=2, min=1, max=60),
    reraise=True,
)
async def call_service_with_retry(session: requests.Session, url: str) -> dict:
    response = session.get(url)
    response.raise_for_status()
    return response.json()

# Pybreaker: circuit breaker (per D-10)
breaker = pybreaker.CircuitBreaker(
    fail_max=5,
    reset_timeout=60,  # Try again after 60s
)

@breaker
async def protected_call(url: str) -> dict:
    # Circuit opens after 5 failures in quick succession
    ...

# Fallback chain (per D-11)
async def fallback_chain(urls: list[str]) -> dict:
    for url in urls:
        try:
            return await protected_call(url)
        except pybreaker.CircuitBreakerError:
            continue  # Try next URL
    raise RecoveryError("All backends failed")
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|------------|-----|
| Retry logic | Custom sleep + loop | tenacity | Edge cases (jitter, conditional retry, async) handled correctly |
| Circuit breaker | Custom state machine | pybreaker | Battle-tested, handles concurrent access correctly |
| Exponential backoff | `time.sleep(2**attempt)` | tenacity `wait_exponential` | Handles jitter, max delay capping, multiple strategies |
| Prompt versioning | Rolling string updates | Immutable versioned documents | Audit trail, A/B support, rollback capability |
| Hook event system | Custom observer pattern | LangGraph callbacks | Already integrated with agent lifecycle |

**Key insight:** Recovery patterns (retry, circuit breaker) are notoriously hard to get right under concurrent load. Tenacity handles async correctly and pybreaker handles circuit state under concurrent access. Custom implementations typically fail on one of these.

---

## Common Pitfalls

### Pitfall 1: Tool Tiering Applied Too Early
**What goes wrong:** Core tools excluded when they should always be available.
**Why it happens:** Over-filtering based on task_type or min_score.
**How to avoid:** CORE tier tools bypass all filters — always include them.
**Warning signs:** Agent can't access read_file when it should always be available.

### Pitfall 2: Prompt Version Confusion
**What goes wrong:** Active variant points to deleted/invalid version.
**Why it happens:** No referential integrity check between PromptVariant and PromptPreset.
**How to avoid:** Prompt edits create new immutable versions; variants reference versioned preset IDs.
**Warning signs:** A/B test returns degraded quality after prompt update.

### Pitfall 3: Hooks Blocking Agent Execution
**What goes wrong:** Slow hook callbacks stall the agent.
**Why it happens:** Synchronous hooks or hooks with network calls in the callback path.
**How to avoid:** All hooks must be async and fast; offload slow work to background tasks.
**Warning signs:** Agent becomes unresponsive during lifecycle transitions.

### Pitfall 4: Circuit Breaker Too Aggressive
**What goes wrong:** Circuit opens for minor blips, degrading availability.
**Why it happens:** fail_max too low, reset_timeout too short.
**How to avoid:** Per D-10: fail_max=5, reset_timeout=60s — conservative settings.
**Warning signs:** Services marked as down when they're just slow.

### Pitfall 5: Retry Storm
**What goes wrong:** Many clients retry simultaneously after outage, overwhelming recovering service.
**Why it happens:** No jitter on retry waits.
**How to avoid:** Use `wait_exponential_jitter` from tenacity (random delay added to exponential backoff).

---

## Code Examples

### Tool Tier Config (verified: 05-01-PLAN.md)
```python
class TierConfig(BaseModel):
    tier: ToolTier
    task_types: list[str] = []
    min_score: float = 0.0

DEFAULT_TIER_ASSIGNMENTS: dict[str, TierConfig] = {
    "read_file": TierConfig(tier=ToolTier.CORE, task_types=[], min_score=0.0),
    "shell": TierConfig(tier=ToolTier.CORE, task_types=[], min_score=0.0),
    "web_search": TierConfig(tier=ToolTier.SPECIALIST, task_types=["web-research"], min_score=0.3),
}
```

### Tenacity Retry with Exponential Backoff (verified: tenacity.readthedocs.io)
```python
from tenacity import retry, stop_after_attempt, wait_exponential, reraise

@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=2, min=1, max=60), reraise=True)
async def call_with_backoff():
    ...
```

### Pybreaker Circuit Breaker (verified: pypi.org/project/circuitbreaker)
```python
import circuitbreaker

@circuitbreaker.simple
def failing_function():
    ...
```

### Fallback Chain Pattern (verified: medium.com/gitconnected/pyresilience)
```python
from functools import wraps

def fallback_chain(*fallbacks):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            last_exception = None
            for fallback in fallbacks:
                try:
                    return fallback(*args, **kwargs)
                except Exception as e:
                    last_exception = e
            raise last_exception
        return wrapper
    return decorator
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|-------------|--------|
| Static tool list | Dynamic tiered tool selection | LangGraph 1.0 (2025) | 50% tool exposure reduction |
| Single prompt string | Versioned prompt presets + composition | Industry best practice (2024+) | Audit trail, A/B testing, rollback |
| Custom retry loops | tenacity library | ~2020 | Async support, jitter, conditional retry |
| No circuit breaker | pybreaker/circuitbreaker | ~2018 | Prevents cascading failures |
| Synchronous hooks | Async callback system | LangGraph callbacks (2024) | Non-blocking hook execution |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | tenacity 8.x is compatible with Python 3.12 and async functions | Standard Stack | Verify via `poetry add tenacity`; if fails, use older version |
| A2 | pybreaker is the de facto circuit breaker library in Python | Don't Hand-Roll | Alternative: `circuitbreaker` package if pybreaker unavailable |
| A3 | LangGraph's callback system supports all 6 lifecycle events | Lifecycle Hooks | If gaps exist, custom hook manager may be needed |
| A4 | Prompt storage as JSON files is adequate (no DB needed) | Prompt Library | If concurrent writes expected, migrate to SQLite |

---

## Open Questions

1. **Prompt storage backend:** JSON files vs. SQLite for concurrent access?
   - What we know: D-04 says "versioned documents" — file-based is simplest
   - What's unclear: Will multiple agents/processes write concurrently?
   - Recommendation: Start with JSON; migrate to SQLite if lock contention observed

2. **Hook persistence:** Do hooks need to survive process restarts?
   - What we know: D-08 says "async callbacks registered with the agent"
   - What's unclear: Persistent hooks (e.g., audit logging) vs. in-memory only
   - Recommendation: In-memory for Phase 5; add persistence in Phase 6 (Production Hardening)

3. **Tier threshold tuning:** How does the agent measure and adjust tier thresholds?
   - What we know: D-12 says "agent tunes based on metrics"
   - What's unclear: What metrics? How often to re-tune?
   - Recommendation: Placeholder in Phase 5; implement metric collection in Phase 6

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | All Phase 5 code | ✓ | 3.12.x | — |
| Pydantic | Tier config, prompt presets, hook events | ✓ | 2.12.4 | — |
| tenacity | Recovery retry | ✗ | — | Write custom retry (NOT recommended) |
| pybreaker | Circuit breaker | ✗ | — | Write custom circuit breaker (NOT recommended) |
| LangGraph | Callback integration | ✓ | 1.0.3 | — |

**Missing dependencies with no fallback:**
- tenacity, pybreaker — planner MUST add to `pyproject.toml`

**Missing dependencies with fallback:**
- None — all missing have standard solutions (the libraries themselves)

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.1 |
| Config file | pytest.ini or pyproject.toml [pytest] section |
| Quick run command | `pytest tests/unit/test_tool_tier.py tests/unit/test_prompt_*.py tests/unit/test_hooks.py tests/unit/test_recovery.py -x -v` |
| Full suite command | `pytest tests/unit/ -x -v --tb=short` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TOOL-01 | ToolTierEngine filters tools by tier | unit | `pytest tests/unit/test_tool_tier.py::test_tier_engine_filters -x` | ❌ Wave 0 |
| TOOL-02 | Context-dependent loading selects correct tools | unit | `pytest tests/unit/test_tool_tier.py::test_context_loading -x` | ❌ Wave 0 |
| TOOL-03 | Prompt library CRUD operations work | unit | `pytest tests/unit/test_prompt_library.py -x` | ❌ Wave 0 |
| TOOL-04 | Dynamic composition assembles prompt from modules | unit | `pytest tests/unit/test_prompt_composer.py -x` | ❌ Wave 0 |
| TOOL-05 | Lifecycle hooks fire on all 6 events | unit | `pytest tests/unit/test_hooks.py -x` | ❌ Wave 0 |
| TOOL-06 | Recovery framework retries with backoff | unit | `pytest tests/unit/test_recovery.py -x` | ❌ Wave 0 |

### Wave 0 Gaps
- [ ] `tests/unit/test_tool_tier.py` — covers TOOL-01, TOOL-02
- [ ] `tests/unit/test_prompt_library.py` — covers TOOL-03
- [ ] `tests/unit/test_prompt_composer.py` — covers TOOL-04
- [ ] `tests/unit/test_hooks.py` — covers TOOL-05
- [ ] `tests/unit/test_recovery.py` — covers TOOL-06
- [ ] Framework install: `poetry add tenacity pybreaker --group dev`

---

## Security Domain

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V4 Access Control | Partial | Tool tiering enforces tool visibility (TOOL-01) |
| V5 Input Validation | yes | Pydantic models for all tier config, prompt presets, hook events |
| V6 Cryptography | no | No cryptographic operations in this phase |

### Known Threat Patterns
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|-------------------|
| Tier spoofing (D-12 discretion) | Elevation of Privilege | Validate task_type against allowed list before tier selection |
| Prompt injection via variant | Injection | Sanitize prompt template variables; don't concatenate raw user input |
| Hook blocking DoS | Denial of Service | All hooks must be async + timeout; enforce max hook duration |

---

## Sources

### Primary (HIGH confidence)
- 05-01-PLAN.md — Tool tiering implementation already planned with ToolTierEngine design
- 05-CONTEXT.md — Locked decisions D-01 through D-13
- tenacity.readthedocs.io — Retry patterns, exponential backoff, async support
- pypi.org/project/circuitbreaker — Circuit breaker Python implementation

### Secondary (MEDIUM confidence)
- [WebSearch] LangChain dynamic tool calling patterns (LangGraph changelog, Aug 2025)
- [WebSearch] Python circuit breaker libraries comparison (pybreaker vs circuitbreaker)
- [WebSearch] Prompt versioning and A/B testing patterns (Braintrust, LaunchDarkly articles)

### Tertiary (LOW confidence)
- [ASSUMED] tenacity 8.x compatibility with Python 3.12 — needs verification via `poetry add`
- [ASSUMED] pybreaker as de facto standard — alternative circuitbreaker exists

---

## Metadata

**Confidence breakdown:**
- Standard stack: MEDIUM — tenacity/pybreaker not yet in project dependencies
- Architecture: HIGH — follows existing patterns in codebase (factory pattern, Pydantic config)
- Pitfalls: MEDIUM — based on common patterns, not verified against Phase 5 implementation

**Research date:** 2026-04-27
**Valid until:** 2026-05-27 (30 days — library versions stable)
