"""Event-based progress reporting system.

Provides structured progress events and reporter protocol for UI-agnostic progress tracking.
Library code emits events; CLI implements reporters (Rich/tqdm/JSON/simple).
"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ProgressEvent:
    """Immutable progress event.

    Attributes:
        stage: Event stage (e.g., "discover", "parse", "normalize")
        message: Optional human-readable description
        advance: Number of items progressed (default: 0)
        total: Total items (None = indeterminate progress)
        item: Current item identifier (e.g., file path)
    """

    stage: str
    message: str | None = None
    advance: int = 0
    total: int | None = None
    item: str | None = None


class ProgressReporter(Protocol):
    """Protocol for progress reporters.

    Implementations should handle progress events and render them
    appropriately (Rich progress bars, tqdm, JSON logs, etc.).
    """

    def report(self, event: ProgressEvent) -> None:
        """Report a progress event.

        Args:
            event: Progress event to report
        """
        ...


class NullReporter:
    """No-op reporter with zero overhead.

    Use as default when progress reporting is disabled.
    """

    def report(self, event: ProgressEvent) -> None:
        """No-op implementation."""
        pass


# Global singleton for default no-progress case
NULL_REPORTER = NullReporter()


__all__ = ["ProgressEvent", "ProgressReporter", "NullReporter", "NULL_REPORTER"]
