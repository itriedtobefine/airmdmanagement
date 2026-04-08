from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime


class TableCreate(BaseModel):
    name: str
    description: Optional[str] = None


class TableUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class TableResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ColumnCreate(BaseModel):
    table_id: int
    name: str
    column_type: str  # text, number, date, boolean, link_to_record, single_select, multi_select
    is_required: bool = False
    is_unique: bool = False
    default_value: Optional[str] = None
    options: Optional[Any] = None  # JSON for select options or linked table info
    validation_rule: Optional[str] = None
    position: int = 0


class ColumnUpdate(BaseModel):
    name: Optional[str] = None
    column_type: Optional[str] = None
    is_required: Optional[bool] = None
    is_unique: Optional[bool] = None
    default_value: Optional[str] = None
    options: Optional[Any] = None
    validation_rule: Optional[str] = None
    position: Optional[int] = None


class ColumnResponse(BaseModel):
    id: int
    table_id: int
    name: str
    column_type: str
    is_required: bool
    is_unique: bool
    default_value: Optional[str] = None
    options: Optional[Any] = None
    validation_rule: Optional[str] = None
    position: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class CellValueInput(BaseModel):
    column_id: int
    value: Any


class RecordCreate(BaseModel):
    table_id: int
    values: List[CellValueInput] = []


class RecordUpdate(BaseModel):
    values: List[CellValueInput] = []


class CellValueResponse(BaseModel):
    id: int
    column_id: int
    value: Optional[Any] = None
    
    class Config:
        from_attributes = True


class RecordResponse(BaseModel):
    id: int
    table_id: int
    values: List[CellValueResponse] = []
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
