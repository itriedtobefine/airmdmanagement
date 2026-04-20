"""
Pydantic schemas for request/response validation in TimeTracker Pro.
Defines data structures for API endpoints.
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime


# User Schemas
class UserBase(BaseModel):
    """Base schema for user data."""
    username: str = Field(..., min_length=3, max_length=50)
    email: str
    full_name: Optional[str] = Field(None, max_length=100)
    hourly_rate: float = Field(default=100.0, ge=0)


class UserCreate(UserBase):
    """Schema for creating a new user."""
    pass


class UserUpdate(BaseModel):
    """Schema for updating user data."""
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[str] = None
    full_name: Optional[str] = Field(None, max_length=100)
    hourly_rate: Optional[float] = Field(None, ge=0)
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    """Schema for user response."""
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Project Schemas
class ProjectBase(BaseModel):
    """Base schema for project data."""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    hourly_rate: float = Field(default=100.0, ge=0)
    budget: Optional[float] = Field(None, ge=0)
    status: str = Field(default="active")


class ProjectCreate(ProjectBase):
    """Schema for creating a new project."""
    owner_id: int


class ProjectUpdate(BaseModel):
    """Schema for updating project data."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    hourly_rate: Optional[float] = Field(None, ge=0)
    budget: Optional[float] = Field(None, ge=0)
    status: Optional[str] = None


class ProjectResponse(ProjectBase):
    """Schema for project response."""
    id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProjectWithSummary(ProjectResponse):
    """Schema for project response with time and cost summary."""
    total_time_seconds: int = 0
    total_cost: float = 0.0
    task_count: int = 0
    time_entry_count: int = 0


# Task Schemas
class TaskBase(BaseModel):
    """Base schema for task data."""
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    status: str = Field(default="pending")
    estimated_hours: Optional[float] = Field(None, ge=0)


class TaskCreate(TaskBase):
    """Schema for creating a new task."""
    project_id: int


class TaskUpdate(BaseModel):
    """Schema for updating task data."""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    status: Optional[str] = None
    estimated_hours: Optional[float] = Field(None, ge=0)


class TaskResponse(TaskBase):
    """Schema for task response."""
    id: int
    project_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TaskWithTime(TaskResponse):
    """Schema for task response with time tracking summary."""
    total_time_seconds: int = 0
    total_cost: float = 0.0
    time_entry_count: int = 0


# Time Entry Schemas
class TimeEntryBase(BaseModel):
    """Base schema for time entry data."""
    description: Optional[str] = None
    hourly_rate: float = Field(..., ge=0)


class TimeEntryStart(TimeEntryBase):
    """Schema for starting a time entry."""
    task_id: int
    project_id: int
    user_id: int


class TimeEntryStop(BaseModel):
    """Schema for stopping a time entry."""
    entry_id: int


class TimeEntryUpdate(BaseModel):
    """Schema for updating time entry data."""
    description: Optional[str] = None
    hourly_rate: Optional[float] = Field(None, ge=0)


class TimeEntryResponse(TimeEntryBase):
    """Schema for time entry response."""
    id: int
    task_id: int
    project_id: int
    user_id: int
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: int
    total_cost: float
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TimeEntrySummary(BaseModel):
    """Schema for time entry summary statistics."""
    total_entries: int
    total_time_seconds: int
    total_time_formatted: str
    total_cost: float
    active_entries: int


# Dashboard/Statistics Schemas
class ProjectCostSummary(BaseModel):
    """Schema for project cost breakdown."""
    project_id: int
    project_name: str
    total_time_seconds: int
    total_time_formatted: str
    total_cost: float
    budget: Optional[float]
    budget_remaining: Optional[float]
    budget_percentage_used: Optional[float]


class TaskCostSummary(BaseModel):
    """Schema for task cost breakdown."""
    task_id: int
    task_title: str
    project_id: int
    project_name: str
    total_time_seconds: int
    total_time_formatted: str
    total_cost: float
    estimated_hours: Optional[float]


class UserActivitySummary(BaseModel):
    """Schema for user activity summary."""
    user_id: int
    username: str
    total_time_seconds: int
    total_time_formatted: str
    total_earnings: float
    projects_count: int
    tasks_count: int
