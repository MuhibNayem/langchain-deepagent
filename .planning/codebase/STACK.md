# Technology Stack

**Analysis Date:** 2026-04-27

## Languages

**Primary:**
- Python 3.12 - Core language for all application code

## Runtime

**Environment:**
- Python 3.12+ with Poetry as package manager

**Package Manager:**
- Poetry 1.x
- Lockfile: `poetry.lock` present

## Frameworks

**Core:**
- LangChain 1.0.8 - LLM integration framework
- LangGraph 1.0.3 - Agent orchestration via graph-based state machines
- deepagents 0.2.7 - Custom agent creation (`create_deep_agent`)

**CLI & UI:**
- Typer 0.20.0 - CLI framework
- Questionary 2.1.1 - Interactive prompts
- Rich 14.2.0 - Terminal formatting and panels

**LLM Providers:**
- langchain-openai 1.0.3 - OpenAI-compatible API (GLM-4.5-flash default)
- langchain-ollama 1.0.0 - Ollama local model support
- ollama 0.6.1 - Local model runtime

**Web & Parsing:**
- requests 2.32.5 - HTTP client
- beautifulsoup4 4.14.2 - HTML parsing
- google-search-results 2.4.2 - Google search API

**Data & Validation:**
- Pydantic 2.12.4 - Data validation and settings
- patch-ng 1.19.0 - Patch file operations

**Infrastructure:**
- redis 5.0.4 - State checkpoint persistence, distributed rate limiting
- langgraph-cli 0.4.7 (inmem extras) - Local development server

**Observability:**
- structlog 25.5.0 - Structured logging
- prometheus-client 0.21.1 - Metrics collection

**Development:**
- pytest 9.0.1 - Testing framework

## Configuration

**Environment:**
- `.env` file support via `python-dotenv`
- Layered config: global (`~/.config/luminamind/.env`) → project `.env`
- `luminamind/config/env.py` handles loading and interactive configuration

**Key env vars:**
- `LLM_PROVIDER` - "openai" (default) or "ollama"
- `GLM_API_KEY`, `GLM_API_BASE` - OpenAI-compatible LLM credentials
- `OLLAMA_BASE_URL`, `OLLAMA_MODEL` - Ollama configuration
- `SERPER_API_KEY`, `GOOGLE_API_KEY`, `GOOGLE_CSE_ID` - Web search
- `CHECKPOINT_REDIS_URL`, `CHECKPOINT_DIR` - State persistence
- `LOG_LEVEL`, `LOG_FORMAT` - Logging configuration
- `METRICS_PORT`, `METRICS_DISABLED` - Prometheus metrics

**Build:**
- `pyproject.toml` - Poetry-based project configuration

## Platform Requirements

**Development:**
- Python 3.12+
- Poetry for dependency management
- Redis (optional, for distributed rate limits/checkpointing)

**Production:**
- Kubernetes-ready (per ARCHITECTURE.md)
- Redis cluster for state management
- S3 for checkpoint backups

---

*Stack analysis: 2026-04-27*