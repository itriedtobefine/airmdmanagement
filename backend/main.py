"""
Main FastAPI application entry point for TimeTracker Pro.
Configures the API, CORS, and includes all routers.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import json
import os

from .database import init_db, engine, Base
from .routers import users, projects, tasks, time_entries

# Load configuration
config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
with open(config_path, 'r') as f:
    config = json.load(f)

# Create FastAPI application
app = FastAPI(
    title="TimeTracker Pro API",
    description="""
## TimeTracker Pro - Task Management with Time and Cost Tracking

A comprehensive API for managing projects, tasks, and tracking time with automatic cost calculations.

### Features

* **User Management** - Create and manage users with hourly rates
* **Project Management** - Organize work into projects with budgets
* **Task Management** - Break down projects into trackable tasks
* **Time Tracking** - Start/stop timers and track work duration
* **Cost Calculation** - Automatic cost calculation based on time and hourly rates
* **Reports & Analytics** - Get summaries and insights on project costs

### Quick Start

1. Create a user
2. Create a project for that user
3. Create tasks within the project
4. Start tracking time on tasks
5. Stop tracking to calculate costs
6. View summaries and reports
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize database tables on application startup."""
    # Create all tables
    Base.metadata.create_all(bind=engine)


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "TimeTracker Pro API",
        "version": "1.0.0",
        "description": "Task Management with Time and Cost Tracking",
        "docs": "/docs",
        "endpoints": {
            "users": "/api/users",
            "projects": "/api/projects",
            "tasks": "/api/tasks",
            "time_entries": "/api/time-entries"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "service": "timetracker-pro-api"
    }


# Include routers
app.include_router(users.router)
app.include_router(projects.router)
app.include_router(tasks.router)
app.include_router(time_entries.router)


if __name__ == "__main__":
    import uvicorn
    backend_config = config.get('backend', {})
    host = backend_config.get('host', '0.0.0.0')
    port = backend_config.get('port', 8000)
    
    uvicorn.run(
        "backend.main:app",
        host=host,
        port=port,
        reload=backend_config.get('debug', False)
    )
