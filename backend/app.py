"""
TODO Application - Single File Version
FastAPI + PostgreSQL backend with complete CRUD operations.

Usage:
    uvicorn app:app --host 0.0.0.0 --port 8000 --reload

Environment Variables:
    DATABASE_URL: PostgreSQL connection string (default: postgresql://postgres:postgres@localhost:5432/todo_db)
"""

import os
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text, desc
from sqlalchemy.orm import sessionmaker, declarative_base, Session


# =============================================================================
# Database Configuration
# =============================================================================

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/todo_db"
)

engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =============================================================================
# SQLAlchemy Models
# =============================================================================

class Todo(Base):
    """Todo model representing a task in the TODO application."""
    
    __tablename__ = "todos"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    completed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self):
        """Convert model instance to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "completed": self.completed,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# =============================================================================
# Pydantic Schemas
# =============================================================================

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


# =============================================================================
# CRUD Operations
# =============================================================================

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


# =============================================================================
# FastAPI Application
# =============================================================================

def create_app():
    """Application factory for creating FastAPI app."""
    
    # Create database tables only if engine is available
    try:
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
        todos = get_todos(db=db, skip=skip, limit=limit, completed=completed)
        return todos

    @app.get("/todos/{todo_id}", response_model=TodoResponse, tags=["Todos"])
    def read_todo(todo_id: int, db: Session = Depends(get_db)):
        """Get a specific todo by ID."""
        todo = get_todo(db=db, todo_id=todo_id)
        if todo is None:
            raise HTTPException(status_code=404, detail="Todo not found")
        return todo

    @app.post("/todos", response_model=TodoResponse, status_code=201, tags=["Todos"])
    def create_todo_endpoint(todo: TodoCreate, db: Session = Depends(get_db)):
        """Create a new todo item."""
        return create_todo(db=db, todo=todo)

    @app.put("/todos/{todo_id}", response_model=TodoResponse, tags=["Todos"])
    def update_todo_endpoint(todo_id: int, todo_update: TodoUpdate, db: Session = Depends(get_db)):
        """Update an existing todo item."""
        updated_todo = update_todo(db=db, todo_id=todo_id, todo_update=todo_update)
        if updated_todo is None:
            raise HTTPException(status_code=404, detail="Todo not found")
        return updated_todo

    @app.patch("/todos/{todo_id}/toggle", response_model=TodoResponse, tags=["Todos"])
    def toggle_todo_endpoint(todo_id: int, db: Session = Depends(get_db)):
        """Toggle the completion status of a todo item."""
        toggled_todo = toggle_todo_completion(db=db, todo_id=todo_id)
        if toggled_todo is None:
            raise HTTPException(status_code=404, detail="Todo not found")
        return toggled_todo

    @app.delete("/todos/{todo_id}", status_code=204, tags=["Todos"])
    def delete_todo_endpoint(todo_id: int, db: Session = Depends(get_db)):
        """Delete a todo item."""
        success = delete_todo(db=db, todo_id=todo_id)
        if not success:
            raise HTTPException(status_code=404, detail="Todo not found")
        return None
    
    return app


# Create app instance for production use
app = create_app()


# =============================================================================
# Test Suite (run with: pytest app.py -v)
# =============================================================================

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine as test_create_engine
from sqlalchemy.orm import sessionmaker as test_sessionmaker


# Pytest fixtures for running tests within this file
@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test.db"
    
    test_engine = test_create_engine(
        SQLALCHEMY_TEST_DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    TestingSessionLocal = test_sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with overridden database dependency."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


class TestHealthCheck:
    """Tests for health check endpoint."""
    
    def test_health_check(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


class TestTodoCRUD:
    """Tests for Todo CRUD operations."""
    
    def test_create_todo(self, client):
        todo_data = {
            "title": "Test Task",
            "description": "This is a test task"
        }
        response = client.post("/todos", json=todo_data)
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == todo_data["title"]
        assert data["description"] == todo_data["description"]
        assert data["completed"] is False
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data
    
    def test_create_todo_minimal(self, client):
        todo_data = {"title": "Minimal Task"}
        response = client.post("/todos", json=todo_data)
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == todo_data["title"]
        assert data["description"] is None
    
    def test_get_todos_empty(self, client):
        response = client.get("/todos")
        assert response.status_code == 200
        assert response.json() == []
    
    def test_get_todos_with_items(self, client):
        # Create some todos
        client.post("/todos", json={"title": "Task 1"})
        client.post("/todos", json={"title": "Task 2"})
        
        response = client.get("/todos")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
    
    def test_get_single_todo(self, client):
        # Create a todo
        create_response = client.post("/todos", json={"title": "Single Task"})
        todo_id = create_response.json()["id"]
        
        # Get the todo
        response = client.get(f"/todos/{todo_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == todo_id
        assert data["title"] == "Single Task"
    
    def test_get_nonexistent_todo(self, client):
        response = client.get("/todos/99999")
        assert response.status_code == 404
    
    def test_update_todo(self, client):
        # Create a todo
        create_response = client.post("/todos", json={"title": "Original Title"})
        todo_id = create_response.json()["id"]
        
        # Update the todo
        update_data = {"title": "Updated Title", "description": "New description"}
        response = client.put(f"/todos/{todo_id}", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == update_data["title"]
        assert data["description"] == update_data["description"]
    
    def test_update_nonexistent_todo(self, client):
        response = client.put("/todos/99999", json={"title": "Test"})
        assert response.status_code == 404
    
    def test_toggle_todo_completion(self, client):
        # Create a todo
        create_response = client.post("/todos", json={"title": "Toggle Task"})
        todo_id = create_response.json()["id"]
        
        # Initially should be incomplete
        assert create_response.json()["completed"] is False
        
        # Toggle to complete
        toggle_response = client.patch(f"/todos/{todo_id}/toggle")
        assert toggle_response.status_code == 200
        assert toggle_response.json()["completed"] is True
        
        # Toggle back to incomplete
        toggle_response2 = client.patch(f"/todos/{todo_id}/toggle")
        assert toggle_response2.status_code == 200
        assert toggle_response2.json()["completed"] is False
    
    def test_delete_todo(self, client):
        # Create a todo
        create_response = client.post("/todos", json={"title": "To Delete"})
        todo_id = create_response.json()["id"]
        
        # Delete it
        delete_response = client.delete(f"/todos/{todo_id}")
        assert delete_response.status_code == 204
        
        # Verify it's gone
        get_response = client.get(f"/todos/{todo_id}")
        assert get_response.status_code == 404
    
    def test_delete_nonexistent_todo(self, client):
        response = client.delete("/todos/99999")
        assert response.status_code == 404
    
    def test_filter_todos_by_completion(self, client):
        # Create completed and incomplete todos
        client.post("/todos", json={"title": "Incomplete 1"})
        client.post("/todos", json={"title": "Incomplete 2"})
        
        complete_response = client.post("/todos", json={"title": "Complete 1"})
        complete_id = complete_response.json()["id"]
        client.patch(f"/todos/{complete_id}/toggle")
        
        # Filter incomplete
        incomplete_response = client.get("/todos?completed=false")
        assert incomplete_response.status_code == 200
        assert len(incomplete_response.json()) == 2
        
        # Filter complete
        complete_response = client.get("/todos?completed=true")
        assert complete_response.status_code == 200
        assert len(complete_response.json()) == 1
    
    def test_pagination(self, client):
        # Create 5 todos
        for i in range(5):
            client.post("/todos", json={"title": f"Task {i}"})
        
        # Test limit
        response = client.get("/todos?limit=3")
        assert response.status_code == 200
        assert len(response.json()) == 3
        
        # Test skip
        response = client.get("/todos?skip=2&limit=2")
        assert response.status_code == 200
        assert len(response.json()) == 2
    
    def test_validation_error_empty_title(self, client):
        response = client.post("/todos", json={"title": ""})
        assert response.status_code == 422
    
    def test_validation_error_missing_title(self, client):
        response = client.post("/todos", json={})
        assert response.status_code == 422


# Pytest fixtures for running tests within this file
@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    from sqlalchemy import create_engine as test_create_engine
    from sqlalchemy.orm import sessionmaker as test_sessionmaker
    
    SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test.db"
    
    test_engine = test_create_engine(
        SQLALCHEMY_TEST_DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    TestingSessionLocal = test_sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with overridden database dependency."""
    from fastapi.testclient import TestClient
    
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
