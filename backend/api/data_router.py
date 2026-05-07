from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
import json

from infrastructure.database import get_db
from services.data_service import RecordService
from core.security import get_current_user, TokenData, check_role, check_entity_access
from core.enums import UserRole

router = APIRouter(prefix="/api/v1/data", tags=["data"])


class RecordCreateRequest(BaseModel):
    data: dict


class RecordUpdateRequest(BaseModel):
    data: dict
    version: int = Field(..., gt=0)


@router.get("/{entity_code}")
async def list_records(
    entity_code: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    sort_by: Optional[str] = None,
    sort_order: str = Query("asc", pattern="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(check_entity_access(entity_code))
):
    """List records for entity with pagination."""
    service = RecordService(db)
    
    filters = {}
    for key in ["name", "code", "status"]:
        val = Query(None)
        if val is not None:
            filters[key] = val
    
    records, total = await service.get_records(
        entity_code=entity_code,
        page=page,
        limit=limit,
        filters=filters if filters else None,
        sort_by=sort_by,
        sort_order=sort_order
    )
    
    return {
        "items": [
            {
                "id": str(r.id),
                "version": r.version,
                "data": r.data,
                "created_at": r.created_at,
                "updated_at": r.updated_at,
                "created_by": r.created_by
            }
            for r in records
        ],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit
    }


@router.post("/{entity_code}")
async def create_record(
    entity_code: str,
    request: RecordCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(check_entity_access(entity_code))
):
    """Create new record."""
    if current_user.role == UserRole.VIEWER:
        raise HTTPException(status_code=403, detail="Viewers cannot create records")
    
    service = RecordService(db)
    record = await service.create_record(
        entity_code=entity_code,
        data=request.data,
        created_by=current_user.user_id
    )
    
    return {
        "id": str(record.id),
        "version": record.version,
        "data": record.data,
        "created_at": record.created_at,
        "created_by": record.created_by
    }


@router.get("/{entity_code}/{record_id}")
async def get_record(
    entity_code: str,
    record_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(check_entity_access(entity_code))
):
    """Get single record."""
    service = RecordService(db)
    record = await service.get_record(entity_code, record_id)
    
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    
    return {
        "id": str(record.id),
        "version": record.version,
        "data": record.data,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
        "created_by": record.created_by,
        "updated_by": record.updated_by
    }


@router.put("/{entity_code}/{record_id}")
async def update_record(
    entity_code: str,
    record_id: str,
    request: RecordUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(check_entity_access(entity_code))
):
    """Update existing record."""
    if current_user.role == UserRole.VIEWER:
        raise HTTPException(status_code=403, detail="Viewers cannot update records")
    
    service = RecordService(db)
    record = await service.update_record(
        entity_code=entity_code,
        record_id=record_id,
        data=request.data,
        version=request.version,
        updated_by=current_user.user_id
    )
    
    return {
        "id": str(record.id),
        "version": record.version,
        "data": record.data,
        "updated_at": record.updated_at,
        "updated_by": record.updated_by
    }


@router.delete("/{entity_code}/{record_id}")
async def delete_record(
    entity_code: str,
    record_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(check_entity_access(entity_code))
):
    """Soft delete record."""
    if current_user.role == UserRole.VIEWER:
        raise HTTPException(status_code=403, detail="Viewers cannot delete records")
    
    service = RecordService(db)
    await service.delete_record(
        entity_code=entity_code,
        record_id=record_id,
        deleted_by=current_user.user_id
    )
    
    return {"status": "deleted"}


@router.get("/{entity_code}/{record_id}/history")
async def get_record_history(
    entity_code: str,
    record_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(check_entity_access(entity_code))
):
    """Get record history."""
    service = RecordService(db)
    history = await service.get_record_history(record_id)
    
    return [
        {
            "id": str(h.id),
            "version": h.version,
            "action": h.action,
            "payload_before": h.payload_before,
            "payload_after": h.payload_after,
            "user_id": h.user_id,
            "timestamp": h.timestamp
        }
        for h in history
    ]


@router.post("/{entity_code}/{record_id}/restore")
async def restore_record(
    entity_code: str,
    record_id: str,
    target_version: int = Query(..., gt=0),
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(check_entity_access(entity_code))
):
    """Restore record to specific version."""
    if current_user.role not in [UserRole.ADMIN, UserRole.DATA_STEWARD]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    service = RecordService(db)
    record = await service.restore_record(
        record_id=record_id,
        target_version=target_version,
        restored_by=current_user.user_id
    )
    
    return {
        "id": str(record.id),
        "version": record.version,
        "data": record.data,
        "restored_from": target_version
    }
