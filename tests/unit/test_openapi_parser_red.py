"""Tests for OpenAPIParser - RED phase."""
import pytest
from luminamind.evaluator.openapi_parser import (
    OpenAPIParser,
    DiscoveredEndpoint,
    EndpointParameter,
    EndpointRequest,
    EndpointResponse,
)


class TestOpenAPIParserRed:
    """RED phase: These tests should FAIL until OpenAPIParser is implemented."""

    def test_parse_valid_openapi_30_spec(self):
        """Test: Parse valid OpenAPI 3.0 spec."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "operationId": "listUsers",
                        "summary": "List all users",
                        "responses": {"200": {"description": "Success"}},
                    }
                }
            },
        }
        parser = OpenAPIParser(spec)
        endpoints = parser.discover_endpoints()
        # Should discover at least the /users GET endpoint
        assert len(endpoints) >= 1

    def test_extract_endpoints_with_http_methods(self):
        """Test: Extract endpoints with HTTP methods."""
        spec = {
            "paths": {
                "/users": {
                    "get": {"operationId": "listUsers", "responses": {"200": {"description": "Success"}}},
                    "post": {"operationId": "createUser", "responses": {"201": {"description": "Created"}}},
                },
                "/users/{id}": {
                    "get": {"operationId": "getUser", "responses": {"200": {"description": "Success"}}},
                    "put": {"operationId": "updateUser", "responses": {"200": {"description": "Updated"}}},
                    "delete": {"operationId": "deleteUser", "responses": {"204": {"description": "Deleted"}}},
                },
            }
        }
        parser = OpenAPIParser(spec)
        endpoints = parser.discover_endpoints()
        
        # Should have 5 endpoints total
        assert len(endpoints) == 5
        
        # Check HTTP methods are extracted correctly
        methods = [ep.method for ep in endpoints]
        assert "GET" in methods
        assert "POST" in methods
        assert "PUT" in methods
        assert "DELETE" in methods

    def test_extract_request_response_schemas(self):
        """Test: Extract request/response schemas."""
        spec = {
            "paths": {
                "/users": {
                    "post": {
                        "operationId": "createUser",
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {"type": "object", "properties": {"name": {"type": "string"}}}
                                }
                            }
                        },
                        "responses": {
                            "201": {
                                "content": {
                                    "application/json": {
                                        "schema": {"type": "object", "properties": {"id": {"type": "integer"}, "name": {"type": "string"}}}
                                    }
                                }
                            }
                        },
                    }
                }
            }
        }
        parser = OpenAPIParser(spec)
        endpoints = parser.discover_endpoints()
        
        user_ep = next(ep for ep in endpoints if ep.method == "POST")
        
        # Check request schema
        assert user_ep.request is not None
        assert user_ep.request.content_type == "application/json"
        assert user_ep.request.schema is not None
        
        # Check response schema
        assert len(user_ep.responses) == 1
        assert user_ep.responses[0].status_code == 201
        assert user_ep.responses[0].content_type == "application/json"
        assert user_ep.responses[0].schema is not None

    def test_handle_missing_optional_fields(self):
        """Test: Handle missing optional fields gracefully."""
        spec = {
            "paths": {
                "/simple": {
                    "get": {
                        # No operationId, no summary, no parameters, no requestBody
                        "responses": {"200": {"description": "Success"}}
                    }
                }
            }
        }
        parser = OpenAPIParser(spec)
        endpoints = parser.discover_endpoints()
        
        assert len(endpoints) == 1
        ep = endpoints[0]
        
        # Optional fields should be None or empty
        assert ep.operation_id is None
        assert ep.summary is None
        assert ep.parameters == []
        assert ep.request is None

    def test_discover_endpoints_returns_list(self):
        """Test: discover_endpoints returns a list of DiscoveredEndpoint."""
        parser = OpenAPIParser({"paths": {}})
        result = parser.discover_endpoints()
        assert isinstance(result, list)
        assert all(isinstance(ep, DiscoveredEndpoint) for ep in result)


class TestEndpointParameter:
    """Tests for EndpointParameter dataclass."""

    def test_create_parameter(self):
        """Test creating an EndpointParameter."""
        param = EndpointParameter(
            name="user_id",
            location="path",
            schema={"type": "string"},
            required=True
        )
        assert param.name == "user_id"
        assert param.location == "path"
        assert param.schema == {"type": "string"}
        assert param.required is True


class TestDiscoveredEndpoint:
    """Tests for DiscoveredEndpoint dataclass."""

    def test_create_endpoint(self):
        """Test creating a DiscoveredEndpoint."""
        endpoint = DiscoveredEndpoint(
            path="/users/{id}",
            method="GET",
            operation_id="getUser",
            summary="Get a user"
        )
        assert endpoint.path == "/users/{id}"
        assert endpoint.method == "GET"
        assert endpoint.operation_id == "getUser"
        assert endpoint.summary == "Get a user"