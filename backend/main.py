from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional

from database import get_db, Base
from schemas import TodoCreate, TodoUpdate, TodoResponse
import crud


def create_app():
    """Application factory for creating FastAPI app."""
    
    # Create database tables only if engine is available
    try:
        from database import engine
        Base.metadata.create_all(bind=engine)
    except Exception:
        # Database not available (e.g., during testing with SQLite)
        pass
    
    app = FastAPI(
        title="TODO API",
        description="A simple TODO application API with PostgreSQL backend",
        version="1.0.0"
    )

    # Configure CORS for frontend access
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, specify exact origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health_check():
        """Health check endpoint."""
        return {"status": "healthy"}

    @app.get("/todos", response_model=List[TodoResponse], tags=["Todos"])
    def read_todos(
        skip: int = Query(0, ge=0, description="Number of items to skip"),
        limit: int = Query(100, ge=1, le=1000, description="Maximum number of items to return"),
        completed: Optional[bool] = Query(None, description="Filter by completion status"),
        db: Session = Depends(get_db)
    ):
        """Get all todos with optional filtering and pagination."""
        todos = crud.get_todos(db=db, skip=skip, limit=limit, completed=completed)
        return todos

    @app.get("/todos/{todo_id}", response_model=TodoResponse, tags=["Todos"])
    def read_todo(todo_id: int, db: Session = Depends(get_db)):
        """Get a specific todo by ID."""
        todo = crud.get_todo(db=db, todo_id=todo_id)
        if todo is None:
            raise HTTPException(status_code=404, detail="Todo not found")
        return todo

    @app.post("/todos", response_model=TodoResponse, status_code=201, tags=["Todos"])
    def create_todo(todo: TodoCreate, db: Session = Depends(get_db)):
        """Create a new todo item."""
        return crud.create_todo(db=db, todo=todo)

    @app.put("/todos/{todo_id}", response_model=TodoResponse, tags=["Todos"])
    def update_todo(todo_id: int, todo_update: TodoUpdate, db: Session = Depends(get_db)):
        """Update an existing todo item."""
        updated_todo = crud.update_todo(db=db, todo_id=todo_id, todo_update=todo_update)
        if updated_todo is None:
            raise HTTPException(status_code=404, detail="Todo not found")
        return updated_todo

    @app.patch("/todos/{todo_id}/toggle", response_model=TodoResponse, tags=["Todos"])
    def toggle_todo(todo_id: int, db: Session = Depends(get_db)):
        """Toggle the completion status of a todo item."""
        toggled_todo = crud.toggle_todo_completion(db=db, todo_id=todo_id)
        if toggled_todo is None:
            raise HTTPException(status_code=404, detail="Todo not found")
        return toggled_todo

    @app.delete("/todos/{todo_id}", status_code=204, tags=["Todos"])
    def delete_todo(todo_id: int, db: Session = Depends(get_db)):
        """Delete a todo item."""
        success = crud.delete_todo(db=db, todo_id=todo_id)
        if not success:
            raise HTTPException(status_code=404, detail="Todo not found")
        return None
    
    return app


# Create app instance for production use
app = create_app()
