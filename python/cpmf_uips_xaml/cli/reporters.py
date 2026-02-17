"""Progress reporter implementations for CLI.

Provides multiple reporter types: Rich (animated), tqdm, JSON (machine-readable), Simple (text).
Each implements the ProgressReporter protocol from shared.progress.
"""

import sys
from typing import TextIO

from ..shared.progress import ProgressEvent, ProgressReporter


class RichReporter(ProgressReporter):
    """Rich-based animated progress reporter.

    Uses Rich library for terminal progress bars with color and animation.
    Gracefully degrades if Rich is not installed.
    """

    def __init__(self, file: TextIO = sys.stderr) -> None:
        """Initialize Rich reporter.

        Args:
            file: Output stream (default: stderr)

        Raises:
            ImportError: If Rich library is not installed
        """
        try:
            from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

            self._progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=None,  # Use default console
            )
            self._tasks: dict[str, int] = {}  # stage -> task_id
            self._started = False
        except ImportError as e:
            raise ImportError("Rich library required for RichReporter. Install with: pip install rich") from e

    def report(self, event: ProgressEvent) -> None:
        """Report progress using Rich progress bars."""
        # Start progress context on first event
        if not self._started:
            self._progress.start()
            self._started = True

        # Get or create task for this stage
        task_id = self._tasks.get(event.stage)

        if task_id is None and event.total is not None:
            # Create new task with total
            task_id = self._progress.add_task(
                event.message or event.stage,
                total=event.total,
            )
            self._tasks[event.stage] = task_id
        elif task_id is not None:
            # Update existing task
            if event.advance > 0:
                self._progress.update(task_id, advance=event.advance)
            if event.message:
                self._progress.update(task_id, description=event.message)

    def __del__(self) -> None:
        """Clean up Rich progress display."""
        if hasattr(self, "_started") and self._started:
            self._progress.stop()


class TqdmReporter(ProgressReporter):
    """tqdm-based progress reporter.

    Uses tqdm library for terminal progress bars.
    Gracefully degrades if tqdm is not installed.
    """

    def __init__(self, file: TextIO = sys.stderr) -> None:
        """Initialize tqdm reporter.

        Args:
            file: Output stream (default: stderr)

        Raises:
            ImportError: If tqdm library is not installed
        """
        try:
            import tqdm

            self._tqdm = tqdm
            self._bars: dict[str, tqdm.tqdm] = {}  # stage -> tqdm instance
            self._file = file
        except ImportError as e:
            raise ImportError("tqdm library required for TqdmReporter. Install with: pip install tqdm") from e

    def report(self, event: ProgressEvent) -> None:
        """Report progress using tqdm progress bars."""
        bar = self._bars.get(event.stage)

        if bar is None and event.total is not None:
            # Create new progress bar
            bar = self._tqdm.tqdm(
                total=event.total,
                desc=event.message or event.stage,
                file=self._file,
            )
            self._bars[event.stage] = bar
        elif bar is not None:
            # Update existing bar
            if event.advance > 0:
                bar.update(event.advance)
            if event.message and hasattr(bar, "set_description"):
                bar.set_description(event.message)

    def __del__(self) -> None:
        """Clean up tqdm progress bars."""
        if hasattr(self, "_bars"):
            for bar in self._bars.values():
                bar.close()


class JsonReporter(ProgressReporter):
    """JSON-lines progress reporter.

    Emits progress events as JSON objects (one per line) for machine consumption.
    No external dependencies required.
    """

    def __init__(self, file: TextIO = sys.stderr) -> None:
        """Initialize JSON reporter.

        Args:
            file: Output stream (default: stderr)
        """
        import json

        self._json = json
        self._file = file

    def report(self, event: ProgressEvent) -> None:
        """Report progress as JSON-lines output."""
        event_dict = {
            "stage": event.stage,
            "message": event.message,
            "advance": event.advance,
            "total": event.total,
            "item": event.item,
        }
        # Filter out None values for cleaner JSON
        event_dict = {k: v for k, v in event_dict.items() if v is not None or k in ("advance",)}

        self._file.write(self._json.dumps(event_dict) + "\n")
        self._file.flush()


class SimpleReporter(ProgressReporter):
    """Simple text progress reporter.

    Emits plain text progress messages without colors or animation.
    No external dependencies required.
    """

    def __init__(self, file: TextIO = sys.stderr) -> None:
        """Initialize simple text reporter.

        Args:
            file: Output stream (default: stderr)
        """
        self._file = file
        self._stage_counts: dict[str, int] = {}  # stage -> count

    def report(self, event: ProgressEvent) -> None:
        """Report progress as simple text output."""
        if event.advance > 0:
            # Track progress count
            current = self._stage_counts.get(event.stage, 0) + event.advance
            self._stage_counts[event.stage] = current

            if event.total is not None:
                # Show count/total
                progress_msg = f"[{event.stage}] {current}/{event.total}"
            else:
                # Show count only
                progress_msg = f"[{event.stage}] {current}"

            if event.item:
                progress_msg += f" - {event.item}"

            self._file.write(progress_msg + "\n")
            self._file.flush()
        elif event.message:
            # Show message-only events
            self._file.write(f"[{event.stage}] {event.message}\n")
            self._file.flush()


__all__ = ["RichReporter", "TqdmReporter", "JsonReporter", "SimpleReporter"]
