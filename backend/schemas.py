from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class TodoBase(BaseModel):
    """Base schema for Todo items."""
    
    title: str = Field(..., min_length=1, max_length=255, description="Task title")
    description: Optional[str] = Field(None, description="Task description")


class TodoCreate(TodoBase):
    """Schema for creating a new Todo item."""
    pass


class TodoUpdate(BaseModel):
    """Schema for updating an existing Todo item."""
    
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    completed: Optional[bool] = None


class TodoResponse(TodoBase):
    """Schema for Todo response."""
    
    id: int
    completed: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
