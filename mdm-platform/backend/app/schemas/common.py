"""
Common schemas for API responses and requests
"""
from datetime import datetime
from typing import Optional, List, Dict, Any, Generic, TypeVar
from pydantic import BaseModel, Field


T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response schema"""
    items: List[T] = Field(..., description="List of items")
    total: int = Field(..., description="Total number of items")
    page: int = Field(default=1, description="Current page number")
    page_size: int = Field(default=20, description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(default=False, description="Has next page")
    has_previous: bool = Field(default=False, description="Has previous page")
    
    @classmethod
    def create(cls, items: List[T], total: int, page: int = 1, page_size: int = 20) -> "PaginatedResponse[T]":
        """Create paginated response from items list"""
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1,
        )


class HealthCheckResponse(BaseModel):
    """Health check response schema"""
    status: str = Field(..., description="Overall health status")
    version: str = Field(..., description="Application version")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Check timestamp")
    components: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Component health status"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "timestamp": "2024-01-15T10:30:00Z",
                "components": {
                    "database": {"status": "healthy", "latency_ms": 5},
                    "cache": {"status": "healthy", "latency_ms": 1},
                }
            }
        }


class ErrorResponse(BaseModel):
    """Error response schema"""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional details")
    request_id: Optional[str] = Field(default=None, description="Request ID for tracing")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "ValidationError",
                "message": "Invalid input data",
                "details": {"field": "value is required"},
                "request_id": "req-123456",
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }


class SuccessResponse(BaseModel):
    """Generic success response schema"""
    success: bool = Field(default=True, description="Operation success")
    message: Optional[str] = Field(default=None, description="Success message")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Response data")


class BaseSchema(BaseModel):
    """Base schema with common configuration"""
    
    class Config:
        from_attributes = True
        populate_by_name = True
        use_enum_values = True
