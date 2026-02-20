"""Tests for emitter system.

Tests:
- Emitter base class interface
- EmitterRegistry registration and discovery
- JsonEmitter combined mode
- JsonEmitter per-workflow mode
- Field profile application in emitters
- None value exclusion
- Pretty printing
- Filename sanitization
- Error handling
"""

import json
from pathlib import Path

import pytest

from cpmf_uips_xaml.shared.model.dto import ActivityDto, WorkflowDto, WorkflowMetadata
from cpmf_uips_xaml.stages.emit.emitters import EmitResult, Emitter, EmitterConfig
from cpmf_uips_xaml.stages.emit.emitters.json_emitter import JsonEmitter
from cpmf_uips_xaml.stages.emit.registry import EmitterRegistry


class TestEmitterInterface:
    """Test Emitter base class interface."""

    def test_emitter_is_abstract(self):
        """Test that Emitter cannot be instantiated directly."""
        with pytest.raises(TypeError):
            Emitter()  # type: ignore

    def test_custom_emitter_implementation(self):
        """Test implementing a custom emitter."""

        class TestEmitter(Emitter):
            @property
            def name(self) -> str:
                return "test"

            @property
            def output_extension(self) -> str:
                return ".txt"

            def emit(self, workflows, output_path, config) -> EmitResult:
                return EmitResult(success=True, files_written=[])

        emitter = TestEmitter()
        assert emitter.name == "test"
        assert emitter.output_extension == ".txt"

        result = emitter.emit(
            [],
            Path("output.txt"),
            EmitterConfig(
                format="json",
                combine=False,
                pretty=True,
                exclude_none=False,
                field_profile="full",
                indent=2,
                encoding="utf-8",
                overwrite=True,
            ),
        )
        assert result.success


class TestEmitterRegistry:
    """Test EmitterRegistry."""

    def setup_method(self):
        """Clear registry before each test."""
        EmitterRegistry.clear()

    def teardown_method(self):
        """Clear registry after each test."""
        EmitterRegistry.clear()

    def test_register_emitter(self):
        """Test registering an emitter."""
        EmitterRegistry.register(JsonEmitter)

        assert "json" in EmitterRegistry.list_emitters()

    def test_get_emitter(self):
        """Test getting registered emitter."""
        EmitterRegistry.register(JsonEmitter)

        emitter = EmitterRegistry.get_emitter("json")
        assert isinstance(emitter, JsonEmitter)
        assert emitter.name == "json"

    def test_get_unknown_emitter_raises_error(self):
        """Test that getting unknown emitter raises error."""
        with pytest.raises(ValueError, match="Unknown emitter"):
            EmitterRegistry.get_emitter("unknown")

    def test_register_duplicate_raises_error(self):
        """Test that registering duplicate name raises error."""
        EmitterRegistry.register(JsonEmitter)

        with pytest.raises(ValueError, match="already registered"):
            EmitterRegistry.register(JsonEmitter)

    def test_list_emitters(self):
        """Test listing all registered emitters."""
        EmitterRegistry.register(JsonEmitter)

        emitters = EmitterRegistry.list_emitters()
        assert emitters == ["json"]


class TestJsonEmitter:
    """Test JsonEmitter."""

    def test_emitter_properties(self):
        """Test JsonEmitter properties."""
        emitter = JsonEmitter()

        assert emitter.name == "json"
        assert emitter.output_extension == ".json"

    def test_emit_combined_mode(self, tmp_path):
        """Test emitting single combined JSON file."""
        # Create test workflow
        workflow = WorkflowDto(
            id="wf:sha256:test123",
            name="TestWorkflow",
            collected_at="2025-10-11T12:00:00Z",
            metadata=WorkflowMetadata(),
            activities=[
                ActivityDto(
                    id="act:sha256:abc",
                    type="System.Activities.Statements.Sequence",
                    type_short="Sequence",
                )
            ],
        )

        # Emit combined
        emitter = JsonEmitter()
        config = EmitterConfig(
            format="json",
            combine=True,
            pretty=True,
            exclude_none=False,
            field_profile="full",
            indent=2,
            encoding="utf-8",
            overwrite=True,
        )
        output_file = tmp_path / "workflows.json"

        result = emitter.emit([workflow], output_file, config)

        # Verify result
        assert result.success
        assert len(result.files_written) == 1
        assert result.files_written[0] == output_file
        assert len(result.errors) == 0

        # Verify file contents
        assert output_file.exists()
        with open(output_file, encoding="utf-8") as f:
            data = json.load(f)

        assert data["schema_id"] == "https://rpax.io/schemas/xaml-workflow-collection.json"
        assert len(data["workflows"]) == 1
        assert data["workflows"][0]["name"] == "TestWorkflow"

    def test_emit_per_workflow_mode(self, tmp_path):
        """Test emitting one file per workflow."""
        # Create test workflows
        workflow1 = WorkflowDto(
            id="wf:sha256:test1",
            name="Workflow1",
            collected_at="2025-10-11T12:00:00Z",
        )
        workflow2 = WorkflowDto(
            id="wf:sha256:test2",
            name="Workflow2",
            collected_at="2025-10-11T12:00:00Z",
        )

        # Emit per-workflow
        emitter = JsonEmitter()
        config = EmitterConfig(
            format="json",
            combine=False,
            pretty=True,
            exclude_none=False,
            field_profile="full",
            indent=2,
            encoding="utf-8",
            overwrite=True,
        )
        output_dir = tmp_path / "workflows"

        result = emitter.emit([workflow1, workflow2], output_dir, config)

        # Verify result
        assert result.success
        assert len(result.files_written) == 2
        assert len(result.errors) == 0

        # Verify files created
        file1 = output_dir / "Workflow1.json"
        file2 = output_dir / "Workflow2.json"
        assert file1.exists()
        assert file2.exists()

        # Verify file contents
        with open(file1, encoding="utf-8") as f:
            data1 = json.load(f)
        assert data1["name"] == "Workflow1"

        with open(file2, encoding="utf-8") as f:
            data2 = json.load(f)
        assert data2["name"] == "Workflow2"

    def test_field_profile_minimal(self, tmp_path):
        """Test field profile filtering."""
        # Create workflow with many fields
        workflow = WorkflowDto(
            id="wf:sha256:test",
            name="TestWorkflow",
            collected_at="2025-10-11T12:00:00Z",
            metadata=WorkflowMetadata(
                annotation="Test annotation",
            ),
            activities=[
                ActivityDto(
                    id="act:sha256:abc",
                    type="System.Activities.Statements.Sequence",
                    type_short="Sequence",
                    display_name="Main",
                )
            ],
        )

        # Emit with minimal profile
        emitter = JsonEmitter()
        config = EmitterConfig(
            format="json",
            combine=False,
            field_profile="minimal",
            pretty=True,
            exclude_none=False,
            indent=2,
            encoding="utf-8",
            overwrite=True,
        )
        output_dir = tmp_path / "workflows"

        result = emitter.emit([workflow], output_dir, config)
        assert result.success

        # Verify minimal fields only
        output_file = output_dir / "TestWorkflow.json"
        with open(output_file, encoding="utf-8") as f:
            data = json.load(f)

        # Should have minimal fields per profile definition
        assert "schema_id" in data
        assert "name" in data
        assert "activities" in data

        # Should NOT have metadata (not in minimal profile)
        assert "metadata" not in data

    def test_exclude_none_values(self, tmp_path):
        """Test None value exclusion."""
        # Create workflow with None values
        workflow = WorkflowDto(
            id="wf:sha256:test",
            name="TestWorkflow",
            collected_at="2025-10-11T12:00:00Z",
            activities=[
                ActivityDto(
                    id="act:sha256:abc",
                    type="System.Activities.Statements.Sequence",
                    type_short="Sequence",
                    display_name=None,  # None value
                    annotation=None,  # None value
                )
            ],
        )

        # Emit with exclude_none=True
        emitter = JsonEmitter()
        config = EmitterConfig(
            format="json",
            combine=False,
            exclude_none=True,
            pretty=True,
            field_profile="full",
            indent=2,
            encoding="utf-8",
            overwrite=True,
        )
        output_dir = tmp_path / "workflows"

        result = emitter.emit([workflow], output_dir, config)
        assert result.success

        # Verify None values excluded
        output_file = output_dir / "TestWorkflow.json"
        with open(output_file, encoding="utf-8") as f:
            content = f.read()

        # None fields should not appear in JSON
        assert "display_name" not in content
        assert "annotation" not in content

    def test_pretty_printing(self, tmp_path):
        """Test pretty printing option."""
        workflow = WorkflowDto(
            id="wf:sha256:test",
            name="TestWorkflow",
            collected_at="2025-10-11T12:00:00Z",
        )

        emitter = JsonEmitter()
        output_dir = tmp_path / "workflows"

        # Emit with pretty=True
        config_pretty = EmitterConfig(
            format="json",
            combine=False,
            pretty=True,
            exclude_none=False,
            field_profile="full",
            indent=2,
            encoding="utf-8",
            overwrite=True,
        )
        emitter.emit([workflow], output_dir, config_pretty)

        file_pretty = output_dir / "TestWorkflow.json"
        with open(file_pretty, encoding="utf-8") as f:
            content_pretty = f.read()

        # Should have indentation
        assert "\n" in content_pretty
        assert "  " in content_pretty  # Indentation

        # Emit with pretty=False
        output_dir2 = tmp_path / "workflows2"
        config_compact = EmitterConfig(
            format="json",
            combine=False,
            pretty=False,
            exclude_none=False,
            field_profile="full",
            indent=2,
            encoding="utf-8",
            overwrite=True,
        )
        emitter.emit([workflow], output_dir2, config_compact)

        file_compact = output_dir2 / "TestWorkflow.json"
        with open(file_compact, encoding="utf-8") as f:
            content_compact = f.read()

        # Should be single line (no indentation)
        assert len(content_compact.split("\n")) == 1

    def test_filename_sanitization(self, tmp_path):
        """Test filename sanitization for invalid characters."""
        # Create workflows with problematic names
        workflows = [
            WorkflowDto(
                id="wf:sha256:test1",
                name='Workflow<>:"/\\|?*Name',  # Invalid chars
                collected_at="2025-10-11T12:00:00Z",
            ),
            WorkflowDto(
                id="wf:sha256:test2",
                name="  .Workflow.  ",  # Leading/trailing dots and spaces
                collected_at="2025-10-11T12:00:00Z",
            ),
        ]

        emitter = JsonEmitter()
        config = EmitterConfig(
            format="json",
            combine=False,
            pretty=True,
            exclude_none=False,
            field_profile="full",
            indent=2,
            encoding="utf-8",
            overwrite=True,
        )
        output_dir = tmp_path / "workflows"

        result = emitter.emit(workflows, output_dir, config)

        # Verify sanitization
        assert result.success
        assert len(result.files_written) == 2

        # Files should exist with sanitized names
        files = list(output_dir.glob("*.json"))
        assert len(files) == 2

        # Check that files have valid names
        for file in files:
            assert "<" not in file.name
            assert ">" not in file.name
            assert ":" not in file.name

    def test_error_handling(self, tmp_path):
        """Test error handling in emit."""
        workflow = WorkflowDto(
            id="wf:sha256:test",
            name="TestWorkflow",
            collected_at="2025-10-11T12:00:00Z",
        )

        emitter = JsonEmitter()
        config = EmitterConfig(
            format="json",
            combine=False,
            pretty=True,
            exclude_none=False,
            field_profile="full",
            indent=2,
            encoding="utf-8",
            overwrite=True,
        )

        # Try to emit to invalid path (e.g., file instead of directory)
        invalid_path = tmp_path / "file.txt"
        invalid_path.touch()

        # Emit should handle error gracefully
        result = emitter.emit([workflow], invalid_path, config)

        # Should report failure
        assert not result.success or len(result.errors) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
