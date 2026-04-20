"""
Time Entry router for TimeTracker Pro API.
Handles time tracking operations including start, stop, and cost calculations.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from datetime import datetime

from ..database import get_db
from ..models import TimeEntry, Task, Project, User
from ..schemas import TimeEntryStart, TimeEntryStop, TimeEntryResponse, TimeEntrySummary

router = APIRouter(prefix="/api/time-entries", tags=["time-entries"])


@router.post("/start/", response_model=TimeEntryResponse, status_code=status.HTTP_201_CREATED)
def start_time_entry(entry: TimeEntryStart, db: Session = Depends(get_db)):
    """
    Start tracking time for a task.
    
    - **task_id**: ID of the task to track time on
    - **project_id**: ID of the parent project
    - **user_id**: ID of the user tracking time
    - **hourly_rate**: Hourly rate for cost calculation
    - **description**: Optional description of the work being done
    """
    # Verify task exists
    task = db.query(Task).filter(Task.id == entry.task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Verify project exists
    project = db.query(Project).filter(Project.id == entry.project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Verify user exists
    user = db.query(User).filter(User.id == entry.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check for existing active entry for this task
    existing_active = db.query(TimeEntry).filter(
        TimeEntry.task_id == entry.task_id,
        TimeEntry.is_active == True
    ).first()
    
    if existing_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="There is already an active time entry for this task. Stop it first."
        )
    
    # Create new time entry
    db_entry = TimeEntry(
        task_id=entry.task_id,
        project_id=entry.project_id,
        user_id=entry.user_id,
        start_time=datetime.utcnow(),
        hourly_rate=entry.hourly_rate,
        description=entry.description,
        is_active=True,
        duration_seconds=0,
        total_cost=0.0
    )
    
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)
    return db_entry


@router.post("/stop/", response_model=TimeEntryResponse)
def stop_time_entry(entry_stop: TimeEntryStop, db: Session = Depends(get_db)):
    """
    Stop tracking time for an active time entry.
    
    - **entry_id**: ID of the time entry to stop
    """
    # Find the active time entry
    time_entry = db.query(TimeEntry).filter(
        TimeEntry.id == entry_stop.entry_id,
        TimeEntry.is_active == True
    ).first()
    
    if not time_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active time entry not found"
        )
    
    # Calculate duration
    end_time = datetime.utcnow()
    duration = end_time - time_entry.start_time
    duration_seconds = int(duration.total_seconds())
    
    # Update time entry
    time_entry.end_time = end_time
    time_entry.duration_seconds = duration_seconds
    time_entry.is_active = False
    
    # Calculate cost
    hours = duration_seconds / 3600.0
    time_entry.total_cost = round(hours * time_entry.hourly_rate, 2)
    
    db.commit()
    db.refresh(time_entry)
    return time_entry


@router.get("/", response_model=List[TimeEntryResponse])
def get_time_entries(
    project_id: int = None,
    task_id: int = None,
    user_id: int = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Get list of time entries with optional filters and pagination.
    
    - **project_id**: Optional filter by project ID
    - **task_id**: Optional filter by task ID
    - **user_id**: Optional filter by user ID
    - **skip**: Number of records to skip (pagination)
    - **limit**: Maximum number of records to return
    """
    query = db.query(TimeEntry)
    
    if project_id is not None:
        query = query.filter(TimeEntry.project_id == project_id)
    if task_id is not None:
        query = query.filter(TimeEntry.task_id == task_id)
    if user_id is not None:
        query = query.filter(TimeEntry.user_id == user_id)
    
    entries = query.order_by(TimeEntry.start_time.desc()).offset(skip).limit(limit).all()
    return entries


@router.get("/summary/", response_model=TimeEntrySummary)
def get_time_summary(
    project_id: int = None,
    task_id: int = None,
    user_id: int = None,
    db: Session = Depends(get_db)
):
    """
    Get summary statistics for time entries with optional filters.
    
    - **project_id**: Optional filter by project ID
    - **task_id**: Optional filter by task ID
    - **user_id**: Optional filter by user ID
    """
    query = db.query(TimeEntry)
    
    if project_id is not None:
        query = query.filter(TimeEntry.project_id == project_id)
    if task_id is not None:
        query = query.filter(TimeEntry.task_id == task_id)
    if user_id is not None:
        query = query.filter(TimeEntry.user_id == user_id)
    
    # Calculate aggregates
    total_entries = query.count()
    total_time = db.query(func.sum(TimeEntry.duration_seconds)).filter(
        TimeEntry.project_id == project_id if project_id else True,
        TimeEntry.task_id == task_id if task_id else True,
        TimeEntry.user_id == user_id if user_id else True
    ).scalar() or 0
    
    total_cost = db.query(func.sum(TimeEntry.total_cost)).filter(
        TimeEntry.project_id == project_id if project_id else True,
        TimeEntry.task_id == task_id if task_id else True,
        TimeEntry.user_id == user_id if user_id else True
    ).scalar() or 0.0
    
    active_entries = db.query(func.count(TimeEntry.id)).filter(
        TimeEntry.is_active == True
    ).scalar() or 0
    
    # Format time
    hours = total_time // 3600
    minutes = (total_time % 3600) // 60
    seconds = total_time % 60
    formatted_time = f"{hours}h {minutes}m {seconds}s"
    
    return {
        "total_entries": total_entries,
        "total_time_seconds": total_time,
        "total_time_formatted": formatted_time,
        "total_cost": round(total_cost, 2),
        "active_entries": active_entries
    }


@router.get("/{entry_id}", response_model=TimeEntryResponse)
def get_time_entry(entry_id: int, db: Session = Depends(get_db)):
    """
    Get a specific time entry by ID.
    
    - **entry_id**: Unique identifier of the time entry
    """
    entry = db.query(TimeEntry).filter(TimeEntry.id == entry_id).first()
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Time entry not found"
        )
    return entry


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_time_entry(entry_id: int, db: Session = Depends(get_db)):
    """
    Delete a time entry.
    
    - **entry_id**: Unique identifier of the time entry
    """
    entry = db.query(TimeEntry).filter(TimeEntry.id == entry_id).first()
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Time entry not found"
        )
    
    # Cannot delete active entries
    if entry.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete an active time entry. Stop it first."
        )
    
    db.delete(entry)
    db.commit()
    return None
