"""
MDM Platform - Main FastAPI Application Entry Point
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import structlog

from app.config import settings
from app.database import init_database, close_database
from app.api import tenants_router, entities_router, admin_router


# Configure structured logging
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer() if settings.debug else structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(
        getattr(structlog, settings.log_level.upper(), 20)  # 20 = INFO level
    ),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events"""
    # Startup
    logger.info("Starting MDM Platform", version=settings.app_version)
    
    try:
        await init_database()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize database", error=str(e))
        raise
    
    logger.info("MDM Platform started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down MDM Platform")
    await close_database()
    logger.info("Database connections closed")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="""
## Master Data Management Platform

A comprehensive MDM solution with support for:

### Core Features
- **Multi-Tenancy**: Logical isolation of data per tenant
- **Entity Management**: CRUD operations for master data entities
- **Dynamic Attributes**: Flexible schema with JSON-based attributes
- **Bitemporal Versioning**: Track both valid time and system time
- **Audit Logging**: Immutable audit trail for compliance

### Integration
- **REST API**: Full RESTful API with OpenAPI documentation
- **Event-Driven**: Kafka integration for real-time synchronization
- **Edge Sync**: Support for offline-first edge devices

### Security & Compliance
- **RBAC/ABAC**: Role and attribute-based access control
- **Data Classification**: PII, sensitive data tagging
- **GDPR Ready**: Built-in support for data retention and deletion
    """,
    version=settings.app_version,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
    lifespan=lifespan,
)


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    logger.warning("Validation error", errors=exc.errors())
    return JSONResponse(
        status_code=422,
        content={
            "error": "ValidationError",
            "message": "Request validation failed",
            "details": exc.errors(),
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unhandled exceptions"""
    logger.error("Unhandled exception", error=str(exc), exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred",
        },
    )


# Include routers
app.include_router(tenants_router)
app.include_router(entities_router)
app.include_router(admin_router)


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "description": "Master Data Management Platform",
        "docs": "/docs" if settings.debug else "Disabled in production",
        "health": "/api/v1/admin/health",
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        workers=settings.workers if not settings.debug else 1,
    )
