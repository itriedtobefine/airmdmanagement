"""
Конфигурация базы данных для Spreadsheet App.
Использует SQLite для легковесности и отсутствия внешних зависимостей.
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./spreadsheet.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False},
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Зависимость для получения сессии БД."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
