"""
Version models for bitemporal data support
Implements valid_time and system_time for full auditability
"""
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import (
    String,
    Boolean,
    DateTime,
    Integer,
    ForeignKey,
    Index,
    Text,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class VersionedRecord(Base):
    """
    Versioned record for tracking entity changes over time.
    
    Supports:
    - System time (when record was stored)
    - Valid time (when fact is true in reality)
    - Full history with immutable snapshots
    """
    
    __tablename__ = "versioned_records"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Entity reference
    entity_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("entities.id"), nullable=False, index=True
    )
    
    # Version info
    version_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    previous_version_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("versioned_records.id"), nullable=True
    )
    
    # Bitemporal fields
    # System time: when this version was recorded in the database
    system_time_from: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False, index=True
    )
    system_time_to: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, index=True
    )
    
    # Valid time: when this fact is/was true in the real world
    valid_time_from: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False, index=True
    )
    valid_time_to: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, index=True
    )
    
    # Snapshot of entity data at this version
    snapshot_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, default=dict, nullable=True
    )
    
    # Change metadata
    changed_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    change_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    change_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Is this the current version?
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    
    # Relationships
    entity = relationship("Entity", back_populates="versions")
    next_versions = relationship(
        "VersionedRecord",
        remote_side=[previous_version_id],
        backref="previous_version",
    )
    
    # Indexes for temporal queries
    __table_args__ = (
        Index(
            "ix_versions_entity_current",
            "entity_id",
            "is_current",
        ),
        Index(
            "ix_versions_system_time",
            "system_time_from",
            "system_time_to",
        ),
        Index(
            "ix_versions_valid_time",
            "valid_time_from",
            "valid_time_to",
        ),
        Index(
            "ix_versions_temporal",
            "entity_id",
            "system_time_from",
            "valid_time_from",
        ),
    )
    
    def __repr__(self) -> str:
        return (
            f"<VersionedRecord(id={self.id}, entity={self.entity_id}, "
            f"version={self.version_number})>"
        )
    
    @property
    def is_valid_now(self) -> bool:
        """Check if this version is currently valid"""
        now = datetime.utcnow()
        
        # Check valid time
        if self.valid_time_to and now > self.valid_time_to:
            return False
        
        # Check system time (is this the latest system version?)
        if not self.is_current:
            return False
        
        return True
    
    def get_snapshot_value(self, key: str, default=None) -> Any:
        """Get value from snapshot"""
        if self.snapshot_json:
            return self.snapshot_json.get(key, default)
        return default


class BitemporalRecord(Base):
    """
    Simplified bitemporal tracking for specific attributes.
    Used when full versioning is not needed but temporal tracking is required.
    """
    
    __tablename__ = "bitemporal_records"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Entity reference
    entity_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("entities.id"), nullable=False, index=True
    )
    
    # Attribute being tracked
    attribute_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    attribute_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Bitemporal fields
    system_time_from: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    system_time_to: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    valid_time_from: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    valid_time_to: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Metadata
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    source_system: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    
    # Indexes
    __table_args__ = (
        Index(
            "ix_bitemporal_entity_attr",
            "entity_id",
            "attribute_name",
            "is_current",
        ),
        Index(
            "ix_bitemporal_valid",
            "valid_time_from",
            "valid_time_to",
        ),
    )
    
    def __repr__(self) -> str:
        return (
            f"<BitemporalRecord(id={self.id}, entity={self.entity_id}, "
            f"attr='{self.attribute_name}')>"
        )
