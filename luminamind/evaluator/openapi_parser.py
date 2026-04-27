"""OpenAPI spec parser for endpoint discovery."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class EndpointParameter:
    """API endpoint parameter."""
    name: str
    location: str  # query, path, header, cookie
    schema: dict
    required: bool = False


@dataclass
class EndpointRequest:
    """API endpoint request body."""
    content_type: str
    schema: dict


@dataclass
class EndpointResponse:
    """API endpoint response."""
    status_code: int
    content_type: str | None
    schema: dict | None


@dataclass
class DiscoveredEndpoint:
    """Discovered API endpoint."""
    path: str
    method: str
    operation_id: str | None = None
    summary: str | None = None
    parameters: list[EndpointParameter] = field(default_factory=list)
    request: EndpointRequest | None = None
    responses: list[EndpointResponse] = field(default_factory=list)


class OpenAPIParser:
    """Parses OpenAPI specs to discover API endpoints."""
    
    def __init__(self, spec: dict | Path | str):
        """Initialize parser.
        
        Args:
            spec: OpenAPI spec dict, file path, or JSON string
        """
        if isinstance(spec, dict):
            self.spec = spec
        elif isinstance(spec, (Path, str)):
            spec_path = Path(spec)
            if spec_path.suffix == ".json" or spec_path.suffix == ".yaml" or spec_path.suffix == ".yml":
                with open(spec_path) as f:
                    if spec_path.suffix in (".yaml", ".yml"):
                        import yaml
                        self.spec = yaml.safe_load(f)
                    else:
                        self.spec = json.load(f)
            else:
                # JSON string
                self.spec = json.loads(spec)
        else:
            raise ValueError(f"Invalid spec type: {type(spec)}")
        
        self._endpoints: list[DiscoveredEndpoint] | None = None
    
    def discover_endpoints(self) -> list[DiscoveredEndpoint]:
        """Discover all endpoints from OpenAPI spec."""
        if self._endpoints is not None:
            return self._endpoints
        
        self._endpoints = []
        paths = self.spec.get("paths", {})
        
        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method not in ("get", "post", "put", "patch", "delete", "head", "options"):
                    continue
                
                endpoint = self._parse_endpoint(path, method, operation, path_item)
                self._endpoints.append(endpoint)
        
        return self._endpoints
    
    def _parse_endpoint(self, path: str, method: str, operation: dict, path_item: dict) -> DiscoveredEndpoint:
        """Parse single endpoint."""
        # Extract parameters
        params = []
        
        # Path-level parameters
        for param in path_item.get("parameters", []):
            if param.get("in") == "path":
                params.append(EndpointParameter(
                    name=param["name"],
                    location="path",
                    schema=param.get("schema", {}),
                    required=True,
                ))
        
        # Operation-level parameters
        for param in operation.get("parameters", []):
            params.append(EndpointParameter(
                name=param["name"],
                location=param["in"],
                schema=param.get("schema", {}),
                required=param.get("required", False),
            ))
        
        # Extract request body
        request_body = operation.get("requestBody")
        request = None
        if request_body:
            content = request_body.get("content", {})
            for ct, ct_schema in content.items():
                request = EndpointRequest(
                    content_type=ct,
                    schema=ct_schema.get("schema", {}),
                )
                break
        
        # Extract responses
        responses = []
        for status_code, response_spec in operation.get("responses", {}).items():
            content = response_spec.get("content", {})
            ct = list(content.keys())[0] if content else None
            schema = content.get(ct, {}).get("schema") if ct else None
            responses.append(EndpointResponse(
                status_code=int(status_code),
                content_type=ct,
                schema=schema,
            ))
        
        return DiscoveredEndpoint(
            path=path,
            method=method.upper(),
            operation_id=operation.get("operationId"),
            summary=operation.get("summary"),
            parameters=params,
            request=request,
            responses=responses,
        )
    
    def generate_test_cases(self) -> list[dict[str, Any]]:
        """Generate test cases for discovered endpoints."""
        endpoints = self.discover_endpoints()
        test_cases = []
        
        for ep in endpoints:
            test_case = {
                "name": ep.operation_id or f"{ep.method}_{ep.path}".replace("/", "_"),
                "method": ep.method,
                "url": ep.path,
                "parameters": [
                    {"name": p.name, "in": p.location, "required": p.required}
                    for p in ep.parameters
                ],
            }
            test_cases.append(test_case)
        
        return test_cases


__all__ = ["OpenAPIParser", "DiscoveredEndpoint", "EndpointParameter", "EndpointRequest", "EndpointResponse"]