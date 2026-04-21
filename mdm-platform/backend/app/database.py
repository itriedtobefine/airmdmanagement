"""
Database connection and session management
Supports PostgreSQL with async operations
"""
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
    async_scoped_session,
)
from sqlalchemy.orm import Session, declarative_base, scoped_session
from sqlalchemy.pool import NullPool
import asyncio

from app.config import settings


# SQLAlchemy Base for model definitions
Base = declarative_base()


class DatabaseManager:
    """Database connection manager with async support"""
    
    def __init__(self):
        self._engine = None
        self._async_engine = None
        self._session_factory = None
        self._async_session_factory = None
    
    @property
    def engine_url(self) -> str:
        """Get database URL, converting to async if needed"""
        url = settings.database_url
        # Convert postgresql:// to postgresql+asyncpg:// for async support
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://")
        return url
    
    def get_engine(self):
        """Get synchronous engine"""
        if self._engine is None:
            # For SQLite in-memory or simple setups
            if settings.database_url.startswith("sqlite"):
                from sqlalchemy import create_engine as sync_create_engine
                self._engine = sync_create_engine(
                    settings.database_url,
                    connect_args={"check_same_thread": False},
                )
            else:
                # Use psycopg2 for sync connections
                url = settings.database_url.replace(
                    "postgresql+asyncpg://", "postgresql://"
                )
                from sqlalchemy import create_engine as sync_create_engine
                self._engine = sync_create_engine(
                    url,
                    pool_size=settings.database_pool_size,
                    max_overflow=settings.database_max_overflow,
                )
        return self._engine
    
    def get_async_engine(self):
        """Get asynchronous engine"""
        if self._async_engine is None:
            self._async_engine = create_async_engine(
                self.engine_url,
                echo=settings.debug,
                pool_size=settings.database_pool_size,
                max_overflow=settings.database_max_overflow,
            )
        return self._async_engine
    
    def get_session_factory(self):
        """Get synchronous session factory"""
        if self._session_factory is None:
            engine = self.get_engine()
            self._session_factory = scoped_session(
                sessionmaker(bind=engine, autoflush=False, autocommit=False)
            )
        return self._session_factory
    
    def get_async_session_factory(self):
        """Get asynchronous session factory"""
        if self._async_session_factory is None:
            engine = self.get_async_engine()
            self._async_session_factory = async_scoped_session(
                async_sessionmaker(bind=engine, autoflush=False, autocommit=False),
                scopefunc=asyncio.current_task
            )
        return self._async_session_factory
    
    async def get_db(self) -> AsyncGenerator[AsyncSession, None]:
        """Dependency for getting async database sessions"""
        async_session = self.get_async_session_factory()
        try:
            async with async_session() as session:
                yield session
        finally:
            await async_session.remove()
    
    def get_db_sync(self) -> Session:
        """Get synchronous database session"""
        session = self.get_session_factory()
        try:
            return session()
        finally:
            session.remove()
    
    async def init_db(self) -> None:
        """Initialize database tables"""
        async_engine = self.get_async_engine()
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    async def close(self) -> None:
        """Close database connections"""
        if self._async_engine:
            await self._async_engine.dispose()
        if self._engine:
            self._engine.dispose()


# Global database manager instance
db_manager = DatabaseManager()


# Convenience functions for dependency injection
async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session (for FastAPI dependencies)"""
    async for session in db_manager.get_db():
        yield session


def get_sync_db() -> Session:
    """Get sync database session"""
    return db_manager.get_db_sync()


async def init_database():
    """Initialize database on startup"""
    await db_manager.init_db()


async def close_database():
    """Close database connections on shutdown"""
    await db_manager.close()
