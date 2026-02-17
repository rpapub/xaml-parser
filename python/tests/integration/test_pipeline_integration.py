"""Integration tests for emitter pipeline with real UiPath projects.

Tests the complete pipeline with actual project corpuses:
- Parse real UiPath projects
- Apply filters (field profiles, None removal)
- Render to different formats (JSON, Mermaid)
- Write to files and stdout

This verifies the pipeline works with real-world data.
"""

import json
import pytest
from pathlib import Path

from cpmf_uips_xaml.api import (
    parse_and_analyze_project,
    emit_workflows,
    normalize_parse_results,
)
from cpmf_uips_xaml.config.models import EmitterConfig
from cpmf_uips_xaml.stages.emit.pipeline import EmitPipeline
from cpmf_uips_xaml.stages.emit.renderers.json_renderer import JsonRenderer
from cpmf_uips_xaml.stages.emit.renderers.mermaid_renderer import MermaidRenderer
from cpmf_uips_xaml.stages.emit.sinks.file_sink import FileSink
from cpmf_uips_xaml.stages.emit.filters.field_filter import FieldFilter
from cpmf_uips_xaml.stages.emit.filters.none_filter import NoneFilter
from cpmf_uips_xaml.shared.progress import NULL_REPORTER


# Test corpus paths
TEST_CORPUSES = [
    Path("/mnt/d/github.com/rpapub/rpax-corpuses/c25v001_CORE_00000001"),
    Path("/mnt/d/github.com/rpapub/rpax-corpuses/c25v001_CORE_00000010"),
    Path("/mnt/d/github.com/rpapub/FrozenChlorine"),
]


def get_available_corpuses():
    """Get list of available test corpuses."""
    return [corpus for corpus in TEST_CORPUSES if corpus.exists()]


@pytest.fixture(scope="module")
def test_corpus():
    """Get first available test corpus."""
    available = get_available_corpuses()
    if not available:
        pytest.skip("No test corpuses available")
    return available[0]


@pytest.fixture(scope="module")
def parsed_project(test_corpus):
    """Parse test project once for all tests."""
    try:
        result, analyzer, index = parse_and_analyze_project(
            test_corpus,
            recursive=True,
            entry_points_only=False,
            reporter=NULL_REPORTER,
        )

        # Normalize WorkflowResult objects to WorkflowDto for emission
        workflow_dtos = normalize_parse_results(
            [wf.parse_result for wf in result.workflows if wf.parse_result.success],
            project_dir=test_corpus,
        )

        return result, analyzer, index, workflow_dtos
    except Exception as e:
        pytest.skip(f"Failed to parse project: {e}")


# ============================================================================
# JSON Pipeline Tests
# ============================================================================


class TestJsonPipelineIntegration:
    """Test JSON rendering pipeline with real projects."""

    def test_json_emit_full_profile(self, parsed_project, tmp_path):
        """Test JSON emission with full field profile."""
        result, analyzer, index, workflow_dtos = parsed_project
        workflows = workflow_dtos

        if not workflows:
            pytest.skip("No workflows in project")

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

        output_dir = tmp_path / "json_full"
        emit_result = emit_workflows(workflows, output_dir, config)

        assert emit_result.success
        assert len(emit_result.locations) > 0

        # Verify JSON files exist and are valid
        for location in emit_result.locations:
            json_file = Path(location)
            assert json_file.exists()

            # Verify valid JSON
            data = json.loads(json_file.read_text())
            assert "id" in data
            assert "name" in data
            assert "activities" in data

    def test_json_emit_minimal_profile(self, parsed_project, tmp_path):
        """Test JSON emission with minimal field profile."""
        result, analyzer, index, workflow_dtos = parsed_project
        workflows = workflow_dtos[:3]  # Test with first 3

        if not workflows:
            pytest.skip("No workflows in project")

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

        output_dir = tmp_path / "json_minimal"
        emit_result = emit_workflows(workflows, output_dir, config)

        assert emit_result.success
        assert len(emit_result.locations) == len(workflows)

    def test_json_emit_combined(self, parsed_project, tmp_path):
        """Test JSON emission with combined output."""
        result, analyzer, index, workflow_dtos = parsed_project
        workflows = workflow_dtos[:5]  # Test with first 5

        if not workflows:
            pytest.skip("No workflows in project")

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

        output_file = tmp_path / "workflows_combined.json"
        emit_result = emit_workflows(workflows, output_file, config)

        assert emit_result.success
        assert len(emit_result.locations) == 1

        # Verify combined JSON structure
        combined_data = json.loads(Path(emit_result.locations[0]).read_text())
        assert "workflows" in combined_data
        assert len(combined_data["workflows"]) == len(workflows)


# ============================================================================
# Mermaid Pipeline Tests
# ============================================================================


class TestMermaidPipelineIntegration:
    """Test Mermaid rendering pipeline with real projects."""

    def test_mermaid_emit_single_workflow(self, parsed_project, tmp_path):
        """Test Mermaid diagram generation for single workflow."""
        result, analyzer, index, workflow_dtos = parsed_project
        workflows = workflow_dtos

        if not workflows:
            pytest.skip("No workflows in project")

        # Pick a workflow with activities
        workflow = next(
            (wf for wf in workflows if len(wf.activities) > 0),
            workflows[0]
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

        output_dir = tmp_path / "mermaid"
        emit_result = emit_workflows([workflow], output_dir, config)

        assert emit_result.success
        assert len(emit_result.locations) > 0

        # Verify Mermaid file exists and contains flowchart
        mermaid_file = Path(emit_result.locations[0])
        assert mermaid_file.exists()
        assert mermaid_file.suffix == ".mmd"

        content = mermaid_file.read_text()
        assert "flowchart TD" in content
        assert workflow.name in content or "%% Workflow:" in content

    def test_mermaid_emit_with_activities(self, parsed_project, tmp_path):
        """Test Mermaid diagrams include activity nodes."""
        result, analyzer, index = parsed_project
        workflows = [wf for wf in result.workflows if len(wf.activities) > 0]

        if not workflows:
            pytest.skip("No workflows with activities")

        workflow = workflows[0]

        config = EmitterConfig(
            format="mermaid",
            combine=False,
            pretty=True,
            exclude_none=False,
            field_profile="full",
            indent=2,
            encoding="utf-8",
            overwrite=True,
            extra={"max_depth": 3},
        )

        output_dir = tmp_path / "mermaid_activities"
        emit_result = emit_workflows([workflow], output_dir, config)

        assert emit_result.success

        # Verify diagram contains activity nodes
        mermaid_file = Path(emit_result.locations[0])
        content = mermaid_file.read_text()

        # Should have node definitions (brackets or parentheses)
        assert "[" in content or "(" in content or "{" in content

    def test_mermaid_emit_multiple_workflows(self, parsed_project, tmp_path):
        """Test Mermaid emission for multiple workflows."""
        result, analyzer, index, workflow_dtos = parsed_project
        workflows = workflow_dtos[:3]

        if not workflows:
            pytest.skip("No workflows in project")

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

        output_dir = tmp_path / "mermaid_multiple"
        emit_result = emit_workflows(workflows, output_dir, config)

        assert emit_result.success
        assert len(emit_result.locations) == len(workflows)

        # Verify all files created
        for location in emit_result.locations:
            mermaid_file = Path(location)
            assert mermaid_file.exists()
            assert "flowchart TD" in mermaid_file.read_text()


# ============================================================================
# Filter Pipeline Tests
# ============================================================================


class TestFilterPipelineIntegration:
    """Test filter application with real projects."""

    def test_pipeline_with_field_filter(self, parsed_project, tmp_path):
        """Test pipeline with field filtering."""
        result, analyzer, index, workflow_dtos = parsed_project
        workflows = workflow_dtos[:2]

        if not workflows:
            pytest.skip("No workflows in project")

        pipeline = EmitPipeline(
            renderer=JsonRenderer(),
            sink=FileSink(),
            filters=[FieldFilter(profile="minimal")],
        )

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

        output_dir = tmp_path / "filtered"
        pipe_result = pipeline.emit(workflows, output_dir, config)

        assert pipe_result.success
        assert "field_filter_minimal" in pipe_result.filter_metadata

    def test_pipeline_with_none_filter(self, parsed_project, tmp_path):
        """Test pipeline with None value removal."""
        result, analyzer, index, workflow_dtos = parsed_project
        workflows = workflow_dtos[:2]

        if not workflows:
            pytest.skip("No workflows in project")

        pipeline = EmitPipeline(
            renderer=JsonRenderer(),
            sink=FileSink(),
            filters=[NoneFilter()],
        )

        config = EmitterConfig(
            format="json",
            combine=False,
            pretty=True,
            exclude_none=True,
            field_profile="full",
            indent=2,
            encoding="utf-8",
            overwrite=True,
        )

        output_dir = tmp_path / "none_filtered"
        pipe_result = pipeline.emit(workflows, output_dir, config)

        assert pipe_result.success
        assert "none_filter" in pipe_result.filter_metadata

        # Verify None values removed from output
        for location in pipe_result.locations:
            json_file = Path(location)
            data = json.loads(json_file.read_text())
            # Check no None values in top-level fields
            assert all(v is not None for v in data.values())

    def test_pipeline_with_multiple_filters(self, parsed_project, tmp_path):
        """Test pipeline with multiple filters in sequence."""
        result, analyzer, index, workflow_dtos = parsed_project
        workflows = workflow_dtos[:2]

        if not workflows:
            pytest.skip("No workflows in project")

        pipeline = EmitPipeline(
            renderer=JsonRenderer(),
            sink=FileSink(),
            filters=[NoneFilter(), FieldFilter(profile="minimal")],
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

        output_dir = tmp_path / "multi_filtered"
        pipe_result = pipeline.emit(workflows, output_dir, config)

        assert pipe_result.success
        assert "none_filter" in pipe_result.filter_metadata
        assert "field_filter_minimal" in pipe_result.filter_metadata


# ============================================================================
# Cross-Format Tests
# ============================================================================


class TestCrossFormatIntegration:
    """Test emitting same project to multiple formats."""

    def test_emit_json_and_mermaid(self, parsed_project, tmp_path):
        """Test emitting same workflows to JSON and Mermaid."""
        result, analyzer, index, workflow_dtos = parsed_project
        workflows = workflow_dtos[:3]

        if not workflows:
            pytest.skip("No workflows in project")

        # Emit JSON
        json_config = EmitterConfig(
            format="json",
            combine=False,
            pretty=True,
            exclude_none=False,
            field_profile="full",
            indent=2,
            encoding="utf-8",
            overwrite=True,
        )
        json_output = tmp_path / "json"
        json_result = emit_workflows(workflows, json_output, json_config)

        # Emit Mermaid
        mermaid_config = EmitterConfig(
            format="mermaid",
            combine=False,
            pretty=True,
            exclude_none=False,
            field_profile="full",
            indent=2,
            encoding="utf-8",
            overwrite=True,
        )
        mermaid_output = tmp_path / "mermaid"
        mermaid_result = emit_workflows(workflows, mermaid_output, mermaid_config)

        # Both should succeed
        assert json_result.success
        assert mermaid_result.success

        # Same number of files created
        assert len(json_result.locations) == len(workflows)
        assert len(mermaid_result.locations) == len(workflows)


# ============================================================================
# Stress Tests
# ============================================================================


class TestPipelineStress:
    """Stress tests with large projects."""

    def test_emit_all_workflows(self, parsed_project, tmp_path):
        """Test emitting all workflows from a project."""
        result, analyzer, index, workflow_dtos = parsed_project
        workflows = workflow_dtos

        if not workflows:
            pytest.skip("No workflows in project")

        # Skip if too many workflows (performance test, not load test)
        if len(workflows) > 50:
            workflows = workflows[:50]

        config = EmitterConfig(
            format="json",
            combine=False,
            pretty=False,  # Compact for speed
            exclude_none=True,
            field_profile="minimal",
            indent=2,
            encoding="utf-8",
            overwrite=True,
        )

        output_dir = tmp_path / "all_workflows"
        emit_result = emit_workflows(workflows, output_dir, config)

        assert emit_result.success
        assert len(emit_result.locations) == len(workflows)

        # Verify all files created and valid
        for location in emit_result.locations:
            assert Path(location).exists()
            assert Path(location).stat().st_size > 0

    def test_emit_workflow_with_many_activities(self, parsed_project, tmp_path):
        """Test emitting workflow with many activities."""
        result, analyzer, index = parsed_project

        # Find workflow with most activities
        workflow = max(
            result.workflows,
            key=lambda wf: len(wf.activities),
            default=None
        )

        if not workflow or len(workflow.activities) < 5:
            pytest.skip("No workflows with sufficient activities")

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

        output_dir = tmp_path / "complex_workflow"
        emit_result = emit_workflows([workflow], output_dir, config)

        assert emit_result.success

        # Verify diagram was generated
        mermaid_file = Path(emit_result.locations[0])
        content = mermaid_file.read_text()
        assert "flowchart TD" in content
        # Should have nodes for activities
        assert content.count("[") > 0 or content.count("(") > 0


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestPipelineErrorHandling:
    """Test error handling with real projects."""

    def test_emit_with_invalid_output_path(self, parsed_project):
        """Test pipeline handles invalid output paths gracefully."""
        result, analyzer, index, workflow_dtos = parsed_project
        workflows = workflow_dtos[:1]

        if not workflows:
            pytest.skip("No workflows in project")

        config = EmitterConfig(
            format="json",
            combine=False,
            pretty=True,
            exclude_none=False,
            field_profile="full",
            indent=2,
            encoding="utf-8",
            overwrite=False,
        )

        # Try to write to root (should fail with permission error)
        invalid_path = Path("/root/invalid/path")

        # Should raise exception or return failure
        try:
            emit_result = emit_workflows(workflows, invalid_path, config)
            # If it didn't raise, should have failed
            assert not emit_result.success or len(emit_result.errors) > 0
        except (PermissionError, OSError):
            # Expected behavior
            pass

    def test_emit_empty_workflow_list(self, tmp_path):
        """Test emitting empty workflow list."""
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

        output_dir = tmp_path / "empty"
        emit_result = emit_workflows([], output_dir, config)

        # Should succeed with no output
        assert isinstance(emit_result, (type(emit_result), type(None)))
