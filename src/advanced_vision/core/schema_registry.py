"""Schema Registry - Centralized schema loading, caching, and version tracking.

Provides a singleton-style registry for JSON Schema files used throughout
the advanced-vision system. Schemas are loaded at startup and cached for
performance.

Usage:
    from advanced_vision.core import SchemaRegistry
    
    registry = SchemaRegistry()
    ui_schema = registry.get_schema('ui_packet')
    version = registry.get_version('event_envelope')
"""

from __future__ import annotations

import functools
import json
import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# Default paths
DEFAULT_SCHEMAS_DIR = Path(__file__).parent.parent.parent.parent / "schemas"
DEFAULT_CONFIG_PATH = Path(__file__).parent.parent.parent.parent / "config" / "schemas.yaml"


class SchemaRegistry:
    """Registry for JSON schemas with caching and version tracking.
    
    Loads all schema files at initialization and provides fast access
    via get_schema(). Schema metadata (versions, compatibility) is
    loaded from config/schemas.yaml.
    
    Attributes:
        _schemas: Cached schema dictionaries keyed by schema name
        _metadata: Schema metadata from schemas.yaml
        _versions: Schema version cache keyed by schema name
    """
    
    _instance: SchemaRegistry | None = None
    _initialized: bool = False
    
    def __new__(cls, *args: Any, **kwargs: Any) -> SchemaRegistry:
        """Singleton pattern - ensures only one registry exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(
        self,
        schemas_dir: Path | str | None = None,
        config_path: Path | str | None = None,
    ) -> None:
        """Initialize the schema registry.
        
        Args:
            schemas_dir: Directory containing .schema.json files.
                        Defaults to project root /schemas.
            config_path: Path to schemas.yaml config file.
                        Defaults to project root /config/schemas.yaml.
        """
        # Skip re-initialization for singleton
        if SchemaRegistry._initialized:
            return
            
        self._schemas_dir = Path(schemas_dir) if schemas_dir else DEFAULT_SCHEMAS_DIR
        self._config_path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
        
        self._schemas: dict[str, dict[str, Any]] = {}
        self._metadata: dict[str, Any] = {}
        self._versions: dict[str, str] = {}
        
        self._load_config()
        self._load_all_schemas()
        
        SchemaRegistry._initialized = True
        logger.info(f"SchemaRegistry initialized with {len(self._schemas)} schemas")
    
    def _load_config(self) -> None:
        """Load schema metadata from schemas.yaml config file."""
        if not self._config_path.exists():
            logger.warning(f"Schema config not found at {self._config_path}")
            self._metadata = {"schemas": {}, "compatibility": {}}
            return
        
        try:
            with open(self._config_path, "r") as f:
                self._metadata = yaml.safe_load(f) or {}
            logger.debug(f"Loaded schema config from {self._config_path}")
        except yaml.YAMLError as e:
            logger.error(f"Failed to parse schemas.yaml: {e}")
            self._metadata = {"schemas": {}, "compatibility": {}}
        except Exception as e:
            logger.error(f"Failed to load schema config: {e}")
            self._metadata = {"schemas": {}, "compatibility": {}}
    
    def _load_all_schemas(self) -> None:
        """Load all JSON schema files from the schemas directory."""
        if not self._schemas_dir.exists():
            logger.error(f"Schemas directory not found: {self._schemas_dir}")
            return
        
        schema_files = list(self._schemas_dir.glob("*.schema.json"))
        
        for schema_file in schema_files:
            try:
                self._load_schema_file(schema_file)
            except Exception as e:
                logger.error(f"Failed to load schema {schema_file.name}: {e}")
    
    def _load_schema_file(self, path: Path) -> None:
        """Load a single schema file and cache it.
        
        Args:
            path: Path to the .schema.json file
        """
        # Extract schema name from filename (e.g., "ui_packet.schema.json" -> "ui_packet")
        schema_name = path.stem.replace(".schema", "")
        
        with open(path, "r") as f:
            schema_data = json.load(f)
        
        self._schemas[schema_name] = schema_data
        
        # Extract version from schema or metadata
        version = self._extract_version(schema_name, schema_data)
        self._versions[schema_name] = version
        
        logger.debug(f"Loaded schema: {schema_name} (v{version})")
    
    def _extract_version(self, schema_name: str, schema_data: dict[str, Any]) -> str:
        """Extract version from schema data or metadata config.
        
        Args:
            schema_name: Name of the schema
            schema_data: The parsed schema JSON
            
        Returns:
            Version string (defaults to "1.0.0" if not found)
        """
        # First check metadata config
        meta_schemas = self._metadata.get("schemas", {})
        if schema_name in meta_schemas:
            version = meta_schemas[schema_name].get("version")
            if version:
                return version
        
        # Then check schema's $id or version field
        if "version" in schema_data:
            return str(schema_data["version"])
        
        # Try to extract from $id URL
        schema_id = schema_data.get("$id", "")
        if "/v" in schema_id:
            # Extract version from URL like .../v1.0.0/...
            parts = schema_id.split("/")
            for part in parts:
                if part.startswith("v") and "." in part:
                    return part[1:]  # Remove 'v' prefix
        
        return "1.0.0"
    
    def get_schema(self, name: str) -> dict[str, Any]:
        """Get a schema by name.
        
        Args:
            name: Schema name (e.g., 'ui_packet', 'event_envelope')
            
        Returns:
            The schema dictionary
            
        Raises:
            KeyError: If schema is not found
        """
        if name not in self._schemas:
            raise KeyError(f"Schema not found: {name}")
        return self._schemas[name].copy()
    
    def get_version(self, name: str) -> str:
        """Get the version of a schema.
        
        Args:
            name: Schema name
            
        Returns:
            Version string (e.g., '1.0.0')
            
        Raises:
            KeyError: If schema is not found
        """
        if name not in self._versions:
            raise KeyError(f"Schema not found: {name}")
        return self._versions[name]
    
    def get_metadata(self, name: str) -> dict[str, Any]:
        """Get metadata for a schema from schemas.yaml.
        
        Args:
            name: Schema name
            
        Returns:
            Metadata dictionary (description, version, file mapping, etc.)
            
        Raises:
            KeyError: If schema is not found in metadata
        """
        meta_schemas = self._metadata.get("schemas", {})
        if name not in meta_schemas:
            raise KeyError(f"Schema metadata not found: {name}")
        return meta_schemas[name].copy()
    
    def list_schemas(self) -> list[str]:
        """List all available schema names.
        
        Returns:
            List of schema names
        """
        return sorted(self._schemas.keys())
    
    def has_schema(self, name: str) -> bool:
        """Check if a schema exists.
        
        Args:
            name: Schema name
            
        Returns:
            True if schema exists, False otherwise
        """
        return name in self._schemas
    
    def reload(self) -> None:
        """Reload all schemas and config. Useful for development."""
        self._schemas.clear()
        self._versions.clear()
        self._metadata.clear()
        self._load_config()
        self._load_all_schemas()
        logger.info(f"SchemaRegistry reloaded with {len(self._schemas)} schemas")
    
    def check_compatibility(
        self, 
        schema_name: str, 
        target_version: str
    ) -> dict[str, Any]:
        """Check version compatibility for a schema.
        
        Args:
            schema_name: Name of the schema
            target_version: Version to check compatibility with
            
        Returns:
            Compatibility info dict with keys:
            - compatible: bool
            - current_version: str
            - notes: str (optional compatibility notes)
        """
        current_version = self.get_version(schema_name)
        
        # Parse versions
        current_parts = [int(x) for x in current_version.split(".")]
        target_parts = [int(x) for x in target_version.split(".")]
        
        # Major version must match for compatibility
        compatible = current_parts[0] == target_parts[0]
        
        result = {
            "compatible": compatible,
            "current_version": current_version,
            "target_version": target_version,
        }
        
        # Check for compatibility notes in metadata
        compat_matrix = self._metadata.get("compatibility", {})
        schema_compat = compat_matrix.get(schema_name, {})
        version_notes = schema_compat.get(target_version)
        if version_notes:
            result["notes"] = version_notes
        
        return result
    
    def validate_against_schema(
        self, 
        data: dict[str, Any], 
        schema_name: str
    ) -> tuple[bool, list[str]]:
        """Validate data against a schema.
        
        Note: This is a basic validation. For full JSON Schema validation,
        use jsonschema library.
        
        Args:
            data: Data to validate
            schema_name: Name of the schema to validate against
            
        Returns:
            Tuple of (is_valid, list of error messages)
        """
        try:
            schema = self.get_schema(schema_name)
        except KeyError as e:
            return False, [str(e)]
        
        errors = []
        
        # Check required fields
        required = schema.get("required", [])
        for field in required:
            if field not in data:
                errors.append(f"Missing required field: {field}")
        
        # Check type constraints for present fields
        properties = schema.get("properties", {})
        for field, value in data.items():
            if field in properties:
                prop_schema = properties[field]
                expected_type = prop_schema.get("type")
                if expected_type and not self._check_type(value, expected_type):
                    errors.append(
                        f"Field '{field}': expected {expected_type}, "
                        f"got {type(value).__name__}"
                    )
        
        return len(errors) == 0, errors
    
    def _check_type(self, value: Any, expected_type: str) -> bool:
        """Check if a value matches an expected JSON Schema type.
        
        Args:
            value: Value to check
            expected_type: JSON Schema type string
            
        Returns:
            True if type matches
        """
        type_map = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "array": list,
            "object": dict,
            "null": type(None),
        }
        
        expected = type_map.get(expected_type)
        if expected is None:
            return True  # Unknown type, assume valid
        
        return isinstance(value, expected)
    
    @property
    def schema_count(self) -> int:
        """Number of loaded schemas."""
        return len(self._schemas)


def get_registry(
    schemas_dir: Path | str | None = None,
    config_path: Path | str | None = None,
) -> SchemaRegistry:
    """Get or create the global schema registry instance.
    
    This is a convenience function that returns the singleton registry.
    
    Args:
        schemas_dir: Optional override for schemas directory
        config_path: Optional override for config file path
        
    Returns:
        The SchemaRegistry instance
    """
    return SchemaRegistry(schemas_dir=schemas_dir, config_path=config_path)


# Convenience function for quick schema access
@functools.lru_cache(maxsize=128)
def get_cached_schema(name: str) -> dict[str, Any]:
    """Get a schema with LRU caching for repeated access.
    
    Args:
        name: Schema name
        
    Returns:
        Schema dictionary
    """
    registry = get_registry()
    return registry.get_schema(name)
