"""
Attribute models for dynamic entity attributes
Supports meta-modeling with inheritance and validation rules
"""
from datetime import datetime
from typing import Optional, Any, List, Dict
from enum import Enum
from sqlalchemy import (
    String,
    Boolean,
    DateTime,
    Integer,
    ForeignKey,
    UniqueConstraint,
    Index,
    Text,
    JSON,
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class AttributeType(str, Enum):
    """Supported attribute data types"""
    STRING = "string"
    TEXT = "text"
    INTEGER = "integer"
    FLOAT = "float"
    DECIMAL = "decimal"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    TIME = "time"
    EMAIL = "email"
    PHONE = "phone"
    URL = "url"
    JSON = "json"
    REFERENCE = "reference"  # Reference to another entity
    ENUM = "enum"
    MULTISELECT = "multiselect"


class Attribute(Base):
    """
    Dynamic attribute definition for entities.
    
    Features:
    - Type-safe attribute definitions
    - Validation rules
    - Multi-language support
    - Inheritance from parent attributes
    """
    
    __tablename__ = "attributes"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Entity reference
    entity_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("entities.id"), nullable=False, index=True
    )
    
    # Attribute identification
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Type and validation
    attribute_type: Mapped[str] = mapped_column(
        SQLEnum(AttributeType), nullable=False, index=True
    )
    is_required: Mapped[bool] = mapped_column(Boolean, default=False)
    is_unique: Mapped[bool] = mapped_column(Boolean, default=False)
    is_searchable: Mapped[bool] = mapped_column(Boolean, default=True)
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Constraints
    min_length: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_length: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    min_value: Mapped[Optional[float]] = mapped_column(nullable=True)
    max_value: Mapped[Optional[float]] = mapped_column(nullable=True)
    pattern: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # Regex
    
    # Default value
    default_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Multi-language support
    localized_values: Mapped[Optional[Dict[str, str]]] = mapped_column(
        JSON, default=dict, nullable=True
    )  # {"en": "value", "ru": "значение"}
    
    # Enum options (for ENUM/MULTISELECT types)
    enum_options: Mapped[Optional[List[str]]] = mapped_column(
        JSON, default=list, nullable=True
    )
    
    # Reference configuration
    reference_entity_type: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )
    
    # Metadata
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, default=dict, nullable=True
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    
    # Relationships
    entity = relationship("Entity", back_populates="attributes")
    
    # Indexes
    __table_args__ = (
        UniqueConstraint("entity_id", "name", name="uq_entity_attribute_name"),
        Index("ix_attributes_type", "attribute_type"),
        Index("ix_attributes_searchable", "is_searchable", "is_visible"),
    )
    
    def __repr__(self) -> str:
        return f"<Attribute(id={self.id}, name='{self.name}', type='{self.attribute_type}')>"
    
    def validate_value(self, value: Any) -> tuple[bool, Optional[str]]:
        """
        Validate attribute value against constraints.
        Returns (is_valid, error_message)
        """
        if value is None:
            if self.is_required:
                return False, f"Attribute '{self.name}' is required"
            return True, None
        
        # Type validation
        if self.attribute_type == AttributeType.STRING:
            if not isinstance(value, str):
                return False, f"Value must be a string"
            if self.min_length and len(value) < self.min_length:
                return False, f"Value must be at least {self.min_length} characters"
            if self.max_length and len(value) > self.max_length:
                return False, f"Value must be at most {self.max_length} characters"
        
        elif self.attribute_type == AttributeType.INTEGER:
            try:
                int_val = int(value)
                if self.min_value is not None and int_val < self.min_value:
                    return False, f"Value must be at least {self.min_value}"
                if self.max_value is not None and int_val > self.max_value:
                    return False, f"Value must be at most {self.max_value}"
            except (ValueError, TypeError):
                return False, f"Value must be an integer"
        
        elif self.attribute_type == AttributeType.FLOAT:
            try:
                float_val = float(value)
                if self.min_value is not None and float_val < self.min_value:
                    return False, f"Value must be at least {self.min_value}"
                if self.max_value is not None and float_val > self.max_value:
                    return False, f"Value must be at most {self.max_value}"
            except (ValueError, TypeError):
                return False, f"Value must be a number"
        
        elif self.attribute_type == AttributeType.BOOLEAN:
            if not isinstance(value, bool):
                return False, f"Value must be a boolean"
        
        elif self.attribute_type == AttributeType.EMAIL:
            if not isinstance(value, str) or "@" not in value:
                return False, f"Value must be a valid email address"
        
        # Pattern validation
        if self.pattern and isinstance(value, str):
            import re
            if not re.match(self.pattern, value):
                return False, f"Value does not match required pattern"
        
        # Enum validation
        if self.attribute_type in [AttributeType.ENUM, AttributeType.MULTISELECT]:
            if self.enum_options:
                if isinstance(value, list):
                    for v in value:
                        if v not in self.enum_options:
                            return False, f"Value '{v}' is not in allowed options"
                elif value not in self.enum_options:
                    return False, f"Value '{value}' is not in allowed options"
        
        return True, None
