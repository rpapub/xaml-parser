"""Performance profiling for XAML parser (v0.2.11).

This module provides low-overhead profiling capabilities for measuring
parse performance and identifying bottlenecks.

Key features:
- Context manager-based timing with < 1% overhead when disabled
- Memory tracking via tracemalloc and psutil
- Detailed timing breakdowns for all parse phases
- Summary reporting for optimization insights
"""

import tracemalloc
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field


@dataclass
class ProfileData:
    """Storage for profiling data collected during parse."""

    # Timing data: operation name -> list of durations in milliseconds
    timings: dict[str, list[float]] = field(default_factory=dict)

    # Memory tracking (bytes)
    memory_start: int = 0
    memory_peak: int = 0
    memory_end: int = 0

    # psutil memory (process RSS including C extensions)
    psutil_start: int = 0
    psutil_peak: int = 0
    psutil_end: int = 0

    # Whether psutil is available
    has_psutil: bool = False

    def add_timing(self, operation: str, duration_ms: float) -> None:
        """Add a timing measurement for an operation.

        Args:
            operation: Operation name (e.g., 'xml_parse', 'activities_extract')
            duration_ms: Duration in milliseconds
        """
        if operation not in self.timings:
            self.timings[operation] = []
        self.timings[operation].append(duration_ms)

    def get_total_time(self) -> float:
        """Get total time across all operations in milliseconds."""
        total = 0.0
        for durations in self.timings.values():
            total += sum(durations)
        return total

    def get_operation_total(self, operation: str) -> float:
        """Get total time for a specific operation in milliseconds."""
        return sum(self.timings.get(operation, []))

    def get_operation_count(self, operation: str) -> int:
        """Get number of times an operation was called."""
        return len(self.timings.get(operation, []))

    def get_operation_average(self, operation: str) -> float:
        """Get average time for an operation in milliseconds."""
        durations = self.timings.get(operation, [])
        if not durations:
            return 0.0
        return sum(durations) / len(durations)

    def get_operation_percentage(self, operation: str) -> float:
        """Get percentage of total time spent on operation."""
        total = self.get_total_time()
        if total == 0:
            return 0.0
        operation_total = self.get_operation_total(operation)
        return (operation_total / total) * 100.0

    def get_memory_delta_bytes(self) -> int:
        """Get memory change during profiling (bytes)."""
        return self.memory_end - self.memory_start

    def get_memory_delta_mb(self) -> float:
        """Get memory change during profiling (MB)."""
        return self.get_memory_delta_bytes() / (1024 * 1024)

    def get_memory_peak_mb(self) -> float:
        """Get peak memory usage (MB)."""
        return self.memory_peak / (1024 * 1024)

    def get_psutil_delta_mb(self) -> float:
        """Get psutil memory change (MB)."""
        if not self.has_psutil:
            return 0.0
        return (self.psutil_end - self.psutil_start) / (1024 * 1024)

    def get_psutil_peak_mb(self) -> float:
        """Get psutil peak memory (MB)."""
        if not self.has_psutil:
            return 0.0
        return self.psutil_peak / (1024 * 1024)


class Profiler:
    """Performance profiler with context manager interface.

    Provides low-overhead timing and memory profiling for parse operations.
    When disabled, has zero overhead (immediate yield in context manager).

    Usage:
        profiler = Profiler(enabled=True)

        profiler.start_memory_tracking()
        try:
            with profiler.profile("xml_parse"):
                root = parse_xml(content)

            with profiler.profile("activities_extract"):
                activities = extract_activities(root)
        finally:
            profiler.stop_memory_tracking()

        # Get summary
        summary = profiler.get_summary()
    """

    def __init__(self, enabled: bool = False) -> None:
        """Initialize profiler.

        Args:
            enabled: Whether profiling is enabled (default: False for zero overhead)
        """
        self.enabled = enabled
        self.data = ProfileData()

        # Check psutil availability
        try:
            import psutil  # noqa: F401

            self.data.has_psutil = True
        except ImportError:
            self.data.has_psutil = False

    @contextmanager
    def profile(self, operation: str) -> Generator[None, None, None]:
        """Time an operation with zero overhead when disabled.

        Args:
            operation: Operation name for timing tracking

        Yields:
            None (context manager)

        Example:
            with profiler.profile("xml_parse"):
                root = parse_xml(content)
        """
        if not self.enabled:
            yield  # Zero overhead - immediate return
            return

        import time

        start = time.perf_counter()
        try:
            yield
        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            self.data.add_timing(operation, duration_ms)

    def start_memory_tracking(self) -> None:
        """Start tracking memory usage.

        Starts tracemalloc for Python object tracking and
        records psutil process RSS if available.
        """
        if not self.enabled:
            return

        # Start tracemalloc for Python objects
        tracemalloc.start()
        self.data.memory_start = tracemalloc.get_traced_memory()[0]

        # Record psutil memory if available
        if self.data.has_psutil:
            self.data.psutil_start = self._get_psutil_memory()
            self.data.psutil_peak = self.data.psutil_start

    def stop_memory_tracking(self) -> None:
        """Stop tracking memory and record peak usage.

        Records peak memory from tracemalloc and final psutil RSS.
        """
        if not self.enabled:
            return

        # Get tracemalloc peak and current
        current, peak = tracemalloc.get_traced_memory()
        self.data.memory_peak = peak
        self.data.memory_end = current
        tracemalloc.stop()

        # Get final psutil memory
        if self.data.has_psutil:
            self.data.psutil_end = self._get_psutil_memory()
            # Update peak if current is higher
            if self.data.psutil_end > self.data.psutil_peak:
                self.data.psutil_peak = self.data.psutil_end

    def _get_psutil_memory(self) -> int:
        """Get current process memory from psutil (bytes).

        Returns:
            Process RSS in bytes, or 0 if psutil unavailable
        """
        if not self.data.has_psutil:
            return 0

        try:
            import psutil

            process = psutil.Process()
            return process.memory_info().rss
        except Exception:
            # Graceful degradation if psutil fails
            return 0

    def get_summary(self) -> dict[str, float]:
        """Get summary of profiling data for ParseDiagnostics.

        Returns:
            Dictionary of performance metrics suitable for ParseDiagnostics.performance_metrics

        Example output:
            {
                "file_read_total_ms": 12.5,
                "file_read_count": 1,
                "file_read_avg_ms": 12.5,
                "xml_parse_total_ms": 45.2,
                "xml_parse_count": 1,
                "xml_parse_avg_ms": 45.2,
                ...
                "total_parse_ms": 234.8,
                "memory_peak_mb": 12.5,
                "memory_delta_mb": 8.2,
                "psutil_peak_mb": 15.3,
                "psutil_delta_mb": 10.1,
            }
        """
        summary = {}

        # Add timing metrics for each operation
        for operation in sorted(self.data.timings.keys()):
            total = self.data.get_operation_total(operation)
            count = self.data.get_operation_count(operation)
            avg = self.data.get_operation_average(operation)

            summary[f"{operation}_total_ms"] = round(total, 2)
            summary[f"{operation}_count"] = count
            summary[f"{operation}_avg_ms"] = round(avg, 2)

        # Add overall timing
        summary["total_profiled_ms"] = round(self.data.get_total_time(), 2)

        # Add memory metrics
        summary["memory_peak_mb"] = round(self.data.get_memory_peak_mb(), 2)
        summary["memory_delta_mb"] = round(self.data.get_memory_delta_mb(), 2)

        if self.data.has_psutil:
            summary["psutil_peak_mb"] = round(self.data.get_psutil_peak_mb(), 2)
            summary["psutil_delta_mb"] = round(self.data.get_psutil_delta_mb(), 2)

        return summary

    def get_bottlenecks(self, threshold_percent: float = 10.0) -> list[tuple[str, float]]:
        """Identify operations consuming > threshold% of total time.

        Args:
            threshold_percent: Percentage threshold (default: 10.0%)

        Returns:
            List of (operation, percentage) tuples sorted by percentage descending

        Example:
            [('activities_extract', 58.2), ('xml_parse', 21.0)]
        """
        bottlenecks = []

        for operation in self.data.timings.keys():
            pct = self.data.get_operation_percentage(operation)
            if pct >= threshold_percent:
                bottlenecks.append((operation, pct))

        # Sort by percentage descending
        bottlenecks.sort(key=lambda x: x[1], reverse=True)
        return bottlenecks

    def reset(self) -> None:
        """Reset profiling data.

        Useful for re-using the same profiler for multiple parses.
        """
        self.data = ProfileData()
        # Preserve psutil availability
        try:
            import psutil  # noqa: F401

            self.data.has_psutil = True
        except ImportError:
            self.data.has_psutil = False
