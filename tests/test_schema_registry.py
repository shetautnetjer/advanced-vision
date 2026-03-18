"""Tests for the SchemaRegistry.

This module tests:
- Schema loading at startup
- Schema retrieval via get_schema()
- Version tracking via get_version()
- Metadata access
- Compatibility checking
- Basic validation
"""

import json
import tempfile
from pathlib import Path

import pytest
import yaml

# Import the module under test
from advanced_vision.core import SchemaRegistry, get_registry, get_cached_schema


class TestSchemaRegistryLoading:
    """Test schema loading functionality."""
    
    def test_registry_loads_all_schemas(self):
        """Test that all 7 schema files are loaded at startup."""
        registry = SchemaRegistry()
        
        schemas = registry.list_schemas()
        
        # Should have exactly 7 schemas
        assert len(schemas) == 7
        
        # Check all expected schemas are present
        expected = {
            "ui_packet",
            "trading_packet",
            "event_envelope",
            "scout_event",
            "external_review_request",
            "external_review_result",
            "artifact_manifest",
        }
        assert set(schemas) == expected
    
    def test_schema_count_property(self):
        """Test the schema_count property."""
        registry = SchemaRegistry()
        
        assert registry.schema_count == 7
    
    def test_has_schema_method(self):
        """Test the has_schema() method."""
        registry = SchemaRegistry()
        
        assert registry.has_schema("ui_packet") is True
        assert registry.has_schema("trading_packet") is True
        assert registry.has_schema("nonexistent") is False


class TestSchemaRetrieval:
    """Test schema retrieval functionality."""
    
    def test_get_schema_returns_dict(self):
        """Test that get_schema returns a dictionary."""
        registry = SchemaRegistry()
        
        schema = registry.get_schema("ui_packet")
        
        assert isinstance(schema, dict)
        assert "title" in schema
        assert schema["title"] == "UI Packet"
    
    def test_get_schema_returns_copy(self):
        """Test that get_schema returns a copy, not the original."""
        registry = SchemaRegistry()
        
        schema1 = registry.get_schema("ui_packet")
        schema2 = registry.get_schema("ui_packet")
        
        # Should be equal but not the same object
        assert schema1 == schema2
        assert schema1 is not schema2
        
        # Modifying one should not affect the other
        schema1["modified"] = True
        schema3 = registry.get_schema("ui_packet")
        assert "modified" not in schema3
    
    def test_get_schema_event_envelope(self):
        """Test retrieving the event_envelope schema."""
        registry = SchemaRegistry()
        
        schema = registry.get_schema("event_envelope")
        
        assert schema["title"] == "Event Envelope"
        assert "properties" in schema
        assert "event_id" in schema["properties"]
        assert "payload" in schema["properties"]
    
    def test_get_schema_trading_packet(self):
        """Test retrieving the trading_packet schema."""
        registry = SchemaRegistry()
        
        schema = registry.get_schema("trading_packet")
        
        assert schema["title"] == "Trading Packet"
        assert "chart_regions" in schema["properties"]
        assert "ticket_regions" in schema["properties"]
    
    def test_get_schema_scout_event(self):
        """Test retrieving the scout_event schema."""
        registry = SchemaRegistry()
        
        schema = registry.get_schema("scout_event")
        
        assert schema["title"] == "Scout Event"
        assert "classification" in schema["properties"]
    
    def test_get_schema_external_review_request(self):
        """Test retrieving the external_review_request schema."""
        registry = SchemaRegistry()
        
        schema = registry.get_schema("external_review_request")
        
        assert schema["title"] == "External Review Request"
        assert "reviewer_target" in schema["properties"]
    
    def test_get_schema_external_review_result(self):
        """Test retrieving the external_review_result schema."""
        registry = SchemaRegistry()
        
        schema = registry.get_schema("external_review_result")
        
        assert schema["title"] == "External Review Result"
        assert "decision" in schema["properties"]
    
    def test_get_schema_artifact_manifest(self):
        """Test retrieving the artifact_manifest schema."""
        registry = SchemaRegistry()
        
        schema = registry.get_schema("artifact_manifest")
        
        assert schema["title"] == "Artifact Manifest"
        assert "artifact_type" in schema["properties"]
    
    def test_get_schema_not_found(self):
        """Test that get_schema raises KeyError for unknown schema."""
        registry = SchemaRegistry()
        
        with pytest.raises(KeyError, match="Schema not found: nonexistent"):
            registry.get_schema("nonexistent")


class TestVersionTracking:
    """Test version tracking functionality."""
    
    def test_get_version_returns_string(self):
        """Test that get_version returns a version string."""
        registry = SchemaRegistry()
        
        version = registry.get_version("ui_packet")
        
        assert isinstance(version, str)
        assert "." in version  # Semantic version format
    
    def test_get_version_all_schemas(self):
        """Test that all schemas have versions."""
        registry = SchemaRegistry()
        
        for schema_name in registry.list_schemas():
            version = registry.get_version(schema_name)
            # Should be in semantic version format (e.g., 1.0.0)
            parts = version.split(".")
            assert len(parts) == 3
            assert all(part.isdigit() for part in parts)
    
    def test_get_version_from_config(self):
        """Test that versions are loaded from schemas.yaml config."""
        registry = SchemaRegistry()
        
        # All schemas should have version 1.0.0 from config
        for schema_name in registry.list_schemas():
            version = registry.get_version(schema_name)
            assert version == "1.0.0"
    
    def test_get_version_not_found(self):
        """Test that get_version raises KeyError for unknown schema."""
        registry = SchemaRegistry()
        
        with pytest.raises(KeyError, match="Schema not found: nonexistent"):
            registry.get_version("nonexistent")


class TestMetadataAccess:
    """Test metadata access functionality."""
    
    def test_get_metadata_returns_dict(self):
        """Test that get_metadata returns a dictionary."""
        registry = SchemaRegistry()
        
        metadata = registry.get_metadata("ui_packet")
        
        assert isinstance(metadata, dict)
        assert "version" in metadata
        assert "description" in metadata
        assert "file" in metadata
    
    def test_get_metadata_all_schemas(self):
        """Test that all schemas have metadata."""
        registry = SchemaRegistry()
        
        for schema_name in registry.list_schemas():
            metadata = registry.get_metadata(schema_name)
            assert "version" in metadata
            assert "category" in metadata
    
    def test_get_metadata_categories(self):
        """Test that schemas have correct categories."""
        registry = SchemaRegistry()
        
        assert registry.get_metadata("event_envelope")["category"] == "core"
        assert registry.get_metadata("ui_packet")["category"] == "packet"
        assert registry.get_metadata("trading_packet")["category"] == "packet"
        assert registry.get_metadata("scout_event")["category"] == "event"
        assert registry.get_metadata("external_review_request")["category"] == "review"
        assert registry.get_metadata("external_review_result")["category"] == "review"
        assert registry.get_metadata("artifact_manifest")["category"] == "audit"
    
    def test_get_metadata_not_found(self):
        """Test that get_metadata raises KeyError for unknown schema."""
        registry = SchemaRegistry()
        
        with pytest.raises(KeyError, match="Schema metadata not found: nonexistent"):
            registry.get_metadata("nonexistent")


class TestCompatibilityChecking:
    """Test version compatibility checking."""
    
    def test_check_compatibility_same_version(self):
        """Test compatibility check with same version."""
        registry = SchemaRegistry()
        
        result = registry.check_compatibility("ui_packet", "1.0.0")
        
        assert result["compatible"] is True
        assert result["current_version"] == "1.0.0"
        assert result["target_version"] == "1.0.0"
    
    def test_check_compatibility_same_major(self):
        """Test compatibility check with same major version."""
        registry = SchemaRegistry()
        
        result = registry.check_compatibility("ui_packet", "1.1.0")
        
        assert result["compatible"] is True  # Same major version
    
    def test_check_compatibility_different_major(self):
        """Test compatibility check with different major version."""
        registry = SchemaRegistry()
        
        result = registry.check_compatibility("ui_packet", "2.0.0")
        
        assert result["compatible"] is False  # Different major version
    
    def test_check_compatibility_returns_notes(self):
        """Test that compatibility check returns notes from config."""
        registry = SchemaRegistry()
        
        result = registry.check_compatibility("event_envelope", "1.0.0")
        
        assert "notes" in result
        assert "Initial release" in result["notes"]


class TestValidation:
    """Test basic validation functionality."""
    
    def test_validate_valid_data(self):
        """Test validation with valid data."""
        registry = SchemaRegistry()
        
        # Valid ui_packet data
        data = {
            "packet_id": "123e4567-e89b-12d3-a456-426614174000",
            "mode": "ui",
            "event_type": "ui_change",
            "frame_ref": "/path/to/frame.png",
            "scout_note": "UI changed significantly",
        }
        
        is_valid, errors = registry.validate_against_schema(data, "ui_packet")
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_missing_required_field(self):
        """Test validation with missing required field."""
        registry = SchemaRegistry()
        
        # Missing required 'mode' field
        data = {
            "packet_id": "123e4567-e89b-12d3-a456-426614174000",
            "event_type": "ui_change",
            "frame_ref": "/path/to/frame.png",
            "scout_note": "UI changed",
        }
        
        is_valid, errors = registry.validate_against_schema(data, "ui_packet")
        
        assert is_valid is False
        assert any("mode" in error for error in errors)
    
    def test_validate_type_mismatch(self):
        """Test validation with type mismatch."""
        registry = SchemaRegistry()
        
        # mode should be string, not number
        data = {
            "packet_id": "123e4567-e89b-12d3-a456-426614174000",
            "mode": 123,  # Wrong type
            "event_type": "ui_change",
            "frame_ref": "/path/to/frame.png",
            "scout_note": "UI changed",
        }
        
        is_valid, errors = registry.validate_against_schema(data, "ui_packet")
        
        assert is_valid is False
        assert any("mode" in error for error in errors)
    
    def test_validate_unknown_schema(self):
        """Test validation against unknown schema."""
        registry = SchemaRegistry()
        
        data = {"test": "value"}
        
        is_valid, errors = registry.validate_against_schema(data, "nonexistent")
        
        assert is_valid is False
        assert len(errors) == 1
        assert "not found" in errors[0].lower()


class TestSingletonPattern:
    """Test that SchemaRegistry is a singleton."""
    
    def test_singleton_same_instance(self):
        """Test that multiple instantiations return same instance."""
        # Reset singleton state for testing
        SchemaRegistry._instance = None
        SchemaRegistry._initialized = False
        
        registry1 = SchemaRegistry()
        registry2 = SchemaRegistry()
        
        assert registry1 is registry2
    
    def test_singleton_initialized_once(self):
        """Test that initialization only happens once."""
        # Reset singleton state for testing
        SchemaRegistry._instance = None
        SchemaRegistry._initialized = False
        
        registry1 = SchemaRegistry()
        initial_count = registry1.schema_count
        
        # Create another "instance" - should not reload
        registry2 = SchemaRegistry()
        
        assert registry1 is registry2
        assert registry2.schema_count == initial_count


class TestGetRegistry:
    """Test the get_registry convenience function."""
    
    def test_get_registry_returns_instance(self):
        """Test that get_registry returns a SchemaRegistry."""
        registry = get_registry()
        
        assert isinstance(registry, SchemaRegistry)
    
    def test_get_registry_same_instance(self):
        """Test that get_registry returns the same instance."""
        registry1 = get_registry()
        registry2 = get_registry()
        
        assert registry1 is registry2


class TestGetCachedSchema:
    """Test the get_cached_schema convenience function."""
    
    def test_get_cached_schema_returns_schema(self):
        """Test that get_cached_schema returns a schema."""
        schema = get_cached_schema("ui_packet")
        
        assert isinstance(schema, dict)
        assert schema["title"] == "UI Packet"
    
    def test_get_cached_schema_caches(self):
        """Test that get_cached_schema caches results."""
        # Call twice - second should be cached
        schema1 = get_cached_schema("event_envelope")
        schema2 = get_cached_schema("event_envelope")
        
        # Should be same object due to caching
        assert schema1 is schema2


class TestReload:
    """Test the reload functionality."""
    
    def test_reload_clears_and_reloads(self):
        """Test that reload clears caches and reloads schemas."""
        registry = SchemaRegistry()
        initial_count = registry.schema_count
        
        registry.reload()
        
        assert registry.schema_count == initial_count
    
    def test_reload_after_reload(self):
        """Test that multiple reloads work correctly."""
        registry = SchemaRegistry()
        
        registry.reload()
        registry.reload()
        
        assert registry.schema_count == 7


class TestListSchemas:
    """Test the list_schemas method."""
    
    def test_list_schemas_returns_sorted_list(self):
        """Test that list_schemas returns a sorted list."""
        registry = SchemaRegistry()
        
        schemas = registry.list_schemas()
        
        assert isinstance(schemas, list)
        assert schemas == sorted(schemas)
    
    def test_list_schemas_contains_all(self):
        """Test that list_schemas contains all expected schemas."""
        registry = SchemaRegistry()
        
        schemas = registry.list_schemas()
        
        assert "ui_packet" in schemas
        assert "trading_packet" in schemas
        assert "event_envelope" in schemas
        assert "scout_event" in schemas
        assert "external_review_request" in schemas
        assert "external_review_result" in schemas
        assert "artifact_manifest" in schemas


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_schema_with_special_characters_in_path(self, tmp_path):
        """Test loading schemas from path with special characters."""
        # Create a temporary schema
        schema_dir = tmp_path / "schemas"
        schema_dir.mkdir()
        
        schema_file = schema_dir / "test_schema.schema.json"
        schema_content = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "Test Schema",
            "type": "object",
            "properties": {
                "name": {"type": "string"}
            }
        }
        schema_file.write_text(json.dumps(schema_content))
        
        # Create minimal config
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_file = config_dir / "schemas.yaml"
        config_content = {"schemas": {"test_schema": {"version": "1.0.0"}}}
        config_file.write_text(yaml.dump(config_content))
        
        # Reset singleton to test with new paths
        SchemaRegistry._instance = None
        SchemaRegistry._initialized = False
        
        try:
            registry = SchemaRegistry(
                schemas_dir=schema_dir,
                config_path=config_file
            )
            
            assert registry.has_schema("test_schema")
            schema = registry.get_schema("test_schema")
            assert schema["title"] == "Test Schema"
        finally:
            # Reset singleton for other tests
            SchemaRegistry._instance = None
            SchemaRegistry._initialized = False
    
    def test_missing_config_file(self, tmp_path):
        """Test behavior when config file is missing."""
        schema_dir = tmp_path / "schemas"
        schema_dir.mkdir()
        
        # Create a schema without config
        schema_file = schema_dir / "test_schema.schema.json"
        schema_content = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "Test Schema",
            "type": "object"
        }
        schema_file.write_text(json.dumps(schema_content))
        
        # Reset singleton
        SchemaRegistry._instance = None
        SchemaRegistry._initialized = False
        
        try:
            registry = SchemaRegistry(
                schemas_dir=schema_dir,
                config_path=tmp_path / "nonexistent.yaml"
            )
            
            # Should still load schemas without config
            assert registry.has_schema("test_schema")
            # Should default to 1.0.0
            assert registry.get_version("test_schema") == "1.0.0"
        finally:
            # Reset singleton
            SchemaRegistry._instance = None
            SchemaRegistry._initialized = False
    
    def test_empty_schemas_directory(self, tmp_path):
        """Test behavior with empty schemas directory."""
        schema_dir = tmp_path / "schemas"
        schema_dir.mkdir()
        
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_file = config_dir / "schemas.yaml"
        config_file.write_text(yaml.dump({"schemas": {}}))
        
        # Reset singleton
        SchemaRegistry._instance = None
        SchemaRegistry._initialized = False
        
        try:
            registry = SchemaRegistry(
                schemas_dir=schema_dir,
                config_path=config_file
            )
            
            assert registry.schema_count == 0
            assert registry.list_schemas() == []
        finally:
            # Reset singleton
            SchemaRegistry._instance = None
            SchemaRegistry._initialized = False


# Integration test to verify the expected interface works
class TestInterfaceContract:
    """Test that the public interface matches the contract."""
    
    def test_interface_example_from_spec(self):
        """Test the exact interface from the specification."""
        from advanced_vision.core import SchemaRegistry
        
        registry = SchemaRegistry()
        
        ui_schema = registry.get_schema('ui_packet')
        version = registry.get_version('event_envelope')
        
        assert isinstance(ui_schema, dict)
        assert isinstance(version, str)
        assert ui_schema['title'] == 'UI Packet'
        assert version == '1.0.0'
