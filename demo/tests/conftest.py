import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from database import get_db, Base
from models import User, Task

# Test database configuration
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
Base.metadata.create_all(bind=engine)

# Override the get_db dependency
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="session")
def client():
    """Create test client"""
    with TestClient(app) as c:
        yield c

@pytest.fixture(scope="function")
def db():
    """Create a test database session"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture(scope="function")
def test_user(db):
    """Create a test user"""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password="hashedpassword123"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture(scope="function")
def test_user_password():
    """Return test user credentials"""
    return {"username": "testuser", "password": "password123"}

@pytest.fixture(scope="function")
def test_tasks(db, test_user):
    """Create test tasks for a user"""
    tasks = [
        Task(
            title="Test Task 1",
            description="Description 1",
            status="pending",
            user_id=test_user.id
        ),
        Task(
            title="Test Task 2",
            description="Description 2",
            status="in_progress",
            user_id=test_user.id
        ),
        Task(
            title="Test Task 3",
            description="Description 3",
            status="completed",
            user_id=test_user.id
        )
    ]
    db.add_all(tasks)
    db.commit()
    return tasks

@pytest.fixture(scope="function")
def auth_headers(client, test_user_password):
    """Get authentication headers for test user"""
    # Register user first
    client.post("/api/auth/register", json={
        "username": test_user_password["username"],
        "email": "test@example.com",
        "password": test_user_password["password"]
    })
    
    # Login and get token
    response = client.post("/api/auth/login", data=test_user_password)
    token = response.json()["access_token"]
    
    return {"Authorization": f"Bearer {token}"}