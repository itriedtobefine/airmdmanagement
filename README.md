# TODO Application

A modern TODO application built with FastAPI (backend) and vanilla JavaScript (frontend), integrated with PostgreSQL database.

## 📁 Project Structure

```
/workspace
├── backend/
│   ├── main.py              # FastAPI application entry point
│   ├── database.py          # Database configuration and session management
│   ├── models.py            # SQLAlchemy ORM models
│   ├── schemas.py           # Pydantic schemas for validation
│   ├── crud.py              # Database operations (Create, Read, Update, Delete)
│   ├── test_main.py         # Pytest test suite
│   ├── requirements.txt     # Python dependencies
│   └── setup_and_run.sh     # Setup and run script
├── frontend/
│   └── index.html           # Single-page TODO application UI
└── README.md                # This file
```

## 🚀 Features

### Backend (FastAPI + PostgreSQL)
- RESTful API with full CRUD operations
- PostgreSQL database integration with SQLAlchemy ORM
- Request validation with Pydantic
- Automatic API documentation (Swagger UI)
- CORS support for frontend integration
- Pagination and filtering support
- Comprehensive test suite

### Frontend (Vanilla JavaScript)
- Modern, responsive UI with gradient design
- Real-time task management
- Filter tasks by status (All/Active/Completed)
- Task completion toggle
- Edit and delete functionality
- Task statistics display
- Error handling and user feedback

## 📋 Prerequisites

- Python 3.12+
- PostgreSQL 12+
- pip (Python package manager)
- A modern web browser

## 🛠️ Installation

### 1. Clone or navigate to the project directory

```bash
cd /workspace
```

### 2. Install Python dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 3. Set up PostgreSQL

#### Option A: Using Docker (Recommended)

```bash
docker run -d \
  --name todo-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=todo_db \
  -p 5432:5432 \
  postgres:15-alpine
```

#### Option B: Manual Installation

1. Install PostgreSQL from https://www.postgresql.org/download/
2. Create the database:

```sql
CREATE DATABASE todo_db;
```

### 4. Configure environment variables (optional)

The application uses these default values:

```bash
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/todo_db"
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=postgres
export POSTGRES_DB=todo_db
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
```

## ▶️ Running the Application

### Start the Backend

```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Or use the setup script:

```bash
cd backend
./setup_and_run.sh
```

### Access the API

- **API Base URL**: http://localhost:8000
- **Swagger Documentation**: http://localhost:8000/docs
- **ReDoc Documentation**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

### Open the Frontend

Simply open `frontend/index.html` in your web browser, or serve it with a local server:

```bash
# Using Python's built-in server
cd frontend
python -m http.server 3000
```

Then open http://localhost:3000 in your browser.

## 🧪 Running Tests

```bash
cd backend
pytest test_main.py -v
```

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/todos` | Get all todos (with pagination and filtering) |
| GET | `/todos/{id}` | Get a specific todo |
| POST | `/todos` | Create a new todo |
| PUT | `/todos/{id}` | Update a todo |
| PATCH | `/todos/{id}/toggle` | Toggle todo completion status |
| DELETE | `/todos/{id}` | Delete a todo |

### Query Parameters for GET /todos

- `skip` (int): Number of items to skip (default: 0)
- `limit` (int): Maximum items to return (default: 100, max: 1000)
- `completed` (bool): Filter by completion status (optional)

### Request/Response Examples

**Create Todo:**
```json
POST /todos
{
  "title": "Buy groceries",
  "description": "Milk, eggs, bread"
}
```

**Response:**
```json
{
  "id": 1,
  "title": "Buy groceries",
  "description": "Milk, eggs, bread",
  "completed": false,
  "created_at": "2026-01-15T10:30:00",
  "updated_at": "2026-01-15T10:30:00"
}
```

## 🔧 Configuration

### Database Configuration

The application reads the database connection string from the `DATABASE_URL` environment variable:

```
postgresql://username:password@host:port/database_name
```

### CORS Configuration

By default, CORS is enabled for all origins (`*`). For production, update the `allow_origins` list in `main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 🏗️ Architecture

### Backend Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   FastAPI   │────▶│  SQLAlchemy │────▶│ PostgreSQL  │
│   Routes    │     │    ORM      │     │  Database   │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │
       ▼                   ▼
┌─────────────┐     ┌─────────────┐
│  Pydantic   │     │    CRUD     │
│  Schemas    │     │  Operations │
└─────────────┘     └─────────────┘
```

### Data Flow

1. Client sends HTTP request to FastAPI endpoint
2. Request validated by Pydantic schemas
3. CRUD operations executed via SQLAlchemy ORM
4. Database queries executed on PostgreSQL
5. Response serialized and returned to client

## 📝 License

This project is licensed under the MIT License.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## 🐛 Troubleshooting

### Database Connection Error

Ensure PostgreSQL is running and the connection string is correct:

```bash
# Check if PostgreSQL is running
pg_isready -h localhost -p 5432

# Test connection
psql -h localhost -U postgres -d todo_db
```

### CORS Issues

If you're getting CORS errors, ensure the backend is running and CORS middleware is properly configured.

### Port Already in Use

Change the port in the uvicorn command:

```bash
uvicorn main:app --host 0.0.0.0 --port 8001
```

Then update `API_BASE_URL` in `frontend/index.html`.
