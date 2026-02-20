"""Base protocol for data filters.

Filters transform data structures (dict/list) WITHOUT rendering to output format.
They operate after DTO → dict conversion but before rendering.

Key principles:
- Pure functions (no side effects)
- Composable (can chain multiple filters)
- Operate on dict/list, not DTOs
- Return FilterResult with metadata
"""

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class FilterResult:
    """Result of a filter operation.

    Attributes:
        data: Filtered data
        modified: Whether data was changed
        metadata: Filter metadata (e.g., fields_removed, size_reduction)
    """

    data: Any  # Filtered data
    modified: bool  # Whether data changed
    metadata: dict[str, Any] = field(default_factory=dict)


class Filter(Protocol):
    """Protocol for data filters.

    Filters transform data structures WITHOUT rendering to output format.
    They operate on dict/list structures (after dataclasses.asdict()).

    All filters must implement:
    - name: unique identifier
    - apply(): apply filter to data
    - can_handle(): check if filter can process data type
    """

    @property
    def name(self) -> str:
        """Unique filter identifier.

        Returns:
            Filter name
        """
        ...

    def apply(
        self, data: Any, config: dict[str, Any] | None = None
    ) -> FilterResult:
        """Apply filter to data structure.

        Args:
            data: Data to filter (dict, list, or primitive)
            config: Optional filter-specific configuration

        Returns:
            FilterResult with filtered data and metadata
        """
        ...

    def can_handle(self, data: Any) -> bool:
        """Check if filter can handle this data type.

        Args:
            data: Data to check

        Returns:
            True if filter can process this data
        """
        ...


__all__ = ["Filter", "FilterResult"]
