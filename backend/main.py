"""
Task Manager Application - Backend
A full-featured task management system with REST API and database integration.
"""
from contextlib import asynccontextmanager
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, ConfigDict
import aiosqlite

# ============================================================================
# Configuration
# ============================================================================
DATABASE_PATH = Path(__file__).parent / "tasks.db"
TEMPLATES_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"

# ============================================================================
# Database Models
# ============================================================================
class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ============================================================================
# Pydantic Schemas
# ============================================================================
class TaskCreate(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    
    title: str = Field(..., min_length=1, max_length=200, description="Task title")
    description: str = Field(default="", max_length=2000, description="Task description")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Task status")
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM, description="Task priority")
    due_date: Optional[str] = Field(default=None, description="Due date in ISO format")


class TaskUpdate(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    status: Optional[TaskStatus] = Field(default=None)
    priority: Optional[TaskPriority] = Field(default=None)
    due_date: Optional[str] = Field(default=None)


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    title: str
    description: str
    status: str
    priority: str
    due_date: Optional[str]
    created_at: str
    updated_at: str


# ============================================================================
# Database Manager
# ============================================================================
class DatabaseManager:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._connection: Optional[aiosqlite.Connection] = None

    async def connect(self) -> aiosqlite.Connection:
        """Establish database connection and initialize schema."""
        self._connection = await aiosqlite.connect(self.db_path)
        self._connection.row_factory = aiosqlite.Row
        await self._init_schema()
        return self._connection

    async def disconnect(self):
        """Close database connection."""
        if self._connection:
            await self._connection.close()
            self._connection = None

    async def _init_schema(self):
        """Initialize database schema."""
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'pending',
                priority TEXT NOT NULL DEFAULT 'medium',
                due_date TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)
        """)
        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority)
        """)
        await self._connection.commit()

    async def get_all_tasks(self, status_filter: Optional[str] = None) -> List[dict]:
        """Retrieve all tasks, optionally filtered by status."""
        query = "SELECT * FROM tasks"
        params = []
        
        if status_filter:
            query += " WHERE status = ?"
            params.append(status_filter)
        
        query += """ ORDER BY CASE priority 
            WHEN 'critical' THEN 1 
            WHEN 'high' THEN 2 
            WHEN 'medium' THEN 3 
            WHEN 'low' THEN 4 
        END, created_at DESC"""
        
        cursor = await self._connection.execute(query, params)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def get_task_by_id(self, task_id: int) -> Optional[dict]:
        """Retrieve a single task by ID."""
        cursor = await self._connection.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def create_task(self, task_data: dict) -> dict:
        """Create a new task."""
        now = datetime.utcnow().isoformat()
        task_data["created_at"] = now
        task_data["updated_at"] = now
        
        cursor = await self._connection.execute("""
            INSERT INTO tasks (title, description, status, priority, due_date, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            task_data["title"],
            task_data["description"],
            task_data["status"],
            task_data["priority"],
            task_data.get("due_date"),
            now,
            now
        ))
        await self._connection.commit()
        
        task_data["id"] = cursor.lastrowid
        return task_data

    async def update_task(self, task_id: int, update_data: dict) -> Optional[dict]:
        """Update an existing task."""
        existing = await self.get_task_by_id(task_id)
        if not existing:
            return None
        
        update_fields = []
        values = []
        
        for key, value in update_data.items():
            if value is not None:
                update_fields.append(f"{key} = ?")
                values.append(value)
        
        if not update_fields:
            return existing
        
        update_fields.append("updated_at = ?")
        values.append(datetime.utcnow().isoformat())
        values.append(task_id)
        
        query = f"UPDATE tasks SET {', '.join(update_fields)} WHERE id = ?"
        await self._connection.execute(query, values)
        await self._connection.commit()
        
        return await self.get_task_by_id(task_id)

    async def delete_task(self, task_id: int) -> bool:
        """Delete a task by ID."""
        cursor = await self._connection.execute(
            "DELETE FROM tasks WHERE id = ?", (task_id,)
        )
        await self._connection.commit()
        return cursor.rowcount > 0

    async def get_statistics(self) -> dict:
        """Get task statistics."""
        cursor = await self._connection.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END) as in_progress,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) as cancelled
            FROM tasks
        """)
        row = await cursor.fetchone()
        return dict(row)


# ============================================================================
# Lifespan Context Manager
# ============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events."""
    # Startup
    await db_manager.connect()
    TEMPLATES_DIR.mkdir(exist_ok=True)
    STATIC_DIR.mkdir(exist_ok=True)
    yield
    # Shutdown
    await db_manager.disconnect()


# ============================================================================
# FastAPI Application
# ============================================================================
app = FastAPI(
    title="Task Manager API",
    description="A comprehensive task management system with REST API",
    version="1.0.0",
    license_info={"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
    lifespan=lifespan
)

# Initialize database manager
db_manager = DatabaseManager(DATABASE_PATH)


# ============================================================================
# API Routes
# ============================================================================
@app.get("/api/tasks", response_model=List[TaskResponse], tags=["Tasks"])
async def list_tasks(status: Optional[TaskStatus] = None):
    """List all tasks, optionally filtered by status."""
    tasks = await db_manager.get_all_tasks(status.value if status else None)
    return tasks


@app.get("/api/tasks/{task_id}", response_model=TaskResponse, tags=["Tasks"])
async def get_task(task_id: int):
    """Get a specific task by ID."""
    task = await db_manager.get_task_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.post("/api/tasks", response_model=TaskResponse, status_code=201, tags=["Tasks"])
async def create_task(task: TaskCreate):
    """Create a new task."""
    task_data = task.model_dump()
    created_task = await db_manager.create_task(task_data)
    return created_task


@app.put("/api/tasks/{task_id}", response_model=TaskResponse, tags=["Tasks"])
async def update_task(task_id: int, task_update: TaskUpdate):
    """Update an existing task."""
    update_data = task_update.model_dump(exclude_unset=True)
    updated_task = await db_manager.update_task(task_id, update_data)
    if not updated_task:
        raise HTTPException(status_code=404, detail="Task not found")
    return updated_task


@app.patch("/api/tasks/{task_id}/status", response_model=TaskResponse, tags=["Tasks"])
async def update_task_status(task_id: int, status: TaskStatus):
    """Update only the status of a task."""
    updated_task = await db_manager.update_task(task_id, {"status": status.value})
    if not updated_task:
        raise HTTPException(status_code=404, detail="Task not found")
    return updated_task


@app.delete("/api/tasks/{task_id}", status_code=204, tags=["Tasks"])
async def delete_task(task_id: int):
    """Delete a task."""
    deleted = await db_manager.delete_task(task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")
    return None


@app.get("/api/statistics", tags=["Statistics"])
async def get_statistics():
    """Get task statistics."""
    stats = await db_manager.get_statistics()
    return stats


@app.get("/api/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


# ============================================================================
# Frontend Routes
# ============================================================================
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def index(request: Request):
    """Render the main page."""
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    return templates.TemplateResponse("index.html", {"request": request})


# ============================================================================
# Main Entry Point
# ============================================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
