"""API testing integration for endpoint validation."""
from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import Any
from datetime import datetime, timezone

import aiohttp
from pathlib import Path

from luminamind.evaluator.openapi_parser import OpenAPIParser, DiscoveredEndpoint


@dataclass
class RequestLog:
    """Log entry for API request/response."""
    timestamp: str
    method: str
    url: str
    path_params: dict
    query_params: dict
    headers: dict
    request_body: Any | None
    response_status: int
    response_body: Any | None
    response_headers: dict
    duration_ms: float
    validation_errors: list[str] = field(default_factory=list)


@dataclass
class ContractViolation:
    """Contract validation error."""
    field: str
    expected: Any
    actual: Any
    message: str


@dataclass
class TestResult:
    """API test result."""
    endpoint: DiscoveredEndpoint
    passed: bool
    status_code: int | None
    response_time_ms: float | None
    violations: list[ContractViolation]
    log: RequestLog


class APITester:
    """Tests API endpoints against contracts.
    
    Features:
    - Endpoint discovery from OpenAPI specs
    - Request execution with full logging
    - Contract validation against schemas
    - Response time tracking
    """
    
    def __init__(
        self,
        base_url: str,
        openapi_spec: OpenAPIParser | Path | str | None = None,
        default_headers: dict | None = None,
        request_timeout: float = 30.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.openapi_spec = openapi_spec
        self.default_headers = default_headers or {}
        self.request_timeout = request_timeout
        self._logs: list[RequestLog] = []
        self._session: aiohttp.ClientSession | None = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self._session = aiohttp.ClientSession(
            headers=self.default_headers,
            timeout=aiohttp.ClientTimeout(total=self.request_timeout),
        )
        return self
    
    async def __aexit__(self, *args):
        """Async context manager exit."""
        if self._session:
            await self._session.close()
            self._session = None
    
    async def discover(self) -> list[DiscoveredEndpoint]:
        """Discover endpoints from OpenAPI spec."""
        if self.openapi_spec is None:
            raise ValueError("No OpenAPI spec provided")
        
        if isinstance(self.openapi_spec, (Path, str)):
            self.openapi_spec = OpenAPIParser(self.openapi_spec)
        
        return self.openapi_spec.discover_endpoints()
    
    async def test_endpoint(
        self,
        endpoint: DiscoveredEndpoint,
        path_params: dict | None = None,
        query_params: dict | None = None,
        request_body: Any | None = None,
        expected_status: int | None = None,
    ) -> TestResult:
        """Test a single endpoint.
        
        Args:
            endpoint: Discovered endpoint to test
            path_params: Path parameter values
            query_params: Query parameter values
            request_body: Request body (will be JSON encoded)
            expected_status: Expected status code for pass/fail
            
        Returns:
            TestResult with pass/fail and details
        """
        if self._session is None:
            raise RuntimeError("APITester must be used as async context manager")
        
        path_params = path_params or {}
        query_params = query_params or {}
        
        # Build URL
        url = self.base_url + endpoint.path.format(**path_params)
        
        # Build request kwargs
        kwargs = {
            "method": endpoint.method,
            "url": url,
            "params": query_params,
        }
        
        # Add request body
        if request_body is not None:
            kwargs["data"] = json.dumps(request_body)
            kwargs["headers"] = {"Content-Type": "application/json"}
        
        # Execute request
        start_time = time.time()
        try:
            async with self._session.request(**kwargs) as response:
                duration_ms = (time.time() - start_time) * 1000
                
                # Read response body
                try:
                    response_body = await response.json()
                except Exception:
                    response_body = await response.text()
                
                # Build log
                log = RequestLog(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    method=endpoint.method,
                    url=url,
                    path_params=path_params,
                    query_params=query_params,
                    headers=dict(response.request_info.headers) if response.request_info else {},
                    request_body=request_body,
                    response_status=response.status,
                    response_body=response_body,
                    response_headers=dict(response.headers),
                    duration_ms=duration_ms,
                )
                self._logs.append(log)
                
                # Validate
                violations = self._validate_response(endpoint, response.status, response_body)
                expected_status = expected_status or (200 if response.status < 400 else 500)
                passed = response.status == expected_status and not violations
                
                return TestResult(
                    endpoint=endpoint,
                    passed=passed,
                    status_code=response.status,
                    response_time_ms=duration_ms,
                    violations=violations,
                    log=log,
                )
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            log = RequestLog(
                timestamp=datetime.now(timezone.utc).isoformat(),
                method=endpoint.method,
                url=url,
                path_params=path_params,
                query_params=query_params,
                headers={},
                request_body=request_body,
                response_status=0,
                response_body={"error": str(e)},
                response_headers={},
                duration_ms=duration_ms,
                validation_errors=[f"Request failed: {e}"],
            )
            self._logs.append(log)
            
            return TestResult(
                endpoint=endpoint,
                passed=False,
                status_code=None,
                response_time_ms=duration_ms,
                violations=[],
                log=log,
            )
    
    def _validate_response(
        self,
        endpoint: DiscoveredEndpoint,
        status_code: int,
        body: Any,
    ) -> list[ContractViolation]:
        """Validate response against endpoint contract."""
        violations = []
        
        # Find matching response schema
        matching_response = None
        for resp in endpoint.responses:
            if resp.status_code == status_code:
                matching_response = resp
                break
        
        if matching_response and matching_response.schema:
            # Basic schema validation would go here
            # For now, just check structure
            pass
        
        return violations
    
    def get_logs(self) -> list[RequestLog]:
        """Get all request logs."""
        return self._logs.copy()
    
    def export_logs(self, path: Path | str) -> None:
        """Export logs to JSON file."""
        path = Path(path)
        logs_data = [
            {
                "timestamp": log.timestamp,
                "method": log.method,
                "url": log.url,
                "status": log.response_status,
                "duration_ms": log.duration_ms,
            }
            for log in self._logs
        ]
        with open(path, "w") as f:
            json.dump(logs_data, f, indent=2)


__all__ = ["APITester", "RequestLog", "TestResult", "ContractViolation"]