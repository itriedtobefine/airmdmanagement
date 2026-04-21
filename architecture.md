# Master Data Management Platform Architecture

## Overview
MDM Platform - гибридная платформа управления мастер-данными с поддержкой мультиарендности, edge-синхронизации и multi-cloud развертывания.

## Architecture Components

### 1. Core Services
```
┌─────────────────────────────────────────────────────────────┐
│                      Nginx (Reverse Proxy)                   │
│                    Port 80/443, SSL Termination              │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐   ┌─────────────────┐   ┌───────────────┐
│   Frontend    │   │   Backend API   │   │  Edge Agent   │
│   (React/Vue) │   │  (FastAPI)      │   │  (Lightweight)│
│   Port 3000   │   │   Port 8000     │   │   Port 8001   │
└───────────────┘   └─────────────────┘   └───────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌───────────────┐  ┌─────────────────┐  ┌───────────────┐
│  PostgreSQL   │  │     Redis       │  │   Kafka/Pulsar│
│  (Main DB)    │  │    (Cache)      │  │  (Event Bus)  │
│   Port 5432   │  │    Port 6379    │  │   Port 9092   │
└───────────────┘  └─────────────────┘  └───────────────┘
```

### 2. Directory Structure
```
/workspace/mdm-platform/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI application entry point
│   │   ├── config.py               # Configuration management
│   │   ├── database.py             # Database connection & models
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── tenant.py           # Multi-tenancy model
│   │   │   ├── entity.py           # Master data entities
│   │   │   ├── attribute.py        # Dynamic attributes
│   │   │   ├── relationship.py     # Graph relationships
│   │   │   ├── version.py          # Bitemporal versioning
│   │   │   └── audit.py            # Audit logging
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── tenant.py           # Pydantic schemas
│   │   │   ├── entity.py
│   │   │   └── common.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── deps.py             # Dependencies (auth, tenant)
│   │   │   ├── tenants.py          # Tenant management API
│   │   │   ├── entities.py         # Entity CRUD API
│   │   │   ├── matching.py         # Deduplication API
│   │   │   ├── quality.py          # Data quality API
│   │   │   ├── sync.py             # Sync & replication API
│   │   │   └── admin.py            # Admin & monitoring API
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── tenant_service.py   # Tenant isolation logic
│   │   │   ├── entity_service.py   # Entity operations
│   │   │   ├── matching_service.py # Duplicate detection
│   │   │   ├── quality_service.py  # Data quality checks
│   │   │   ├── sync_service.py     # Replication & sync
│   │   │   └── ml_service.py       # ML-based resolution
│   │   ├── utils/
│   │   │   ├── __init__.py
│   │   │   ├── hashing.py          # Hash utilities
│   │   │   ├── validation.py       # Schema validation
│   │   │   └── logging.py          # Structured logging
│   │   └── middleware/
│   │       ├── __init__.py
│   │       ├── auth.py             # Authentication
│   │       └── tenant.py           # Tenant context
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── test_api.py
│   │   └── test_services.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.vue
│   │   ├── main.js
│   │   ├── components/
│   │   ├── views/
│   │   └── stores/
│   ├── package.json
│   └── vite.config.js
├── infrastructure/
│   ├── docker-compose.yml
│   ├── nginx.conf
│   └── terraform/
├── scripts/
│   ├── setup.sh
│   └── init_db.py
└── README.md
```

### 3. Key Design Decisions

#### Multi-Tenancy Strategy
- **Logical Isolation**: All queries include `tenant_id` filter
- **Row Level Security**: PostgreSQL RLS policies per tenant
- **Separate Schemas**: Optional schema-per-tenant for strict isolation

#### Bitemporal Data Model
- **Valid Time**: When fact is true in real world
- **System Time**: When record was stored in system
- **Immutable History**: All changes create new versions

#### Event-Driven Architecture
- **Kafka/Pulsar**: For cross-domain synchronization
- **CDC Agents**: Debezium-style change capture
- **Idempotent Handlers**: Exactly-once processing guarantee

#### Edge Sync Protocol
- **Delta Compression**: Only changed records transmitted
- **Conflict Resolution**: Vector clocks + last-write-wins
- **Offline First**: Local cache with background sync

### 4. API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/tenants` | GET/POST | Tenant management |
| `/api/v1/entities` | GET/POST | Entity CRUD |
| `/api/v1/entities/{id}` | GET/PUT/DELETE | Single entity ops |
| `/api/v1/matching/find` | POST | Duplicate detection |
| `/api/v1/matching/merge` | POST | Merge duplicates |
| `/api/v1/quality/profile` | GET | Data profiling |
| `/api/v1/quality/rules` | GET/POST | Quality rules |
| `/api/v1/sync/status` | GET | Sync status |
| `/api/v1/sync/push` | POST | Push to edge |
| `/api/v1/audit/logs` | GET | Audit trail |
| `/api/v1/admin/health` | GET | Health check |

### 5. Security Model
- **OAuth2/OIDC**: External identity providers
- **RBAC + ABAC**: Role and attribute-based access
- **Field-Level Encryption**: Sensitive data encryption
- **Audit Logging**: Immutable WORM storage

### 6. Scalability Approach
- **Horizontal Scaling**: Stateless API servers
- **Database Sharding**: By tenant_id or entity type
- **Read Replicas**: For read-heavy workloads
- **Caching Layers**: Redis for hot data
