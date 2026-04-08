from sqlalchemy.orm import Session
from sqlalchemy import and_
import json
import re
from typing import Any, Dict, List, Optional

from ..db.models import Table, TableColumn as Column, Record, CellValue, LinkedRecord
from ..schemas.schemas import (
    TableCreate, TableUpdate,
    ColumnCreate, ColumnUpdate,
    RecordCreate, RecordUpdate, CellValueInput
)


class TableService:
    @staticmethod
    def create_table(db: Session, table_data: TableCreate) -> Table:
        db_table = Table(**table_data.model_dump())
        db.add(db_table)
        db.commit()
        db.refresh(db_table)
        return db_table
    
    @staticmethod
    def get_tables(db: Session, skip: int = 0, limit: int = 100) -> List[Table]:
        return db.query(Table).offset(skip).limit(limit).all()
    
    @staticmethod
    def get_table(db: Session, table_id: int) -> Optional[Table]:
        return db.query(Table).filter(Table.id == table_id).first()
    
    @staticmethod
    def update_table(db: Session, table_id: int, table_data: TableUpdate) -> Optional[Table]:
        db_table = db.query(Table).filter(Table.id == table_id).first()
        if db_table:
            for key, value in table_data.model_dump(exclude_unset=True).items():
                setattr(db_table, key, value)
            db.commit()
            db.refresh(db_table)
        return db_table
    
    @staticmethod
    def delete_table(db: Session, table_id: int) -> bool:
        db_table = db.query(Table).filter(Table.id == table_id).first()
        if db_table:
            db.delete(db_table)
            db.commit()
            return True
        return False


class ColumnService:
    @staticmethod
    def validate_column_data(column_type: str, value: Any, validation_rule: Optional[str], 
                            options: Optional[Any], is_required: bool) -> tuple[bool, str]:
        """Validate cell value based on column configuration"""
        if value is None or value == "":
            if is_required:
                return False, f"Value is required"
            return True, ""
        
        if column_type == "text":
            if not isinstance(value, str):
                return False, "Value must be text"
            if validation_rule:
                try:
                    if not re.match(validation_rule, str(value)):
                        return False, f"Value does not match validation rule: {validation_rule}"
                except re.error:
                    return False, "Invalid validation rule"
        
        elif column_type == "number":
            try:
                float(value)
            except (ValueError, TypeError):
                return False, "Value must be a number"
        
        elif column_type == "boolean":
            if not isinstance(value, bool):
                return False, "Value must be boolean"
        
        elif column_type == "date":
            # Basic date validation - could be enhanced
            if not isinstance(value, str):
                return False, "Date must be string"
        
        elif column_type in ["single_select", "multi_select"]:
            if options:
                try:
                    opts = json.loads(options) if isinstance(options, str) else options
                    if column_type == "single_select":
                        if value not in opts:
                            return False, f"Value must be one of: {opts}"
                    else:  # multi_select
                        if isinstance(value, list):
                            for v in value:
                                if v not in opts:
                                    return False, f"All values must be in options: {opts}"
                        else:
                            return False, "Multi-select value must be a list"
                except json.JSONDecodeError:
                    return False, "Invalid options format"
        
        elif column_type == "link_to_record":
            if options:
                try:
                    linked_table_id = json.loads(options) if isinstance(options, str) else options
                    if not isinstance(value, int):
                        return False, "Linked record value must be record ID"
                    # Could verify the linked record exists here
                except json.JSONDecodeError:
                    return False, "Invalid linked table configuration"
        
        return True, ""
    
    @staticmethod
    def create_column(db: Session, column_data: ColumnCreate) -> Column:
        # Validate column name uniqueness within table
        existing = db.query(Column).filter(
            and_(Column.table_id == column_data.table_id, Column.name == column_data.name)
        ).first()
        if existing:
            raise ValueError(f"Column '{column_data.name}' already exists in this table")
        
        options_json = None
        if column_data.options is not None:
            options_json = json.dumps(column_data.options) if not isinstance(column_data.options, str) else column_data.options
        
        db_column = Column(
            **column_data.model_dump(exclude={'options'}),
            options=options_json
        )
        db.add(db_column)
        db.commit()
        db.refresh(db_column)
        return db_column
    
    @staticmethod
    def get_columns(db: Session, table_id: int) -> List[Column]:
        return db.query(Column).filter(Column.table_id == table_id).order_by(Column.position).all()
    
    @staticmethod
    def get_column(db: Session, column_id: int) -> Optional[Column]:
        return db.query(Column).filter(Column.id == column_id).first()
    
    @staticmethod
    def update_column(db: Session, column_id: int, column_data: ColumnUpdate) -> Optional[Column]:
        db_column = db.query(Column).filter(Column.id == column_id).first()
        if db_column:
            update_data = column_data.model_dump(exclude_unset=True)
            if 'options' in update_data and update_data['options'] is not None:
                update_data['options'] = json.dumps(update_data['options']) if not isinstance(update_data['options'], str) else update_data['options']
            for key, value in update_data.items():
                setattr(db_column, key, value)
            db.commit()
            db.refresh(db_column)
        return db_column
    
    @staticmethod
    def delete_column(db: Session, column_id: int) -> bool:
        db_column = db.query(Column).filter(Column.id == column_id).first()
        if db_column:
            db.delete(db_column)
            db.commit()
            return True
        return False


class RecordService:
    @staticmethod
    def create_record(db: Session, record_data: RecordCreate) -> Record:
        db_record = Record(table_id=record_data.table_id)
        db.add(db_record)
        db.commit()
        db.refresh(db_record)
        
        # Add cell values
        if record_data.values:
            for cell_input in record_data.values:
                column = db.query(Column).filter(Column.id == cell_input.column_id).first()
                if not column:
                    continue
                
                # Validate data quality
                is_valid, error_msg = ColumnService.validate_column_data(
                    column.column_type,
                    cell_input.value,
                    column.validation_rule,
                    column.options,
                    column.is_required
                )
                
                if not is_valid:
                    raise ValueError(f"Validation failed for column '{column.name}': {error_msg}")
                
                # Check uniqueness constraint
                if column.is_unique and cell_input.value is not None:
                    existing = db.query(CellValue).join(Record).filter(
                        and_(
                            CellValue.column_id == column.id,
                            CellValue.record_id != db_record.id,
                            Record.table_id == record_data.table_id
                        )
                    ).first()
                    
                    # Get existing value for comparison
                    existing_value = None
                    if existing:
                        if column.column_type == "number":
                            existing_value = existing.value_number
                        elif column.column_type == "boolean":
                            existing_value = existing.value_boolean
                        elif column.column_type == "date":
                            existing_value = existing.value_date
                        else:
                            existing_value = existing.value_text
                    
                    if existing_value == cell_input.value:
                        raise ValueError(f"Duplicate value '{cell_input.value}' in unique column '{column.name}'")
                
                # Create cell value based on column type
                db_cell = CellValue(record_id=db_record.id, column_id=cell_input.column_id)
                
                if column.column_type == "number":
                    db_cell.value_number = int(cell_input.value) if cell_input.value is not None else None
                elif column.column_type == "boolean":
                    db_cell.value_boolean = cell_input.value
                elif column.column_type == "date":
                    from datetime import datetime
                    if cell_input.value:
                        try:
                            db_cell.value_date = datetime.fromisoformat(cell_input.value.replace('Z', '+00:00'))
                        except:
                            db_cell.value_date = None
                else:
                    db_cell.value_text = str(cell_input.value) if cell_input.value is not None else None
                
                db.add(db_cell)
            
            db.commit()
            db.refresh(db_record)
        
        return db_record
    
    @staticmethod
    def get_records(db: Session, table_id: int, skip: int = 0, limit: int = 100) -> List[Record]:
        return db.query(Record).filter(Record.table_id == table_id).offset(skip).limit(limit).all()
    
    @staticmethod
    def get_record(db: Session, record_id: int) -> Optional[Record]:
        return db.query(Record).filter(Record.id == record_id).first()
    
    @staticmethod
    def update_record(db: Session, record_id: int, record_data: RecordUpdate, table_id: int) -> Optional[Record]:
        db_record = db.query(Record).filter(Record.id == record_id).first()
        if not db_record:
            return None
        
        # Update cell values
        if record_data.values:
            for cell_input in record_data.values:
                column = db.query(Column).filter(Column.id == cell_input.column_id).first()
                if not column:
                    continue
                
                # Validate data quality
                is_valid, error_msg = ColumnService.validate_column_data(
                    column.column_type,
                    cell_input.value,
                    column.validation_rule,
                    column.options,
                    column.is_required
                )
                
                if not is_valid:
                    raise ValueError(f"Validation failed for column '{column.name}': {error_msg}")
                
                # Get or create cell value
                db_cell = db.query(CellValue).filter(
                    and_(CellValue.record_id == record_id, CellValue.column_id == cell_input.column_id)
                ).first()
                
                if not db_cell:
                    db_cell = CellValue(record_id=record_id, column_id=cell_input.column_id)
                    db.add(db_cell)
                
                # Update value based on column type
                if column.column_type == "number":
                    db_cell.value_number = int(cell_input.value) if cell_input.value is not None else None
                    db_cell.value_text = None
                    db_cell.value_boolean = None
                    db_cell.value_date = None
                elif column.column_type == "boolean":
                    db_cell.value_boolean = cell_input.value
                    db_cell.value_text = None
                    db_cell.value_number = None
                    db_cell.value_date = None
                elif column.column_type == "date":
                    from datetime import datetime
                    if cell_input.value:
                        try:
                            db_cell.value_date = datetime.fromisoformat(cell_input.value.replace('Z', '+00:00'))
                        except:
                            db_cell.value_date = None
                    else:
                        db_cell.value_date = None
                    db_cell.value_text = None
                    db_cell.value_number = None
                    db_cell.value_boolean = None
                else:
                    db_cell.value_text = str(cell_input.value) if cell_input.value is not None else None
                    db_cell.value_number = None
                    db_cell.value_boolean = None
                    db_cell.value_date = None
            
            db.commit()
            db.refresh(db_record)
        
        return db_record
    
    @staticmethod
    def delete_record(db: Session, record_id: int) -> bool:
        db_record = db.query(Record).filter(Record.id == record_id).first()
        if db_record:
            db.delete(db_record)
            db.commit()
            return True
        return False
