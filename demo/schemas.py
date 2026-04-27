from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class TaskStatus(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"

# User schemas
class UserBase(BaseModel):
    username: str
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# Task schemas
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

# Pagination schemas
class PaginationParams(BaseModel):
    page: int = 1
    size: int = 10

class PaginatedResponse(BaseModel):
    tasks: List[TaskResponse]
    pagination: Dict[str, Any]