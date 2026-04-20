# Task Manager Application

A comprehensive task management system with a modern web interface and REST API.

## Features

- **Full CRUD Operations**: Create, Read, Update, Delete tasks
- **Task Management**: 
  - Priority levels (Low, Medium, High, Critical)
  - Status tracking (Pending, In Progress, Completed, Cancelled)
  - Due dates
  - Descriptions
- **Real-time Statistics**: Dashboard showing task counts by status
- **Filtering**: Filter tasks by status
- **Responsive Design**: Works on desktop and mobile devices
- **RESTful API**: Full JSON API for integration

## Technology Stack

### Backend
- **Python 3.12+**
- **FastAPI** - Modern async web framework
- **SQLite** with **aiosqlite** - Async database operations
- **Pydantic** - Data validation
- **Jinja2** - Template rendering

### Frontend
- **Vanilla JavaScript** - No build step required
- **CSS3** - Modern styling with CSS variables
- **HTML5** - Semantic markup

## Project Structure

```
backend/
├── main.py              # FastAPI application and database logic
├── templates/
│   └── index.html       # Frontend HTML/CSS/JS
├── static/              # Static files directory
├── tests/
│   ├── __init__.py
│   └── test_app.py      # Unit and integration tests
├── requirements.txt     # Python dependencies
└── tasks.db            # SQLite database (created on first run)
```

## Installation

### Prerequisites
- Python 3.12 or higher
- pip package manager

### Step 1: Clone or Download
```bash
cd /workspace/backend
```

### Step 2: Create Virtual Environment (Optional but Recommended)

#### Linux/macOS:
```bash
python3 -m venv venv
source venv/bin/activate
```

#### Windows:
```bash
python -m venv venv
venv\Scripts\activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Run the Application
```bash
python main.py
```

The application will start on `http://localhost:8000`

## API Endpoints

### Health Check
```
GET /api/health
```

### Tasks
```
GET    /api/tasks              # List all tasks
GET    /api/tasks?status=X     # Filter by status
POST   /api/tasks              # Create new task
GET    /api/tasks/{id}         # Get specific task
PUT    /api/tasks/{id}         # Update task
PATCH  /api/tasks/{id}/status  # Update task status only
DELETE /api/tasks/{id}         # Delete task
```

### Statistics
```
GET /api/statistics
```

## API Examples

### Create a Task
```bash
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Complete project",
    "description": "Finish the task manager application",
    "priority": "high",
    "status": "pending",
    "due_date": "2026-12-31"
  }'
```

### Get All Tasks
```bash
curl http://localhost:8000/api/tasks
```

### Update Task Status
```bash
curl -X PATCH "http://localhost:8000/api/tasks/1/status?status=completed"
```

### Get Statistics
```bash
curl http://localhost:8000/api/statistics
```

## Running Tests

### Install Test Dependencies
```bash
pip install pytest pytest-asyncio httpx
```

### Run All Tests
```bash
cd backend
pytest tests/ -v
```

### Run Specific Test File
```bash
pytest tests/test_app.py -v
```

## Configuration

The application uses sensible defaults:
- **Database**: SQLite file at `backend/tasks.db`
- **Port**: 8000
- **Host**: 0.0.0.0 (all interfaces)

To change the port, modify the `uvicorn.run()` call in `main.py`:
```python
uvicorn.run(app, host="0.0.0.0", port=8080)
```

## License

MIT License - See LICENSE file for details.

## Support

For issues or questions, please check the documentation or review the source code comments.
