from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from infrastructure.database import get_db
from services.data_service import MetadataService, RecordService
from core.security import get_current_user, TokenData, check_role
from core.enums import UserRole

router = APIRouter(prefix="/api/v1/meta", tags=["metadata"])


class SchemaCreateRequest(BaseModel):
    entity_code: str = Field(..., min_length=1, max_length=100, pattern="^[a-z][a-z0-9_]*$")
    entity_name: str = Field(..., min_length=1, max_length=255)
    json_schema: dict
    description: Optional[str] = None


class SchemaActivateRequest(BaseModel):
    version: int = Field(..., gt=0)


@router.post("/entities")
async def create_entity(
    request: SchemaCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(check_role([UserRole.ADMIN]))
):
    """Create new entity schema."""
    service = MetadataService(db)
    schema = await service.create_schema(
        entity_code=request.entity_code,
        entity_name=request.entity_name,
        json_schema=request.json_schema,
        description=request.description,
        created_by=current_user.user_id
    )
    return {
        "id": str(schema.id),
        "entity_code": schema.entity_code,
        "entity_name": schema.entity_name,
        "version": schema.version,
        "is_active": schema.is_active,
        "created_at": schema.created_at
    }


@router.get("/entities/{entity_code}")
async def get_entity(
    entity_code: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
):
    """Get active schema for entity."""
    service = MetadataService(db)
    schema = await service.get_active_schema(entity_code)
    if not schema:
        raise HTTPException(status_code=404, detail=f"Entity not found: {entity_code}")
    
    return {
        "id": str(schema.id),
        "entity_code": schema.entity_code,
        "entity_name": schema.entity_name,
        "version": schema.version,
        "json_schema": schema.json_schema,
        "description": schema.description,
        "is_active": schema.is_active,
        "created_at": schema.created_at
    }


@router.put("/entities/{entity_code}")
async def update_entity(
    entity_code: str,
    request: SchemaCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(check_role([UserRole.ADMIN]))
):
    """Create new version of entity schema."""
    service = MetadataService(db)
    schema = await service.create_schema(
        entity_code=entity_code,
        entity_name=request.entity_name,
        json_schema=request.json_schema,
        description=request.description,
        created_by=current_user.user_id
    )
    return {
        "id": str(schema.id),
        "entity_code": schema.entity_code,
        "entity_name": schema.entity_name,
        "version": schema.version,
        "is_active": schema.is_active,
        "created_at": schema.created_at
    }


@router.post("/entities/{entity_code}/activate")
async def activate_entity_version(
    entity_code: str,
    request: SchemaActivateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(check_role([UserRole.ADMIN]))
):
    """Activate specific schema version."""
    service = MetadataService(db)
    schema = await service.activate_schema(
        entity_code=entity_code,
        version=request.version,
        user_id=current_user.user_id
    )
    return {
        "id": str(schema.id),
        "entity_code": schema.entity_code,
        "version": schema.version,
        "is_active": schema.is_active
    }


@router.get("/entities/{entity_code}/versions")
async def get_entity_versions(
    entity_code: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
):
    """Get all versions of entity schema."""
    service = MetadataService(db)
    schemas = await service.get_schema_versions(entity_code)
    
    return [
        {
            "id": str(s.id),
            "version": s.version,
            "entity_name": s.entity_name,
            "is_active": s.is_active,
            "created_at": s.created_at,
            "created_by": s.created_by
        }
        for s in schemas
    ]
