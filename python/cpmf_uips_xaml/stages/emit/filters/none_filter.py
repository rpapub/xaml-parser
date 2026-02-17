"""None value filter for removing null fields.

Extracts _exclude_none logic from JsonEmitter to make it reusable
across all renderers.
"""

from typing import Any

from .base import Filter, FilterResult


class NoneFilter(Filter):
    """Remove None values from nested data structures.

    Recursively traverses dicts and lists, removing any None values.
    Useful for reducing output size and avoiding null fields in JSON.
    """

    @property
    def name(self) -> str:
        """Filter name.

        Returns:
            'none_filter'
        """
        return "none_filter"

    def apply(
        self, data: Any, config: dict[str, Any] | None = None
    ) -> FilterResult:
        """Recursively remove None values.

        Args:
            data: Data to filter (any type)
            config: Optional configuration (unused)

        Returns:
            FilterResult with None values removed

        Example:
            filter = NoneFilter()
            result = filter.apply({"a": 1, "b": None, "c": {"d": None}})
            # result.data == {"a": 1, "c": {}}
        """
        filtered = self._exclude_none(data)

        # Check if data was modified
        modified = filtered != data

        return FilterResult(
            data=filtered,
            modified=modified,
            metadata={"none_values_removed": modified},
        )

    def _exclude_none(self, data: Any) -> Any:
        """Recursively exclude None values.

        Same logic as JsonEmitter._exclude_none().

        Args:
            data: Data to process

        Returns:
            Data with None values removed
        """
        if isinstance(data, dict):
            return {
                k: self._exclude_none(v) for k, v in data.items() if v is not None
            }
        elif isinstance(data, list):
            return [self._exclude_none(item) for item in data]
        else:
            return data

    def can_handle(self, data: Any) -> bool:
        """Check if filter can handle this data type.

        Args:
            data: Data to check

        Returns:
            True (can handle any data type)
        """
        return True  # Can handle any data type


__all__ = ["NoneFilter"]
