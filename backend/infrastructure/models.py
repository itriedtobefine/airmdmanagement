from sqlalchemy import Column, String, Boolean, Integer, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from infrastructure.database import Base
import uuid


class MdmSchema(Base):
    __tablename__ = "mdm_schemas"
    __table_args__ = {"schema": "mdm_meta"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_code = Column(String(100), nullable=False, index=True)
    entity_name = Column(String(255), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    json_schema = Column(JSONB, nullable=False)
    is_active = Column(Boolean, default=False, index=True)
    description = Column(String(1000))
    created_by = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index("idx_entity_version", "entity_code", "version"),
        {"schema": "mdm_meta"}
    )


class MdmRecord(Base):
    __tablename__ = "mdm_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_code = Column(String(100), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)
    data = Column(JSONB, nullable=False)
    is_deleted = Column(Boolean, default=False, index=True)
    created_by = Column(String(100), nullable=False)
    updated_by = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index("idx_entity_deleted", "entity_code", "is_deleted"),
        Index("idx_data_gin", "data", using="gin"),
    )


class MdmRecordHistory(Base):
    __tablename__ = "mdm_record_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    record_id = Column(UUID(as_uuid=True), ForeignKey("mdm_records.id"), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    action = Column(String(20), nullable=False)
    payload_before = Column(JSONB)
    payload_after = Column(JSONB)
    user_id = Column(String(100), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    __table_args__ = (
        Index("idx_record_version", "record_id", "version"),
    )


class MdmAuditLog(Base):
    __tablename__ = "mdm_audit_log"
    __table_args__ = {"schema": "mdm_meta"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String(50), nullable=False, index=True)
    entity_code = Column(String(100), index=True)
    record_id = Column(UUID(as_uuid=True))
    user_id = Column(String(100), nullable=False)
    details = Column(JSONB)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)


class MdmUser(Base):
    __tablename__ = "mdm_users"
    __table_args__ = {"schema": "mdm_meta"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="viewer")
    allowed_entities = Column(JSONB, default=list)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
