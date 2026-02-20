"""Data structure utilities for XAML parsing operations.

This module provides helper functions for data structure manipulation,
dictionary operations, and data extraction.
"""

from typing import Any


class DataUtils:
    """Data structure and conversion utilities."""

    @staticmethod
    def merge_dictionaries(dict1: dict[str, Any], dict2: dict[str, Any]) -> dict[str, Any]:
        """Merge two dictionaries with deep merging of nested dicts.

        Args:
            dict1: First dictionary
            dict2: Second dictionary (takes precedence)

        Returns:
            Merged dictionary
        """
        result = dict1.copy()

        for key, value in dict2.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = DataUtils.merge_dictionaries(result[key], value)
            else:
                result[key] = value

        return result

    @staticmethod
    def flatten_nested_dict(nested_dict: dict[str, Any], separator: str = ".") -> dict[str, Any]:
        """Flatten nested dictionary structure.

        Args:
            nested_dict: Dictionary with nested structure
            separator: Separator for flattened keys

        Returns:
            Flattened dictionary
        """

        def _flatten(obj: Any, parent_key: str = "") -> dict[str, Any]:
            items: list[tuple[str, Any]] = []

            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_key = f"{parent_key}{separator}{key}" if parent_key else key
                    items.extend(_flatten(value, new_key).items())
            else:
                return {parent_key: obj}

            return dict(items)

        return _flatten(nested_dict)

    @staticmethod
    def extract_unique_values(data: list[dict[str, Any]], field: str) -> set[str]:
        """Extract unique values for a field from list of dictionaries.

        Args:
            data: List of dictionaries
            field: Field name to extract

        Returns:
            Set of unique values
        """
        values: set[str] = set()
        for item in data:
            if field in item and item[field]:
                if isinstance(item[field], list | tuple):
                    values.update(str(v) for v in item[field])
                else:
                    values.add(str(item[field]))
        return values

    @staticmethod
    def group_by_field(data: list[dict[str, Any]], field: str) -> dict[str, list[dict[str, Any]]]:
        """Group list of dictionaries by field value.

        Args:
            data: List of dictionaries
            field: Field to group by

        Returns:
            Dictionary with field values as keys and lists as values
        """
        groups: dict[str, list[dict[str, Any]]] = {}
        for item in data:
            key = str(item.get(field, "unknown"))
            if key not in groups:
                groups[key] = []
            groups[key].append(item)
        return groups
