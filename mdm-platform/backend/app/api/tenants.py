"""
Tenant management API endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.api.deps import get_db_session, require_admin
from app.models.tenant import Tenant
from app.schemas.tenant import (
    TenantCreate,
    TenantUpdate,
    TenantResponse,
    TenantListResponse,
)
from app.schemas.common import PaginatedResponse, SuccessResponse


router = APIRouter(prefix="/api/v1/tenants", tags=["Tenants"])


@router.get("", response_model=PaginatedResponse[TenantResponse])
async def list_tenants(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Page size"),
    search: Optional[str] = Query(default=None, description="Search by name or code"),
    is_active: Optional[bool] = Query(default=None, description="Filter by active status"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    List all tenants with pagination and filtering.
    
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 20, max: 100)
    - **search**: Search by tenant name or code
    - **is_active**: Filter by active status
    """
    # Build query
    query = select(Tenant).where(Tenant.deleted_at.is_(None))
    
    # Apply filters
    if search:
        search_filter = f"%{search}%"
        query = query.where(
            (Tenant.name.ilike(search_filter)) | (Tenant.tenant_code.ilike(search_filter))
        )
    
    if is_active is not None:
        query = query.where(Tenant.is_active == is_active)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    # Execute query
    result = await db.execute(query)
    tenants = result.scalars().all()
    
    # Convert to response models
    items = [TenantResponse.model_validate(tenant) for tenant in tenants]
    
    return PaginatedResponse.create(items, total, page, page_size)


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: int,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get a specific tenant by ID.
    
    - **tenant_id**: Tenant unique identifier
    """
    result = await db.execute(
        select(Tenant).where(
            Tenant.id == tenant_id,
            Tenant.deleted_at.is_(None)
        )
    )
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant with id {tenant_id} not found"
        )
    
    return TenantResponse.model_validate(tenant)


@router.post("", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    tenant_data: TenantCreate,
    user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Create a new tenant.
    
    Requires admin privileges.
    
    - **tenant_code**: Unique tenant code (alphanumeric)
    - **name**: Tenant display name
    - **description**: Optional description
    - **max_entities**: Maximum number of entities allowed
    - **max_users**: Maximum number of users allowed
    - **max_storage_mb**: Maximum storage in MB
    """
    # Check if tenant code already exists
    existing = await db.execute(
        select(Tenant).where(Tenant.tenant_code == tenant_data.tenant_code)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Tenant with code '{tenant_data.tenant_code}' already exists"
        )
    
    # Create tenant
    tenant = Tenant(
        tenant_code=tenant_data.tenant_code,
        name=tenant_data.name,
        description=tenant_data.description,
        max_entities=tenant_data.max_entities,
        max_users=tenant_data.max_users,
        max_storage_mb=tenant_data.max_storage_mb,
    )
    
    if tenant_data.config:
        import json
        tenant.config_json = json.dumps(tenant_data.config)
    
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
    
    return TenantResponse.model_validate(tenant)


@router.put("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: int,
    tenant_data: TenantUpdate,
    user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Update an existing tenant.
    
    Requires admin privileges. Only provided fields will be updated.
    """
    result = await db.execute(
        select(Tenant).where(
            Tenant.id == tenant_id,
            Tenant.deleted_at.is_(None)
        )
    )
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant with id {tenant_id} not found"
        )
    
    # Update fields
    update_data = tenant_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "config" and value is not None:
            import json
            tenant.config_json = json.dumps(value)
        elif value is not None:
            setattr(tenant, field, value)
    
    await db.commit()
    await db.refresh(tenant)
    
    return TenantResponse.model_validate(tenant)


@router.delete("/{tenant_id}", response_model=SuccessResponse)
async def delete_tenant(
    tenant_id: int,
    user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Soft-delete a tenant.
    
    Requires admin privileges. This performs a soft delete - data is preserved but marked as deleted.
    """
    result = await db.execute(
        select(Tenant).where(
            Tenant.id == tenant_id,
            Tenant.deleted_at.is_(None)
        )
    )
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant with id {tenant_id} not found"
        )
    
    # Soft delete
    from datetime import datetime
    tenant.deleted_at = datetime.utcnow()
    
    await db.commit()
    
    return SuccessResponse(
        success=True,
        message=f"Tenant '{tenant.tenant_code}' has been deleted"
    )


@router.post("/{tenant_id}/activate", response_model=TenantResponse)
async def activate_tenant(
    tenant_id: int,
    user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    """Activate a suspended tenant"""
    result = await db.execute(
        select(Tenant).where(
            Tenant.id == tenant_id,
            Tenant.deleted_at.is_(None)
        )
    )
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant with id {tenant_id} not found"
        )
    
    tenant.is_active = True
    tenant.is_suspended = False
    
    await db.commit()
    await db.refresh(tenant)
    
    return TenantResponse.model_validate(tenant)


@router.post("/{tenant_id}/suspend", response_model=TenantResponse)
async def suspend_tenant(
    tenant_id: int,
    user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    """Suspend an active tenant"""
    result = await db.execute(
        select(Tenant).where(
            Tenant.id == tenant_id,
            Tenant.deleted_at.is_(None)
        )
    )
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant with id {tenant_id} not found"
        )
    
    tenant.is_suspended = True
    
    await db.commit()
    await db.refresh(tenant)
    
    return TenantResponse.model_validate(tenant)
