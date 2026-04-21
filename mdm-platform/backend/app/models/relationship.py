"""
Relationship models for graph-based entity connections
Supports hierarchical and network relationships with traversal
"""
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum
from sqlalchemy import (
    String,
    Boolean,
    DateTime,
    Integer,
    ForeignKey,
    Index,
    Text,
    JSON,
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class RelationshipType(str, Enum):
    """Standard relationship types"""
    PARENT_CHILD = "parent_child"
    OWNS = "owns"
    WORKS_FOR = "works_for"
    LOCATED_AT = "located_at"
    SUPPLIES = "supplies"
    RELATED_TO = "related_to"
    DUPLICATE_OF = "duplicate_of"
    MERGED_INTO = "merged_into"
    HIERARCHY = "hierarchy"
    ASSOCIATION = "association"
    CUSTOM = "custom"


class Relationship(Base):
    """
    Graph relationship between entities.
    
    Features:
    - Directed edges (source -> target)
    - Relationship attributes
    - Temporal validity
    - Cycle detection support
    """
    
    __tablename__ = "relationships"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Tenant isolation
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tenants.id"), nullable=False, index=True
    )
    
    # Entity references
    source_entity_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("entities.id"), nullable=False, index=True
    )
    target_entity_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("entities.id"), nullable=False, index=True
    )
    
    # Relationship type
    relationship_type: Mapped[str] = mapped_column(
        SQLEnum(RelationshipType), nullable=False, index=True
    )
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationship properties
    properties_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, default=dict, nullable=True
    )
    
    # Weight/strength for probabilistic relationships
    weight: Mapped[Optional[float]] = mapped_column(nullable=True)
    confidence_score: Mapped[Optional[float]] = mapped_column(nullable=True)
    
    # Temporal validity
    valid_from: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    valid_to: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    
    # Relationships
    source_entity = relationship(
        "Entity",
        foreign_keys=[source_entity_id],
        back_populates="relationships",
    )
    target_entity = relationship(
        "Entity",
        foreign_keys=[target_entity_id],
    )
    
    # Indexes for graph traversal
    __table_args__ = (
        Index(
            "ix_relationships_source_target",
            "source_entity_id",
            "target_entity_id",
            unique=True,
        ),
        Index(
            "ix_relationships_target_source",
            "target_entity_id",
            "source_entity_id",
        ),
        Index("ix_relationships_type", "relationship_type", "is_active"),
        Index("ix_relationships_tenant_type", "tenant_id", "relationship_type"),
    )
    
    def __repr__(self) -> str:
        return (
            f"<Relationship(id={self.id}, "
            f"type='{self.relationship_type}', "
            f"source={self.source_entity_id} -> target={self.target_entity_id})>"
        )
    
    @property
    def is_valid_now(self) -> bool:
        """Check if relationship is currently valid"""
        if not self.is_active:
            return False
        
        now = datetime.utcnow()
        if self.valid_from and now < self.valid_from:
            return False
        if self.valid_to and now > self.valid_to:
            return False
        return True
    
    def get_property(self, key: str, default=None) -> Any:
        """Get relationship property value"""
        if self.properties_json:
            return self.properties_json.get(key, default)
        return default
    
    def set_property(self, key: str, value: Any):
        """Set relationship property"""
        if self.properties_json is None:
            self.properties_json = {}
        self.properties_json[key] = value
