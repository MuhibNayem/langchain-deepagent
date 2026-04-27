# External Integrations

**Analysis Date:** 2026-04-27

## APIs & External Services

**LLM Providers:**
- **GLM-4.5-Flash** (default) - OpenAI-compatible API via `ChatOpenAI`
  - Auth: `GLM_API_KEY` env var
  - Base URL: `https://api.z.ai/api/paas/v4/`
  - Config: `luminamind/deep_agent.py:get_llm()`
- **Ollama** (local models) - via `ChatOllama`
  - Auth: `OLLAMA_API_KEY` (optional)
  - Base URL: `OLLAMA_BASE_URL` (default `http://localhost:11434`)
  - Models: `OLLAMA_MODEL` (default `qwen3:latest`)

**Web Search Providers (fallback chain):**
- **Google Custom Search Engine** - `_search_google_cse()` in `luminamind/py_tools/web_search.py`
  - Auth: `GOOGLE_API_KEY`, `GOOGLE_CSE_ID`
  - Endpoint: `https://customsearch.googleapis.com/customsearch/v1`
- **Serper.dev** - `_search_serper()` in `luminamind/py_tools/web_search.py`
  - Auth: `SERPER_API_KEY`
  - Endpoint: `https://google.serper.dev/search`
- **Ollama Web Search** - `search_ollama()` fallback
  - Uses `ollama.web_search()` function

## Data Storage

**State Management:**
- **Redis** (primary for production)
  - Connection: `CHECKPOINT_REDIS_URL`
  - Used by: `RedisBackedMemorySaver` in `luminamind/config/checkpointer.py`
  - Purpose: Agent conversation checkpoint persistence
- **In-memory** (development fallback)
  - `MemorySaver` from LangGraph
  - `FileBackedMemorySaver` for local file-based checkpointing

**Rate Limiting:**
- **Redis** (distributed rate limits) - `luminamind/utils/rate_limit.py`
  - Connection: `RATE_LIMIT_REDIS_URL`
- **In-memory** (fallback)

## Authentication & Identity

**Auth Provider:**
- API keys via environment variables (not a dedicated auth service)
- Session tracking via UUID (`langsmith.uuid7`)

## Monitoring & Observability

**Metrics:**
- **Prometheus Client** - `luminamind/observability/metrics.py`
  - Port: `METRICS_PORT` (default 9090)
  - Counters: `luminamind_tool_invocations_total`, `luminamind_tool_errors_total`
  - Histogram: `luminamind_tool_duration_seconds`

**Logging:**
- **Structlog** - `luminamind/observability/logging.py`
  - Formats: JSON (production) or Console (development)
  - Config: `LOG_LEVEL`, `LOG_FORMAT`

## CI/CD & Deployment

**Container:**
- `Dockerfile` present at project root

**Platform:**
- Kubernetes-ready (per ARCHITECTURE.md docs)
- LangGraph platform integration via env vars:
  - `LANGGRAPH_API_BASE`, `LANGGRAPH_API_KEY`
  - `LANGGRAPH_PROJECT_ID`, `LANGGRAPH_CLOUD`
  - `LANGGRAPH_PLATFORM`

## Environment Configuration

**Required env vars:**
- `GLM_API_KEY` - Required for default OpenAI-compatible provider
- `SERPER_API_KEY` or `GOOGLE_API_KEY` + `GOOGLE_CSE_ID` - For web search

**Optional env vars:**
- `LLM_PROVIDER` - "openai" or "ollama"
- `OLLAMA_BASE_URL`, `OLLAMA_MODEL`
- `CHECKPOINT_REDIS_URL` - Redis for state persistence
- `RATE_LIMIT_REDIS_URL` - Redis for distributed rate limits

**Secrets location:**
- Global config: `~/.config/luminamind/.env`
- Project: `.env` (not committed)
- Environment takes priority over file-based config

---

*Integration audit: 2026-04-27*