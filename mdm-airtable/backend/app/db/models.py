from sqlalchemy import create_engine, Column as SAColumn, Integer, String, ForeignKey, Text, DateTime, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime

Base = declarative_base()

class Table(Base):
    __tablename__ = "tables"
    
    id = SAColumn(Integer, primary_key=True, index=True)
    name = SAColumn(String, unique=True, nullable=False)
    description = SAColumn(Text, nullable=True)
    created_at = SAColumn(DateTime, default=datetime.utcnow)
    updated_at = SAColumn(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    columns = relationship("TableColumn", back_populates="table", cascade="all, delete-orphan")
    records = relationship("Record", back_populates="table", cascade="all, delete-orphan")


class TableColumn(Base):
    __tablename__ = "columns"
    
    id = SAColumn(Integer, primary_key=True, index=True)
    table_id = SAColumn(Integer, ForeignKey("tables.id"), nullable=False)
    name = SAColumn(String, nullable=False)
    column_type = SAColumn(String, nullable=False)  # text, number, date, boolean, link_to_record, single_select, multi_select
    is_required = SAColumn(Boolean, default=False)
    is_unique = SAColumn(Boolean, default=False)
    default_value = SAColumn(String, nullable=True)
    options = SAColumn(Text, nullable=True)  # JSON string for select options or linked table info
    validation_rule = SAColumn(String, nullable=True)  # Regex or custom validation
    position = SAColumn(Integer, default=0)
    created_at = SAColumn(DateTime, default=datetime.utcnow)
    
    table = relationship("Table", back_populates="columns")


class Record(Base):
    __tablename__ = "records"
    
    id = SAColumn(Integer, primary_key=True, index=True)
    table_id = SAColumn(Integer, ForeignKey("tables.id"), nullable=False)
    created_at = SAColumn(DateTime, default=datetime.utcnow)
    updated_at = SAColumn(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    table = relationship("Table", back_populates="records")
    values = relationship("CellValue", back_populates="record", cascade="all, delete-orphan")


class CellValue(Base):
    __tablename__ = "cell_values"
    
    id = SAColumn(Integer, primary_key=True, index=True)
    record_id = SAColumn(Integer, ForeignKey("records.id"), nullable=False)
    column_id = SAColumn(Integer, ForeignKey("columns.id"), nullable=False)
    value_text = SAColumn(Text, nullable=True)
    value_number = SAColumn(Integer, nullable=True)
    value_boolean = SAColumn(Boolean, nullable=True)
    value_date = SAColumn(DateTime, nullable=True)
    created_at = SAColumn(DateTime, default=datetime.utcnow)
    updated_at = SAColumn(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    record = relationship("Record", back_populates="values")
    column = relationship("TableColumn")


# Link table for many-to-many relationships (multi_select, linked records)
class LinkedRecord(Base):
    __tablename__ = "linked_records"
    
    id = SAColumn(Integer, primary_key=True, index=True)
    source_record_id = SAColumn(Integer, ForeignKey("records.id"), nullable=False)
    target_record_id = SAColumn(Integer, ForeignKey("records.id"), nullable=False)
    column_id = SAColumn(Integer, ForeignKey("columns.id"), nullable=False)
    created_at = SAColumn(DateTime, default=datetime.utcnow)
    
    source_record = relationship("Record", foreign_keys=[source_record_id])
    target_record = relationship("Record", foreign_keys=[target_record_id])
    column = relationship("TableColumn")
