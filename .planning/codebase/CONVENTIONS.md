# Coding Conventions

**Analysis Date:** 2026-04-27

## Naming Patterns

**Files:**
- Python modules: `lowercase_with_underscores.py`
- Test files: `test_<subject>.py` or `<feature>_test.py`

**Functions:**
- `lowercase_with_underscores` for regular functions
- `PascalCase` for classes and decorator-returned tools

**Variables:**
- `lowercase_with_underscores` for locals/params
- `UPPER_SNAKE_CASE` for module-level constants

**Types:**
- Pydantic models: `PascalCase` ending in `Input` or `Config` (e.g., `ShellInput`)
- Dataclasses: `PascalCase`

## Code Style

**Formatting:**
- Tool: Not explicitly configured (no pyproject.toml ruff/black config visible)
- Manual formatting follows PEP 8

**Linting:**
- Tool: Not explicitly configured
- Manual review follows Python conventions

## Import Organization

**Order:**
1. Standard library (`os`, `sys`, `subprocess`, `json`)
2. Third-party (`langchain`, `pydantic`, `requests`)
3. Local application (`luminamind`)

**Pattern:**
```python
from __future__ import annotations  # Optional future imports

import os
import subprocess
from typing import Optional

from langchain.tools import tool
from pydantic import BaseModel, validator

from .config.checkpointer import create_checkpointer
from .py_tools.registry import PY_TOOL_REGISTRY
```

## Error Handling

**Tool Errors:**
- Return `{"error": True, "message": "...", ...}` dict structure
- Never raise exceptions from tool execution

**Validation Errors:**
- Pydantic `ValidationError` caught and returned as `{"error": True, "message": exc.errors()}`

**Rate Limit Errors:**
- Raise `RateLimitError` exception
- Caught by caller and returned as error dict

**HTTP Errors:**
- `requests.HTTPError` caught, detail extracted, returned as error

## Logging

**Framework:** structlog

**Pattern:**
```python
import structlog

logger = structlog.get_logger()

# Usage
logger.info("action", key="value")
logger.error("failed", error=exc)
```

**Configuration:** `luminamind/observability/logging.py:setup_logging()`

## Comments

**When to Comment:**
- Complex business logic
- Non-obvious workarounds
- TODO items for future work

**TSDoc/JSDoc:**
- Not used; standard Python docstrings

**Example:**
```python
def create_checkpointer() -> MemorySaver:
    """Factory mirroring original JS logic."""
```

## Function Design

**Size:** Keep functions focused; one responsibility per function

**Parameters:**
- Use type hints for all parameters
- Use `Optional[T]` for nullable parameters
- Max ~5 parameters; use dataclass for complex configs

**Return Values:**
- Tools return `dict` with `{"error": bool, ...}` structure
- Regular functions return typed values or raise exceptions

## Module Design

**Exports:**
- Use `__all__` to define public API
- Example: `__all__ = ["PY_TOOL_REGISTRY"]` in `registry.py`

**Barrel Files:**
- `__init__.py` files expose package-level imports
- `py_tools/__init__.py` re-exports `PY_TOOL_REGISTRY`

---

*Convention analysis: 2026-04-27*