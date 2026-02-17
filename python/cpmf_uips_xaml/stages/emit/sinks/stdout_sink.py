"""Standard output sink for piping content.

Handles writing content to stdout for CLI piping scenarios.
"""

import sys
from pathlib import Path

from .base import Sink, SinkResult


class StdoutSink(Sink):
    """Write content to stdout (for CLI piping).

    Useful for piping output to other commands:
    $ cpmf-uips-xaml emit --output - | jq .
    """

    @property
    def name(self) -> str:
        """Sink name.

        Returns:
            'stdout'
        """
        return "stdout"

    def write_one(
        self, content: str | bytes, destination: Path | str, overwrite: bool = False
    ) -> SinkResult:
        """Write content to stdout.

        Args:
            content: Content to write (string or bytes)
            destination: Ignored for stdout (can be "-" or anything)
            overwrite: Ignored for stdout

        Returns:
            SinkResult with "stdout" as location

        Example:
            sink = StdoutSink()
            result = sink.write_one('{"data": 1}', "-")
            # Content written to stdout
        """
        try:
            if isinstance(content, bytes):
                sys.stdout.buffer.write(content)
                bytes_written = len(content)
            else:
                print(content)
                bytes_written = len(content.encode("utf-8"))

            return SinkResult(
                success=True,
                locations=["stdout"],
                bytes_written=bytes_written,
                errors=[],
                warnings=[],
            )

        except Exception as e:
            return SinkResult(
                success=False,
                locations=[],
                bytes_written=0,
                errors=[f"Failed to write to stdout: {e}"],
                warnings=[],
            )

    def write_many(
        self,
        content_map: dict[str, str | bytes],
        base_destination: Path | str,
        overwrite: bool = False,
    ) -> SinkResult:
        """Write multiple items to stdout with separators.

        Args:
            content_map: Map of filename → content
            base_destination: Ignored for stdout
            overwrite: Ignored for stdout

        Returns:
            SinkResult with "stdout" as location

        Example:
            sink = StdoutSink()
            content_map = {
                "file1.json": '{"data": 1}',
                "file2.json": '{"data": 2}',
            }
            result = sink.write_many(content_map, "-")
            # Output:
            # --- file1.json ---
            # {"data": 1}
            # --- file2.json ---
            # {"data": 2}
        """
        try:
            total_bytes = 0

            for filename, content in content_map.items():
                # Add separator with filename
                separator = f"\n--- {filename} ---\n"
                print(separator, end="")

                if isinstance(content, bytes):
                    sys.stdout.buffer.write(content)
                    total_bytes += len(content)
                else:
                    print(content)
                    total_bytes += len(content.encode("utf-8"))

            return SinkResult(
                success=True,
                locations=["stdout"] * len(content_map),
                bytes_written=total_bytes,
                errors=[],
                warnings=[],
            )

        except Exception as e:
            return SinkResult(
                success=False,
                locations=[],
                bytes_written=0,
                errors=[f"Failed to write to stdout: {e}"],
                warnings=[],
            )


__all__ = ["StdoutSink"]
