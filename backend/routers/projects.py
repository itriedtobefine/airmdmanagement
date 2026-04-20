"""
Project router for TimeTracker Pro API.
Handles CRUD operations for projects with cost tracking.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

from ..database import get_db
from ..models import Project, Task, TimeEntry, User
from ..schemas import ProjectCreate, ProjectUpdate, ProjectResponse, ProjectWithSummary

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(project: ProjectCreate, db: Session = Depends(get_db)):
    """
    Create a new project.
    
    - **name**: Project name (1-200 characters)
    - **description**: Optional project description
    - **owner_id**: ID of the user who owns the project
    - **hourly_rate**: Hourly rate for this project (default: 100.0)
    - **budget**: Optional budget limit
    - **status**: Project status (default: "active")
    """
    # Verify owner exists
    owner = db.query(User).filter(User.id == project.owner_id).first()
    if not owner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Owner user not found"
        )
    
    # Create new project
    db_project = Project(**project.model_dump())
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project


@router.get("/", response_model=List[ProjectResponse])
def get_projects(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Get list of all projects with pagination.
    
    - **skip**: Number of records to skip (pagination)
    - **limit**: Maximum number of records to return
    """
    projects = db.query(Project).offset(skip).limit(limit).all()
    return projects


@router.get("/{project_id}", response_model=ProjectWithSummary)
def get_project(project_id: int, db: Session = Depends(get_db)):
    """
    Get a specific project by ID with time and cost summary.
    
    - **project_id**: Unique identifier of the project
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Calculate summary statistics
    total_time = db.query(func.sum(TimeEntry.duration_seconds)).filter(
        TimeEntry.project_id == project_id
    ).scalar() or 0
    
    total_cost = db.query(func.sum(TimeEntry.total_cost)).filter(
        TimeEntry.project_id == project_id
    ).scalar() or 0.0
    
    task_count = db.query(func.count(Task.id)).filter(
        Task.project_id == project_id
    ).scalar() or 0
    
    time_entry_count = db.query(func.count(TimeEntry.id)).filter(
        TimeEntry.project_id == project_id
    ).scalar() or 0
    
    # Build response with summary
    result = ProjectWithSummary(**project.to_dict())
    result.total_time_seconds = total_time
    result.total_cost = total_cost
    result.task_count = task_count
    result.time_entry_count = time_entry_count
    
    return result


@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(project_id: int, project_update: ProjectUpdate, db: Session = Depends(get_db)):
    """
    Update an existing project.
    
    - **project_id**: Unique identifier of the project
    - **project_update**: Fields to update (any subset of project fields)
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Update only provided fields
    update_data = project_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)
    
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: int, db: Session = Depends(get_db)):
    """
    Delete a project and all associated tasks and time entries.
    
    - **project_id**: Unique identifier of the project
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    db.delete(project)
    db.commit()
    return None


@router.get("/{project_id}/summary")
def get_project_summary(project_id: int, db: Session = Depends(get_db)):
    """
    Get detailed cost and time summary for a project.
    
    - **project_id**: Unique identifier of the project
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Calculate total time and cost
    total_time = db.query(func.sum(TimeEntry.duration_seconds)).filter(
        TimeEntry.project_id == project_id
    ).scalar() or 0
    
    total_cost = db.query(func.sum(TimeEntry.total_cost)).filter(
        TimeEntry.project_id == project_id
    ).scalar() or 0.0
    
    # Format time
    hours = total_time // 3600
    minutes = (total_time % 3600) // 60
    seconds = total_time % 60
    formatted_time = f"{hours}h {minutes}m {seconds}s"
    
    # Budget calculations
    budget_remaining = None
    budget_percentage_used = None
    if project.budget is not None:
        budget_remaining = project.budget - total_cost
        if project.budget > 0:
            budget_percentage_used = round((total_cost / project.budget) * 100, 2)
    
    return {
        "project_id": project_id,
        "project_name": project.name,
        "total_time_seconds": total_time,
        "total_time_formatted": formatted_time,
        "total_cost": round(total_cost, 2),
        "budget": project.budget,
        "budget_remaining": round(budget_remaining, 2) if budget_remaining is not None else None,
        "budget_percentage_used": budget_percentage_used,
        "hourly_rate": project.hourly_rate,
        "status": project.status
    }
