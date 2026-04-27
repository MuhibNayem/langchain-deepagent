from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import uvicorn

# Import our modules
from database import get_db, engine, Base
from models import User, Task
from schemas import UserCreate, UserResponse, TaskCreate, TaskUpdate, TaskResponse, TaskStatus
from auth import authenticate_user, create_access_token, get_current_user, get_password_hash, verify_password

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Task Management API",
    description="A REST API for task management with JWT authentication",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

# User endpoints
@app.post("/api/auth/register", response_model=UserResponse)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user
    """
    # Check if user already exists
    db_user = db.query(User).filter(
        (User.username == user.username) | (User.email == user.email)
    ).first()
    
    if db_user:
        raise HTTPException(
            status_code=409,
            detail="Username or email already exists"
        )
    
    # Create new user
    hashed_password = get_password_hash(user.password)
    db_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user

@app.post("/api/auth/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Login user and return JWT token
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/users/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """
    Get current user profile
    """
    return current_user

# Task endpoints
@app.post("/api/tasks", response_model=TaskResponse)
async def create_task(task: TaskCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Create a new task for the current user
    """
    db_task = Task(
        title=task.title,
        description=task.description,
        status=task.status,
        user_id=current_user.id
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    
    return db_task

@app.get("/api/tasks", response_model=Dict[str, Any])
async def get_tasks(
    page: int = 1,
    size: int = 10,
    status: Optional[TaskStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get tasks for the current user with pagination
    """
    # Validate pagination parameters
    if page < 1:
        page = 1
    if size > 100:
        size = 100
    
    # Build query
    query = db.query(Task).filter(Task.user_id == current_user.id)
    
    # Filter by status if provided
    if status:
        query = query.filter(Task.status == status)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    tasks = query.offset((page - 1) * size).limit(size).all()
    
    # Calculate pagination metadata
    total_pages = (total + size - 1) // size
    
    return {
        "tasks": tasks,
        "pagination": {
            "page": page,
            "size": size,
            "total": total,
            "total_pages": total_pages
        }
    }

@app.get("/api/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Get a specific task by ID
    """
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == current_user.id).first()
    
    if not task:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )
    
    return task

@app.put("/api/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_update: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a specific task
    """
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == current_user.id).first()
    
    if not task:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )
    
    # Update task fields
    task.title = task_update.title
    task.description = task_update.description
    task.status = task_update.status
    task.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(task)
    
    return task

@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Delete a specific task
    """
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == current_user.id).first()
    
    if not task:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )
    
    db.delete(task)
    db.commit()
    
    return {"detail": "Task deleted successfully"}

@app.get("/")
async def root():
    """
    Root endpoint
    """
    return {"message": "Task Management API is running"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)