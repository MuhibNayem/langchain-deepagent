"""Tests for APITester - RED phase."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from luminamind.evaluator.openapi_parser import DiscoveredEndpoint, EndpointResponse


class TestAPITesterRed:
    """RED phase: These tests should FAIL until APITester is implemented."""

    @pytest.mark.asyncio
    async def test_execute_get_request_successfully(self):
        """Test: Execute GET request successfully."""
        from luminamind.evaluator.api_tester import APITester, TestResult
        
        async with APITester("https://api.example.com") as tester:
            endpoint = DiscoveredEndpoint(
                path="/users",
                method="GET",
                operation_id="listUsers",
                summary="List users",
                responses=[EndpointResponse(status_code=200, content_type="application/json", schema=None)],
            )
            
            result = await tester.test_endpoint(endpoint)
            
            assert result is not None
            assert isinstance(result, TestResult)
            assert result.endpoint == endpoint

    @pytest.mark.asyncio
    async def test_execute_post_with_json_body(self):
        """Test: Execute POST with JSON body."""
        from luminamind.evaluator.api_tester import APITester, TestResult
        
        async with APITester("https://api.example.com") as tester:
            endpoint = DiscoveredEndpoint(
                path="/users",
                method="POST",
                operation_id="createUser",
                summary="Create a user",
                responses=[EndpointResponse(status_code=201, content_type="application/json", schema=None)],
            )
            
            request_body = {"name": "John Doe", "email": "john@example.com"}
            result = await tester.test_endpoint(endpoint, request_body=request_body)
            
            assert result is not None
            assert isinstance(result, TestResult)

    @pytest.mark.asyncio
    async def test_validate_response_against_contract_schema(self):
        """Test: Validate response against contract schema."""
        from luminamind.evaluator.api_tester import APITester, TestResult
        
        async with APITester("https://api.example.com") as tester:
            endpoint = DiscoveredEndpoint(
                path="/users",
                method="GET",
                responses=[
                    EndpointResponse(
                        status_code=200,
                        content_type="application/json",
                        schema={"type": "array"}
                    )
                ],
            )
            
            result = await tester.test_endpoint(endpoint)
            
            assert result is not None
            assert hasattr(result, 'violations')

    @pytest.mark.asyncio
    async def test_log_request_response_for_audit(self):
        """Test: Log request/response for audit."""
        from luminamind.evaluator.api_tester import APITester, RequestLog
        
        async with APITester("https://api.example.com") as tester:
            endpoint = DiscoveredEndpoint(
                path="/users",
                method="GET",
                responses=[],
            )
            
            await tester.test_endpoint(endpoint)
            
            logs = tester.get_logs()
            assert len(logs) == 1
            log = logs[0]
            assert isinstance(log, RequestLog)
            assert log.method == "GET"
            assert log.url == "https://api.example.com/users"


class TestContractValidation:
    """Tests for contract validation."""

    def test_contract_violation_dataclass(self):
        """Test ContractViolation dataclass structure."""
        from luminamind.evaluator.api_tester import ContractViolation
        
        violation = ContractViolation(
            field="email",
            expected="string",
            actual=123,
            message="Email must be a string"
        )
        
        assert violation.field == "email"
        assert violation.expected == "string"
        assert violation.actual == 123
        assert violation.message == "Email must be a string"

    def test_test_result_dataclass(self):
        """Test TestResult dataclass structure."""
        from luminamind.evaluator.api_tester import TestResult
        
        endpoint = DiscoveredEndpoint(path="/test", method="GET")
        log = MagicMock()
        
        result = TestResult(
            endpoint=endpoint,
            passed=True,
            status_code=200,
            response_time_ms=50.0,
            violations=[],
            log=log,
        )
        
        assert result.passed is True
        assert result.status_code == 200
        assert result.response_time_ms == 50.0
        assert result.violations == []

    def test_request_log_dataclass(self):
        """Test RequestLog dataclass structure."""
        from luminamind.evaluator.api_tester import RequestLog
        
        log = RequestLog(
            timestamp="2026-04-27T10:00:00Z",
            method="GET",
            url="https://api.example.com/users",
            path_params={},
            query_params={},
            headers={},
            request_body=None,
            response_status=200,
            response_body=[{"id": 1}],
            response_headers={"Content-Type": "application/json"},
            duration_ms=50.0,
        )
        
        assert log.method == "GET"
        assert log.response_status == 200
        assert log.response_body == [{"id": 1}]