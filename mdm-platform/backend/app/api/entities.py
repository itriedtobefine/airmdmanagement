"""
Entity management API endpoints
Supports CRUD operations, search, and filtering
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_

from app.api.deps import get_db_session, get_tenant_id_from_request
from app.models.entity import Entity, EntityType, EntityStatus
from app.models.tenant import Tenant
from app.schemas.entity import (
    EntityCreate,
    EntityUpdate,
    EntityResponse,
    EntityListResponse,
    EntitySearchRequest,
)
from app.schemas.common import PaginatedResponse, SuccessResponse


router = APIRouter(prefix="/api/v1/entities", tags=["Entities"])


@router.get("", response_model=PaginatedResponse[EntityResponse])
async def list_entities(
    tenant_id: int = Depends(get_tenant_id_from_request),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Page size"),
    entity_type: Optional[str] = Query(default=None, description="Filter by entity type"),
    status: Optional[str] = Query(default=None, description="Filter by status"),
    search: Optional[str] = Query(default=None, description="Search by name"),
    is_golden_record: Optional[bool] = Query(default=None, description="Filter golden records"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    List entities with pagination and filtering.
    
    Requires X-Tenant-ID header or tenant_id query parameter.
    """
    # Build query
    query = select(Entity).where(
        Entity.tenant_id == tenant_id,
        Entity.deleted_at.is_(None)
    )
    
    # Apply filters
    if entity_type:
        query = query.where(Entity.entity_type == entity_type)
    
    if status:
        query = query.where(Entity.status == status)
    
    if search:
        query = query.where(Entity.name.ilike(f"%{search}%"))
    
    if is_golden_record is not None:
        query = query.where(Entity.is_golden_record == is_golden_record)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(Entity.created_at.desc())
    
    # Execute query
    result = await db.execute(query)
    entities = result.scalars().all()
    
    # Convert to response models
    items = [EntityResponse.model_validate(entity) for entity in entities]
    
    return PaginatedResponse.create(items, total, page, page_size)


@router.get("/{entity_id}", response_model=EntityResponse)
async def get_entity(
    entity_id: int,
    tenant_id: int = Depends(get_tenant_id_from_request),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get a specific entity by ID.
    """
    result = await db.execute(
        select(Entity).where(
            Entity.id == entity_id,
            Entity.tenant_id == tenant_id,
            Entity.deleted_at.is_(None)
        )
    )
    entity = result.scalar_one_or_none()
    
    if not entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity with id {entity_id} not found"
        )
    
    return EntityResponse.model_validate(entity)


@router.post("", response_model=EntityResponse, status_code=status.HTTP_201_CREATED)
async def create_entity(
    entity_data: EntityCreate,
    tenant_id: int = Depends(get_tenant_id_from_request),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Create a new entity.
    
    - **entity_type**: Type of entity (customer, product, etc.)
    - **name**: Entity name
    - **attributes**: Dynamic attributes as JSON
    - **tags**: Classification tags
    - **classifications**: Data classifications (pii, sensitive, etc.)
    """
    # Verify tenant exists
    tenant_result = await db.execute(
        select(Tenant).where(
            Tenant.id == tenant_id,
            Tenant.deleted_at.is_(None),
            Tenant.is_active == True
        )
    )
    tenant = tenant_result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tenant with id {tenant_id} not found or inactive"
        )
    
    # Check for duplicate external_id within tenant
    if entity_data.external_id:
        existing = await db.execute(
            select(Entity).where(
                Entity.tenant_id == tenant_id,
                Entity.external_id == entity_data.external_id,
                Entity.deleted_at.is_(None)
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Entity with external_id '{entity_data.external_id}' already exists"
            )
    
    # Generate global_id
    import uuid
    global_id = f"ent-{uuid.uuid4().hex[:16]}"
    
    # Create entity
    entity = Entity(
        tenant_id=tenant_id,
        entity_type=entity_data.entity_type,
        external_id=entity_data.external_id,
        global_id=global_id,
        name=entity_data.name,
        description=entity_data.description,
        attributes_json=entity_data.attributes or {},
        tags=entity_data.tags or [],
        classifications=entity_data.classifications or {},
        source_system=entity_data.source_system,
        source_id=entity_data.source_id,
        status=EntityStatus.DRAFT,
    )
    
    db.add(entity)
    await db.commit()
    await db.refresh(entity)
    
    return EntityResponse.model_validate(entity)


@router.put("/{entity_id}", response_model=EntityResponse)
async def update_entity(
    entity_id: int,
    entity_data: EntityUpdate,
    tenant_id: int = Depends(get_tenant_id_from_request),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Update an existing entity.
    """
    result = await db.execute(
        select(Entity).where(
            Entity.id == entity_id,
            Entity.tenant_id == tenant_id,
            Entity.deleted_at.is_(None)
        )
    )
    entity = result.scalar_one_or_none()
    
    if not entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity with id {entity_id} not found"
        )
    
    # Update fields
    update_data = entity_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(entity, field, value)
    
    await db.commit()
    await db.refresh(entity)
    
    return EntityResponse.model_validate(entity)


@router.delete("/{entity_id}", response_model=SuccessResponse)
async def delete_entity(
    entity_id: int,
    tenant_id: int = Depends(get_tenant_id_from_request),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Soft-delete an entity.
    """
    result = await db.execute(
        select(Entity).where(
            Entity.id == entity_id,
            Entity.tenant_id == tenant_id,
            Entity.deleted_at.is_(None)
        )
    )
    entity = result.scalar_one_or_none()
    
    if not entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity with id {entity_id} not found"
        )
    
    from datetime import datetime
    entity.deleted_at = datetime.utcnow()
    
    await db.commit()
    
    return SuccessResponse(
        success=True,
        message=f"Entity '{entity.name}' has been deleted"
    )


@router.post("/search", response_model=PaginatedResponse[EntityResponse])
async def search_entities(
    search_request: EntitySearchRequest,
    tenant_id: int = Depends(get_tenant_id_from_request),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Advanced entity search with multiple filters.
    """
    # Build query
    query = select(Entity).where(
        Entity.tenant_id == tenant_id,
        Entity.deleted_at.is_(None)
    )
    
    # Apply filters
    if search_request.entity_type:
        query = query.where(Entity.entity_type == search_request.entity_type)
    
    if search_request.query:
        query = query.where(Entity.name.ilike(f"%{search_request.query}%"))
    
    if search_request.status:
        query = query.where(Entity.status == search_request.status)
    
    if search_request.is_golden_record is not None:
        query = query.where(Entity.is_golden_record == search_request.is_golden_record)
    
    if search_request.created_from:
        query = query.where(Entity.created_at >= search_request.created_from)
    
    if search_request.created_to:
        query = query.where(Entity.created_at <= search_request.created_to)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination
    offset = (search_request.page - 1) * search_request.page_size
    query = query.offset(offset).limit(search_request.page_size)
    
    # Execute query
    result = await db.execute(query)
    entities = result.scalars().all()
    
    items = [EntityResponse.model_validate(entity) for entity in entities]
    
    return PaginatedResponse.create(
        items, 
        total, 
        search_request.page, 
        search_request.page_size
    )
