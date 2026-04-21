"""
Audit log models for compliance and traceability
Implements WORM (Write Once Read Many) pattern for immutable logging
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
    BigInteger,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class AuditAction(str, Enum):
    """Standard audit actions"""
    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    MERGE = "MERGE"
    SPLIT = "SPLIT"
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    EXPORT = "EXPORT"
    IMPORT = "IMPORT"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    PERMISSION_CHANGE = "PERMISSION_CHANGE"
    CONFIG_CHANGE = "CONFIG_CHANGE"
    SYNC = "SYNC"
    MATCH = "MATCH"
    VALIDATE = "VALIDATE"


class AuditLog(Base):
    """
    Immutable audit log for tracking all data changes.
    
    Features:
    - WORM storage pattern (no updates/deletes allowed)
    - Cryptographic hash chain for integrity
    - Business event correlation
    - Compliance reporting support
    """
    
    __tablename__ = "audit_logs"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Tenant isolation
    tenant_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("tenants.id"), nullable=True, index=True
    )
    
    # Entity reference (if applicable)
    entity_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("entities.id"), nullable=True, index=True
    )
    
    # Action details
    action: Mapped[str] = mapped_column(
        SQLEnum(AuditAction), nullable=False, index=True
    )
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # User/context information
    user_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    user_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    user_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Session and request context
    session_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    request_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Business event correlation
    business_event_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True
    )
    business_event_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Change details
    old_values_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, nullable=True
    )
    new_values_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, nullable=True
    )
    changed_fields: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    
    # Result
    status: Mapped[str] = mapped_column(String(50), default="SUCCESS")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Integrity chain (for WORM verification)
    previous_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    current_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    
    # Timestamps (immutable once set)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    
    # Retention
    retention_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="audit_logs")
    entity = relationship("Entity", back_populates="audit_logs")
    
    # Indexes for querying
    __table_args__ = (
        Index("ix_audit_timestamp", "timestamp"),
        Index("ix_audit_user", "user_id", "timestamp"),
        Index("ix_audit_action", "action", "resource_type"),
        Index("ix_audit_business_event", "business_event_id"),
        Index("ix_audit_retention", "is_archived", "retention_until"),
    )
    
    def __repr__(self) -> str:
        return (
            f"<AuditLog(id={self.id}, action='{self.action}', "
            f"resource='{self.resource_type}:{self.resource_id}')>"
        )
    
    def compute_hash(self) -> str:
        """Compute SHA-256 hash of this audit record for integrity chain"""
        import hashlib
        
        # Create deterministic string representation
        data = f"{self.id}:{self.timestamp.isoformat()}:{self.action}:" \
               f"{self.resource_type}:{self.resource_id}:{self.user_id}:" \
               f"{str(self.old_values_json)}:{str(self.new_values_json)}"
        
        if self.previous_hash:
            data = f"{self.previous_hash}:{data}"
        
        return hashlib.sha256(data.encode()).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "entity_id": self.entity_id,
            "action": self.action.value if isinstance(self.action, AuditAction) else self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "user_id": self.user_id,
            "user_email": self.user_email,
            "user_name": self.user_name,
            "session_id": self.session_id,
            "request_id": self.request_id,
            "ip_address": self.ip_address,
            "business_event_id": self.business_event_id,
            "business_event_type": self.business_event_type,
            "old_values": self.old_values_json,
            "new_values": self.new_values_json,
            "changed_fields": self.changed_fields,
            "status": self.status,
            "error_message": self.error_message,
            "timestamp": self.timestamp.isoformat(),
            "current_hash": self.current_hash,
        }
