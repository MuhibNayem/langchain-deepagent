# Task Management API

A complete REST API for task management built with FastAPI, featuring JWT authentication, task CRUD operations, and pagination.

## Features

- User authentication with JWT tokens
- CRUD operations for tasks
- Task status management (pending, in_progress, completed)
- Pagination for task listings
- Input validation with Pydantic
- Proper error handling

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
python main.py
```

The API will be available at `http://localhost:8000`

## API Documentation

After starting the server, visit `http://localhost:8000/docs` for interactive API documentation.

## Testing

Run the test suite with pytest:
```bash
pytest
```

To run tests with coverage:
```bash
pytest --cov=. --cov-report=html
```

## API Endpoints

### Authentication

- `POST /api/auth/register` - Register a new user
- `POST /api/auth/login` - Login and get JWT token
- `GET /api/users/me` - Get current user profile

### Tasks

- `POST /api/tasks` - Create a new task
- `GET /api/tasks` - Get tasks with pagination
- `GET /api/tasks/{task_id}` - Get a specific task
- `PUT /api/tasks/{task_id}` - Update a task
- `DELETE /api/tasks/{task_id}` - Delete a task

## Project Structure

```
demo/
├── main.py              # FastAPI application entry point
├── database.py          # Database configuration
├── models.py            # SQLAlchemy models
├── schemas.py           # Pydantic schemas
├── auth.py              # Authentication logic
├── requirements.txt     # Dependencies
├── pytest.ini          # Pytest configuration
├── README.md           # This file
├── SPEC.md             # Detailed API specifications
└── tests/              # Test files
    ├── conftest.py     # Test configuration
    ├── test_auth.py    # Authentication tests
    ├── test_tasks.py   # Task operation tests
    └── test_main.py    # General API tests
```