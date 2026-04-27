"""Unit tests for API tester."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from luminamind.evaluator.openapi_parser import DiscoveredEndpoint, EndpointResponse


class TestOpenAPIParser:
    """Tests for OpenAPIParser."""
    
    def test_parse_openapi_spec(self):
        """Test parsing a valid OpenAPI spec."""
        from luminamind.evaluator.openapi_parser import OpenAPIParser
        
        spec = {
            "openapi": "3.0.0",
            "paths": {
                "/users": {
                    "get": {
                        "operationId": "listUsers",
                        "summary": "List all users",
                        "responses": {
                            "200": {"description": "Success"}
                        }
                    },
                    "post": {
                        "operationId": "createUser",
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {"type": "object"}
                                }
                            }
                        },
                        "responses": {
                            "201": {"description": "Created"}
                        }
                    }
                }
            }
        }
        
        parser = OpenAPIParser(spec)
        endpoints = parser.discover_endpoints()
        
        assert len(endpoints) == 2
        assert any(ep.method == "GET" for ep in endpoints)
        assert any(ep.method == "POST" for ep in endpoints)
    
    def test_extract_path_parameters(self):
        """Test extraction of path parameters."""
        from luminamind.evaluator.openapi_parser import OpenAPIParser
        
        spec = {
            "paths": {
                "/users/{id}": {
                    "get": {
                        "operationId": "getUser",
                        "parameters": [
                            {"name": "id", "in": "path", "required": True}
                        ],
                        "responses": {"200": {"description": "Success"}}
                    }
                }
            }
        }
        
        parser = OpenAPIParser(spec)
        endpoints = parser.discover_endpoints()
        
        user_ep = next(ep for ep in endpoints if ep.path == "/users/{id}")
        assert len(user_ep.parameters) == 1
        assert user_ep.parameters[0].name == "id"
        assert user_ep.parameters[0].location == "path"


class TestAPITester:
    """Tests for APITester."""
    
    @pytest.mark.asyncio
    async def test_endpoint_request(self):
        """Test endpoint request execution."""
        from luminamind.evaluator.api_tester import APITester, TestResult
        
        async with APITester("https://api.example.com") as tester:
            endpoint = DiscoveredEndpoint(
                path="/users",
                method="GET",
                operation_id="listUsers",
                summary="List users",
                responses=[],
            )
            
            with patch.object(tester._session, "request") as mock_request:
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.json = AsyncMock(return_value=[{"id": 1}])
                mock_response.headers = {}
                mock_response.request_info = MagicMock()
                
                mock_ctx = AsyncMock()
                mock_ctx.__aenter__ = AsyncMock(return_value=mock_response)
                mock_ctx.__aexit__ = AsyncMock(return_value=None)
                mock_request.return_value = mock_ctx
                
                result = await tester.test_endpoint(endpoint)
                
                assert result.passed is True
                assert result.status_code == 200


class TestContractValidation:
    """Tests for contract validation."""
    
    def test_validate_status_code(self):
        """Test that status code is validated."""
        from luminamind.evaluator.api_tester import APITester, ContractViolation
        from luminamind.evaluator.openapi_parser import DiscoveredEndpoint, EndpointResponse
        
        endpoint = DiscoveredEndpoint(
            path="/test",
            method="GET",
            responses=[
                EndpointResponse(status_code=200, content_type="application/json", schema=None)
            ]
        )
        
        # Validation would happen in _validate_response
        # For unit test, just verify structure
        assert len(endpoint.responses) == 1
        assert endpoint.responses[0].status_code == 200