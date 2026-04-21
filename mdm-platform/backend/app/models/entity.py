"""
Entity models for master data management
Supports dynamic attributes, classifications, and multi-domain entities
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
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
    Float,
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class EntityType(str, Enum):
    """Standard entity types for MDM domains"""
    CUSTOMER = "customer"
    PRODUCT = "product"
    SUPPLIER = "supplier"
    EMPLOYEE = "employee"
    ASSET = "asset"
    LOCATION = "location"
    ORGANIZATION = "organization"
    CUSTOM = "custom"


class EntityStatus(str, Enum):
    """Entity lifecycle status"""
    DRAFT = "draft"
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING_APPROVAL = "pending_approval"
    REJECTED = "rejected"
    ARCHIVED = "archived"
    DELETED = "deleted"


class Entity(Base):
    """
    Master data entity representing a business object.
    
    Features:
    - Multi-tenant isolation via tenant_id
    - Dynamic attributes via JSONB
    - Classification tags
    - Golden record support
    - Bitemporal versioning (via related table)
    """
    
    __tablename__ = "entities"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Tenant isolation (required for multi-tenancy)
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tenants.id"), nullable=False, index=True
    )
    
    # Entity identification
    entity_type: Mapped[str] = mapped_column(
        SQLEnum(EntityType), nullable=False, index=True
    )
    external_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )
    global_id: Mapped[Optional[str]] = mapped_column(
        String(64), unique=True, nullable=True, index=True
    )
    
    # Entity data
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Dynamic attributes stored as JSON
    # Schema is validated at application layer
    attributes_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, default=dict, nullable=True
    )
    
    # Classification and tags
    tags: Mapped[Optional[List[str]]] = mapped_column(
        JSON, default=list, nullable=True
    )
    classifications: Mapped[Optional[Dict[str, str]]] = mapped_column(
        JSON, default=dict, nullable=True
    )  # e.g., {"pii": "true", "sensitive": "high"}
    
    # Status and lifecycle
    status: Mapped[str] = mapped_column(
        SQLEnum(EntityStatus), default=EntityStatus.DRAFT, index=True
    )
    is_golden_record: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Source tracking
    source_system: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    source_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="entities")
    attributes = relationship(
        "Attribute", back_populates="entity", cascade="all, delete-orphan"
    )
    relationships = relationship(
        "Relationship",
        foreign_keys="Relationship.source_entity_id",
        back_populates="source_entity",
        cascade="all, delete-orphan",
    )
    versions = relationship(
        "VersionedRecord", back_populates="entity", cascade="all, delete-orphan"
    )
    audit_logs = relationship("AuditLog", back_populates="entity")
    
    # Indexes for performance
    __table_args__ = (
        UniqueConstraint("tenant_id", "external_id", name="uq_tenant_external_id"),
        Index("ix_entities_type_status", "entity_type", "status"),
        Index("ix_entities_tenant_type", "tenant_id", "entity_type"),
        Index("ix_entities_golden", "is_golden_record", "deleted_at"),
        Index("ix_entities_tags", "tags", postgresql_using="gin"),
    )
    
    def __repr__(self) -> str:
        return f"<Entity(id={self.id}, type='{self.entity_type}', name='{self.name}')>"
    
    @property
    def is_deleted(self) -> bool:
        """Check if entity is soft-deleted"""
        return self.deleted_at is not None
    
    def get_attribute(self, key: str, default=None) -> Any:
        """Get attribute value by key"""
        if self.attributes_json:
            return self.attributes_json.get(key, default)
        return default
    
    def set_attribute(self, key: str, value: Any):
        """Set attribute value"""
        if self.attributes_json is None:
            self.attributes_json = {}
        self.attributes_json[key] = value
    
    def add_tag(self, tag: str):
        """Add a classification tag"""
        if self.tags is None:
            self.tags = []
        if tag not in self.tags:
            self.tags.append(tag)
    
    def remove_tag(self, tag: str):
        """Remove a classification tag"""
        if self.tags and tag in self.tags:
            self.tags.remove(tag)
    
    def has_classification(self, key: str, value: str) -> bool:
        """Check if entity has specific classification"""
        if self.classifications:
            return self.classifications.get(key) == value
        return False
