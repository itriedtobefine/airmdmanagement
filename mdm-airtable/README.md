# MDM AirTable Clone

Master Data Management (MDM) system with flexible tables and relationships, inspired by AirTable.

## Features

- **Dynamic Table Creation**: Create unlimited tables with custom schemas
- **Flexible Column Types**: 
  - Text
  - Number
  - Date
  - Boolean (Checkbox)
  - Single Select (Dropdown)
  - Multi Select
  - Link to Record (1:1 and 1:N relationships)
- **Data Quality Management**:
  - Required fields validation
  - Unique value constraints
  - Regex-based validation rules
  - Default values
- **CRUD Operations**: Full create, read, update, delete for tables, columns, and records
- **CSV Import/Export**: Bulk data import and export functionality
- **Lazy Loading**: Pagination support for large datasets (100 records per page)
- **Web Interface**: Modern React-based UI with inline editing
- **Administration Panel**: Manage table structure and column definitions

## Architecture

### Backend (FastAPI + SQLAlchemy + SQLite)
- RESTful API with OpenAPI documentation
- Dynamic schema management using metadata tables
- Data validation at API level
- SQLite database (can be switched to PostgreSQL)

### Frontend (React + Vite)
- Component-based architecture
- React Router for navigation
- Axios for API communication
- Inline cell editing
- Modal dialogs for complex operations

## Project Structure

```
mdm-airtable/
├── backend/
│   ├── app/
│   │   ├── db/
│   │   │   ├── database.py    # DB connection & session management
│   │   │   └── models.py      # SQLAlchemy models
│   │   ├── routers/
│   │   │   └── api.py         # API endpoints
│   │   ├── schemas/
│   │   │   └── schemas.py     # Pydantic schemas
│   │   ├── services/
│   │   │   └── data_service.py # Business logic
│   │   └── main.py            # FastAPI app entry point
│   ├── requirements.txt
│   └── mdm.db                 # SQLite database
└── frontend/
    ├── src/
    │   ├── api/
    │   │   └── api.js         # API client
    │   ├── components/
    │   │   ├── CreateTableModal.jsx
    │   │   └── CreateColumnModal.jsx
    │   ├── pages/
    │   │   ├── Home.jsx
    │   │   └── TableView.jsx
    │   ├── App.jsx
    │   └── main.jsx
    └── package.json
```

## Quick Start

### Prerequisites
- Python 3.9+
- Node.js 16+
- npm or yarn

### Backend Setup

```bash
cd backend

# Create virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`
API documentation: `http://localhost:8000/docs`

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

The frontend will be available at `http://localhost:5173`

## API Endpoints

### Tables
- `GET /api/v1/tables` - List all tables
- `POST /api/v1/tables` - Create a new table
- `GET /api/v1/tables/{id}` - Get table details
- `PUT /api/v1/tables/{id}` - Update table
- `DELETE /api/v1/tables/{id}` - Delete table
- `POST /api/v1/tables/{id}/import-csv` - Import CSV data
- `GET /api/v1/tables/{id}/export-csv` - Export table to CSV

### Columns
- `POST /api/v1/columns` - Create a new column
- `GET /api/v1/tables/{tableId}/columns` - Get all columns for a table
- `GET /api/v1/columns/{id}` - Get column details
- `PUT /api/v1/columns/{id}` - Update column
- `DELETE /api/v1/columns/{id}` - Delete column

### Records
- `POST /api/v1/records` - Create a new record
- `GET /api/v1/tables/{tableId}/records` - Get records with pagination
- `GET /api/v1/records/{id}` - Get record details
- `PUT /api/v1/records/{id}` - Update record
- `DELETE /api/v1/records/{id}` - Delete record

## Usage Guide

### Creating a Table
1. Click "Create New Table" on the home page
2. Enter table name and optional description
3. Click "Create Table"

### Adding Columns
1. Open the table
2. Click "⚙️ Administration" button
3. Click "+ Add Column"
4. Configure column properties:
   - Name
   - Type (text, number, date, etc.)
   - Required/Unique constraints
   - Validation rules (regex)
   - Options (for select types)
   - Linked table (for link_to_record type)

### Managing Data
- Click on any cell to edit its value
- Press Enter or click outside to save
- Click "+ Add Record" to add new rows
- Click "Delete" to remove records

### CSV Import
1. Open the target table
2. Click "Import CSV"
3. Select a CSV file (headers must match column names)
4. Review import results

### CSV Export
1. Open the table
2. Click "Export CSV"
3. File will be downloaded automatically

## Data Quality Features

### Validation Rules
Use regex patterns to validate data:
- Email: `^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$`
- Phone: `^\+?[0-9\s\-()]+$`
- Custom codes: `^[A-Z]{3}-\d{4}$`

### Unique Constraints
Enable "Unique values" to prevent duplicates in a column.

### Required Fields
Enable "Required field" to ensure data completeness.

## Relationships

### 1:1 Relationship
Create a "Link to Record" column and link to another table. Each record can link to one record in the target table.

### 1:N Relationship
Create a "Link to Record" column in the "many" side table pointing to the "one" side table.

## Testing

### Backend Tests
```bash
cd backend
pytest
```

### Frontend Tests
```bash
cd frontend
npm test
```

## Production Deployment

### Backend
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

Consider:
- Using PostgreSQL instead of SQLite
- Setting up proper CORS origins
- Adding authentication/authorization
- Using environment variables for configuration

### Frontend
```bash
npm run build
# Deploy the dist/ folder to your web server
```

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
