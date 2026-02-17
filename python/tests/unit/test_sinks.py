"""Unit tests for emitter sinks (I/O operations)."""

import pytest
from pathlib import Path
from io import StringIO
import sys

from cpmf_uips_xaml.stages.emit.sinks.file_sink import FileSink
from cpmf_uips_xaml.stages.emit.sinks.stdout_sink import StdoutSink
from cpmf_uips_xaml.stages.emit.sinks.base import SinkResult


# ============================================================================
# FileSink Tests
# ============================================================================


class TestFileSink:
    """Test FileSink filesystem I/O operations."""

    def test_name_property(self):
        """Test sink name."""
        sink = FileSink()
        assert sink.name == "file"

    def test_write_one_creates_file(self, tmp_path):
        """Test writing single file creates the file."""
        sink = FileSink()
        content = "test content"
        destination = tmp_path / "test.txt"

        result = sink.write_one(content, destination, overwrite=True)

        assert isinstance(result, SinkResult)
        assert result.success is True
        assert destination.exists()
        assert destination.read_text() == content
        assert result.locations == [destination]
        assert result.bytes_written == len(content.encode("utf-8"))
        assert result.errors == []

    def test_write_one_creates_parent_directories(self, tmp_path):
        """Test writing file creates parent directories if needed."""
        sink = FileSink()
        content = "test"
        destination = tmp_path / "subdir" / "nested" / "file.txt"

        result = sink.write_one(content, destination, overwrite=True)

        assert result.success
        assert destination.exists()
        assert destination.parent.exists()

    def test_write_one_respects_overwrite_false(self, tmp_path):
        """Test overwrite=False prevents overwriting existing file."""
        sink = FileSink()
        destination = tmp_path / "existing.txt"
        destination.write_text("original content")

        result = sink.write_one("new content", destination, overwrite=False)

        assert result.success is False
        assert len(result.errors) > 0
        assert "exists" in result.errors[0].lower()
        assert "overwrite" in result.errors[0].lower()
        # Original content preserved
        assert destination.read_text() == "original content"

    def test_write_one_overwrites_when_allowed(self, tmp_path):
        """Test overwrite=True allows overwriting existing file."""
        sink = FileSink()
        destination = tmp_path / "existing.txt"
        destination.write_text("original content")

        result = sink.write_one("new content", destination, overwrite=True)

        assert result.success is True
        assert destination.read_text() == "new content"

    def test_write_one_with_bytes(self, tmp_path):
        """Test writing bytes content."""
        sink = FileSink()
        content = b"binary\x00content"
        destination = tmp_path / "binary.dat"

        result = sink.write_one(content, destination, overwrite=True)

        assert result.success
        assert destination.read_bytes() == content
        assert result.bytes_written == len(content)

    def test_write_one_with_unicode(self, tmp_path):
        """Test writing unicode content."""
        sink = FileSink()
        content = "Unicode: 中文 🎉"
        destination = tmp_path / "unicode.txt"

        result = sink.write_one(content, destination, overwrite=True)

        assert result.success
        assert destination.read_text(encoding="utf-8") == content

    def test_write_many_creates_multiple_files(self, tmp_path):
        """Test writing multiple files to directory."""
        sink = FileSink()
        content_map = {
            "file1.txt": "content 1",
            "file2.txt": "content 2",
            "file3.txt": "content 3",
        }

        result = sink.write_many(content_map, tmp_path, overwrite=True)

        assert result.success is True
        assert len(result.locations) == 3
        assert (tmp_path / "file1.txt").exists()
        assert (tmp_path / "file2.txt").exists()
        assert (tmp_path / "file3.txt").exists()
        assert (tmp_path / "file1.txt").read_text() == "content 1"
        assert result.errors == []

    def test_write_many_with_subdirectories(self, tmp_path):
        """Test write_many handles filenames with subdirectories."""
        sink = FileSink()
        content_map = {
            "workflows/Main.json": "{}",
            "workflows/Helper.json": "{}",
            "metadata.json": "{}",
        }

        result = sink.write_many(content_map, tmp_path, overwrite=True)

        assert result.success
        assert (tmp_path / "workflows" / "Main.json").exists()
        assert (tmp_path / "workflows" / "Helper.json").exists()
        assert (tmp_path / "metadata.json").exists()

    def test_write_many_creates_base_directory(self, tmp_path):
        """Test write_many creates base directory if needed."""
        sink = FileSink()
        base_dir = tmp_path / "output"
        content_map = {"file.txt": "content"}

        result = sink.write_many(content_map, base_dir, overwrite=True)

        assert result.success
        assert base_dir.exists()
        assert (base_dir / "file.txt").exists()

    def test_write_many_partial_failure(self, tmp_path):
        """Test write_many reports errors but continues."""
        sink = FileSink()

        # Create one file that exists
        existing_file = tmp_path / "existing.txt"
        existing_file.write_text("original")

        content_map = {
            "existing.txt": "new content",
            "new_file.txt": "content",
        }

        result = sink.write_many(content_map, tmp_path, overwrite=False)

        # Should fail overall due to existing file
        assert result.success is False
        assert len(result.errors) > 0

        # But new file should still be created
        assert (tmp_path / "new_file.txt").exists()

    def test_write_many_bytes_written_total(self, tmp_path):
        """Test write_many returns total bytes written."""
        sink = FileSink()
        content_map = {
            "file1.txt": "12345",  # 5 bytes
            "file2.txt": "67890",  # 5 bytes
        }

        result = sink.write_many(content_map, tmp_path, overwrite=True)

        assert result.success
        assert result.bytes_written == 10  # Total bytes

    def test_write_one_with_path_string(self, tmp_path):
        """Test write_one accepts string path."""
        sink = FileSink()
        destination = str(tmp_path / "test.txt")

        result = sink.write_one("content", destination, overwrite=True)

        assert result.success
        assert Path(destination).exists()

    def test_write_many_empty_content_map(self, tmp_path):
        """Test write_many with empty content map."""
        sink = FileSink()
        result = sink.write_many({}, tmp_path, overwrite=True)

        assert result.success
        assert len(result.locations) == 0
        assert result.bytes_written == 0


# ============================================================================
# StdoutSink Tests
# ============================================================================


class TestStdoutSink:
    """Test StdoutSink stdout output operations."""

    def test_name_property(self):
        """Test sink name."""
        sink = StdoutSink()
        assert sink.name == "stdout"

    def test_write_one_prints_to_stdout(self, capsys):
        """Test writing to stdout."""
        sink = StdoutSink()
        content = "test output"

        result = sink.write_one(content, "-", overwrite=False)

        captured = capsys.readouterr()
        assert result.success is True
        assert content in captured.out
        assert result.locations == ["stdout"]
        assert result.bytes_written == len(content.encode("utf-8"))

    def test_write_one_with_unicode(self, capsys):
        """Test stdout with unicode characters."""
        sink = StdoutSink()
        content = "Unicode: 中文 🎉"

        result = sink.write_one(content, "-", overwrite=False)

        captured = capsys.readouterr()
        assert result.success
        assert content in captured.out

    def test_write_one_with_bytes(self):
        """Test writing bytes to stdout (verified via success, not captured output)."""
        sink = StdoutSink()
        content = b"binary content"

        # Note: sys.stdout.buffer is readonly and cannot be redirected easily
        # We verify the operation succeeds rather than capturing output
        result = sink.write_one(content, "-", overwrite=False)

        assert result.success
        assert result.bytes_written == len(content)
        assert result.locations == ["stdout"]

    def test_write_many_with_separators(self, capsys):
        """Test write_many prints multiple items with separators."""
        sink = StdoutSink()
        content_map = {
            "file1.json": '{"id": 1}',
            "file2.json": '{"id": 2}',
        }

        result = sink.write_many(content_map, "-", overwrite=False)

        captured = capsys.readouterr()
        assert result.success is True
        assert "file1.json" in captured.out
        assert "file2.json" in captured.out
        assert '{"id": 1}' in captured.out
        assert '{"id": 2}' in captured.out
        # Check for separator
        assert "---" in captured.out

    def test_write_many_returns_correct_locations(self):
        """Test write_many returns stdout locations for all items."""
        sink = StdoutSink()
        content_map = {"f1": "c1", "f2": "c2", "f3": "c3"}

        result = sink.write_many(content_map, "-", overwrite=False)

        assert result.success
        assert result.locations == ["stdout", "stdout", "stdout"]
        assert len(result.locations) == 3

    def test_write_many_bytes_written_total(self, capsys):
        """Test write_many returns total bytes written."""
        sink = StdoutSink()
        content_map = {"f1": "12345", "f2": "67890"}

        result = sink.write_many(content_map, "-", overwrite=False)

        # Should count all bytes (at least the content bytes, possibly more with separators)
        assert result.bytes_written >= 10

    def test_write_one_ignores_destination(self, capsys):
        """Test stdout sink ignores destination parameter."""
        sink = StdoutSink()
        content = "output"

        # Destination is ignored (always stdout)
        result = sink.write_one(content, "/some/path", overwrite=False)

        captured = capsys.readouterr()
        assert result.success
        assert content in captured.out

    def test_write_one_ignores_overwrite(self, capsys):
        """Test stdout sink ignores overwrite parameter."""
        sink = StdoutSink()

        # Both calls should succeed (overwrite doesn't matter for stdout)
        result1 = sink.write_one("first", "-", overwrite=False)
        result2 = sink.write_one("second", "-", overwrite=True)

        assert result1.success
        assert result2.success

    def test_write_many_empty_content_map(self, capsys):
        """Test write_many with empty content map."""
        sink = StdoutSink()
        result = sink.write_many({}, "-", overwrite=False)

        assert result.success
        assert len(result.locations) == 0
        assert result.bytes_written == 0


# ============================================================================
# Sink Integration Tests
# ============================================================================


class TestSinkIntegration:
    """Test sinks in realistic scenarios."""

    def test_file_sink_json_workflow(self, tmp_path):
        """Test FileSink with JSON workflow output."""
        sink = FileSink()
        json_content = """{
  "id": "workflow_1",
  "name": "TestWorkflow",
  "activities": []
}"""
        destination = tmp_path / "workflow.json"

        result = sink.write_one(json_content, destination, overwrite=True)

        assert result.success
        # Verify valid JSON was written
        import json

        data = json.loads(destination.read_text())
        assert data["id"] == "workflow_1"

    def test_file_sink_mermaid_diagram(self, tmp_path):
        """Test FileSink with Mermaid diagram output."""
        sink = FileSink()
        mermaid_content = """flowchart TD
    %% Workflow: TestWorkflow

    a1["Start"]
    a2["End"]

    a1 --> a2
"""
        destination = tmp_path / "diagram.mmd"

        result = sink.write_one(mermaid_content, destination, overwrite=True)

        assert result.success
        content = destination.read_text()
        assert "flowchart TD" in content
        assert "TestWorkflow" in content

    def test_stdout_sink_json_pipeline(self, capsys):
        """Test StdoutSink with JSON for CLI piping."""
        sink = StdoutSink()
        json_content = '{"id": "wf1", "name": "Test"}'

        result = sink.write_one(json_content, "-", overwrite=False)

        captured = capsys.readouterr()
        assert result.success
        # Verify output can be parsed as JSON
        import json

        data = json.loads(captured.out.strip())
        assert data["id"] == "wf1"


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


class TestSinkEdgeCases:
    """Test edge cases and error handling."""

    def test_file_sink_write_to_readonly_directory(self, tmp_path):
        """Test FileSink handles permission errors."""
        sink = FileSink()
        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir()

        # Make directory read-only (Unix-like systems)
        import os

        try:
            os.chmod(readonly_dir, 0o444)
            destination = readonly_dir / "file.txt"

            result = sink.write_one("content", destination, overwrite=True)

            # Should fail due to permissions
            # (may succeed on Windows, skip assertion on Windows)
            if os.name != "nt":
                assert result.success is False or not destination.exists()
        finally:
            # Restore permissions for cleanup
            os.chmod(readonly_dir, 0o755)

    def test_file_sink_empty_content(self, tmp_path):
        """Test FileSink with empty content."""
        sink = FileSink()
        destination = tmp_path / "empty.txt"

        result = sink.write_one("", destination, overwrite=True)

        assert result.success
        assert destination.exists()
        assert destination.read_text() == ""
        assert result.bytes_written == 0

    def test_file_sink_very_long_path(self, tmp_path):
        """Test FileSink with very long file path."""
        sink = FileSink()
        # Create nested directory structure
        long_path = tmp_path
        for i in range(10):
            long_path = long_path / f"subdir_{i}"

        destination = long_path / "file.txt"

        result = sink.write_one("content", destination, overwrite=True)

        # Should succeed (path length limits are OS-dependent)
        if result.success:
            assert destination.exists()

    def test_stdout_sink_very_large_output(self, capsys):
        """Test StdoutSink with large content."""
        sink = StdoutSink()
        large_content = "x" * 100000  # 100KB

        result = sink.write_one(large_content, "-", overwrite=False)

        captured = capsys.readouterr()
        assert result.success
        assert len(captured.out) >= len(large_content)

    def test_file_sink_mixed_content_types_in_write_many(self, tmp_path):
        """Test write_many with mixed str and bytes content."""
        sink = FileSink()
        content_map = {
            "text.txt": "string content",
            "binary.dat": b"binary content",
        }

        result = sink.write_many(content_map, tmp_path, overwrite=True)

        assert result.success
        assert (tmp_path / "text.txt").read_text() == "string content"
        assert (tmp_path / "binary.dat").read_bytes() == b"binary content"
