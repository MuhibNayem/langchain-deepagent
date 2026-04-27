import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from models import Task, TaskStatus

def test_create_task(client, auth_headers):
    """Test creating a new task"""
    response = client.post("/api/tasks", json={
        "title": "Test Task",
        "description": "This is a test task",
        "status": "pending"
    }, headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Task"
    assert data["description"] == "This is a test task"
    assert data["status"] == "pending"
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data
    assert "user_id" in data

def test_create_task_without_auth(client):
    """Test creating a task without authentication"""
    response = client.post("/api/tasks", json={
        "title": "Test Task",
        "description": "This should fail"
    })
    
    assert response.status_code == 401

def test_create_task_validation_error(client, auth_headers):
    """Test task creation with invalid data"""
    # Missing title
    response = client.post("/api/tasks", json={
        "description": "This should fail"
    }, headers=auth_headers)
    
    assert response.status_code == 422

def test_get_tasks(client, auth_headers, test_tasks):
    """Test getting tasks with pagination"""
    response = client.get("/api/tasks", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert "tasks" in data
    assert "pagination" in data
    assert len(data["tasks"]) == 3
    assert data["pagination"]["page"] == 1
    assert data["pagination"]["size"] == 10
    assert data["pagination"]["total"] == 3
    assert data["pagination"]["total_pages"] == 1

def test_get_tasks_pagination(client, auth_headers, test_tasks):
    """Test task pagination"""
    # Test page 1 with size 2
    response = client.get("/api/tasks?page=1&size=2", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["tasks"]) == 2
    assert data["pagination"]["page"] == 1
    assert data["pagination"]["size"] == 2
    assert data["pagination"]["total"] == 3
    assert data["pagination"]["total_pages"] == 2

def test_get_tasks_filter_by_status(client, auth_headers, test_tasks):
    """Test filtering tasks by status"""
    # Filter by pending tasks
    response = client.get("/api/tasks?status=pending", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["tasks"]) == 1
    assert data["tasks"][0]["status"] == "pending"

def test_get_task_by_id(client, auth_headers, test_tasks):
    """Test getting a specific task by ID"""
    task_id = test_tasks[0].id
    response = client.get(f"/api/tasks/{task_id}", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == task_id
    assert data["title"] == "Test Task 1"

def test_get_nonexistent_task(client, auth_headers):
    """Test getting a non-existent task"""
    response = client.get("/api/tasks/999", headers=auth_headers)
    
    assert response.status_code == 404
    assert "Task not found" in response.json()["detail"]

def test_update_task(client, auth_headers, test_tasks):
    """Test updating a task"""
    task_id = test_tasks[0].id
    response = client.put(f"/api/tasks/{task_id}", json={
        "title": "Updated Task Title",
        "description": "Updated description",
        "status": "in_progress"
    }, headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Task Title"
    assert data["description"] == "Updated description"
    assert data["status"] == "in_progress"

def test_update_nonexistent_task(client, auth_headers):
    """Test updating a non-existent task"""
    response = client.put("/api/tasks/999", json={
        "title": "Updated Task",
        "status": "completed"
    }, headers=auth_headers)
    
    assert response.status_code == 404
    assert "Task not found" in response.json()["detail"]

def test_delete_task(client, auth_headers, test_tasks):
    """Test deleting a task"""
    task_id = test_tasks[0].id
    response = client.delete(f"/api/tasks/{task_id}", headers=auth_headers)
    
    assert response.status_code == 200
    assert "Task deleted successfully" in response.json()["detail"]
    
    # Verify task is deleted
    get_response = client.get(f"/api/tasks/{task_id}", headers=auth_headers)
    assert get_response.status_code == 404

def test_delete_nonexistent_task(client, auth_headers):
    """Test deleting a non-existent task"""
    response = client.delete("/api/tasks/999", headers=auth_headers)
    
    assert response.status_code == 404
    assert "Task not found" in response.json()["detail"]

def test_task_status_enum_values():
    """Test that TaskStatus enum has correct values"""
    assert TaskStatus.pending == "pending"
    assert TaskStatus.in_progress == "in_progress"
    assert TaskStatus.completed == "completed"

def test_task_creation_with_default_status(client, auth_headers):
    """Test task creation with default status"""
    response = client.post("/api/tasks", json={
        "title": "Task with default status",
        "description": "Should be pending by default"
    }, headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "pending"