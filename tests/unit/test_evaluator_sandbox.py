"""Unit tests for EvaluatorSandbox.

Tests cover:
- Sandbox isolation and cleanup
- Playwright MCP bridge structure
- API testing integration
- DB verification integration

Per GE-07, GE-08 requirements.
"""
import pytest
import tempfile
import shutil
from pathlib import Path

from luminamind.evaluator.sandbox import EvaluatorSandbox, SandboxConfig, SandboxResult
from luminamind.evaluator.mcp_bridge import (
    PlaywrightMCPBridge,
    PlaywrightResult,
    UserFlowStep,
    PerformanceMetrics,
)


class TestEvaluatorSandbox:
    """Tests for EvaluatorSandbox base class."""

    def test_sandbox_isolation(self):
        """Test sandbox creates isolated execution context."""
        config = SandboxConfig(max_execution_time=5.0)
        with EvaluatorSandbox(config) as sandbox:
            result = sandbox.evaluate_artifact({}, [])
            assert result is not None
            assert "_meta" in result

    def test_sandbox_context_manager(self):
        """Test sandbox context manager creates and cleans up temp dir."""
        temp_dirs = []

        with EvaluatorSandbox() as sandbox:
            temp_dirs.append(sandbox._temp_dir)
            assert sandbox._temp_dir is not None
            assert Path(sandbox._temp_dir).exists()

        # After exit, temp dir should be cleaned up
        assert not Path(temp_dirs[0]).exists()

    def test_sandbox_setup_teardown(self):
        """Test sandbox setup() and teardown() methods."""
        sandbox = EvaluatorSandbox()
        assert sandbox._temp_dir is None

        sandbox.setup()
        assert sandbox._temp_dir is not None
        assert Path(sandbox._temp_dir).exists()

        sandbox.teardown()
        assert sandbox._temp_dir is None

    def test_sandbox_resource_limits(self):
        """Test sandbox respects resource limits from config."""
        config = SandboxConfig(
            max_execution_time=1.0,
            max_memory_mb=256,
            network_isolated=True,
        )
        with EvaluatorSandbox(config) as sandbox:
            assert sandbox.config.max_execution_time == 1.0
            assert sandbox.config.max_memory_mb == 256
            assert sandbox.config.network_isolated is True

    def test_sandbox_get_workspace_path(self):
        """Test sandbox workspace path getter."""
        with EvaluatorSandbox() as sandbox:
            workspace = sandbox.get_workspace_path()
            assert workspace is not None
            assert "luminamind_sandbox_" in workspace


class TestSandboxTools:
    """Tests for sandbox tool execution."""

    def test_evaluate_artifact_with_empty_tools(self):
        """Test evaluate_artifact with no tools returns meta only."""
        with EvaluatorSandbox() as sandbox:
            result = sandbox.evaluate_artifact({"test": "artifact"}, [])
            assert "_meta" in result
            assert result["_meta"]["tools_run"] == []

    def test_evaluate_artifact_playwright(self):
        """Test evaluate_artifact dispatches to playwright tool."""
        with EvaluatorSandbox() as sandbox:
            result = sandbox.evaluate_artifact({}, ["playwright"])
            assert "playwright" in result
            assert result["playwright"]["status"] in ["initialized", "unavailable"]

    def test_evaluate_artifact_api_testing(self):
        """Test evaluate_artifact dispatches to api_testing tool."""
        with EvaluatorSandbox() as sandbox:
            result = sandbox.evaluate_artifact({"type": "api"}, ["api_testing"])
            assert "api_testing" in result

    def test_evaluate_artifact_db_verifier(self):
        """Test evaluate_artifact dispatches to db_verifier tool."""
        with EvaluatorSandbox() as sandbox:
            result = sandbox.evaluate_artifact({"type": "db"}, ["db_verifier"])
            assert "db_verifier" in result

    def test_evaluate_artifact_unknown_tool(self):
        """Test evaluate_artifact handles unknown tools gracefully."""
        with EvaluatorSandbox() as sandbox:
            result = sandbox.evaluate_artifact({}, ["unknown_tool"])
            assert "unknown_tool" in result
            assert "error" in result["unknown_tool"]

    def test_evaluate_artifact_multiple_tools(self):
        """Test evaluate_artifact with multiple tools."""
        with EvaluatorSandbox() as sandbox:
            result = sandbox.evaluate_artifact(
                {"openapi": "3.0", "paths": {}},
                ["playwright", "api_testing", "db_verifier"],
            )
            assert "playwright" in result
            assert "api_testing" in result
            assert "db_verifier" in result


class TestAPITesting:
    """Tests for API testing functionality."""

    def test_api_testing_structure(self):
        """Test API testing returns proper structure."""
        config = SandboxConfig()
        with EvaluatorSandbox(config) as sandbox:
            result = sandbox.evaluate_artifact(
                {"type": "api", "openapi": "3.0", "paths": {}},
                ["api_testing"],
            )
            assert "api_testing" in result
            api_result = result["api_testing"]
            assert "summary" in api_result

    def test_endpoint_discovery_openapi(self):
        """Test endpoint discovery from OpenAPI spec."""
        artifact = {
            "openapi": "3.0.0",
            "paths": {
                "/users": {
                    "get": {"summary": "List users"},
                    "post": {"summary": "Create user"},
                },
                "/users/{id}": {
                    "get": {"summary": "Get user"},
                    "put": {"summary": "Update user"},
                    "delete": {"summary": "Delete user"},
                },
            },
        }
        with EvaluatorSandbox() as sandbox:
            endpoints = sandbox._discover_endpoints(artifact)
            assert len(endpoints) == 5
            paths = [e["path"] for e in endpoints]
            assert "/users" in paths
            assert "/users/{id}" in paths

    def test_endpoint_discovery_direct(self):
        """Test endpoint discovery from direct endpoints list."""
        artifact = {
            "endpoints": [
                {"path": "/api/health", "method": "GET"},
                {"path": "/api/data", "method": "POST"},
            ]
        }
        with EvaluatorSandbox() as sandbox:
            endpoints = sandbox._discover_endpoints(artifact)
            assert len(endpoints) == 2


class TestDBVerification:
    """Tests for database state verification."""

    def test_db_verification_structure(self):
        """Test DB verification returns proper structure."""
        config = SandboxConfig()
        with EvaluatorSandbox(config) as sandbox:
            result = sandbox.evaluate_artifact(
                {"type": "db", "database": {"assertions": []}},
                ["db_verifier"],
            )
            assert "db_verifier" in result

    def test_db_verification_extract_assertions(self):
        """Test DB verification extracts assertions from artifact."""
        artifact = {
            "database": {
                "assertions": [
                    {"description": "users table exists", "expected": True},
                    {"description": "email column unique", "expected": True},
                ]
            }
        }
        with EvaluatorSandbox() as sandbox:
            assertions = sandbox._extract_assertions(artifact)
            assert len(assertions) == 2
            assert assertions[0]["description"] == "users table exists"


class TestPlaywrightMCPBridge:
    """Tests for Playwright MCP bridge."""

    def test_bridge_initialization(self):
        """Test PlaywrightMCPBridge initializes correctly."""
        bridge = PlaywrightMCPBridge()
        assert bridge is not None

    def test_bridge_with_endpoint(self):
        """Test PlaywrightMCPBridge with custom endpoint."""
        bridge = PlaywrightMCPBridge(mcp_endpoint="http://localhost:3000")
        assert bridge.mcp_endpoint == "http://localhost:3000"

    def test_bridge_session_management(self):
        """Test session start/end."""
        bridge = PlaywrightMCPBridge()
        assert not bridge.is_session_active()
        result = bridge.start_session()
        assert result is True
        assert bridge.is_session_active()
        bridge.end_session()
        assert not bridge.is_session_active()

    def test_bridge_capture_screenshot_method_exists(self):
        """Test screenshot capture method exists."""
        bridge = PlaywrightMCPBridge()
        assert hasattr(bridge, "capture_screenshot")

    def test_bridge_simulate_user_flow_method_exists(self):
        """Test user flow simulation method exists."""
        bridge = PlaywrightMCPBridge()
        assert hasattr(bridge, "simulate_user_flow")

    def test_bridge_detect_console_errors_method_exists(self):
        """Test console error detection method exists."""
        bridge = PlaywrightMCPBridge()
        assert hasattr(bridge, "detect_console_errors")

    def test_bridge_measure_performance_method_exists(self):
        """Test performance measurement method exists."""
        bridge = PlaywrightMCPBridge()
        assert hasattr(bridge, "measure_performance")

    def test_simulate_user_flow_returns_list(self):
        """Test simulate_user_flow returns list of results."""
        bridge = PlaywrightMCPBridge()
        steps = [
            {"action": "navigate", "value": "/"},
            {"action": "click", "selector": "#btn"},
        ]
        results = bridge.simulate_user_flow("https://example.com", steps)
        assert isinstance(results, list)
        assert len(results) == 2

    def test_measure_performance_returns_metrics(self):
        """Test measure_performance returns proper structure."""
        bridge = PlaywrightMCPBridge()
        metrics = bridge.measure_performance("https://example.com")
        assert isinstance(metrics, dict)
        assert "lcp_ms" in metrics


class TestPlaywrightResult:
    """Tests for PlaywrightResult dataclass."""

    def test_playwright_result_creation(self):
        """Test PlaywrightResult can be created."""
        result = PlaywrightResult(
            screenshot_path="/tmp/screenshot.png",
            console_errors=["Error 1", "Error 2"],
            success=True,
        )
        assert result.screenshot_path == "/tmp/screenshot.png"
        assert len(result.console_errors) == 2
        assert result.success is True


class TestSandboxResult:
    """Tests for SandboxResult dataclass."""

    def test_sandbox_result_creation(self):
        """Test SandboxResult can be created."""
        result = SandboxResult(
            success=True,
            results={"tool": "result"},
            execution_time_ms=100.5,
        )
        assert result.success is True
        assert result.results["tool"] == "result"
        assert result.execution_time_ms == 100.5

    def test_sandbox_result_with_errors(self):
        """Test SandboxResult with errors."""
        result = SandboxResult(
            success=False,
            results={},
            errors=["Error 1", "Error 2"],
        )
        assert result.success is False
        assert len(result.errors) == 2