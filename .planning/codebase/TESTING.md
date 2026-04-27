# Testing Patterns

**Analysis Date:** 2026-04-27

## Test Framework

**Runner:**
- pytest 9.0.1
- Config: No `pytest.ini` or `pyproject.toml` config found

**Assertion Library:**
- pytest built-in `assert`

**Run Commands:**
```bash
pytest                    # Run all tests
pytest tests/unit/        # Run unit tests only
pytest tests/integration/ # Run integration tests only
pytest -v                 # Verbose output
pytest --asyncio-mode=auto  # Async test support
```

## Test File Organization

**Location:**
- Tests co-located in `tests/` directory at project root
- Unit tests: `tests/unit/`
- Integration tests: `tests/integration/`

**Naming:**
- `test_<module_name>.py` for unit tests
- `<feature>_test.py` for integration tests

**Structure:**
```
tests/
├── unit/
│   ├── test_shell.py
│   ├── test_weather.py
│   ├── test_web_search.py
│   └── ...
└── integration/
    ├── __init__.py
    └── test_tool_execution.py
```

## Test Structure

**Unit Tests (test_shell.py):**
```python
class TestShell:
    """Test cases for the shell tool."""

    @patch('module.subprocess.run')
    def test_shell_success(self, mock_run):
        """Test successful shell command execution."""
        result = shell.invoke({"command": "echo 'hello world'"})
        assert result["error"] is False
```

**Integration Tests (test_tool_execution.py):**
```python
@pytest.fixture
def anyio_backend():
    return "asyncio"

async def test_file_write_completes():
    """Test that write_file tool completes without cancellation."""
    config = {"configurable": {"thread_id": "test-write-123"}}
    messages = [HumanMessage(content="...")]

    async for chunk in app.astream({"messages": messages}, config):
        final_state = chunk

    assert test_file.exists()
```

## Mocking

**Framework:** unittest.mock (patch, Mock)

**Patterns:**
```python
@patch('luminamind.py_tools.shell.subprocess.run')
def test_shell_success(self, mock_run):
    mock_run.return_value = Mock(returncode=0, stdout="output", stderr="")
    result = shell.invoke({"command": "echo hello"})
    assert result["error"] is False
```

**What to Mock:**
- External services (subprocess, HTTP clients, Redis)
- Time-dependent operations
- File system operations (in unit tests)

**What NOT to Mock:**
- Pydantic validation (test actual input)
- Simple logic without external dependencies

## Fixtures and Factories

**Test Fixtures:**
```python
@pytest.fixture
def anyio_backend():
    return "asyncio"
```

**Test Data:**
- Use `tempfile.TemporaryDirectory()` for file operations
- Use `pathlib.Path` for file paths

## Coverage

**Requirements:** None enforced

**View Coverage:** Not configured

## Test Types

**Unit Tests:**
- Individual tool/function testing
- Mock external dependencies
- Fast execution, no side effects
- Examples: `tests/unit/test_shell.py`, `tests/unit/test_weather.py`

**Integration Tests:**
- Full agent/tool execution flow
- Real async handling with `app.astream()`
- Thread ID-based state management
- Examples: `tests/integration/test_tool_execution.py`

**E2E Tests:** Not detected

## Common Patterns

**Async Testing:**
```python
@pytest.fixture
def anyio_backend():
    return "asyncio"

async def test_something():
    async for chunk in app.astream(input_data, config):
        # Process chunks
```

**Error Testing:**
```python
result = shell.invoke({"command": "invalid"})
assert result["error"] is True
assert "error message" in result["message"]
```

**Timeout Testing:**
```python
mock_run.side_effect = subprocess.TimeoutExpired(cmd="sleep", timeout=1)
result = shell.invoke({"command": "sleep 10", "timeout_ms": 1000})
assert "Command timed out" in result["message"]
```

---

*Testing analysis: 2026-04-27*