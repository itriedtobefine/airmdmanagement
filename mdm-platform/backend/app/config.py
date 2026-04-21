"""
Configuration management for MDM Platform
Supports environment variables, .env files, and dynamic configuration
"""
import os
from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Application
    app_name: str = Field(default="MDM Platform", description="Application name")
    app_version: str = Field(default="1.0.0", description="Application version")
    debug: bool = Field(default=False, description="Debug mode")
    environment: str = Field(default="development", description="Environment name")
    
    # Server
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    workers: int = Field(default=1, description="Number of worker processes")
    
    # Database
    database_url: str = Field(
        default="postgresql://mdm:mdm_password@localhost:5432/mdm_db",
        description="Database connection URL"
    )
    database_pool_size: int = Field(default=10, description="Database pool size")
    database_max_overflow: int = Field(default=20, description="Database max overflow")
    
    # Redis Cache
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )
    cache_ttl: int = Field(default=300, description="Default cache TTL in seconds")
    
    # Security
    secret_key: str = Field(
        default="change-me-in-production-use-secure-random-string",
        description="Secret key for JWT signing"
    )
    access_token_expire_minutes: int = Field(
        default=30,
        description="Access token expiration in minutes"
    )
    refresh_token_expire_days: int = Field(
        default=7,
        description="Refresh token expiration in days"
    )
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    
    # CORS
    cors_origins: List[str] = Field(
        default=["*"],
        description="Allowed CORS origins"
    )
    cors_allow_credentials: bool = Field(default=True, description="Allow credentials")
    cors_allow_methods: List[str] = Field(
        default=["*"],
        description="Allowed HTTP methods"
    )
    cors_allow_headers: List[str] = Field(
        default=["*"],
        description="Allowed HTTP headers"
    )
    
    # Multi-tenancy
    default_tenant_id: str = Field(
        default="default",
        description="Default tenant ID for single-tenant mode"
    )
    multi_tenant_enabled: bool = Field(
        default=True,
        description="Enable multi-tenancy"
    )
    
    # Event Bus (Kafka)
    kafka_bootstrap_servers: str = Field(
        default="localhost:9092",
        description="Kafka bootstrap servers"
    )
    kafka_events_topic: str = Field(
        default="mdm-events",
        description="Kafka events topic"
    )
    kafka_sync_topic: str = Field(
        default="mdm-sync",
        description="Kafka sync topic"
    )
    
    # Edge Sync
    edge_sync_enabled: bool = Field(default=True, description="Enable edge sync")
    edge_sync_interval: int = Field(
        default=60,
        description="Edge sync interval in seconds"
    )
    edge_batch_size: int = Field(default=100, description="Edge sync batch size")
    
    # Data Quality
    dq_rules_enabled: bool = Field(default=True, description="Enable DQ rules")
    dq_default_threshold: float = Field(
        default=0.8,
        description="Default DQ threshold"
    )
    
    # Matching
    matching_default_threshold: float = Field(
        default=0.85,
        description="Default matching threshold"
    )
    matching_fuzzy_enabled: bool = Field(default=True, description="Enable fuzzy matching")
    
    # Audit
    audit_enabled: bool = Field(default=True, description="Enable audit logging")
    audit_retention_days: int = Field(
        default=365,
        description="Audit log retention in days"
    )
    
    # Monitoring
    prometheus_enabled: bool = Field(default=True, description="Enable Prometheus metrics")
    health_check_interval: int = Field(
        default=30,
        description="Health check interval in seconds"
    )
    
    # File Storage
    storage_backend: str = Field(
        default="local",
        description="Storage backend (local, s3, azure, gcs)"
    )
    storage_path: str = Field(
        default="/tmp/mdm-storage",
        description="Local storage path"
    )
    
    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Log format (json, text)")
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.environment == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.environment == "development"


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get settings instance (for dependency injection)"""
    return settings
