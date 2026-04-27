#!/usr/bin/env python3
"""
Script to verify API endpoints work correctly.
This script would be run after installing dependencies.
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_endpoint(endpoint, method="GET", data=None, headers=None):
    """Test an API endpoint and return response"""
    url = f"{BASE_URL}{endpoint}"
    
    if method == "GET":
        response = requests.get(url, headers=headers)
    elif method == "POST":
        response = requests.post(url, json=data, headers=headers)
    elif method == "PUT":
        response = requests.put(url, json=data, headers=headers)
    elif method == "DELETE":
        response = requests.delete(url, headers=headers)
    
    return response

def test_api():
    """Test all API endpoints"""
    print("=== Task Management API Verification ===\n")
    
    # Test 1: Root endpoint
    print("1. Testing root endpoint...")
    response = test_endpoint("/")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}\n")
    
    # Test 2: User registration
    print("2. Testing user registration...")
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "password123"
    }
    response = test_endpoint("/api/auth/register", method="POST", data=user_data)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print(f"   Response: {response.json()}")
    else:
        print(f"   Error: {response.text}\n")
    
    # Test 3: User login
    print("3. Testing user login...")
    login_data = {
        "username": "testuser",
        "password": "password123"
    }
    response = test_endpoint("/api/auth/login", method="POST", data=login_data)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        token = response.json()["access_token"]
        print(f"   Token received: {token[:20]}...")
        auth_headers = {"Authorization": f"Bearer {token}"}
        
        # Test 4: Get user profile
        print("4. Testing user profile...")
        response = test_endpoint("/api/users/me", method="GET", headers=auth_headers)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}\n")
        
        # Test 5: Create task
        print("5. Testing task creation...")
        task_data = {
            "title": "Test Task",
            "description": "This is a test task",
            "status": "pending"
        }
        response = test_endpoint("/api/tasks", method="POST", data=task_data, headers=auth_headers)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            task_id = response.json()["id"]
            print(f"   Task created with ID: {task_id}")
            
            # Test 6: Get tasks
            print("6. Testing get tasks...")
            response = test_endpoint("/api/tasks", method="GET", headers=auth_headers)
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.json()}\n")
            
            # Test 7: Get specific task
            print("7. Testing get specific task...")
            response = test_endpoint(f"/api/tasks/{task_id}", method="GET", headers=auth_headers)
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.json()}\n")
            
            # Test 8: Update task
            print("8. Testing task update...")
            update_data = {
                "title": "Updated Task",
                "description": "Updated description",
                "status": "in_progress"
            }
            response = test_endpoint(f"/api/tasks/{task_id}", method="PUT", data=update_data, headers=auth_headers)
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.json()}\n")
            
            # Test 9: Delete task
            print("9. Testing task deletion...")
            response = test_endpoint(f"/api/tasks/{task_id}", method="DELETE", headers=auth_headers)
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.json()}\n")
            
        else:
            print(f"   Error: {response.text}\n")
    else:
        print(f"   Error: {response.text}\n")

if __name__ == "__main__":
    print("Waiting for server to start...")
    time.sleep(2)
    test_api()