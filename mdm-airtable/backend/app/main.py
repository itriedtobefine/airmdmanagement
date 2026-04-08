from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import csv
import io
import json

from .db.database import init_db, get_db
from .routers import api

app = FastAPI(title="MDM AirTable Clone", description="Master Data Management system with flexible tables and relationships")

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(api.router, prefix="/api/v1", tags=["MDM"])


@app.on_event("startup")
def startup_event():
    init_db()


@app.get("/")
def read_root():
    return {
        "message": "MDM AirTable Clone API",
        "docs": "/docs",
        "endpoints": {
            "tables": "/api/v1/tables",
            "columns": "/api/v1/columns",
            "records": "/api/v1/records"
        }
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/api/v1/tables/{table_id}/import-csv")
async def import_csv_to_table(table_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Import CSV data into a table"""
    from ..services.data_service import RecordService, ColumnService
    from ..schemas.schemas import RecordCreate, CellValueInput
    
    try:
        # Read CSV content
        content = await file.read()
        csv_content = content.decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        
        # Get columns for this table
        columns = ColumnService.get_columns(db, table_id)
        column_map = {col.name: col for col in columns}
        
        imported_count = 0
        errors = []
        
        for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 (header is row 1)
            try:
                values = []
                for col_name, cell_value in row.items():
                    if col_name in column_map:
                        column = column_map[col_name]
                        # Convert value based on column type
                        converted_value = cell_value
                        if column.column_type == "number" and cell_value:
                            try:
                                converted_value = float(cell_value)
                            except ValueError:
                                converted_value = None
                        elif column.column_type == "boolean":
                            converted_value = cell_value.lower() in ['true', 'yes', '1'] if cell_value else False
                        elif column.column_type == "date":
                            pass  # Keep as string, will be parsed by service
                        
                        if cell_value or column.is_required:
                            values.append(CellValueInput(column_id=column.id, value=converted_value if converted_value != "" else None))
                
                if values:
                    record_data = RecordCreate(table_id=table_id, values=values)
                    RecordService.create_record(db, record_data)
                    imported_count += 1
            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")
        
        db.commit()
        return {
            "imported": imported_count,
            "errors": errors[:10]  # Return first 10 errors
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"CSV import failed: {str(e)}")


@app.get("/api/v1/tables/{table_id}/export-csv")
async def export_table_to_csv(table_id: int, db: Session = Depends(get_db)):
    """Export table data to CSV"""
    from ..services.data_service import RecordService, ColumnService
    
    # Get columns and records
    columns = ColumnService.get_columns(db, table_id)
    records = RecordService.get_records(db, table_id, skip=0, limit=10000)
    
    # Create CSV content
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    headers = [col.name for col in columns]
    writer.writerow(headers)
    
    # Write data rows
    for record in records:
        row = []
        cell_values = {cell.column_id: cell for cell in record.values}
        for col in columns:
            cell = cell_values.get(col.id)
            value = ""
            if cell:
                if col.column_type == "number":
                    value = cell.value_number if cell.value_number is not None else ""
                elif col.column_type == "boolean":
                    value = cell.value_boolean if cell.value_boolean is not None else ""
                elif col.column_type == "date":
                    value = cell.value_date.isoformat() if cell.value_date else ""
                else:
                    value = cell.value_text if cell.value_text else ""
            row.append(value)
        writer.writerow(row)
    
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=table_{table_id}.csv"}
    )
