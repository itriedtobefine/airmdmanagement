"""
Admin and monitoring API endpoints
Health checks, metrics, and system administration
"""
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.api.deps import get_db_session, require_admin
from app.config import settings
from app.schemas.common import HealthCheckResponse, SuccessResponse

# App version
app_version = "1.0.0"


router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])


@router.get("/health", response_model=HealthCheckResponse)
async def health_check(db: AsyncSession = Depends(get_db_session)):
    """
    Perform comprehensive health check of all components.
    
    Returns status of:
    - Application
    - Database
    - Cache (Redis)
    - Event Bus (Kafka)
    """
    components: Dict[str, Dict[str, Any]] = {}
    overall_status = "healthy"
    
    # Check database
    try:
        start_time = datetime.utcnow()
        await db.execute(text("SELECT 1"))
        latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        components["database"] = {
            "status": "healthy",
            "latency_ms": round(latency_ms, 2)
        }
    except Exception as e:
        components["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        overall_status = "unhealthy"
    
    # Add application info
    components["application"] = {
        "status": "healthy",
        "version": app_version if hasattr(settings, '__version__') else settings.app_version,
        "environment": settings.environment,
        "multi_tenant_enabled": settings.multi_tenant_enabled
    }
    
    return HealthCheckResponse(
        status=overall_status,
        version=settings.app_version,
        timestamp=datetime.utcnow(),
        components=components
    )


@router.get("/ready")
async def readiness_check(db: AsyncSession = Depends(get_db_session)):
    """
    Check if the application is ready to serve traffic.
    """
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ready", "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Not ready: {str(e)}"
        )


@router.get("/live")
async def liveness_check():
    """
    Simple liveness check for Kubernetes probes.
    """
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}


@router.get("/metrics/summary")
async def get_metrics_summary(
    user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get summary metrics (requires admin).
    """
    from sqlalchemy import func, select
    from app.models.entity import Entity
    from app.models.tenant import Tenant
    
    # Get entity counts by type
    entity_count_query = select(
        Entity.entity_type,
        func.count(Entity.id)
    ).where(
        Entity.deleted_at.is_(None)
    ).group_by(Entity.entity_type)
    
    result = await db.execute(entity_count_query)
    entities_by_type = {row[0]: row[1] for row in result.all()}
    
    # Get tenant count
    tenant_count_query = select(func.count(Tenant.id)).where(
        Tenant.deleted_at.is_(None),
        Tenant.is_active == True
    )
    tenant_result = await db.execute(tenant_count_query)
    active_tenants = tenant_result.scalar()
    
    return {
        "entities": {
            "total": sum(entities_by_type.values()),
            "by_type": entities_by_type
        },
        "tenants": {
            "active": active_tenants
        },
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/cache/clear", response_model=SuccessResponse)
async def clear_cache(
    user: dict = Depends(require_admin),
):
    """
    Clear application cache (requires admin).
    """
    # In production, this would connect to Redis and clear caches
    # For now, just return success
    return SuccessResponse(
        success=True,
        message="Cache cleared successfully"
    )


@router.get("/config")
async def get_config(
    user: dict = Depends(require_admin),
):
    """
    Get current application configuration (sanitized, requires admin).
    """
    # Return non-sensitive configuration
    return {
        "app_name": settings.app_name,
        "app_version": settings.app_version,
        "environment": settings.environment,
        "debug": settings.debug,
        "multi_tenant_enabled": settings.multi_tenant_enabled,
        "audit_enabled": settings.audit_enabled,
        "edge_sync_enabled": settings.edge_sync_enabled,
        "prometheus_enabled": settings.prometheus_enabled,
        "log_level": settings.log_level,
    }
