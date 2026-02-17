"""Tests for DataUtils utility functions."""

from cpmf_uips_xaml.shared.utils import DataUtils


class TestMergeDictionaries:
    """Tests for DataUtils.merge_dictionaries()."""

    def test_merge_empty_dicts(self):
        """Test merging two empty dictionaries."""
        result = DataUtils.merge_dictionaries({}, {})
        assert result == {}

    def test_merge_with_empty_second(self):
        """Test merging when second dict is empty."""
        dict1 = {"a": 1, "b": 2}
        result = DataUtils.merge_dictionaries(dict1, {})
        assert result == {"a": 1, "b": 2}

    def test_merge_with_empty_first(self):
        """Test merging when first dict is empty."""
        dict2 = {"a": 1, "b": 2}
        result = DataUtils.merge_dictionaries({}, dict2)
        assert result == {"a": 1, "b": 2}

    def test_merge_non_overlapping(self):
        """Test merging dictionaries with no overlapping keys."""
        dict1 = {"a": 1, "b": 2}
        dict2 = {"c": 3, "d": 4}
        result = DataUtils.merge_dictionaries(dict1, dict2)
        assert result == {"a": 1, "b": 2, "c": 3, "d": 4}

    def test_merge_overlapping_scalars(self):
        """Test merging with overlapping scalar values (second wins)."""
        dict1 = {"a": 1, "b": 2}
        dict2 = {"b": 20, "c": 3}
        result = DataUtils.merge_dictionaries(dict1, dict2)
        assert result == {"a": 1, "b": 20, "c": 3}

    def test_merge_nested_dicts(self):
        """Test deep merging of nested dictionaries."""
        dict1 = {"a": {"x": 1, "y": 2}, "b": 3}
        dict2 = {"a": {"y": 20, "z": 30}, "c": 4}
        result = DataUtils.merge_dictionaries(dict1, dict2)
        assert result == {"a": {"x": 1, "y": 20, "z": 30}, "b": 3, "c": 4}

    def test_merge_deeply_nested(self):
        """Test merging deeply nested structures."""
        dict1 = {"level1": {"level2": {"level3": {"value": 1}}}}
        dict2 = {"level1": {"level2": {"level3": {"other": 2}}}}
        result = DataUtils.merge_dictionaries(dict1, dict2)
        assert result == {"level1": {"level2": {"level3": {"value": 1, "other": 2}}}}

    def test_merge_dict_replaces_scalar(self):
        """Test that dict in second replaces scalar in first."""
        dict1 = {"a": 1}
        dict2 = {"a": {"nested": 2}}
        result = DataUtils.merge_dictionaries(dict1, dict2)
        assert result == {"a": {"nested": 2}}

    def test_merge_scalar_replaces_dict(self):
        """Test that scalar in second replaces dict in first."""
        dict1 = {"a": {"nested": 1}}
        dict2 = {"a": 2}
        result = DataUtils.merge_dictionaries(dict1, dict2)
        assert result == {"a": 2}

    def test_merge_preserves_original(self):
        """Test that original dictionaries are not modified."""
        dict1 = {"a": 1}
        dict2 = {"b": 2}
        result = DataUtils.merge_dictionaries(dict1, dict2)
        assert dict1 == {"a": 1}  # Unchanged
        assert dict2 == {"b": 2}  # Unchanged
        assert result == {"a": 1, "b": 2}


class TestFlattenNestedDict:
    """Tests for DataUtils.flatten_nested_dict()."""

    def test_flatten_empty_dict(self):
        """Test flattening empty dictionary."""
        result = DataUtils.flatten_nested_dict({})
        assert result == {}

    def test_flatten_flat_dict(self):
        """Test flattening already flat dictionary."""
        nested = {"a": 1, "b": 2, "c": 3}
        result = DataUtils.flatten_nested_dict(nested)
        assert result == {"a": 1, "b": 2, "c": 3}

    def test_flatten_one_level(self):
        """Test flattening one level of nesting."""
        nested = {"a": {"x": 1, "y": 2}, "b": 3}
        result = DataUtils.flatten_nested_dict(nested)
        assert result == {"a.x": 1, "a.y": 2, "b": 3}

    def test_flatten_multiple_levels(self):
        """Test flattening multiple levels."""
        nested = {"level1": {"level2": {"level3": {"value": 42}}}}
        result = DataUtils.flatten_nested_dict(nested)
        assert result == {"level1.level2.level3.value": 42}

    def test_flatten_custom_separator(self):
        """Test flattening with custom separator."""
        nested = {"a": {"b": {"c": 1}}}
        result = DataUtils.flatten_nested_dict(nested, separator="/")
        assert result == {"a/b/c": 1}

    def test_flatten_mixed_structure(self):
        """Test flattening mixed flat and nested structure."""
        nested = {"flat1": 1, "nested": {"a": 2, "b": {"c": 3}}, "flat2": 4}
        result = DataUtils.flatten_nested_dict(nested)
        assert result == {"flat1": 1, "nested.a": 2, "nested.b.c": 3, "flat2": 4}

    def test_flatten_with_list_values(self):
        """Test flattening dict with list values (lists stay as values)."""
        nested = {"a": {"b": [1, 2, 3]}}
        result = DataUtils.flatten_nested_dict(nested)
        assert result == {"a.b": [1, 2, 3]}

    def test_flatten_complex_nested(self):
        """Test flattening complex nested structure."""
        nested = {
            "config": {"database": {"host": "localhost", "port": 5432}, "cache": True},
            "version": "1.0",
        }
        result = DataUtils.flatten_nested_dict(nested)
        assert result == {
            "config.database.host": "localhost",
            "config.database.port": 5432,
            "config.cache": True,
            "version": "1.0",
        }


class TestExtractUniqueValues:
    """Tests for DataUtils.extract_unique_values()."""

    def test_extract_from_empty_list(self):
        """Test extracting from empty list."""
        result = DataUtils.extract_unique_values([], "field")
        assert result == set()

    def test_extract_simple_values(self):
        """Test extracting simple field values."""
        data = [{"name": "Alice"}, {"name": "Bob"}, {"name": "Charlie"}]
        result = DataUtils.extract_unique_values(data, "name")
        assert result == {"Alice", "Bob", "Charlie"}

    def test_extract_with_duplicates(self):
        """Test that duplicates are removed."""
        data = [{"tag": "A"}, {"tag": "B"}, {"tag": "A"}, {"tag": "C"}, {"tag": "B"}]
        result = DataUtils.extract_unique_values(data, "tag")
        assert result == {"A", "B", "C"}

    def test_extract_missing_field(self):
        """Test extracting field that doesn't exist in some items."""
        data = [{"name": "Alice"}, {"name": "Bob"}, {"other": "value"}]
        result = DataUtils.extract_unique_values(data, "name")
        assert result == {"Alice", "Bob"}

    def test_extract_none_values(self):
        """Test that None values are skipped."""
        data = [{"tag": "A"}, {"tag": None}, {"tag": "B"}]
        result = DataUtils.extract_unique_values(data, "tag")
        # None is falsy, so it should be skipped
        assert result == {"A", "B"}

    def test_extract_empty_string_values(self):
        """Test that empty strings are skipped."""
        data = [{"tag": "A"}, {"tag": ""}, {"tag": "B"}]
        result = DataUtils.extract_unique_values(data, "tag")
        # Empty string is falsy, so it should be skipped
        assert result == {"A", "B"}

    def test_extract_list_values(self):
        """Test extracting when field contains lists."""
        data = [{"tags": ["A", "B"]}, {"tags": ["C", "A"]}, {"tags": ["D"]}]
        result = DataUtils.extract_unique_values(data, "tags")
        assert result == {"A", "B", "C", "D"}

    def test_extract_tuple_values(self):
        """Test extracting when field contains tuples."""
        data = [{"tags": ("X", "Y")}, {"tags": ("Z", "X")}]
        result = DataUtils.extract_unique_values(data, "tags")
        assert result == {"X", "Y", "Z"}

    def test_extract_numeric_values(self):
        """Test extracting numeric values (converted to strings)."""
        data = [{"id": 1}, {"id": 2}, {"id": 3}, {"id": 1}]
        result = DataUtils.extract_unique_values(data, "id")
        assert result == {"1", "2", "3"}


class TestGroupByField:
    """Tests for DataUtils.group_by_field()."""

    def test_group_empty_list(self):
        """Test grouping empty list."""
        result = DataUtils.group_by_field([], "field")
        assert result == {}

    def test_group_single_value(self):
        """Test grouping with single unique value."""
        data = [{"type": "A", "value": 1}, {"type": "A", "value": 2}]
        result = DataUtils.group_by_field(data, "type")
        assert result == {"A": [{"type": "A", "value": 1}, {"type": "A", "value": 2}]}

    def test_group_multiple_values(self):
        """Test grouping with multiple unique values."""
        data = [
            {"type": "A", "value": 1},
            {"type": "B", "value": 2},
            {"type": "A", "value": 3},
            {"type": "C", "value": 4},
        ]
        result = DataUtils.group_by_field(data, "type")
        assert result == {
            "A": [{"type": "A", "value": 1}, {"type": "A", "value": 3}],
            "B": [{"type": "B", "value": 2}],
            "C": [{"type": "C", "value": 4}],
        }

    def test_group_missing_field(self):
        """Test grouping when field is missing (uses 'unknown')."""
        data = [{"type": "A", "value": 1}, {"value": 2}, {"type": "B", "value": 3}]
        result = DataUtils.group_by_field(data, "type")
        assert "A" in result
        assert "B" in result
        assert "unknown" in result
        assert result["unknown"] == [{"value": 2}]

    def test_group_numeric_values(self):
        """Test grouping by numeric field values."""
        data = [
            {"priority": 1, "task": "a"},
            {"priority": 2, "task": "b"},
            {"priority": 1, "task": "c"},
        ]
        result = DataUtils.group_by_field(data, "priority")
        assert result == {
            "1": [{"priority": 1, "task": "a"}, {"priority": 1, "task": "c"}],
            "2": [{"priority": 2, "task": "b"}],
        }

    def test_group_preserves_order(self):
        """Test that items within groups preserve original order."""
        data = [
            {"type": "A", "seq": 1},
            {"type": "B", "seq": 2},
            {"type": "A", "seq": 3},
            {"type": "B", "seq": 4},
            {"type": "A", "seq": 5},
        ]
        result = DataUtils.group_by_field(data, "type")
        assert result["A"][0]["seq"] == 1
        assert result["A"][1]["seq"] == 3
        assert result["A"][2]["seq"] == 5
        assert result["B"][0]["seq"] == 2
        assert result["B"][1]["seq"] == 4

    def test_group_none_field_value(self):
        """Test grouping when field value is None."""
        data = [{"type": "A"}, {"type": None}, {"type": "B"}]
        result = DataUtils.group_by_field(data, "type")
        assert "A" in result
        assert "B" in result
        assert "None" in result
        assert result["None"] == [{"type": None}]
