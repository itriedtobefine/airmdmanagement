"""
Pydantic models for request/response validation.
Uses Pydantic v2 with strict typing.
License: MIT
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


class TaskType(str, Enum):
    """Valid task types for reference data management."""
    MANUAL_REGISTRY = "manual_registry"
    EXTERNAL_INTEGRATION = "external_integration"
    CLASSIFICATION_REGISTRY = "classification_registry"
    REFERENCE_DATA = "reference_data"
    MASTER_DATA = "master_data"
    UI_COMPONENT = "ui_component"
    DATA_MIGRATION = "data_migration"
    DOCUMENTATION = "documentation"
    UNKNOWN = "unknown"


class ComponentLevel(str, Enum):
    """Component complexity levels."""
    BASIC = "basic"
    STANDARD = "standard"
    ADVANCED = "advanced"
    COMPLEX = "complex"
    SIMPLE = "simple"
    HIERARCHICAL = "hierarchical"
    READ_ONLY = "read_only"
    SYNC_BASIC = "sync_basic"
    SYNC_ADVANCED = "sync_advanced"
    API_INTEGRATION = "api_integration"
    WITH_VERSIONING = "with_versioning"
    WITH_APPROVAL_WORKFLOW = "with_approval_workflow"
    WITH_GOLDEN_RECORD = "with_golden_record"
    WITH_MATCHING = "with_matching"
    GRID_VIEW = "grid_view"
    SEARCH_FILTER = "search_filter"
    BULK_OPERATIONS = "bulk_operations"
    AUDIT_LOG = "audit_log"
    INITIAL_LOAD = "initial_load"
    TRANSFORMATION = "transformation"
    TECHNICAL = "technical"
    USER_GUIDE = "user_guide"
    VALIDATION_RULES = "validation_rules"
    ADVANCED_VALIDATION = "advanced_validation"
    BASIC_STRUCTURE = "basic_structure"
    UNKNOWN = "unknown"


class ExtractedParameters(BaseModel):
    """
    Schema for LLM-extracted parameters from user input.
    Strict JSON schema for forced JSON mode.
    """
    task_type: TaskType = Field(
        ...,
        description="Type of task (manual_registry, external_integration, classification_registry, reference_data, master_data, ui_component, data_migration, documentation)"
    )
    component: ComponentLevel = Field(
        ...,
        description="Component complexity level"
    )
    registry_name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Name of the registry/directory being described"
    )
    has_external_integration: bool = Field(
        default=False,
        description="Whether external system integration is required"
    )
    has_validation_rules: bool = Field(
        default=False,
        description="Whether validation rules are required"
    )
    requires_support: bool = Field(
        default=False,
        description="Whether annual support is required"
    )
    estimated_records: Optional[int] = Field(
        default=None,
        ge=0,
        le=10000000,
        description="Estimated number of records (optional)"
    )
    additional_components: List[str] = Field(
        default_factory=list,
        description="Additional components mentioned (audit_log, bulk_operations, search_filter, etc.)"
    )

    class Config:
        json_schema_extra = {
            "required": ["task_type", "component", "registry_name"]
        }


class CostBreakdownItem(BaseModel):
    """Individual cost breakdown item."""
    component: str = Field(..., description="Component name")
    effort_hours: float = Field(..., description="Effort in hours")
    rate_rub: float = Field(..., description="Hourly rate in RUB")
    cost_rub: float = Field(..., description="Total cost in RUB")


class CostCalculationResponse(BaseModel):
    """Response schema for cost calculation result."""
    success: bool = Field(..., description="Whether calculation was successful")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")
    
    # Development costs
    development_total_hours: float = Field(..., description="Total development hours")
    development_total_cost_rub: float = Field(..., description="Total development cost in RUB")
    
    # Support costs
    support_total_hours_per_year: float = Field(..., description="Annual support hours")
    support_total_cost_per_year_rub: float = Field(..., description="Annual support cost in RUB")
    
    # Breakdown
    development_breakdown: List[CostBreakdownItem] = Field(
        default_factory=list,
        description="Development cost breakdown"
    )
    support_breakdown: List[CostBreakdownItem] = Field(
        default_factory=list,
        description="Support cost breakdown"
    )
    
    # Summary
    summary: str = Field(..., description="Human-readable summary of the calculation")
    registry_name: str = Field(..., description="Name of the registry")
    components_included: List[str] = Field(
        default_factory=list,
        description="List of components included in calculation"
    )


class UserRequest(BaseModel):
    """User input request schema."""
    description: str = Field(
        ...,
        min_length=10,
        max_length=5000,
        description="Text description of the planned registry/directory"
    )


class ErrorResponse(BaseModel):
    """Error response schema."""
    success: bool = Field(default=False)
    error: str = Field(..., description="Error message")
    error_code: str = Field(..., description="Error code")
