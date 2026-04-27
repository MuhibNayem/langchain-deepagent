# Task Management API Specification

## Overview
This document outlines the specifications for a REST API for a task management system built with FastAPI.

## Technology Stack
- **Framework**: FastAPI
- **Authentication**: JWT (JSON Web Tokens)
- **Database**: SQLAlchemy with SQLite (for simplicity)
- **Validation**: Pydantic
- **Testing**: pytest
- **Documentation**: OpenAPI/Swagger

## API Endpoints

### Authentication Endpoints

#### 1. Register User
- **POST** `/api/auth/register`
- **Description**: Create a new user account
- **Request Body**:
  ```json
  {
    "username": "string (min: 3, max: 50)",
    "email": "string (valid email format)",
    "password": "string (min: 8)"
  }
  ```
- **Response**:
  ```json
  {
    "id": "integer",
    "username": "string",
    "email": "string",
    "created_at": "datetime (ISO format)"
  }
  ```
- **Error Codes**: 400 (validation errors), 409 (username/email already exists)

#### 2. Login
- **POST** `/api/auth/login`
- **Description**: Authenticate user and return JWT token
- **Request Body**:
  ```json
  {
    "username": "string",
    "password": "string"
  }
  ```
- **Response**:
  ```json
  {
    "access_token": "string (JWT token)",
    "token_type": "Bearer"
  }
  ```
- **Error Codes**: 401 (invalid credentials), 422 (validation errors)

### User Endpoints

#### 3. Get Current User Profile
- **GET** `/api/users/me`
- **Description**: Get the profile of the currently authenticated user
- **Headers**: `Authorization: Bearer <token>`
- **Response**:
  ```json
  {
    "id": "integer",
    "username": "string",
    "email": "string",
    "created_at": "datetime (ISO format)"
  }
  ```
- **Error Codes**: 401 (unauthorized)

### Task Endpoints

#### 4. Create Task
- **POST** `/api/tasks`
- **Description**: Create a new task for the authenticated user
- **Headers**: `Authorization: Bearer <token>`
- **Request Body**:
  ```json
  {
    "title": "string (min: 1, max: 200)",
    "description": "string (optional, max: 1000)",
    "status": "pending | in_progress | completed (default: pending)"
  }
  ```
- **Response**:
  ```json
  {
    "id": "integer",
    "title": "string",
    "description": "string | null",
    "status": "string",
    "created_at": "datetime (ISO format)",
    "updated_at": "datetime (ISO format)",
    "user_id": "integer"
  }
  ```
- **Error Codes**: 400 (validation errors), 401 (unauthorized)

#### 5. Get Tasks (with Pagination)
- **GET** `/api/tasks`
- **Description**: Get tasks for the authenticated user with pagination
- **Headers**: `Authorization: Bearer <token>`
- **Query Parameters**:
  - `page`: integer (default: 1)
  - `size`: integer (default: 10, max: 100)
  - `status`: optional filter (pending, in_progress, completed)
- **Response**:
  ```json
  {
    "tasks": [
      {
        "id": "integer",
        "title": "string",
        "description": "string | null",
        "status": "string",
        "created_at": "datetime (ISO format)",
        "updated_at": "datetime (ISO format)",
        "user_id": "integer"
      }
    ],
    "pagination": {
      "page": "integer",
      "size": "integer",
      "total": "integer",
      "total_pages": "integer"
    }
  }
  ```
- **Error Codes**: 401 (unauthorized)

#### 6. Get Task by ID
- **GET** `/api/tasks/{task_id}`
- **Description**: Get a specific task by ID
- **Headers**: `Authorization: Bearer <token>`
- **Response**:
  ```json
  {
    "id": "integer",
    "title": "string",
    "description": "string | null",
    "status": "string",
    "created_at": "datetime (ISO format)",
    "updated_at": "datetime (ISO format)",
    "user_id": "integer"
  }
  ```
- **Error Codes**: 401 (unauthorized), 404 (task not found)

#### 7. Update Task
- **PUT** `/api/tasks/{task_id}`
- **Description**: Update a specific task
- **Headers**: `Authorization: Bearer <token>`
- **Request Body**:
  ```json
  {
    "title": "string (min: 1, max: 200)",
    "description": "string (optional, max: 1000)",
    "status": "pending | in_progress | completed"
  }
  ```
- **Response**: Same as Create Task
- **Error Codes**: 400 (validation errors), 401 (unauthorized), 404 (task not found)

#### 8. Delete Task
- **DELETE** `/api/tasks/{task_id}`
- **Description**: Delete a specific task
- **Headers**: `Authorization: Bearer <token>`
- **Response**: 204 No Content
- **Error Codes**: 401 (unauthorized), 404 (task not found)

## Data Models

### User Model
```python
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
```

### Task Model
```python
class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(String(1000), nullable=True)
    status = Column(Enum(TaskStatus), default=TaskStatus.pending)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
```

### Pydantic Schemas

#### User Schemas
```python
class UserBase(BaseModel):
    username: str
    email: str

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True
```

#### Task Schemas
```python
class TaskStatus(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"

class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.pending

class TaskCreate(TaskBase):
    pass

class TaskUpdate(TaskBase):
    pass

class TaskResponse(TaskBase):
    id: int
    created_at: datetime
    updated_at: datetime
    user_id: int
    
    class Config:
        from_attributes = True
```

#### Pagination Schema
```python
class PaginationParams(BaseModel):
    page: int = 1
    size: int = 10

class PaginatedResponse(BaseModel):
    tasks: List[TaskResponse]
    pagination: Dict[str, Any]
```

## Authentication
- JWT tokens are used for authentication
- Token expiration: 1 hour
- Token refresh mechanism not implemented (for simplicity)
- All task endpoints require authentication
- User profile endpoint requires authentication

## Error Handling
- Custom exception classes for different error scenarios
- HTTP status codes following REST conventions
- Error responses include detailed messages
- Validation errors use Pydantic validation

## Security Considerations
- Passwords are hashed using bcrypt
- JWT tokens are signed with a secret key
- Input validation on all endpoints
- SQL injection prevention through SQLAlchemy ORM
- CORS configuration for cross-origin requests

## Testing
- Unit tests for all endpoints
- Integration tests for API workflows
- Test coverage minimum: 80%
- Mock database for testing
- Test data cleanup after each test