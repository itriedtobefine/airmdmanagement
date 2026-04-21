"""
Entity schemas for API validation
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict

from app.schemas.common import BaseSchema


class EntityBase(BaseModel):
    """Base entity schema with common fields"""
    name: str = Field(..., min_length=1, max_length=500, description="Entity name")
    description: Optional[str] = Field(default=None, max_length=2000, description="Entity description")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "John Doe",
                "description": "Customer record"
            }
        }


class EntityCreate(EntityBase):
    """Schema for creating a new entity"""
    entity_type: str = Field(
        ..., 
        description="Entity type (customer, product, supplier, etc.)"
    )
    external_id: Optional[str] = Field(default=None, max_length=255, description="External system ID")
    attributes: Optional[Dict[str, Any]] = Field(
        default_factory=dict, 
        description="Dynamic attributes"
    )
    tags: Optional[List[str]] = Field(default_factory=list, description="Classification tags")
    classifications: Optional[Dict[str, str]] = Field(
        default_factory=dict, 
        description="Classifications (e.g., pii, sensitive)"
    )
    source_system: Optional[str] = Field(default=None, max_length=100, description="Source system name")
    source_id: Optional[str] = Field(default=None, max_length=255, description="Source system ID")
    
    class Config:
        json_schema_extra = {
            "example": {
                "entity_type": "customer",
                "name": "John Doe",
                "external_id": "CRM-12345",
                "attributes": {
                    "email": "john.doe@example.com",
                    "phone": "+1-555-123-4567",
                    "address": "123 Main St, New York, NY 10001"
                },
                "tags": ["vip", "active"],
                "classifications": {"pii": "true"},
                "source_system": "Salesforce",
                "source_id": "003xxx"
            }
        }


class EntityUpdate(BaseModel):
    """Schema for updating an existing entity"""
    name: Optional[str] = Field(default=None, min_length=1, max_length=500)
    description: Optional[str] = Field(default=None, max_length=2000)
    attributes: Optional[Dict[str, Any]] = Field(default=None)
    tags: Optional[List[str]] = Field(default=None)
    classifications: Optional[Dict[str, str]] = Field(default=None)
    status: Optional[str] = Field(default=None)
    is_golden_record: Optional[bool] = Field(default=None)
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "John D. Doe",
                "attributes": {
                    "email": "john.d.doe@example.com"
                },
                "tags": ["vip", "active", "verified"]
            }
        }


class EntityResponse(BaseModel):
    """Schema for entity response"""
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "tenant_id": 1,
                "entity_type": "customer",
                "external_id": "CRM-12345",
                "global_id": "ent-uuid-12345",
                "name": "John Doe",
                "description": "Customer record",
                "attributes": {
                    "email": "john.doe@example.com",
                    "phone": "+1-555-123-4567"
                },
                "tags": ["vip", "active"],
                "classifications": {"pii": "true"},
                "status": "active",
                "is_golden_record": True,
                "confidence_score": 0.95,
                "source_system": "Salesforce",
                "source_id": "003xxx",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z"
            }
        }
    )
    
    id: int = Field(..., description="Entity ID")
    tenant_id: int = Field(..., description="Tenant ID")
    entity_type: str = Field(..., description="Entity type")
    external_id: Optional[str] = Field(default=None, description="External system ID")
    global_id: Optional[str] = Field(default=None, description="Global unique ID")
    name: str = Field(..., description="Entity name")
    description: Optional[str] = Field(default=None, description="Entity description")
    attributes: Optional[Dict[str, Any]] = Field(default=None, description="Dynamic attributes")
    tags: Optional[List[str]] = Field(default=None, description="Classification tags")
    classifications: Optional[Dict[str, str]] = Field(default=None, description="Classifications")
    status: str = Field(default="draft", description="Entity status")
    is_golden_record: bool = Field(default=False, description="Is golden record")
    confidence_score: Optional[float] = Field(default=None, description="Confidence score")
    source_system: Optional[str] = Field(default=None, description="Source system")
    source_id: Optional[str] = Field(default=None, description="Source ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class EntityListResponse(BaseModel):
    """Schema for list of entities"""
    items: List[EntityResponse] = Field(..., description="List of entities")
    total: int = Field(..., description="Total count")
    
    class Config:
        json_schema_extra = {
            "example": {
                "items": [
                    {
                        "id": 1,
                        "entity_type": "customer",
                        "name": "John Doe",
                        "is_golden_record": True
                    }
                ],
                "total": 1
            }
        }


class EntitySearchRequest(BaseModel):
    """Schema for entity search request"""
    entity_type: Optional[str] = Field(default=None, description="Filter by entity type")
    query: Optional[str] = Field(default=None, description="Full-text search query")
    tags: Optional[List[str]] = Field(default=None, description="Filter by tags")
    classifications: Optional[Dict[str, str]] = Field(default=None, description="Filter by classifications")
    status: Optional[str] = Field(default=None, description="Filter by status")
    is_golden_record: Optional[bool] = Field(default=None, description="Filter golden records")
    created_from: Optional[datetime] = Field(default=None, description="Created after date")
    created_to: Optional[datetime] = Field(default=None, description="Created before date")
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Page size")
    
    class Config:
        json_schema_extra = {
            "example": {
                "entity_type": "customer",
                "query": "john",
                "tags": ["vip"],
                "page": 1,
                "page_size": 20
            }
        }
