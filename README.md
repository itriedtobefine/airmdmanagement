# Master Data Management MVP

## Overview
MDM system for centralized master data management with dynamic model creation.

## Architecture
- **Backend**: FastAPI (Python 3.11+)
- **Frontend**: React 18 + TypeScript + Vite
- **Database**: PostgreSQL 15+ with JSONB
- **Cache**: Redis 7+
- **Queue**: Celery for async tasks

## Project Structure
```
/workspace
├── backend/          # FastAPI application
│   ├── core/         # Config, security
│   ├── metadata/     # Schema CRUD, validation
│   ├── data/         # Record CRUD, history
│   ├── api/          # Routers, dependencies
│   ├── services/     # Business logic
│   └── infrastructure/ # DB, cache
├── frontend/         # React application
│   └── src/
│       ├── components/
│       ├── hooks/
│       ├── services/
│       ├── pages/
│       └── types/
└── docker/           # Docker configuration
```

## Quick Start
```bash
docker-compose up -d
```

## API Documentation
Available at `/docs` after startup.
