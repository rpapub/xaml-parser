"""Composite filter for chaining multiple filters.

Allows composing filters in sequence to create complex transformation pipelines.
"""

from typing import Any

from .base import Filter, FilterResult


class CompositeFilter(Filter):
    """Chain multiple filters together.

    Applies filters in sequence: data → Filter1 → Filter2 → Filter3 → output

    Each filter's output becomes the input to the next filter.
    Only applies filters that can handle the current data type.
    """

    def __init__(self, filters: list[Filter]):
        """Initialize composite filter.

        Args:
            filters: List of filters to apply in order

        Example:
            composite = CompositeFilter([
                FieldFilter("minimal"),
                NoneFilter(),
            ])
            # Applies minimal profile, then removes None values
        """
        self.filters = filters

    @property
    def name(self) -> str:
        """Composite filter name.

        Returns:
            Composite name with all filter names joined
        """
        return "composite_" + "_".join(f.name for f in self.filters)

    def apply(
        self, data: Any, config: dict[str, Any] | None = None
    ) -> FilterResult:
        """Apply all filters in sequence.

        Args:
            data: Data to filter
            config: Optional configuration (passed to each filter)

        Returns:
            FilterResult with data after all filters applied

        Example:
            composite = CompositeFilter([FieldFilter("minimal"), NoneFilter()])
            result = composite.apply(workflow_dict)
            # result.metadata contains info from both filters
        """
        current_data = data
        all_metadata = {}
        total_modified = False

        for filter_obj in self.filters:
            # Only apply filter if it can handle current data
            if not filter_obj.can_handle(current_data):
                continue

            # Apply filter
            result = filter_obj.apply(current_data, config)
            current_data = result.data
            total_modified = total_modified or result.modified

            # Collect metadata from each filter
            all_metadata[filter_obj.name] = result.metadata

        return FilterResult(
            data=current_data,
            modified=total_modified,
            metadata={"filters_applied": all_metadata},
        )

    def can_handle(self, data: Any) -> bool:
        """Check if at least one filter can handle this data.

        Args:
            data: Data to check

        Returns:
            True if any filter can handle this data
        """
        return any(f.can_handle(data) for f in self.filters)


__all__ = ["CompositeFilter"]
