# Codebase Structure

**Analysis Date:** 2026-04-27

## Directory Layout

```
langchain-deepagent/
├── luminamind/           # Main package
│   ├── __init__.py
│   ├── main.py           # CLI entry point
│   ├── deep_agent.py     # Agent factory
│   ├── config/           # Configuration
│   ├── observability/    # Logging, metrics
│   ├── py_tools/         # Tool implementations
│   ├── utils/            # HTTP client, rate limiting
│   └── langgraph.json    # LangGraph config
├── tests/                # Test suite
│   ├── unit/             # Unit tests
│   └── integration/      # Integration tests
├── docs/                 # Documentation
├── scripts/              # Installation scripts
├── pyproject.toml        # Poetry config
├── poetry.lock           # Locked dependencies
├── Dockerfile            # Container definition
└── README.md             # Project overview
```

## Directory Purposes

**`luminamind/`:**
- Purpose: Main application package
- Contains: All Python modules for agent, tools, config, observability

**`luminamind/config/`:**
- Purpose: Environment and state configuration
- Contains: `env.py` (environment loading), `checkpointer.py` (state persistence)
- Key files: `luminamind/config/checkpointer.py`, `luminamind/config/env.py`

**`luminamind/observability/`:**
- Purpose: Observability infrastructure
- Contains: Structured logging, Prometheus metrics, metrics server
- Key files: `luminamind/observability/logging.py`, `luminamind/observability/metrics.py`

**`luminamind/py_tools/`:**
- Purpose: Reusable tool implementations
- Contains: 11 tools (web_search, shell, grep, tree, patch, etc.)
- Key files: `luminamind/py_tools/registry.py`, `luminamind/py_tools/shell.py`, `luminamind/py_tools/web_search.py`

**`luminamind/utils/`:**
- Purpose: Cross-cutting utilities
- Contains: HTTP client with retries, rate limiting
- Key files: `luminamind/utils/http_client.py`, `luminamind/utils/rate_limit.py`

**`tests/`:**
- Purpose: Test suite
- Contains: Unit tests, integration tests
- Structure: Mirrors `luminamind/` structure

**`docs/`:**
- Purpose: Project documentation
- Contains: Architecture, operations, security guides

**`scripts/`:**
- Purpose: Installation/deployment scripts
- Contains: Shell and PowerShell install scripts

## Key File Locations

**Entry Points:**
- `luminamind/main.py` - CLI app (`typer.Typer`)
- `luminamind/deep_agent.py` - Agent factory (`create_deep_agent`)

**Configuration:**
- `pyproject.toml` - Poetry dependencies and project metadata
- `luminamind/config/env.py` - Environment variable management
- `luminamind/langgraph.json` - LangGraph platform config

**Core Logic:**
- `luminamind/deep_agent.py` - Agent setup with tools/subagents
- `luminamind/py_tools/registry.py` - Tool registry (`PY_TOOL_REGISTRY`)
- `luminamind/config/checkpointer.py` - State persistence

**Testing:**
- `tests/unit/test_shell.py` - Unit test example
- `tests/integration/test_tool_execution.py` - Integration test example

## Naming Conventions

**Files:**
- Python modules: lowercase_with_underscores (`shell.py`, `web_search.py`)
- Test files: `test_<module>.py` (unit), `<feature>_test.py` (integration)

**Directories:**
- All lowercase with underscores

**Classes:**
- PascalCase: `RedisBackedMemorySaver`, `FileBackedMemorySaver`, `ShellInput`

**Functions:**
- lowercase_with_underscores: `get_llm()`, `create_checkpointer()`, `enforce_rate_limit()`

**Decorators:**
- `@tool("name")` - LangChain tool decorator

**Constants:**
- UPPER_SNAKE_CASE: `ALLOWED_COMMANDS`, `DEFAULT_TIMEOUT_MS`, `CONTEXT_WINDOW_LIMIT`

## Where to Add New Code

**New Tool:**
1. Create `luminamind/py_tools/<tool_name>.py` with `@tool` decorator
2. Add to `PY_TOOL_REGISTRY` in `luminamind/py_tools/registry.py`
3. Add unit tests in `tests/unit/test_<tool_name>.py`

**New Utility:**
- Shared: `luminamind/utils/<utility_name>.py`
- Observability: `luminamind/observability/<module>.py`

**New Configuration:**
- Environment: `luminamind/config/env.py` (add to `config_definitions`)
- Checkpointer: `luminamind/config/checkpointer.py`

**New CLI Command:**
- Add to `luminamind/main.py` with `@cli.command()` decorator

## Special Directories

**`luminamind/__pycache__/`:**
- Purpose: Python bytecode cache
- Generated: Yes (auto-created by Python)
- Committed: No (in .gitignore)

**`.venv/`:**
- Purpose: Poetry virtual environment
- Generated: Yes (by Poetry)
- Committed: No (in .gitignore)

**`.langgraph_api/`:**
- Purpose: LangGraph API configuration
- Generated: May be
- Committed: Yes

---

*Structure analysis: 2026-04-27*