from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from ..db.database import get_db
from ..schemas.schemas import (
    TableCreate, TableUpdate, TableResponse,
    ColumnCreate, ColumnUpdate, ColumnResponse,
    RecordCreate, RecordUpdate, RecordResponse, CellValueResponse
)
from ..services.data_service import TableService, ColumnService, RecordService

router = APIRouter()


# Table endpoints
@router.post("/tables", response_model=TableResponse)
def create_table(table_data: TableCreate, db: Session = Depends(get_db)):
    """Create a new table"""
    try:
        return TableService.create_table(db, table_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/tables", response_model=List[TableResponse])
def get_tables(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all tables"""
    return TableService.get_tables(db, skip, limit)


@router.get("/tables/{table_id}", response_model=TableResponse)
def get_table(table_id: int, db: Session = Depends(get_db)):
    """Get a specific table"""
    db_table = TableService.get_table(db, table_id)
    if not db_table:
        raise HTTPException(status_code=404, detail="Table not found")
    return db_table


@router.put("/tables/{table_id}", response_model=TableResponse)
def update_table(table_id: int, table_data: TableUpdate, db: Session = Depends(get_db)):
    """Update a table"""
    db_table = TableService.update_table(db, table_id, table_data)
    if not db_table:
        raise HTTPException(status_code=404, detail="Table not found")
    return db_table


@router.delete("/tables/{table_id}")
def delete_table(table_id: int, db: Session = Depends(get_db)):
    """Delete a table"""
    success = TableService.delete_table(db, table_id)
    if not success:
        raise HTTPException(status_code=404, detail="Table not found")
    return {"message": "Table deleted successfully"}


# Column endpoints
@router.post("/columns", response_model=ColumnResponse)
def create_column(column_data: ColumnCreate, db: Session = Depends(get_db)):
    """Create a new column in a table"""
    try:
        return ColumnService.create_column(db, column_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/tables/{table_id}/columns", response_model=List[ColumnResponse])
def get_columns(table_id: int, db: Session = Depends(get_db)):
    """Get all columns for a table"""
    return ColumnService.get_columns(db, table_id)


@router.get("/columns/{column_id}", response_model=ColumnResponse)
def get_column(column_id: int, db: Session = Depends(get_db)):
    """Get a specific column"""
    db_column = ColumnService.get_column(db, column_id)
    if not db_column:
        raise HTTPException(status_code=404, detail="Column not found")
    return db_column


@router.put("/columns/{column_id}", response_model=ColumnResponse)
def update_column(column_id: int, column_data: ColumnUpdate, db: Session = Depends(get_db)):
    """Update a column"""
    db_column = ColumnService.update_column(db, column_id, column_data)
    if not db_column:
        raise HTTPException(status_code=404, detail="Column not found")
    return db_column


@router.delete("/columns/{column_id}")
def delete_column(column_id: int, db: Session = Depends(get_db)):
    """Delete a column"""
    success = ColumnService.delete_column(db, column_id)
    if not success:
        raise HTTPException(status_code=404, detail="Column not found")
    return {"message": "Column deleted successfully"}


# Record endpoints
@router.post("/records", response_model=RecordResponse)
def create_record(record_data: RecordCreate, db: Session = Depends(get_db)):
    """Create a new record in a table"""
    try:
        return RecordService.create_record(db, record_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/tables/{table_id}/records", response_model=List[dict])
def get_records(table_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all records for a table with their cell values"""
    records = RecordService.get_records(db, table_id, skip, limit)
    
    # Format records with cell values
    formatted_records = []
    for record in records:
        values = []
        for cell in record.values:
            value = None
            column = cell.column
            if column.column_type == "number":
                value = cell.value_number
            elif column.column_type == "boolean":
                value = cell.value_boolean
            elif column.column_type == "date":
                value = cell.value_date.isoformat() if cell.value_date else None
            else:
                value = cell.value_text
            
            values.append({"id": cell.id, "column_id": cell.column_id, "value": value})
        
        formatted_records.append({
            "id": record.id,
            "table_id": record.table_id,
            "values": values,
            "created_at": record.created_at,
            "updated_at": record.updated_at
        })
    
    return formatted_records


@router.get("/records/{record_id}", response_model=dict)
def get_record(record_id: int, db: Session = Depends(get_db)):
    """Get a specific record with its cell values"""
    db_record = RecordService.get_record(db, record_id)
    if not db_record:
        raise HTTPException(status_code=404, detail="Record not found")
    
    # Format record with cell values
    values = []
    for cell in db_record.values:
        value = None
        column = cell.column
        if column.column_type == "number":
            value = cell.value_number
        elif column.column_type == "boolean":
            value = cell.value_boolean
        elif column.column_type == "date":
            value = cell.value_date.isoformat() if cell.value_date else None
        else:
            value = cell.value_text
        
        values.append({"id": cell.id, "column_id": cell.column_id, "value": value})
    
    return {
        "id": db_record.id,
        "table_id": db_record.table_id,
        "values": values,
        "created_at": db_record.created_at,
        "updated_at": db_record.updated_at
    }


@router.put("/records/{record_id}", response_model=dict)
def update_record(record_id: int, record_data: RecordUpdate, db: Session = Depends(get_db)):
    """Update a record"""
    db_record = RecordService.get_record(db, record_id)
    if not db_record:
        raise HTTPException(status_code=404, detail="Record not found")
    
    try:
        updated_record = RecordService.update_record(db, record_id, record_data, db_record.table_id)
        
        # Format record with cell values
        values = []
        for cell in updated_record.values:
            value = None
            column = cell.column
            if column.column_type == "number":
                value = cell.value_number
            elif column.column_type == "boolean":
                value = cell.value_boolean
            elif column.column_type == "date":
                value = cell.value_date.isoformat() if cell.value_date else None
            else:
                value = cell.value_text
            
            values.append({"id": cell.id, "column_id": cell.column_id, "value": value})
        
        return {
            "id": updated_record.id,
            "table_id": updated_record.table_id,
            "values": values,
            "created_at": updated_record.created_at,
            "updated_at": updated_record.updated_at
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/records/{record_id}")
def delete_record(record_id: int, db: Session = Depends(get_db)):
    """Delete a record"""
    success = RecordService.delete_record(db, record_id)
    if not success:
        raise HTTPException(status_code=404, detail="Record not found")
    return {"message": "Record deleted successfully"}
