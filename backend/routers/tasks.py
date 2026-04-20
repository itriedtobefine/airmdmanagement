"""
Task router for TimeTracker Pro API.
Handles CRUD operations for tasks with time tracking integration.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

from ..database import get_db
from ..models import Task, Project, TimeEntry
from ..schemas import TaskCreate, TaskUpdate, TaskResponse, TaskWithTime

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    """
    Create a new task within a project.
    
    - **title**: Task title (1-200 characters)
    - **description**: Optional task description
    - **project_id**: ID of the parent project
    - **status**: Task status (default: "pending")
    - **estimated_hours**: Optional estimated hours for completion
    """
    # Verify project exists
    project = db.query(Project).filter(Project.id == task.project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Create new task
    db_task = Task(**task.model_dump())
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


@router.get("/", response_model=List[TaskResponse])
def get_tasks(project_id: int = None, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Get list of tasks with optional project filter and pagination.
    
    - **project_id**: Optional filter by project ID
    - **skip**: Number of records to skip (pagination)
    - **limit**: Maximum number of records to return
    """
    query = db.query(Task)
    if project_id is not None:
        query = query.filter(Task.project_id == project_id)
    
    tasks = query.offset(skip).limit(limit).all()
    return tasks


@router.get("/{task_id}", response_model=TaskWithTime)
def get_task(task_id: int, db: Session = Depends(get_db)):
    """
    Get a specific task by ID with time tracking summary.
    
    - **task_id**: Unique identifier of the task
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Calculate summary statistics
    total_time = db.query(func.sum(TimeEntry.duration_seconds)).filter(
        TimeEntry.task_id == task_id
    ).scalar() or 0
    
    total_cost = db.query(func.sum(TimeEntry.total_cost)).filter(
        TimeEntry.task_id == task_id
    ).scalar() or 0.0
    
    time_entry_count = db.query(func.count(TimeEntry.id)).filter(
        TimeEntry.task_id == task_id
    ).scalar() or 0
    
    # Build response with summary
    result = TaskWithTime(**task.to_dict())
    result.total_time_seconds = total_time
    result.total_cost = total_cost
    result.time_entry_count = time_entry_count
    
    return result


@router.put("/{task_id}", response_model=TaskResponse)
def update_task(task_id: int, task_update: TaskUpdate, db: Session = Depends(get_db)):
    """
    Update an existing task.
    
    - **task_id**: Unique identifier of the task
    - **task_update**: Fields to update (any subset of task fields)
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Update only provided fields
    update_data = task_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)
    
    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    """
    Delete a task and all associated time entries.
    
    - **task_id**: Unique identifier of the task
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    db.delete(task)
    db.commit()
    return None


@router.get("/{task_id}/summary")
def get_task_summary(task_id: int, db: Session = Depends(get_db)):
    """
    Get detailed time and cost summary for a task.
    
    - **task_id**: Unique identifier of the task
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Get project info
    project = db.query(Project).filter(Project.id == task.project_id).first()
    
    # Calculate total time and cost
    total_time = db.query(func.sum(TimeEntry.duration_seconds)).filter(
        TimeEntry.task_id == task_id
    ).scalar() or 0
    
    total_cost = db.query(func.sum(TimeEntry.total_cost)).filter(
        TimeEntry.task_id == task_id
    ).scalar() or 0.0
    
    # Format time
    hours = total_time // 3600
    minutes = (total_time % 3600) // 60
    seconds = total_time % 60
    formatted_time = f"{hours}h {minutes}m {seconds}s"
    
    return {
        "task_id": task_id,
        "task_title": task.title,
        "project_id": task.project_id,
        "project_name": project.name if project else "Unknown",
        "total_time_seconds": total_time,
        "total_time_formatted": formatted_time,
        "total_cost": round(total_cost, 2),
        "estimated_hours": task.estimated_hours,
        "status": task.status
    }
