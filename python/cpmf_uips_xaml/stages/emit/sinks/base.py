"""Base protocol for output sinks (I/O layer).

Sinks handle writing rendered content to destinations (filesystem, stdout, network).
They are responsible for ALL I/O operations.

Key principles:
- Handle ALL I/O operations
- No data transformation (that's Renderer/Filter's job)
- Support both single-file and multi-file output
- Return SinkResult with locations written
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


@dataclass
class SinkResult:
    """Result of a sink operation (I/O).

    Attributes:
        success: Whether I/O succeeded
        locations: Where data was written (file paths, URLs, "stdout", etc.)
        bytes_written: Total bytes written
        errors: List of error messages
        warnings: List of warning messages
    """

    success: bool
    locations: list[str | Path] = field(default_factory=list)
    bytes_written: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class Sink(Protocol):
    """Protocol for output sinks (I/O layer).

    Sinks handle writing rendered content to destinations
    (filesystem, stdout, network, etc.).

    All sinks must implement:
    - name: unique identifier
    - write_one(): write single content item
    - write_many(): write multiple content items
    """

    @property
    def name(self) -> str:
        """Unique sink identifier (e.g., 'file', 'stdout', 'stream').

        Returns:
            Sink name
        """
        ...

    def write_one(
        self, content: str | bytes, destination: Path | str, overwrite: bool = False
    ) -> SinkResult:
        """Write single content item to destination.

        Args:
            content: Rendered content to write
            destination: Target location (file path, stream name, etc.)
            overwrite: Whether to overwrite existing content

        Returns:
            SinkResult with write status and location
        """
        ...

    def write_many(
        self,
        content_map: dict[str, str | bytes],
        base_destination: Path | str,
        overwrite: bool = False,
    ) -> SinkResult:
        """Write multiple content items.

        Args:
            content_map: Map of filename → content
            base_destination: Base directory or stream
            overwrite: Whether to overwrite existing content

        Returns:
            SinkResult with write status and all locations
        """
        ...


__all__ = ["Sink", "SinkResult"]
