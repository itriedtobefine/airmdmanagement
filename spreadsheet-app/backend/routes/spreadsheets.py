"""
Маршруты API для работы с таблицами.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

import models
import schemas
from database import get_db
from routes.auth import get_current_user

router = APIRouter(prefix="/spreadsheets", tags=["spreadsheets"])


@router.post("/", response_model=schemas.SpreadsheetResponse)
def create_spreadsheet(
    spreadsheet_data: schemas.SpreadsheetCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Создание новой таблицы."""
    db_spreadsheet = models.Spreadsheet(
        name=spreadsheet_data.name,
        description=spreadsheet_data.description or "",
        owner_id=current_user.id,
        data={"cells": {}}
    )
    
    db.add(db_spreadsheet)
    db.commit()
    db.refresh(db_spreadsheet)
    
    return db_spreadsheet


@router.get("/", response_model=List[schemas.SpreadsheetResponse])
def get_spreadsheets(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Получение списка таблиц пользователя."""
    spreadsheets = db.query(models.Spreadsheet).filter(
        models.Spreadsheet.owner_id == current_user.id
    ).offset(skip).limit(limit).all()
    
    return spreadsheets


@router.get("/{spreadsheet_id}", response_model=schemas.SpreadsheetResponse)
def get_spreadsheet(
    spreadsheet_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Получение таблицы по ID."""
    spreadsheet = db.query(models.Spreadsheet).filter(
        models.Spreadsheet.id == spreadsheet_id,
        models.Spreadsheet.owner_id == current_user.id
    ).first()
    
    if not spreadsheet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Spreadsheet not found"
        )
    
    return spreadsheet


@router.put("/{spreadsheet_id}", response_model=schemas.SpreadsheetResponse)
def update_spreadsheet(
    spreadsheet_id: int,
    spreadsheet_update: schemas.SpreadsheetUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Обновление таблицы."""
    spreadsheet = db.query(models.Spreadsheet).filter(
        models.Spreadsheet.id == spreadsheet_id,
        models.Spreadsheet.owner_id == current_user.id
    ).first()
    
    if not spreadsheet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Spreadsheet not found"
        )
    
    # Обновление полей
    if spreadsheet_update.name is not None:
        spreadsheet.name = spreadsheet_update.name
    if spreadsheet_update.description is not None:
        spreadsheet.description = spreadsheet_update.description
    if spreadsheet_update.data is not None:
        spreadsheet.data = spreadsheet_update.data.model_dump()
    
    db.commit()
    db.refresh(spreadsheet)
    
    return spreadsheet


@router.delete("/{spreadsheet_id}")
def delete_spreadsheet(
    spreadsheet_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Удаление таблицы."""
    spreadsheet = db.query(models.Spreadsheet).filter(
        models.Spreadsheet.id == spreadsheet_id,
        models.Spreadsheet.owner_id == current_user.id
    ).first()
    
    if not spreadsheet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Spreadsheet not found"
        )
    
    db.delete(spreadsheet)
    db.commit()
    
    return {"message": "Spreadsheet deleted successfully"}


@router.put("/{spreadsheet_id}/cells/{cell_address}", response_model=schemas.SpreadsheetResponse)
def update_cell(
    spreadsheet_id: int,
    cell_address: str,
    cell_update: schemas.CellUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Обновление ячейки в таблице."""
    spreadsheet = db.query(models.Spreadsheet).filter(
        models.Spreadsheet.id == spreadsheet_id,
        models.Spreadsheet.owner_id == current_user.id
    ).first()
    
    if not spreadsheet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Spreadsheet not found"
        )
    
    # Инициализация данных, если пустые
    if not spreadsheet.data:
        spreadsheet.data = {"cells": {}}
    
    cells = spreadsheet.data.get("cells", {})
    
    # Сохранение истории
    old_value = cells.get(cell_address)
    
    # Обновление ячейки
    cell_data = {
        "value": cell_update.value,
        "formula": cell_update.formula,
        "style": cell_update.style or {}
    }
    cells[cell_address] = {k: v for k, v in cell_data.items() if v is not None}
    
    spreadsheet.data["cells"] = cells
    
    # Запись в историю
    history_entry = models.CellHistory(
        spreadsheet_id=spreadsheet_id,
        cell_address=cell_address,
        old_value=old_value,
        new_value=cells[cell_address]
    )
    db.add(history_entry)
    
    db.commit()
    db.refresh(spreadsheet)
    
    return spreadsheet


@router.get("/{spreadsheet_id}/history", response_model=List[schemas.CellHistoryResponse])
def get_cell_history(
    spreadsheet_id: int,
    cell_address: str = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Получение истории изменений ячеек."""
    query = db.query(models.CellHistory).filter(
        models.CellHistory.spreadsheet_id == spreadsheet_id
    )
    
    if cell_address:
        query = query.filter(models.CellHistory.cell_address == cell_address)
    
    history = query.order_by(
        models.CellHistory.changed_at.desc()
    ).limit(limit).all()
    
    return history
