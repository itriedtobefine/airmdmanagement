"""
Модели данных для приложения таблиц.
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

from database import Base


class User(Base):
    """Пользователь системы."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    spreadsheets = relationship("Spreadsheet", back_populates="owner", cascade="all, delete-orphan")


class Spreadsheet(Base):
    """Таблица (документ)."""
    __tablename__ = "spreadsheets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    data = Column(JSON, default=lambda: {"cells": {}})  # Хранение данных ячеек в формате {"A1": {"value": "...", "style": {...}}}

    owner = relationship("User", back_populates="spreadsheets")


class CellHistory(Base):
    """История изменений ячеек для возможности отката."""
    __tablename__ = "cell_history"

    id = Column(Integer, primary_key=True, index=True)
    spreadsheet_id = Column(Integer, ForeignKey("spreadsheets.id"), nullable=False)
    cell_address = Column(String(20), nullable=False)  # Например, "A1", "B5"
    old_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)
    changed_at = Column(DateTime, default=datetime.utcnow)
