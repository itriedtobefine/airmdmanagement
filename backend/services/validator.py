import json
from typing import Optional, Any
from fastjsonschema import compile, JsonSchemaException
from core.exceptions import RecordValidationException, ValidationErrorMessage


class SchemaValidator:
    _validators: dict[str, Any] = {}

    @classmethod
    def compile_schema(cls, json_schema: dict) -> Any:
        """Compile JSON schema into a validator function."""
        return compile(json_schema)

    @classmethod
    def validate_record(cls, data: dict, json_schema: dict) -> bool:
        """Validate record data against JSON schema."""
        try:
            validator = cls.compile_schema(json_schema)
            validator(data)
            return True
        except JsonSchemaException as e:
            raise RecordValidationException([
                {
                    "field": e.path or "root",
                    "rule": e.rule or "unknown",
                    "message": e.message,
                    "value": e.value
                }
            ])

    @classmethod
    def validate_schema(cls, json_schema: dict) -> tuple[bool, list[dict]]:
        """Validate JSON schema itself."""
        errors = []
        
        if not isinstance(json_schema, dict):
            errors.append({
                "field": "schema",
                "rule": "type",
                "message": "Schema must be a JSON object"
            })
            return False, errors

        if "type" not in json_schema:
            errors.append({
                "field": "type",
                "rule": "required",
                "message": "Schema must have a 'type' field"
            })

        if json_schema.get("type") != "object":
            errors.append({
                "field": "type",
                "rule": "enum",
                "message": "Schema type must be 'object'"
            })

        properties = json_schema.get("properties", {})
        if not isinstance(properties, dict):
            errors.append({
                "field": "properties",
                "rule": "type",
                "message": "Properties must be an object"
            })

        required = json_schema.get("required", [])
        if not isinstance(required, list):
            errors.append({
                "field": "required",
                "rule": "type",
                "message": "Required must be an array"
            })
        elif not set(required).issubset(set(properties.keys())):
            errors.append({
                "field": "required",
                "rule": "subset",
                "message": "All required fields must be defined in properties"
            })

        for prop_name, prop_def in properties.items():
            if not isinstance(prop_def, dict):
                errors.append({
                    "field": f"properties.{prop_name}",
                    "rule": "type",
                    "message": f"Property definition must be an object"
                })
                continue

            prop_type = prop_def.get("type")
            if prop_type and not isinstance(prop_type, (str, list)):
                errors.append({
                    "field": f"properties.{prop_name}.type",
                    "rule": "type",
                    "message": "Property type must be a string or array"
                })

        return len(errors) == 0, errors
