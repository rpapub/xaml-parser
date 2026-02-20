"""File system sink for writing content to disk.

Handles all filesystem I/O operations for rendered content.
"""

from pathlib import Path

from ..utils import ensure_dir, write_text
from .base import Sink, SinkResult


class FileSink(Sink):
    """Write content to filesystem.

    Handles both single-file and multi-file output modes.
    Creates parent directories as needed.
    """

    @property
    def name(self) -> str:
        """Sink name.

        Returns:
            'file'
        """
        return "file"

    def write_one(
        self, content: str | bytes, destination: Path | str, overwrite: bool = False
    ) -> SinkResult:
        """Write single file to filesystem.

        Args:
            content: Content to write (string or bytes)
            destination: File path to write to
            overwrite: Whether to overwrite existing files

        Returns:
            SinkResult with success status and file path

        Example:
            sink = FileSink()
            result = sink.write_one("content", Path("output.txt"), overwrite=True)
            # result.locations == [Path("output.txt")]
        """
        try:
            file_path = Path(destination)

            # Check overwrite
            if file_path.exists() and not overwrite:
                return SinkResult(
                    success=False,
                    locations=[],
                    bytes_written=0,
                    errors=[f"File exists and overwrite=False: {file_path}"],
                    warnings=[],
                )

            # Ensure parent directory exists
            ensure_dir(file_path.parent)

            # Write file
            if isinstance(content, bytes):
                file_path.write_bytes(content)
                bytes_written = len(content)
            else:
                write_text(file_path, content)
                bytes_written = len(content.encode("utf-8"))

            return SinkResult(
                success=True,
                locations=[file_path],
                bytes_written=bytes_written,
                errors=[],
                warnings=[],
            )

        except Exception as e:
            return SinkResult(
                success=False,
                locations=[],
                bytes_written=0,
                errors=[f"Failed to write {destination}: {e}"],
                warnings=[],
            )

    def write_many(
        self,
        content_map: dict[str, str | bytes],
        base_destination: Path | str,
        overwrite: bool = False,
    ) -> SinkResult:
        """Write multiple files to directory.

        Args:
            content_map: Map of filename → content
            base_destination: Base directory for output files
            overwrite: Whether to overwrite existing files

        Returns:
            SinkResult with all file paths written

        Example:
            sink = FileSink()
            content_map = {
                "file1.json": '{"data": 1}',
                "file2.json": '{"data": 2}',
            }
            result = sink.write_many(content_map, Path("output/"), overwrite=True)
            # result.locations == [Path("output/file1.json"), Path("output/file2.json")]
        """
        base_path = Path(base_destination)
        ensure_dir(base_path)

        locations = []
        errors = []
        total_bytes = 0

        for filename, content in content_map.items():
            file_path = base_path / filename
            result = self.write_one(content, file_path, overwrite)

            if result.success:
                locations.extend(result.locations)
                total_bytes += result.bytes_written
            else:
                errors.extend(result.errors)

        return SinkResult(
            success=len(errors) == 0,
            locations=locations,
            bytes_written=total_bytes,
            errors=errors,
            warnings=[],
        )


__all__ = ["FileSink"]
