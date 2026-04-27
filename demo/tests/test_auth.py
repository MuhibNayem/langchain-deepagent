import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from models import User
from auth import authenticate_user, get_password_hash, verify_password

def test_user_registration(client):
    """Test user registration endpoint"""
    response = client.post("/api/auth/register", json={
        "username": "newuser",
        "email": "newuser@example.com",
        "password": "password123"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "newuser"
    assert data["email"] == "newuser@example.com"
    assert "id" in data
    assert "created_at" in data

def test_user_registration_duplicate_username(client, db):
    """Test user registration with duplicate username"""
    # Register first user
    client.post("/api/auth/register", json={
        "username": "duplicate",
        "email": "user1@example.com",
        "password": "password123"
    })
    
    # Try to register with same username
    response = client.post("/api/auth/register", json={
        "username": "duplicate",
        "email": "user2@example.com",
        "password": "password456"
    })
    
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]

def test_user_registration_duplicate_email(client, db):
    """Test user registration with duplicate email"""
    # Register first user
    client.post("/api/auth/register", json={
        "username": "user1",
        "email": "duplicate@example.com",
        "password": "password123"
    })
    
    # Try to register with same email
    response = client.post("/api/auth/register", json={
        "username": "user2",
        "email": "duplicate@example.com",
        "password": "password456"
    })
    
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]

def test_user_login(client, test_user_password):
    """Test user login endpoint"""
    # Register user first
    client.post("/api/auth/register", json={
        "username": test_user_password["username"],
        "email": "login@example.com",
        "password": test_user_password["password"]
    })
    
    # Login
    response = client.post("/api/auth/login", data=test_user_password)
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_user_login_invalid_credentials(client, test_user_password):
    """Test user login with invalid credentials"""
    # Register user first
    client.post("/api/auth/register", json={
        "username": test_user_password["username"],
        "email": "login@example.com",
        "password": test_user_password["password"]
    })
    
    # Login with wrong password
    response = client.post("/api/auth/login", data={
        "username": test_user_password["username"],
        "password": "wrongpassword"
    })
    
    assert response.status_code == 401
    assert "Incorrect username or password" in response.json()["detail"]

def test_get_current_user(client, auth_headers):
    """Test getting current user profile"""
    response = client.get("/api/users/me", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert "username" in data
    assert "email" in data
    assert "id" in data

def test_get_current_user_unauthorized(client):
    """Test getting current user without authentication"""
    response = client.get("/api/users/me")
    
    assert response.status_code == 401

def test_password_hashing():
    """Test password hashing and verification"""
    password = "testpassword123"
    hashed = get_password_hash(password)
    
    # Hash should not be the same as plain password
    assert hashed != password
    
    # Verification should work
    assert verify_password(password, hashed) == True
    
    # Wrong password should not verify
    assert verify_password("wrongpassword", hashed) == False

def test_authenticate_user(db: Session):
    """Test user authentication function"""
    # Create a test user
    user = User(
        username="authuser",
        email="auth@example.com",
        hashed_password=get_password_hash("password123")
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Test successful authentication
    authenticated_user = authenticate_user(db, "authuser", "password123")
    assert authenticated_user is not None
    assert authenticated_user.username == "authuser"
    
    # Test failed authentication
    failed_user = authenticate_user(db, "authuser", "wrongpassword")
    assert failed_user is None
    
    # Test non-existent user
    non_existent = authenticate_user(db, "nonexistent", "password123")
    assert non_existent is None