import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch

# Import after setting up test environment
from main import app
from database import Base, get_db


# Test database setup (using SQLite for testing)
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test.db"

test_engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
