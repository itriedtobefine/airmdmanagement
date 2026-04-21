"""
Tenant model for multi-tenancy support
Provides logical isolation of data per tenant
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    String,
    Boolean,
    DateTime,
    Integer,
    ForeignKey,
    UniqueConstraint,
    Index,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Tenant(Base):
    """
    Tenant model representing an isolated organization or business unit.
    
    Multi-tenancy is implemented through:
    - Logical isolation via tenant_id on all tables
    - Optional row-level security policies
    - Separate quotas and configurations per tenant
    """
    
    __tablename__ = "tenants"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Tenant identification
    tenant_code: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_suspended: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Configuration
    config_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    max_entities: Mapped[Optional[int]] = mapped_column(Integer, default=100000)
    max_users: Mapped[Optional[int]] = mapped_column(Integer, default=100)
    max_storage_mb: Mapped[Optional[int]] = mapped_column(Integer, default=10240)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    entities = relationship("Entity", back_populates="tenant", cascade="all, delete-orphan")
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="tenant")
    
    # Indexes for performance
    __table_args__ = (
        Index("ix_tenants_active", "is_active", "deleted_at"),
        Index("ix_tenants_status", "is_active", "is_suspended"),
    )
    
    def __repr__(self) -> str:
        return f"<Tenant(id={self.id}, code='{self.tenant_code}', name='{self.name}')>"
    
    @property
    def is_deleted(self) -> bool:
        """Check if tenant is soft-deleted"""
        return self.deleted_at is not None
    
    def get_config(self, key: str, default=None):
        """Get configuration value by key"""
        import json
        if self.config_json:
            try:
                config = json.loads(self.config_json)
                return config.get(key, default)
            except (json.JSONDecodeError, TypeError):
                return default
        return default
    
    def set_config(self, key: str, value):
        """Set configuration value by key"""
        import json
        config = {}
        if self.config_json:
            try:
                config = json.loads(self.config_json)
            except (json.JSONDecodeError, TypeError):
                pass
        config[key] = value
        self.config_json = json.dumps(config)
