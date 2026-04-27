import pytest
from fastapi.testclient import TestClient

def test_root_endpoint(client):
    """Test the root endpoint"""
    response = client.get("/")
    
    assert response.status_code == 200
    assert "Task Management API is running" in response.json()["message"]

def test_cors_middleware(client):
    """Test that CORS middleware is enabled"""
    response = client.get("/")
    
    assert response.status_code == 200
    # CORS headers should be present
    assert "access-control-allow-origin" in response.headers

def test_api_health_check(client):
    """Test API health check"""
    response = client.get("/")
    
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["message"] == "Task Management API is running"