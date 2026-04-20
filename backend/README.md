# TimeTracker Pro Backend

## Setup Instructions

### 1. Create Virtual Environment

**Linux/macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Database

Make sure PostgreSQL is running and the database exists:

```bash
# Create database (if using PostgreSQL)
createdb timetracker_db
```

Or update `config.json` with your database credentials.

### 4. Run the Server

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Access API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

See the main README.md for complete API documentation.
