"""
API Package for REST endpoints
"""
from app.api.tenants import router as tenants_router
from app.api.entities import router as entities_router
from app.api.admin import router as admin_router

__all__ = [
    "tenants_router",
    "entities_router",
    "admin_router",
]
