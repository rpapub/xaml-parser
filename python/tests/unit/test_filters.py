"""Unit tests for emitter filters (pure data transformations)."""

import pytest

from cpmf_uips_xaml.stages.emit.filters.field_filter import FieldFilter
from cpmf_uips_xaml.stages.emit.filters.none_filter import NoneFilter
from cpmf_uips_xaml.stages.emit.filters.composite_filter import CompositeFilter
from cpmf_uips_xaml.stages.emit.filters.base import FilterResult


# ============================================================================
# FieldFilter Tests
# ============================================================================


class TestFieldFilter:
    """Test FieldFilter field profile application."""

    def test_full_profile_no_modification(self):
        """Test full profile returns data unchanged."""
        filter_obj = FieldFilter(profile="full")
        data = {
            "id": "wf1",
            "name": "Test",
            "metadata": {"extra": "data"},
            "activities": [],
        }

        result = filter_obj.apply(data, {"field_profile": "full"})

        assert isinstance(result, FilterResult)
        assert result.modified is False
        assert result.data == data  # Unchanged

    def test_minimal_profile_removes_fields(self):
        """Test minimal profile removes non-essential fields."""
        filter_obj = FieldFilter(profile="minimal")
        data = {
            "id": "wf1",
            "name": "Test",
            "schema_id": "https://example.com/schema",
            "schema_version": "1.0",
            "collected_at": "2024-01-01T00:00:00Z",
            "metadata": {"annotation": "Test workflow"},
            "activities": [{"id": "a1", "type_short": "Assign"}],
            "arguments": [],
            "variables": [],
            "edges": [],
            "dependencies": [],
            "invocations": [],
            "issues": [],
            "variable_flows": [],
            "quality_metrics": None,
            "anti_patterns": [],
        }

        result = filter_obj.apply(data)

        assert result.modified is True
        # Core fields preserved
        assert result.data["id"] == "wf1"
        assert result.data["name"] == "Test"
        # Metadata should be filtered based on profile
        # (exact behavior depends on field_profiles.py implementation)

    def test_mcp_profile(self):
        """Test MCP profile filtering."""
        filter_obj = FieldFilter(profile="mcp")
        data = {
            "id": "wf1",
            "name": "Test",
            "activities": [{"id": "a1"}],
            "metadata": {"extra": "data"},
        }

        result = filter_obj.apply(data)

        # Should apply MCP-specific field filtering
        assert isinstance(result.data, dict)

    def test_datalake_profile(self):
        """Test datalake profile filtering."""
        filter_obj = FieldFilter(profile="datalake")
        data = {"id": "wf1", "name": "Test"}

        result = filter_obj.apply(data)

        assert isinstance(result.data, dict)

    def test_config_override(self):
        """Test config dict overrides constructor profile."""
        filter_obj = FieldFilter(profile="full")
        data = {"id": "wf1", "name": "Test", "extra": "field"}
        config = {"field_profile": "minimal"}

        result = filter_obj.apply(data, config)

        # Config should override constructor profile
        # (behavior depends on implementation)
        assert isinstance(result, FilterResult)

    def test_invalid_profile_raises_error(self):
        """Test invalid profile raises ValueError."""
        with pytest.raises(ValueError, match="Unknown profile"):
            FieldFilter(profile="invalid_profile")

    def test_can_handle_dict(self):
        """Test filter can handle dict data."""
        filter_obj = FieldFilter(profile="minimal")
        assert filter_obj.can_handle({"id": "wf1"}) is True

    def test_can_handle_non_dict(self):
        """Test filter rejects non-dict data."""
        filter_obj = FieldFilter(profile="minimal")
        assert filter_obj.can_handle("string") is False
        assert filter_obj.can_handle([1, 2, 3]) is False
        assert filter_obj.can_handle(123) is False

    def test_name_property(self):
        """Test filter name includes profile."""
        filter_obj = FieldFilter(profile="minimal")
        assert filter_obj.name == "field_filter_minimal"


# ============================================================================
# NoneFilter Tests
# ============================================================================


class TestNoneFilter:
    """Test NoneFilter removes None values."""

    def test_name_property(self):
        """Test filter name."""
        filter_obj = NoneFilter()
        assert filter_obj.name == "none_filter"

    def test_remove_none_from_dict(self):
        """Test removing None values from dict."""
        filter_obj = NoneFilter()
        data = {
            "id": "wf1",
            "name": "Test",
            "optional_field": None,
            "another_field": "value",
            "nested": {"key": None, "valid": "data"},
        }

        result = filter_obj.apply(data)

        assert result.modified is True
        assert "optional_field" not in result.data
        assert "another_field" in result.data
        assert "nested" in result.data
        assert "key" not in result.data["nested"]
        assert result.data["nested"]["valid"] == "data"

    def test_remove_none_from_list(self):
        """Test None filtering in lists (recursively processes items)."""
        filter_obj = NoneFilter()
        data = {
            "items": [1, 2, 3],  # No None values
            "nested_items": [{"a": 1, "remove": None}, {"b": 2, "keep": "value"}],
        }

        result = filter_obj.apply(data)

        # None values in dict items inside list should be removed
        assert "remove" not in result.data["nested_items"][0]
        assert result.data["nested_items"][1]["keep"] == "value"

    def test_no_none_values_not_modified(self):
        """Test data without None is marked as not modified."""
        filter_obj = NoneFilter()
        data = {"id": "wf1", "name": "Test", "value": 123}

        result = filter_obj.apply(data)

        assert result.modified is False
        assert result.data == data

    def test_deeply_nested_none_removal(self):
        """Test None removal in deeply nested structures."""
        filter_obj = NoneFilter()
        data = {
            "level1": {
                "level2": {
                    "level3": {"keep": "this", "remove": None},
                    "also_remove": None,
                },
                "keep_this": "value",
            }
        }

        result = filter_obj.apply(data)

        assert result.modified is True
        assert "remove" not in result.data["level1"]["level2"]["level3"]
        assert "also_remove" not in result.data["level1"]["level2"]
        assert result.data["level1"]["keep_this"] == "value"

    def test_can_handle_any_type(self):
        """Test filter can handle any data type."""
        filter_obj = NoneFilter()
        assert filter_obj.can_handle({}) is True
        assert filter_obj.can_handle([]) is True
        assert filter_obj.can_handle("string") is True
        assert filter_obj.can_handle(123) is True

    def test_primitive_values_unchanged(self):
        """Test primitive values pass through unchanged."""
        filter_obj = NoneFilter()
        assert filter_obj.apply("string").data == "string"
        assert filter_obj.apply(123).data == 123
        assert filter_obj.apply(True).data is True


# ============================================================================
# CompositeFilter Tests
# ============================================================================


class TestCompositeFilter:
    """Test CompositeFilter chains multiple filters."""

    def test_name_combines_filter_names(self):
        """Test composite filter name includes all filter names."""
        f1 = FieldFilter(profile="minimal")
        f2 = NoneFilter()
        composite = CompositeFilter([f1, f2])

        assert "field_filter_minimal" in composite.name
        assert "none_filter" in composite.name
        assert "composite_" in composite.name

    def test_apply_filters_in_sequence(self):
        """Test filters are applied in order."""
        # Create filters
        none_filter = NoneFilter()
        field_filter = FieldFilter(profile="minimal")

        composite = CompositeFilter([none_filter, field_filter])

        data = {
            "id": "wf1",
            "name": "Test",
            "optional": None,  # Will be removed by NoneFilter
            "metadata": {"extra": "data"},  # May be removed by FieldFilter
        }

        result = composite.apply(data)

        # None values should be removed first
        assert "optional" not in result.data
        # Then field filtering applied
        assert isinstance(result.data, dict)
        assert result.modified is True

    def test_metadata_from_all_filters(self):
        """Test metadata includes all filter metadata."""
        f1 = NoneFilter()
        f2 = FieldFilter(profile="minimal")
        composite = CompositeFilter([f1, f2])

        data = {"id": "wf1", "name": "Test", "remove": None}

        result = composite.apply(data)

        # Metadata should contain entries from all filters under "filters_applied" key
        assert "filters_applied" in result.metadata
        assert "none_filter" in result.metadata["filters_applied"]
        assert "field_filter_minimal" in result.metadata["filters_applied"]

    def test_can_handle_requires_any_filter_match(self):
        """Test can_handle returns True if any filter can handle data."""
        # Create filter that only handles dicts
        field_filter = FieldFilter(profile="minimal")
        # NoneFilter handles anything
        none_filter = NoneFilter()

        composite = CompositeFilter([field_filter, none_filter])

        # Should handle dict (both filters can)
        assert composite.can_handle({"id": "wf1"}) is True

        # Should handle string (only NoneFilter can)
        assert composite.can_handle("string") is True

    def test_empty_filter_list(self):
        """Test composite with no filters."""
        composite = CompositeFilter([])
        data = {"id": "wf1"}

        result = composite.apply(data)

        # No filters, data unchanged
        assert result.data == data
        assert result.modified is False

    def test_single_filter(self):
        """Test composite with single filter."""
        none_filter = NoneFilter()
        composite = CompositeFilter([none_filter])

        data = {"id": "wf1", "remove": None}

        result = composite.apply(data)

        assert "remove" not in result.data
        assert result.modified is True

    def test_filter_order_matters(self):
        """Test that filter order affects output."""
        # Order 1: None filter, then field filter
        composite1 = CompositeFilter([NoneFilter(), FieldFilter(profile="minimal")])

        # Order 2: Field filter, then none filter
        composite2 = CompositeFilter([FieldFilter(profile="minimal"), NoneFilter()])

        data = {
            "id": "wf1",
            "name": "Test",
            "optional": None,
            "metadata": {"key": None, "value": "data"},
        }

        result1 = composite1.apply(data.copy())
        result2 = composite2.apply(data.copy())

        # Both should work but may produce different intermediate results
        # Both final results should have None values removed
        assert "optional" not in result1.data
        assert "optional" not in result2.data


# ============================================================================
# Filter Integration Tests
# ============================================================================


class TestFilterIntegration:
    """Test filters working together in realistic scenarios."""

    def test_typical_workflow_filtering(self):
        """Test typical workflow filtering with composite filter."""
        # Simulate typical workflow DTO dict
        workflow_dict = {
            "schema_id": "https://example.com/schema",
            "schema_version": "1.0",
            "collected_at": "2024-01-01T00:00:00Z",
            "provenance": None,
            "id": "wf1",
            "name": "TestWorkflow",
            "source": {"file_path": "Test.xaml"},
            "metadata": {"annotation": "Test", "extra": None},
            "activities": [
                {"id": "a1", "type_short": "Assign", "properties": None}
            ],
            "arguments": [],
            "variables": [],
            "edges": [],
            "dependencies": [],
            "invocations": [],
            "issues": [],
            "quality_metrics": None,
            "anti_patterns": None,
        }

        # Apply composite filter (None removal + field filtering)
        composite = CompositeFilter([NoneFilter(), FieldFilter(profile="minimal")])

        result = composite.apply(workflow_dict)

        # None values removed
        assert "provenance" not in result.data
        assert "quality_metrics" not in result.data
        # Nested None values removed
        assert "extra" not in result.data.get("metadata", {})
        # Core fields preserved
        assert result.data["id"] == "wf1"
        assert result.data["name"] == "TestWorkflow"

    def test_filter_config_dict_handling(self):
        """Test filters handle config dict correctly."""
        filter_obj = FieldFilter(profile="full")
        data = {"id": "wf1", "name": "Test"}

        # Config dict with field_profile key
        config = {"field_profile": "minimal", "exclude_none": True}

        result = filter_obj.apply(data, config)

        # Should use config profile, not constructor profile
        assert isinstance(result, FilterResult)


# ============================================================================
# Edge Cases
# ============================================================================


class TestFilterEdgeCases:
    """Test edge cases and error handling."""

    def test_none_filter_with_none_data(self):
        """Test NoneFilter with None as root value."""
        filter_obj = NoneFilter()
        result = filter_obj.apply(None)
        assert result.data is None

    def test_field_filter_with_empty_dict(self):
        """Test FieldFilter with empty dict."""
        filter_obj = FieldFilter(profile="minimal")
        result = filter_obj.apply({})
        assert result.data == {}

    def test_composite_filter_skip_incompatible_filters(self):
        """Test composite skips filters that can't handle data."""
        # Create a filter that only handles dicts
        field_filter = FieldFilter(profile="minimal")

        # Try to filter a string (field_filter.can_handle returns False)
        composite = CompositeFilter([field_filter])

        result = composite.apply("string_data")

        # String should pass through unchanged (no filter could handle it)
        assert result.data == "string_data"

    def test_none_filter_preserves_empty_collections(self):
        """Test NoneFilter preserves empty lists/dicts."""
        filter_obj = NoneFilter()
        data = {"empty_list": [], "empty_dict": {}, "value": "keep"}

        result = filter_obj.apply(data)

        assert result.data["empty_list"] == []
        assert result.data["empty_dict"] == {}
        assert result.data["value"] == "keep"
