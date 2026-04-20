"""
Схемы Pydantic для валидации данных API.
"""
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
from datetime import datetime


# === User Schemas ===
class UserBase(BaseModel):
    username: str
    email: EmailStr


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# === Spreadsheet Schemas ===
class CellData(BaseModel):
    value: Optional[str] = None
    formula: Optional[str] = None
    style: Optional[Dict[str, Any]] = None


class SpreadsheetData(BaseModel):
    cells: Dict[str, CellData] = {}


class SpreadsheetBase(BaseModel):
    name: str
    description: Optional[str] = ""


class SpreadsheetCreate(SpreadsheetBase):
    pass


class SpreadsheetUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    data: Optional[SpreadsheetData] = None


class SpreadsheetResponse(SpreadsheetBase):
    id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime
    data: Dict[str, Any]

    class Config:
        from_attributes = True


class CellUpdate(BaseModel):
    cell_address: str  # Например, "A1"
    value: Optional[str] = None
    formula: Optional[str] = None
    style: Optional[Dict[str, Any]] = None


class CellHistoryResponse(BaseModel):
    id: int
    spreadsheet_id: int
    cell_address: str
    old_value: Optional[Dict[str, Any]]
    new_value: Optional[Dict[str, Any]]
    changed_at: datetime

    class Config:
        from_attributes = True


# === Auth Schemas ===
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None
