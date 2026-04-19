from sqlalchemy.orm import Session
from sqlalchemy import desc
from models import Todo
from schemas import TodoCreate, TodoUpdate
from typing import List, Optional


def get_todos(db: Session, skip: int = 0, limit: int = 100, completed: Optional[bool] = None) -> List[Todo]:
    """Get all todos with optional filtering by completion status."""
    query = db.query(Todo)
    
    if completed is not None:
        query = query.filter(Todo.completed == completed)
    
    return query.order_by(desc(Todo.created_at)).offset(skip).limit(limit).all()


def get_todo(db: Session, todo_id: int) -> Optional[Todo]:
    """Get a single todo by ID."""
    return db.query(Todo).filter(Todo.id == todo_id).first()


def create_todo(db: Session, todo: TodoCreate) -> Todo:
    """Create a new todo item."""
    db_todo = Todo(
        title=todo.title,
        description=todo.description,
        completed=False
    )
    db.add(db_todo)
    db.commit()
    db.refresh(db_todo)
    return db_todo


def update_todo(db: Session, todo_id: int, todo_update: TodoUpdate) -> Optional[Todo]:
    """Update an existing todo item."""
    db_todo = get_todo(db, todo_id)
    
    if db_todo is None:
        return None
    
    update_data = todo_update.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(db_todo, field, value)
    
    db.commit()
    db.refresh(db_todo)
    return db_todo


def delete_todo(db: Session, todo_id: int) -> bool:
    """Delete a todo item. Returns True if deleted, False if not found."""
    db_todo = get_todo(db, todo_id)
    
    if db_todo is None:
        return False
    
    db.delete(db_todo)
    db.commit()
    return True


def toggle_todo_completion(db: Session, todo_id: int) -> Optional[Todo]:
    """Toggle the completion status of a todo item."""
    db_todo = get_todo(db, todo_id)
    
    if db_todo is None:
        return None
    
    db_todo.completed = not db_todo.completed
    db.commit()
    db.refresh(db_todo)
    return db_todo
