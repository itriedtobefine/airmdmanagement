"""
Unit tests for the Task Manager Application.
Tests cover database operations, API endpoints, and data validation.
"""
import pytest
import pytest_asyncio
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator, Optional

import aiosqlite
from httpx import AsyncClient, ASGITransport

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import after path setup
import main
from main import (
    app, 
    DatabaseManager, 
    TaskStatus, 
    TaskPriority,
    TaskCreate,
    TaskUpdate,
)


# ============================================================================
# Fixtures
# ============================================================================
@pytest.fixture
def test_db_path(tmp_path: Path) -> Path:
    """Create a temporary database path for testing."""
    return tmp_path / "test_tasks.db"


@pytest_asyncio.fixture
async def db_manager(test_db_path: Path) -> AsyncGenerator[DatabaseManager, None]:
    """Create and initialize a database manager for testing."""
    # Override the global db_manager in main module
    manager = DatabaseManager(test_db_path)
    original_db_manager = main.db_manager
    main.db_manager = manager
    
    await manager.connect()
    yield manager
    await manager.disconnect()
    
    # Restore original
    main.db_manager = original_db_manager
    
    if test_db_path.exists():
        test_db_path.unlink()


@pytest_asyncio.fixture
async def client(db_manager: DatabaseManager) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# ============================================================================
# Database Manager Tests
# ============================================================================
class TestDatabaseManager:
    """Tests for DatabaseManager class."""

    @pytest.mark.asyncio
    async def test_create_task(self, db_manager: DatabaseManager):
        """Test creating a new task."""
        task_data = {
            "title": "Test Task",
            "description": "Test Description",
            "status": TaskStatus.PENDING.value,
            "priority": TaskPriority.HIGH.value,
            "due_date": "2026-12-31"
        }
        
        created = await db_manager.create_task(task_data)
        
        assert created["id"] is not None
        assert created["title"] == "Test Task"
        assert created["description"] == "Test Description"
        assert created["status"] == "pending"
        assert created["priority"] == "high"
        assert "created_at" in created
        assert "updated_at" in created

    @pytest.mark.asyncio
    async def test_get_task_by_id(self, db_manager: DatabaseManager):
        """Test retrieving a task by ID."""
        task_data = {
            "title": "Get Task Test",
            "description": "",
            "status": TaskStatus.PENDING.value,
            "priority": TaskPriority.MEDIUM.value,
            "due_date": None
        }
        
        created = await db_manager.create_task(task_data)
        retrieved = await db_manager.get_task_by_id(created["id"])
        
        assert retrieved is not None
        assert retrieved["id"] == created["id"]
        assert retrieved["title"] == "Get Task Test"

    @pytest.mark.asyncio
    async def test_get_nonexistent_task(self, db_manager: DatabaseManager):
        """Test retrieving a nonexistent task."""
        retrieved = await db_manager.get_task_by_id(99999)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_update_task(self, db_manager: DatabaseManager):
        """Test updating a task."""
        task_data = {
            "title": "Update Test",
            "description": "Original",
            "status": TaskStatus.PENDING.value,
            "priority": TaskPriority.LOW.value,
            "due_date": None
        }
        
        created = await db_manager.create_task(task_data)
        
        update_data = {
            "title": "Updated Title",
            "status": TaskStatus.COMPLETED.value
        }
        
        updated = await db_manager.update_task(created["id"], update_data)
        
        assert updated is not None
        assert updated["title"] == "Updated Title"
        assert updated["status"] == "completed"
        assert updated["description"] == "Original"

    @pytest.mark.asyncio
    async def test_delete_task(self, db_manager: DatabaseManager):
        """Test deleting a task."""
        task_data = {
            "title": "Delete Test",
            "description": "",
            "status": TaskStatus.PENDING.value,
            "priority": TaskPriority.MEDIUM.value,
            "due_date": None
        }
        
        created = await db_manager.create_task(task_data)
        deleted = await db_manager.delete_task(created["id"])
        
        assert deleted is True
        
        retrieved = await db_manager.get_task_by_id(created["id"])
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_task(self, db_manager: DatabaseManager):
        """Test deleting a nonexistent task."""
        deleted = await db_manager.delete_task(99999)
        assert deleted is False

    @pytest.mark.asyncio
    async def test_get_all_tasks(self, db_manager: DatabaseManager):
        """Test retrieving all tasks."""
        for i in range(5):
            task_data = {
                "title": f"Task {i}",
                "description": "",
                "status": TaskStatus.PENDING.value,
                "priority": TaskPriority.MEDIUM.value,
                "due_date": None
            }
            await db_manager.create_task(task_data)
        
        tasks = await db_manager.get_all_tasks()
        assert len(tasks) == 5

    @pytest.mark.asyncio
    async def test_get_tasks_filtered_by_status(self, db_manager: DatabaseManager):
        """Test retrieving tasks filtered by status."""
        await db_manager.create_task({
            "title": "Pending Task",
            "description": "",
            "status": TaskStatus.PENDING.value,
            "priority": TaskPriority.MEDIUM.value,
            "due_date": None
        })
        
        await db_manager.create_task({
            "title": "Completed Task",
            "description": "",
            "status": TaskStatus.COMPLETED.value,
            "priority": TaskPriority.MEDIUM.value,
            "due_date": None
        })
        
        pending_tasks = await db_manager.get_all_tasks("pending")
        completed_tasks = await db_manager.get_all_tasks("completed")
        
        assert len(pending_tasks) == 1
        assert len(completed_tasks) == 1
        assert pending_tasks[0]["status"] == "pending"
        assert completed_tasks[0]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_get_statistics(self, db_manager: DatabaseManager):
        """Test getting task statistics."""
        statuses = [
            TaskStatus.PENDING,
            TaskStatus.PENDING,
            TaskStatus.IN_PROGRESS,
            TaskStatus.COMPLETED,
            TaskStatus.CANCELLED
        ]
        
        for status in statuses:
            await db_manager.create_task({
                "title": f"Task with status {status.value}",
                "description": "",
                "status": status.value,
                "priority": TaskPriority.MEDIUM.value,
                "due_date": None
            })
        
        stats = await db_manager.get_statistics()
        
        assert stats["total"] == 5
        assert stats["pending"] == 2
        assert stats["in_progress"] == 1
        assert stats["completed"] == 1
        assert stats["cancelled"] == 1

    @pytest.mark.asyncio
    async def test_task_priority_ordering(self, db_manager: DatabaseManager):
        """Test that tasks are ordered by priority."""
        priorities = [
            TaskPriority.LOW,
            TaskPriority.HIGH,
            TaskPriority.CRITICAL,
            TaskPriority.MEDIUM
        ]
        
        for priority in priorities:
            await db_manager.create_task({
                "title": f"Task with priority {priority.value}",
                "description": "",
                "status": TaskStatus.PENDING.value,
                "priority": priority.value,
                "due_date": None
            })
        
        tasks = await db_manager.get_all_tasks()
        
        assert tasks[0]["priority"] == "critical"
        assert tasks[1]["priority"] == "high"
        assert tasks[2]["priority"] == "medium"
        assert tasks[3]["priority"] == "low"


# ============================================================================
# API Endpoint Tests
# ============================================================================
class TestAPIEndpoints:
    """Tests for FastAPI endpoints."""

    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        """Test health check endpoint."""
        response = await client.get("/api/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_list_tasks_empty(self, client: AsyncClient):
        """Test listing tasks when empty."""
        response = await client.get("/api/tasks")
        
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_create_task(self, client: AsyncClient):
        """Test creating a task via API."""
        task_data = {
            "title": "API Test Task",
            "description": "Created via API",
            "priority": "high",
            "due_date": "2026-06-15"
        }
        
        response = await client.post("/api/tasks", json=task_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "API Test Task"
        assert data["description"] == "Created via API"
        assert data["priority"] == "high"
        assert data["status"] == "pending"

    @pytest.mark.asyncio
    async def test_create_task_validation(self, client: AsyncClient):
        """Test task creation validation."""
        response = await client.post("/api/tasks", json={"title": ""})
        assert response.status_code == 422

        response = await client.post("/api/tasks", json={"description": "No title"})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_task(self, client: AsyncClient):
        """Test getting a specific task."""
        create_response = await client.post("/api/tasks", json={
            "title": "Get Task Test",
            "description": "Test",
            "priority": "medium"
        })
        task_id = create_response.json()["id"]
        
        response = await client.get(f"/api/tasks/{task_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == task_id
        assert data["title"] == "Get Task Test"

    @pytest.mark.asyncio
    async def test_get_nonexistent_task(self, client: AsyncClient):
        """Test getting a nonexistent task."""
        response = await client.get("/api/tasks/99999")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_task(self, client: AsyncClient):
        """Test updating a task via API."""
        create_response = await client.post("/api/tasks", json={
            "title": "Update Test",
            "description": "Original",
            "priority": "low"
        })
        task_id = create_response.json()["id"]
        
        update_data = {
            "title": "Updated Title",
            "status": "completed"
        }
        response = await client.put(f"/api/tasks/{task_id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["status"] == "completed"

    @pytest.mark.asyncio
    async def test_update_task_status(self, client: AsyncClient):
        """Test updating only task status."""
        create_response = await client.post("/api/tasks", json={
            "title": "Status Update Test",
            "priority": "medium"
        })
        task_id = create_response.json()["id"]
        
        response = await client.patch(f"/api/tasks/{task_id}/status?status=in_progress")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "in_progress"

    @pytest.mark.asyncio
    async def test_delete_task(self, client: AsyncClient):
        """Test deleting a task via API."""
        create_response = await client.post("/api/tasks", json={
            "title": "Delete Test",
            "priority": "medium"
        })
        task_id = create_response.json()["id"]
        
        response = await client.delete(f"/api/tasks/{task_id}")
        
        assert response.status_code == 204
        
        get_response = await client.get(f"/api/tasks/{task_id}")
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_statistics(self, client: AsyncClient):
        """Test getting statistics via API."""
        await client.post("/api/tasks", json={
            "title": "Task 1",
            "priority": "medium",
            "status": "pending"
        })
        await client.post("/api/tasks", json={
            "title": "Task 2",
            "priority": "medium",
            "status": "completed"
        })
        
        response = await client.get("/api/statistics")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert data["pending"] == 1
        assert data["completed"] == 1

    @pytest.mark.asyncio
    async def test_filter_tasks_by_status(self, client: AsyncClient):
        """Test filtering tasks by status."""
        await client.post("/api/tasks", json={
            "title": "Pending Task",
            "status": "pending"
        })
        await client.post("/api/tasks", json={
            "title": "Completed Task",
            "status": "completed"
        })
        
        response = await client.get("/api/tasks?status=pending")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["status"] == "pending"


# ============================================================================
# Pydantic Schema Tests
# ============================================================================
class TestPydanticSchemas:
    """Tests for Pydantic schemas."""

    def test_task_create_valid(self):
        """Test valid TaskCreate schema."""
        task = TaskCreate(
            title="Test Task",
            description="Test Description",
            status="pending",
            priority="high",
            due_date="2026-12-31"
        )
        
        assert task.title == "Test Task"
        assert task.description == "Test Description"
        assert task.status == "pending"
        assert task.priority == "high"

    def test_task_create_defaults(self):
        """Test TaskCreate with default values."""
        task = TaskCreate(title="Minimal Task")
        
        assert task.title == "Minimal Task"
        assert task.description == ""
        assert task.status == "pending"
        assert task.priority == "medium"
        assert task.due_date is None

    def test_task_update_partial(self):
        """Test partial TaskUpdate schema."""
        update = TaskUpdate(title="New Title")
        
        assert update.title == "New Title"
        assert update.description is None
        assert update.status is None

    def test_task_create_title_max_length(self):
        """Test title max length validation."""
        long_title = "A" * 201
        with pytest.raises(Exception):
            TaskCreate(title=long_title)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
