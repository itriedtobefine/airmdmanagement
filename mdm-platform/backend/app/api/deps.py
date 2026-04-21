"""
API Dependencies for authentication, tenant context, and database sessions
"""
from typing import Optional, Generator
from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_async_db
from app.config import settings


async def get_db_session() -> Generator[AsyncSession, None, None]:
    """Get database session from dependency"""
    async for session in get_async_db():
        yield session


async def get_tenant_id_from_request(request: Request) -> Optional[int]:
    """Extract tenant ID from request headers or query params"""
    # Try header first
    tenant_id = request.headers.get("X-Tenant-ID")
    
    # Try query param
    if not tenant_id:
        tenant_id = request.query_params.get("tenant_id")
    
    if tenant_id:
        try:
            return int(tenant_id)
        except ValueError:
            pass
    
    # Return default if multi-tenancy is disabled
    if not settings.multi_tenant_enabled:
        return None
    
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Tenant ID is required. Provide X-Tenant-ID header or tenant_id query parameter."
    )


async def get_current_user(request: Request) -> Optional[dict]:
    """
    Get current user from authentication token.
    In production, this would validate JWT tokens.
    For now, returns user info from headers for testing.
    """
    auth_header = request.headers.get("Authorization")
    
    if not auth_header:
        # Allow anonymous access for development
        return {"user_id": "anonymous", "email": "anon@example.com", "roles": ["user"]}
    
    # Simple Bearer token parsing (implement proper JWT validation in production)
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        # TODO: Implement proper JWT validation
        return {"user_id": "user-123", "email": "user@example.com", "roles": ["user"], "token": token}
    
    return None


async def require_auth(user: dict = Depends(get_current_user)) -> dict:
    """Require authenticated user"""
    if not user or user.get("user_id") == "anonymous":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def require_admin(user: dict = Depends(require_auth)) -> dict:
    """Require admin role"""
    if "admin" not in user.get("roles", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user
