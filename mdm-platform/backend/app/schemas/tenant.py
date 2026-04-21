"""
Tenant schemas for API validation
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict

from app.schemas.common import BaseSchema


class TenantBase(BaseModel):
    """Base tenant schema with common fields"""
    name: str = Field(..., min_length=1, max_length=255, description="Tenant name")
    description: Optional[str] = Field(default=None, max_length=1000, description="Tenant description")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Acme Corporation",
                "description": "Main tenant for Acme Corp"
            }
        }


class TenantCreate(TenantBase):
    """Schema for creating a new tenant"""
    tenant_code: str = Field(
        ..., 
        min_length=3, 
        max_length=50, 
        pattern=r"^[a-zA-Z][a-zA-Z0-9_-]*$",
        description="Unique tenant code (alphanumeric, starts with letter)"
    )
    config: Optional[Dict[str, Any]] = Field(default=None, description="Initial configuration")
    max_entities: Optional[int] = Field(default=100000, description="Maximum number of entities")
    max_users: Optional[int] = Field(default=100, description="Maximum number of users")
    max_storage_mb: Optional[int] = Field(default=10240, description="Maximum storage in MB")
    
    class Config:
        json_schema_extra = {
            "example": {
                "tenant_code": "acme-corp",
                "name": "Acme Corporation",
                "description": "Main tenant for Acme Corp",
                "max_entities": 100000,
                "max_users": 100,
                "max_storage_mb": 10240
            }
        }


class TenantUpdate(BaseModel):
    """Schema for updating an existing tenant"""
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=1000)
    is_active: Optional[bool] = Field(default=None)
    is_suspended: Optional[bool] = Field(default=None)
    config: Optional[Dict[str, Any]] = Field(default=None)
    max_entities: Optional[int] = Field(default=None)
    max_users: Optional[int] = Field(default=None)
    max_storage_mb: Optional[int] = Field(default=None)
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Acme Corporation Updated",
                "is_active": True,
                "max_entities": 200000
            }
        }


class TenantResponse(BaseModel):
    """Schema for tenant response"""
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "tenant_code": "acme-corp",
                "name": "Acme Corporation",
                "description": "Main tenant for Acme Corp",
                "is_active": True,
                "is_suspended": False,
                "max_entities": 100000,
                "max_users": 100,
                "max_storage_mb": 10240,
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z"
            }
        }
    )
    
    id: int = Field(..., description="Tenant ID")
    tenant_code: str = Field(..., description="Tenant code")
    name: str = Field(..., description="Tenant name")
    description: Optional[str] = Field(default=None, description="Tenant description")
    is_active: bool = Field(default=True, description="Is tenant active")
    is_suspended: bool = Field(default=False, description="Is tenant suspended")
    max_entities: Optional[int] = Field(default=None, description="Max entities quota")
    max_users: Optional[int] = Field(default=None, description="Max users quota")
    max_storage_mb: Optional[int] = Field(default=None, description="Max storage quota")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class TenantListResponse(BaseModel):
    """Schema for list of tenants"""
    items: List[TenantResponse] = Field(..., description="List of tenants")
    total: int = Field(..., description="Total count")
    
    class Config:
        json_schema_extra = {
            "example": {
                "items": [
                    {
                        "id": 1,
                        "tenant_code": "acme-corp",
                        "name": "Acme Corporation",
                        "is_active": True
                    }
                ],
                "total": 1
            }
        }
