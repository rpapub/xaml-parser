"""Progress tracking and colorized output for CLI (v0.2.12).

This module provides progress bars, spinners, and colorized output
using the Rich library for enhanced user experience.
"""

from collections.abc import Callable, Generator
from contextlib import contextmanager

try:
    from rich.console import Console
    from rich.progress import (
        BarColumn,
        Progress,
        SpinnerColumn,
        TaskProgressColumn,
        TextColumn,
        TimeElapsedColumn,
    )

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


class ProgressTracker:
    """Progress tracking with Rich library.

    Provides progress bars and spinners for multi-file operations
    with graceful degradation if Rich is not available.

    Usage:
        tracker = ProgressTracker(total_files=100, show_progress=True)

        with tracker.track_parse("Parsing workflows") as update:
            for file in files:
                result = parser.parse_file(file)
                update()  # Advance progress bar
    """

    def __init__(self, total_files: int, show_progress: bool = True) -> None:
        """Initialize progress tracker.

        Args:
            total_files: Total number of files to process
            show_progress: Whether to show progress bars (default: True)
        """
        self.total_files = total_files
        self.show_progress = show_progress and RICH_AVAILABLE
        self.console = Console() if RICH_AVAILABLE else None

    @contextmanager
    def track_parse(
        self, description: str = "Processing"
    ) -> Generator[Callable[[], None], None, None]:
        """Track parsing progress with a progress bar.

        Args:
            description: Description text for the progress bar

        Yields:
            Callable that advances the progress bar by 1

        Example:
            with tracker.track_parse("Parsing workflows") as update:
                for file in files:
                    parse_file(file)
                    update()
        """
        if not self.show_progress:
            # No-op when progress disabled
            yield lambda: None
            return

        # Show progress bar with Rich
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=self.console,
        ) as progress:
            task = progress.add_task(description, total=self.total_files)

            def update() -> None:
                progress.update(task, advance=1)

            yield update


class ColorizedFormatter:
    """ASCII-based colorized output with Rich.

    Provides colorization for status messages, activity trees,
    and other CLI output with graceful degradation.
    """

    def __init__(self, use_colors: bool = True) -> None:
        """Initialize formatter.

        Args:
            use_colors: Whether to use colors (default: True if Rich available)
        """
        self.use_colors = use_colors and RICH_AVAILABLE
        self.console = Console() if RICH_AVAILABLE else None

    def format_status(self, status: str) -> str:
        """Colorize status indicators.

        Args:
            status: Status string (OK, FAIL, WARN, INFO, ERROR)

        Returns:
            Colorized status string

        Examples:
            [OK]   -> green
            [FAIL] -> red
            [WARN] -> yellow
            [INFO] -> blue
        """
        if not self.use_colors:
            return status

        color_map = {
            "OK": "green",
            "FAIL": "red",
            "WARN": "yellow",
            "INFO": "blue",
            "ERROR": "red",
        }

        for key, color in color_map.items():
            if key in status:
                return f"[{color}]{status}[/{color}]"

        return status

    def print_status(self, message: str, status: str = "INFO") -> None:
        """Print a status message with colorization.

        Args:
            message: Message text
            status: Status level (OK, FAIL, WARN, INFO, ERROR)
        """
        if not self.use_colors or not self.console:
            print(f"[{status}] {message}")
            return

        color_map = {
            "OK": "green",
            "FAIL": "red",
            "WARN": "yellow",
            "INFO": "blue",
            "ERROR": "red",
        }

        color = color_map.get(status, "white")
        self.console.print(f"[{color}][{status}][/{color}] {message}")

    def format_section_header(self, title: str) -> str:
        """Format a section header with emphasis.

        Args:
            title: Section title

        Returns:
            Formatted header string
        """
        if not self.use_colors:
            return f"\n{title}\n{'=' * len(title)}"

        return f"\n[bold cyan]{title}[/bold cyan]\n{'=' * len(title)}"


def print_with_color(
    message: str, color: str = "white", bold: bool = False, console: Console | None = None
) -> None:
    """Print a message with color using Rich.

    Args:
        message: Message to print
        color: Color name (green, red, yellow, blue, cyan, etc.)
        bold: Whether to make text bold
        console: Optional Console instance (creates new if None)

    Example:
        print_with_color("Success!", "green", bold=True)
    """
    if not RICH_AVAILABLE:
        print(message)
        return

    if console is None:
        console = Console()

    style = f"bold {color}" if bold else color
    console.print(f"[{style}]{message}[/{style}]")


def create_progress_bar(total: int, description: str = "Processing") -> tuple[Progress, int] | None:
    """Create a Rich progress bar.

    Args:
        total: Total number of items to process
        description: Description text

    Returns:
        Tuple of (Progress, task_id) or None if Rich not available

    Example:
        progress, task_id = create_progress_bar(100, "Parsing files")
        if progress:
            with progress:
                for i in range(100):
                    # Do work
                    progress.update(task_id, advance=1)
    """
    if not RICH_AVAILABLE:
        return None

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
    )

    task_id = progress.add_task(description, total=total)
    return progress, task_id


# Export Rich availability for conditional features
__all__ = [
    "ProgressTracker",
    "ColorizedFormatter",
    "print_with_color",
    "create_progress_bar",
    "RICH_AVAILABLE",
]
