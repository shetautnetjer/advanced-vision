"""Packet validation layer for advanced-vision.

Provides JSON Schema validation for all packet types with fast-path
optimization for production environments.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from jsonschema import validate, ValidationError, Draft202012Validator

logger = logging.getLogger(__name__)

# Schema name to file mapping
SCHEMA_FILES = {
    "event_envelope": "event_envelope.schema.json",
    "ui_packet": "ui_packet.schema.json",
    "trading_packet": "trading_packet.schema.json",
    "scout_event": "scout_event.schema.json",
    "external_review_request": "external_review_request.schema.json",
    "external_review_result": "external_review_result.schema.json",
    "artifact_manifest": "artifact_manifest.schema.json",
}


class PacketValidationError(Exception):
    """Raised when packet validation fails with detailed error info."""
    
    def __init__(self, message: str, schema_name: str, errors: list[dict] | None = None):
        super().__init__(message)
        self.schema_name = schema_name
        self.errors = errors or []


class PacketValidator:
    """Validates packets against JSON schemas with caching and fast-path support.
    
    Usage:
        validator = PacketValidator()
        
        # Validate and get boolean result
        if validator.validate(packet, 'ui_packet'):
            wss_publisher.publish(packet)
        
        # Or validate and raise on error
        validator.validate_or_raise(packet, 'ui_packet')
    
    Fast Path:
        Set AV_SKIP_VALIDATION=1 in production to skip validation for performance.
    """
    
    def __init__(self, schemas_dir: str | Path | None = None):
        """Initialize the validator with schema loading.
        
        Args:
            schemas_dir: Directory containing .schema.json files. 
                        Defaults to project_root/schemas/
        """
        self._schemas: dict[str, dict] = {}
        self._validators: dict[str, Draft202012Validator] = {}
        self._skip_validation = os.environ.get("AV_SKIP_VALIDATION", "0") == "1"
        
        if self._skip_validation:
            logger.warning("Packet validation is DISABLED (AV_SKIP_VALIDATION=1)")
        
        self._load_schemas(schemas_dir)
    
    def _find_schemas_dir(self) -> Path:
        """Find the schemas directory relative to this file."""
        # Start from this file location and search upward
        current = Path(__file__).resolve()
        for parent in current.parents:
            schemas_dir = parent / "schemas"
            if schemas_dir.exists():
                return schemas_dir
            # Also check project root patterns
            if (parent / "pyproject.toml").exists() or (parent / ".git").exists():
                schemas_dir = parent / "schemas"
                if schemas_dir.exists():
                    return schemas_dir
        
        raise FileNotFoundError("Could not find schemas directory")
    
    def _load_schemas(self, schemas_dir: str | Path | None) -> None:
        """Load all schema files into memory."""
        if schemas_dir is None:
            schemas_path = self._find_schemas_dir()
        else:
            schemas_path = Path(schemas_dir)
        
        logger.info(f"Loading schemas from {schemas_path}")
        
        for schema_name, filename in SCHEMA_FILES.items():
            schema_file = schemas_path / filename
            if not schema_file.exists():
                logger.warning(f"Schema file not found: {schema_file}")
                continue
            
            with open(schema_file, 'r') as f:
                schema = json.load(f)
                self._schemas[schema_name] = schema
                self._validators[schema_name] = Draft202012Validator(schema)
                logger.debug(f"Loaded schema: {schema_name}")
        
        loaded = len(self._schemas)
        expected = len(SCHEMA_FILES)
        logger.info(f"Loaded {loaded}/{expected} schemas")
        
        if loaded < expected:
            missing = set(SCHEMA_FILES.keys()) - set(self._schemas.keys())
            logger.warning(f"Missing schemas: {missing}")
    
    def validate(self, packet: dict[str, Any], schema_name: str) -> bool:
        """Validate a packet against a schema.
        
        Args:
            packet: The packet dict to validate
            schema_name: Name of the schema (e.g., 'ui_packet')
            
        Returns:
            True if valid, False if invalid
            
        Note:
            If AV_SKIP_VALIDATION=1, always returns True
        """
        if self._skip_validation:
            return True
        
        if schema_name not in self._validators:
            logger.error(f"Unknown schema: {schema_name}")
            return False
        
        try:
            self._validators[schema_name].validate(packet)
            return True
        except ValidationError:
            return False
    
    def validate_or_raise(self, packet: dict[str, Any], schema_name: str) -> None:
        """Validate a packet and raise detailed error on failure.
        
        Args:
            packet: The packet dict to validate
            schema_name: Name of the schema
            
        Raises:
            PacketValidationError: If validation fails with detailed error info
            ValueError: If schema_name is unknown
        """
        if self._skip_validation:
            return
        
        if schema_name not in self._validators:
            raise ValueError(f"Unknown schema: {schema_name}")
        
        validator = self._validators[schema_name]
        errors = list(validator.iter_errors(packet))
        
        if errors:
            error_details = []
            for error in errors:
                detail = {
                    "message": error.message,
                    "path": list(error.path),
                    "schema_path": list(error.schema_path),
                    "validator": error.validator,
                }
                error_details.append(detail)
            
            raise PacketValidationError(
                message=f"Validation failed for {schema_name}: {errors[0].message}",
                schema_name=schema_name,
                errors=error_details
            )
    
    def get_validation_errors(
        self, packet: dict[str, Any], schema_name: str
    ) -> list[dict]:
        """Get detailed validation errors without raising.
        
        Args:
            packet: The packet dict to validate
            schema_name: Name of the schema
            
        Returns:
            List of error detail dicts (empty if valid)
        """
        if self._skip_validation or schema_name not in self._validators:
            return []
        
        validator = self._validators[schema_name]
        errors = []
        
        for error in validator.iter_errors(packet):
            errors.append({
                "message": error.message,
                "path": list(error.path),
                "schema_path": list(error.schema_path),
                "validator": error.validator,
                "validator_value": error.validator_value,
            })
        
        return errors
    
    def list_schemas(self) -> list[str]:
        """Return list of loaded schema names."""
        return list(self._schemas.keys())
    
    def is_validation_enabled(self) -> bool:
        """Check if validation is enabled (not skipped)."""
        return not self._skip_validation
