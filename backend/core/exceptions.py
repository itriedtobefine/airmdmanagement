from fastapi import HTTPException, status
from typing import Any, Optional


class MDMException(HTTPException):
    def __init__(
        self,
        status_code: int,
        detail: str,
        error_type: Optional[str] = None,
        field: Optional[str] = None,
        value: Optional[Any] = None
    ):
        super().__init__(status_code=status_code, detail=detail)
        self.error_type = error_type
        self.field = field
        self.value = value


class SchemaNotFoundException(MDMException):
    def __init__(self, entity_code: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schema not found for entity: {entity_code}",
            error_type="SCHEMA_NOT_FOUND"
        )


class SchemaValidationException(MDMException):
    def __init__(self, errors: list[dict]):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Schema validation failed",
            error_type="SCHEMA_VALIDATION_ERROR"
        )
        self.errors = errors


class RecordNotFoundException(MDMException):
    def __init__(self, record_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Record not found: {record_id}",
            error_type="RECORD_NOT_FOUND"
        )


class RecordValidationException(MDMException):
    def __init__(self, errors: list[dict]):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Record validation failed",
            error_type="RECORD_VALIDATION_ERROR"
        )
        self.errors = errors


class ConflictException(MDMException):
    def __init__(self, detail: str = "Resource conflict"):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
            error_type="CONFLICT"
        )


class ValidationErrorMessage(dict):
    def __init__(self, field: str, rule: str, message: str, value: Any = None):
        super().__init__({
            "field": field,
            "rule": rule,
            "message": message,
            "value": value
        })
