from typing import Optional, List
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import json

from infrastructure.models import MdmSchema, MdmRecord, MdmRecordHistory, MdmAuditLog
from core.exceptions import SchemaNotFoundException, ConflictException
from services.validator import SchemaValidator
from infrastructure.cache import redis_client
from core.config import settings


class MetadataService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_active_schema(self, entity_code: str) -> Optional[MdmSchema]:
        """Get active schema for entity with caching."""
        cache_key = f"schema:active:{entity_code}"
        
        cached = await redis_client.get(cache_key)
        if cached:
            schema_data = json.loads(cached)
            return MdmSchema(**schema_data)

        result = await self.db.execute(
            select(MdmSchema)
            .where(MdmSchema.entity_code == entity_code)
            .where(MdmSchema.is_active == True)
            .order_by(MdmSchema.version.desc())
        )
        schema = result.scalar_one_or_none()

        if schema:
            await redis_client.setex(
                cache_key,
                settings.SCHEMA_CACHE_TTL,
                json.dumps({
                    "id": str(schema.id),
                    "entity_code": schema.entity_code,
                    "entity_name": schema.entity_name,
                    "version": schema.version,
                    "json_schema": schema.json_schema,
                    "is_active": schema.is_active,
                    "description": schema.description
                })
            )

        return schema

    async def get_schema_versions(self, entity_code: str) -> List[MdmSchema]:
        """Get all versions of schema for entity."""
        result = await self.db.execute(
            select(MdmSchema)
            .where(MdmSchema.entity_code == entity_code)
            .order_by(MdmSchema.version.desc())
        )
        return list(result.scalars().all())

    async def create_schema(
        self,
        entity_code: str,
        entity_name: str,
        json_schema: dict,
        description: Optional[str],
        created_by: str
    ) -> MdmSchema:
        """Create new schema version."""
        is_valid, errors = SchemaValidator.validate_schema(json_schema)
        if not is_valid:
            from core.exceptions import SchemaValidationException
            raise SchemaValidationException(errors)

        result = await self.db.execute(
            select(MdmSchema)
            .where(MdmSchema.entity_code == entity_code)
            .order_by(MdmSchema.version.desc())
        )
        last_schema = result.scalar_one_or_none()
        next_version = (last_schema.version + 1) if last_schema else 1

        schema = MdmSchema(
            entity_code=entity_code,
            entity_name=entity_name,
            version=next_version,
            json_schema=json_schema,
            is_active=last_schema is None,
            description=description,
            created_by=created_by
        )
        self.db.add(schema)
        await self.db.flush()

        await self._invalidate_cache(entity_code)
        return schema

    async def activate_schema(self, entity_code: str, version: int, user_id: str) -> MdmSchema:
        """Activate specific schema version."""
        result = await self.db.execute(
            select(MdmSchema)
            .where(MdmSchema.entity_code == entity_code)
            .where(MdmSchema.version == version)
        )
        schema = result.scalar_one_or_none()
        if not schema:
            raise SchemaNotFoundException(entity_code)

        await self.db.execute(
            update(MdmSchema)
            .where(MdmSchema.entity_code == entity_code)
            .values(is_active=False)
        )

        schema.is_active = True
        await self.db.flush()

        await self._invalidate_cache(entity_code)
        return schema

    async def _invalidate_cache(self, entity_code: str):
        """Invalidate schema cache."""
        cache_key = f"schema:active:{entity_code}"
        await redis_client.delete(cache_key)


class RecordService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_records(
        self,
        entity_code: str,
        page: int = 1,
        limit: int = 20,
        filters: Optional[dict] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "asc"
    ) -> tuple[List[MdmRecord], int]:
        """Get records with pagination, filtering and sorting."""
        query = select(MdmRecord).where(
            MdmRecord.entity_code == entity_code,
            MdmRecord.is_deleted == False
        )

        if filters:
            for field, value in filters.items():
                query = query.where(
                    MdmRecord.data[field].astext == str(value)
                )

        total_result = await self.db.execute(
            select(MdmRecord.id)
            .where(MdmRecord.entity_code == entity_code, MdmRecord.is_deleted == False)
        )
        total = len(total_result.scalars().all())

        if sort_by:
            order_func = MdmRecord.data[sort_by].astext if sort_by in ["name", "code"] else getattr(MdmRecord, sort_by, MdmRecord.created_at)
            if sort_order == "desc":
                order_func = order_func.desc()
            query = query.order_by(order_func)

        query = query.offset((page - 1) * limit).limit(limit)
        result = await self.db.execute(query)
        records = list(result.scalars().all())

        return records, total

    async def get_record(self, entity_code: str, record_id: str) -> Optional[MdmRecord]:
        """Get single record by ID."""
        result = await self.db.execute(
            select(MdmRecord)
            .where(MdmRecord.id == record_id)
            .where(MdmRecord.entity_code == entity_code)
            .where(MdmRecord.is_deleted == False)
        )
        return result.scalar_one_or_none()

    async def create_record(
        self,
        entity_code: str,
        data: dict,
        created_by: str
    ) -> MdmRecord:
        """Create new record."""
        schema = await MetadataService(self.db).get_active_schema(entity_code)
        if not schema:
            raise SchemaNotFoundException(entity_code)

        SchemaValidator.validate_record(data, schema.json_schema)

        record = MdmRecord(
            entity_code=entity_code,
            version=1,
            data=data,
            created_by=created_by
        )
        self.db.add(record)
        await self.db.flush()

        await self._log_history(record.id, 1, "CREATE", None, data, created_by)
        return record

    async def update_record(
        self,
        entity_code: str,
        record_id: str,
        data: dict,
        version: int,
        updated_by: str
    ) -> MdmRecord:
        """Update existing record with optimistic locking."""
        result = await self.db.execute(
            select(MdmRecord)
            .where(MdmRecord.id == record_id)
            .where(MdmRecord.entity_code == entity_code)
            .where(MdmRecord.is_deleted == False)
        )
        record = result.scalar_one_or_none()
        if not record:
            from core.exceptions import RecordNotFoundException
            raise RecordNotFoundException(record_id)

        if record.version != version:
            raise ConflictException(f"Version conflict: expected {version}, current {record.version}")

        schema = await MetadataService(self.db).get_active_schema(entity_code)
        if not schema:
            raise SchemaNotFoundException(entity_code)

        SchemaValidator.validate_record(data, schema.json_schema)

        old_data = record.data.copy()
        record.data = data
        record.version += 1
        record.updated_by = updated_by
        await self.db.flush()

        await self._log_history(
            record.id, record.version, "UPDATE", old_data, data, updated_by
        )
        return record

    async def delete_record(
        self,
        entity_code: str,
        record_id: str,
        deleted_by: str
    ) -> None:
        """Soft delete record."""
        result = await self.db.execute(
            select(MdmRecord)
            .where(MdmRecord.id == record_id)
            .where(MdmRecord.entity_code == entity_code)
            .where(MdmRecord.is_deleted == False)
        )
        record = result.scalar_one_or_none()
        if not record:
            from core.exceptions import RecordNotFoundException
            raise RecordNotFoundException(record_id)

        old_data = record.data.copy()
        record.is_deleted = True
        record.updated_by = deleted_by
        await self.db.flush()

        await self._log_history(record.id, record.version, "DELETE", old_data, None, deleted_by)

    async def get_record_history(self, record_id: str) -> List[MdmRecordHistory]:
        """Get record history."""
        result = await self.db.execute(
            select(MdmRecordHistory)
            .where(MdmRecordHistory.record_id == record_id)
            .order_by(MdmRecordHistory.version.desc())
        )
        return list(result.scalars().all())

    async def restore_record(
        self,
        record_id: str,
        target_version: int,
        restored_by: str
    ) -> MdmRecord:
        """Restore record to specific version."""
        result = await self.db.execute(
            select(MdmRecordHistory)
            .where(MdmRecordHistory.record_id == record_id)
            .where(MdmRecordHistory.version == target_version)
        )
        history = result.scalar_one_or_none()
        if not history or not history.payload_after:
            from core.exceptions import RecordNotFoundException
            raise RecordNotFoundException(f"Version {target_version} not found")

        record_result = await self.db.execute(
            select(MdmRecord)
            .where(MdmRecord.id == record_id)
        )
        record = record_result.scalar_one_or_none()
        if not record:
            raise RecordNotFoundException(record_id)

        old_data = record.data.copy()
        record.data = history.payload_after
        record.is_deleted = False
        record.version += 1
        record.updated_by = restored_by
        await self.db.flush()

        await self._log_history(
            record.id, record.version, "RESTORE", old_data, record.data, restored_by
        )
        return record

    async def _log_history(
        self,
        record_id: str,
        version: int,
        action: str,
        payload_before: Optional[dict],
        payload_after: Optional[dict],
        user_id: str
    ):
        """Log record change to history."""
        history = MdmRecordHistory(
            record_id=record_id,
            version=version,
            action=action,
            payload_before=payload_before,
            payload_after=payload_after,
            user_id=user_id
        )
        self.db.add(history)
