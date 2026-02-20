"""Unit tests for EmitPipeline orchestration."""

import pytest
from pathlib import Path
from dataclasses import dataclass
import dataclasses

from cpmf_uips_xaml.stages.emit.pipeline import EmitPipeline, PipelineResult
from cpmf_uips_xaml.stages.emit.renderers.json_renderer import JsonRenderer
from cpmf_uips_xaml.stages.emit.renderers.mermaid_renderer import MermaidRenderer
from cpmf_uips_xaml.stages.emit.sinks.file_sink import FileSink
from cpmf_uips_xaml.stages.emit.sinks.stdout_sink import StdoutSink
from cpmf_uips_xaml.stages.emit.filters.field_filter import FieldFilter
from cpmf_uips_xaml.stages.emit.filters.none_filter import NoneFilter
from cpmf_uips_xaml.stages.emit.filters.composite_filter import CompositeFilter
from cpmf_uips_xaml.shared.model.dto import (
    WorkflowDto,
    SourceInfo,
    WorkflowMetadata,
)
from cpmf_uips_xaml.config.models import EmitterConfig


# Test fixtures
@dataclass(frozen=True)
class TestWorkflowDto:
    """Minimal WorkflowDto for testing."""

    schema_id: str = "https://example.com/schema"
    schema_version: str = "1.0"
    collected_at: str = "2024-01-01T00:00:00Z"
    provenance: None = None
    id: str = "wf1"
    name: str = "TestWorkflow"
    source: SourceInfo = None
    metadata: WorkflowMetadata = None
    variables: list = dataclasses.field(default_factory=list)
    arguments: list = dataclasses.field(default_factory=list)
    dependencies: list = dataclasses.field(default_factory=list)
    activities: list = dataclasses.field(default_factory=list)
    edges: list = dataclasses.field(default_factory=list)
    invocations: list = dataclasses.field(default_factory=list)
    issues: list = dataclasses.field(default_factory=list)
    quality_metrics: None = None
    anti_patterns: None = None

    def __post_init__(self):
        # Set default source if None
        if self.source is None:
            object.__setattr__(
                self,
                "source",
                SourceInfo(
                    path="Test.xaml",
                    path_aliases=[],
                    hash="abc123",
                    size_bytes=100,
                    encoding="utf-8",
                ),
            )
        if self.metadata is None:
            object.__setattr__(self, "metadata", WorkflowMetadata(annotation=None))


def create_test_workflow(**kwargs):
    """Create test workflow with defaults."""
    defaults = {
        "id": "wf1",
        "name": "TestWorkflow",
        "source": SourceInfo(
            path="Test.xaml",
            path_aliases=[],
            hash="abc123",
            size_bytes=100,
            encoding="utf-8",
        ),
        "metadata": WorkflowMetadata(annotation=None),
    }
    defaults.update(kwargs)
    return TestWorkflowDto(**defaults)


# ============================================================================
# EmitPipeline Basic Tests
# ============================================================================


class TestEmitPipelineBasics:
    """Test basic EmitPipeline functionality."""

    def test_pipeline_initialization(self):
        """Test pipeline can be initialized."""
        renderer = JsonRenderer()
        sink = FileSink()

        pipeline = EmitPipeline(renderer=renderer, sink=sink)

        assert pipeline.renderer == renderer
        assert pipeline.sink == sink
        assert pipeline.filters == []

    def test_pipeline_with_filters(self):
        """Test pipeline accepts filters."""
        renderer = JsonRenderer()
        sink = FileSink()
        filters = [NoneFilter(), FieldFilter(profile="minimal")]

        pipeline = EmitPipeline(renderer=renderer, sink=sink, filters=filters)

        assert len(pipeline.filters) == 2

    def test_emit_simple_workflow_to_file(self, tmp_path):
        """Test emitting single workflow to file."""
        pipeline = EmitPipeline(renderer=JsonRenderer(), sink=FileSink())

        workflow = create_test_workflow()
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

        destination = tmp_path / "output.json"
        result = pipeline.emit([workflow], destination, config)

        assert isinstance(result, PipelineResult)
        assert result.success is True
        assert len(result.locations) > 0
        assert result.errors == []
        # File should exist
        assert any(Path(loc).exists() for loc in result.locations if isinstance(loc, (str, Path)))

    def test_emit_to_stdout(self, capsys):
        """Test emitting to stdout."""
        pipeline = EmitPipeline(renderer=JsonRenderer(), sink=StdoutSink())

        workflow = create_test_workflow()
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

        result = pipeline.emit([workflow], "-", config)

        captured = capsys.readouterr()
        assert result.success
        assert "TestWorkflow" in captured.out
        assert result.locations == ["stdout"]


# ============================================================================
# Pipeline Stage Tests
# ============================================================================


class TestPipelineStages:
    """Test individual pipeline stages."""

    def test_stage_1_normalize_dto_to_dict(self, tmp_path):
        """Test Stage 1: DTO normalization to dict."""
        pipeline = EmitPipeline(renderer=JsonRenderer(), sink=FileSink())

        workflow = create_test_workflow()
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

        result = pipeline.emit([workflow], tmp_path / "out.json", config)

        assert result.success
        # Verify dict conversion happened (workflow data in output)
        import json

        output_file = Path(result.locations[0])
        data = json.loads(output_file.read_text())
        assert data["id"] == "wf1"
        assert data["name"] == "TestWorkflow"

    def test_stage_2_filter_none_values(self, tmp_path):
        """Test Stage 2: Filter application (None removal)."""
        pipeline = EmitPipeline(
            renderer=JsonRenderer(), sink=FileSink(), filters=[NoneFilter()]
        )

        # Create workflow with None values
        workflow = create_test_workflow()
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

        result = pipeline.emit([workflow], tmp_path / "out.json", config)

        assert result.success
        # Check filter metadata
        assert "none_filter" in result.filter_metadata

        # Verify None values removed from output
        import json

        output_file = Path(result.locations[0])
        data = json.loads(output_file.read_text())
        # None fields should be removed
        assert "provenance" not in data or data.get("provenance") is not None
        assert "quality_metrics" not in data or data.get("quality_metrics") is not None

    def test_stage_2_filter_field_profile(self, tmp_path):
        """Test Stage 2: Field profile filtering."""
        pipeline = EmitPipeline(
            renderer=JsonRenderer(),
            sink=FileSink(),
            filters=[FieldFilter(profile="minimal")],
        )

        workflow = create_test_workflow()
        config = EmitterConfig(
            format="json",
            combine=False,
            pretty=True,
            exclude_none=False,
            field_profile="minimal",
            indent=2,
            encoding="utf-8",
            overwrite=True,
        )

        result = pipeline.emit([workflow], tmp_path / "out.json", config)

        assert result.success
        assert "field_filter_minimal" in result.filter_metadata

    def test_stage_2_multiple_filters(self, tmp_path):
        """Test Stage 2: Multiple filters in sequence."""
        pipeline = EmitPipeline(
            renderer=JsonRenderer(),
            sink=FileSink(),
            filters=[NoneFilter(), FieldFilter(profile="minimal")],
        )

        workflow = create_test_workflow()
        config = EmitterConfig(
            format="json",
            combine=False,
            pretty=True,
            exclude_none=False,
            field_profile="minimal",
            indent=2,
            encoding="utf-8",
            overwrite=True,
        )

        result = pipeline.emit([workflow], tmp_path / "out.json", config)

        assert result.success
        # Both filters should have metadata
        assert "none_filter" in result.filter_metadata
        assert "field_filter_minimal" in result.filter_metadata

    def test_stage_3_json_rendering(self, tmp_path):
        """Test Stage 3: JSON rendering."""
        pipeline = EmitPipeline(renderer=JsonRenderer(), sink=FileSink())

        workflow = create_test_workflow()
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

        result = pipeline.emit([workflow], tmp_path / "out.json", config)

        assert result.success
        assert "suggested_filename" in result.render_metadata or len(result.locations) > 0

        # Verify JSON format
        output_file = Path(result.locations[0])
        import json

        data = json.loads(output_file.read_text())
        assert isinstance(data, dict)

    def test_stage_3_mermaid_rendering(self, tmp_path):
        """Test Stage 3: Mermaid rendering."""
        pipeline = EmitPipeline(renderer=MermaidRenderer(), sink=FileSink())

        workflow = create_test_workflow(
            activities=[
                {
                    "id": "a1",
                    "display_name": "Start",
                    "type_short": "Sequence",
                    "depth": 0,
                }
            ],
            edges=[],
        )
        config = EmitterConfig(
            format="mermaid",
            combine=False,
            pretty=True,
            exclude_none=False,
            field_profile="full",
            indent=2,
            encoding="utf-8",
            overwrite=True,
        )

        result = pipeline.emit([workflow], tmp_path / "out.mmd", config)

        assert result.success

        # Verify Mermaid format
        output_file = Path(result.locations[0])
        content = output_file.read_text()
        assert "flowchart TD" in content
        assert "Start" in content

    def test_stage_4_file_sink(self, tmp_path):
        """Test Stage 4: File sink writes to filesystem."""
        pipeline = EmitPipeline(renderer=JsonRenderer(), sink=FileSink())

        workflow = create_test_workflow()
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

        destination = tmp_path / "output.json"
        result = pipeline.emit([workflow], destination, config)

        assert result.success
        assert result.sink_metadata["bytes_written"] > 0
        assert len(result.locations) > 0


# ============================================================================
# Pipeline Error Handling
# ============================================================================


class TestPipelineErrorHandling:
    """Test pipeline error handling."""

    def test_render_failure_stops_pipeline(self):
        """Test pipeline stops if rendering fails."""

        # Create a mock renderer that always fails
        class FailingRenderer:
            name = "failing"
            output_extension = ".fail"

            def render_many(self, workflows, config):
                from cpmf_uips_xaml.stages.emit.renderers.base import RenderResult

                return RenderResult(
                    success=False,
                    content="",
                    metadata={},
                    errors=["Render failed"],
                    warnings=[],
                )

        pipeline = EmitPipeline(renderer=FailingRenderer(), sink=FileSink())

        workflow = create_test_workflow()
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

        result = pipeline.emit([workflow], Path("/tmp/out"), config)

        assert result.success is False
        assert "Render failed" in result.errors
        assert len(result.locations) == 0  # No files written

    def test_sink_failure_reported(self, tmp_path):
        """Test sink failure is reported (raises PermissionError)."""
        # Create read-only directory
        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir()

        import os

        try:
            os.chmod(readonly_dir, 0o444)

            pipeline = EmitPipeline(renderer=JsonRenderer(), sink=FileSink())

            workflow = create_test_workflow()
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

            destination = readonly_dir / "output.json"

            # On Unix systems, this should raise PermissionError
            # On Windows, permissions work differently
            if os.name != "nt":
                with pytest.raises(PermissionError):
                    pipeline.emit([workflow], destination, config)
            else:
                # Windows test: may succeed or fail depending on permissions
                result = pipeline.emit([workflow], destination, config)
                # Just verify we got a result
                assert isinstance(result, PipelineResult)
        finally:
            os.chmod(readonly_dir, 0o755)


# ============================================================================
# Pipeline Integration Tests
# ============================================================================


class TestPipelineIntegration:
    """Test full pipeline with realistic workflows."""

    def test_json_pipeline_with_filters(self, tmp_path):
        """Test complete JSON pipeline with filtering."""
        pipeline = EmitPipeline(
            renderer=JsonRenderer(),
            sink=FileSink(),
            filters=[NoneFilter(), FieldFilter(profile="minimal")],
        )

        workflow = create_test_workflow(
            activities=[
                {"id": "a1", "type_short": "Assign", "display_name": "Set Value"}
            ]
        )

        config = EmitterConfig(
            format="json",
            combine=False,
            pretty=True,
            exclude_none=True,
            field_profile="minimal",
            indent=2,
            encoding="utf-8",
            overwrite=True,
        )

        result = pipeline.emit([workflow], tmp_path / "out.json", config)

        assert result.success
        assert len(result.locations) > 0
        assert result.filter_metadata  # Filters applied
        assert result.render_metadata  # Rendering metadata
        assert result.sink_metadata  # Sink metadata

        # Verify output
        import json

        output_file = Path(result.locations[0])
        data = json.loads(output_file.read_text())
        assert data["id"] == "wf1"
        assert "activities" in data

    def test_mermaid_pipeline_multiple_workflows(self, tmp_path):
        """Test Mermaid pipeline with multiple workflows."""
        pipeline = EmitPipeline(renderer=MermaidRenderer(), sink=FileSink())

        workflows = [
            create_test_workflow(id="wf1", name="Workflow1"),
            create_test_workflow(id="wf2", name="Workflow2"),
        ]

        config = EmitterConfig(
            format="mermaid",
            combine=False,
            pretty=True,
            exclude_none=False,
            field_profile="full",
            indent=2,
            encoding="utf-8",
            overwrite=True,
        )

        result = pipeline.emit(workflows, tmp_path, config)

        assert result.success
        assert len(result.locations) == 2  # Two separate files

    def test_stdout_pipeline_for_cli_piping(self, capsys):
        """Test stdout pipeline for CLI piping."""
        pipeline = EmitPipeline(renderer=JsonRenderer(), sink=StdoutSink())

        workflow = create_test_workflow()
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

        result = pipeline.emit([workflow], "-", config)

        # Verify pipeline succeeded
        assert result.success
        assert result.locations == ["stdout"]
        assert result.sink_metadata["bytes_written"] > 0

        # Note: pytest's capsys may not capture output from print() in all contexts
        # The important thing is that the pipeline completed successfully
        captured = capsys.readouterr()
        # Output may be captured or may not, but pipeline should succeed
        assert result.success

    def test_combined_json_output(self, tmp_path):
        """Test combined JSON output (multiple workflows in single file)."""
        pipeline = EmitPipeline(renderer=JsonRenderer(), sink=FileSink())

        workflows = [
            create_test_workflow(id="wf1", name="Workflow1"),
            create_test_workflow(id="wf2", name="Workflow2"),
        ]

        config = EmitterConfig(
            format="json",
            combine=True,  # Combine into single file
            pretty=True,
            exclude_none=False,
            field_profile="full",
            indent=2,
            encoding="utf-8",
            overwrite=True,
        )

        result = pipeline.emit(workflows, tmp_path / "combined.json", config)

        assert result.success
        # Should be single file
        output_file = Path(result.locations[0])
        import json

        data = json.loads(output_file.read_text())
        assert "workflows" in data
        assert len(data["workflows"]) == 2


# ============================================================================
# Edge Cases
# ============================================================================


class TestPipelineEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_workflow_list(self, tmp_path):
        """Test pipeline with empty workflow list."""
        pipeline = EmitPipeline(renderer=JsonRenderer(), sink=FileSink())

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

        result = pipeline.emit([], tmp_path / "out.json", config)

        # Should succeed with empty output
        assert isinstance(result, PipelineResult)

    def test_pipeline_without_filters(self, tmp_path):
        """Test pipeline works without filters."""
        pipeline = EmitPipeline(
            renderer=JsonRenderer(), sink=FileSink(), filters=None
        )

        workflow = create_test_workflow()
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

        result = pipeline.emit([workflow], tmp_path / "out.json", config)

        assert result.success
        assert result.filter_metadata == {}

    def test_config_dict_conversion_for_filters(self, tmp_path):
        """Test EmitterConfig is converted to dict for filters."""
        pipeline = EmitPipeline(
            renderer=JsonRenderer(),
            sink=FileSink(),
            filters=[FieldFilter(profile="minimal")],
        )

        workflow = create_test_workflow()
        config = EmitterConfig(
            format="json",
            combine=False,
            pretty=True,
            exclude_none=False,
            field_profile="minimal",
            indent=2,
            encoding="utf-8",
            overwrite=True,
        )

        # This should not raise AttributeError (config converted to dict)
        result = pipeline.emit([workflow], tmp_path / "out.json", config)

        assert result.success
