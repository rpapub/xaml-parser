"""Simplified integration tests for emitter pipeline with real UiPath projects.

Tests the pipeline components work together without full project analysis.
"""

import json
import pytest
from pathlib import Path
import dataclasses

from cpmf_uips_xaml.stages.parsing.parser import XamlParser
from cpmf_uips_xaml.stages.emit.pipeline import EmitPipeline
from cpmf_uips_xaml.stages.emit.renderers.json_renderer import JsonRenderer
from cpmf_uips_xaml.stages.emit.renderers.mermaid_renderer import MermaidRenderer
from cpmf_uips_xaml.stages.emit.sinks.file_sink import FileSink
from cpmf_uips_xaml.stages.emit.filters.field_filter import FieldFilter
from cpmf_uips_xaml.stages.emit.filters.none_filter import NoneFilter
from cpmf_uips_xaml.config.models import EmitterConfig
from cpmf_uips_xaml.platforms.uipath.constants import DEFAULT_CONFIG


# Test corpus paths
TEST_CORPUSES = [
    Path("/mnt/d/github.com/rpapub/FrozenChlorine"),
    Path("/mnt/d/github.com/rpapub/rpax-corpuses/c25v001_CORE_00000001"),
]


def get_test_workflows():
    """Get a few test workflows by parsing XAML files directly."""
    for corpus_dir in TEST_CORPUSES:
        if not corpus_dir.exists():
            continue

        # Find XAML files
        xaml_files = list(corpus_dir.rglob("*.xaml"))[:3]  # Just take first 3

        parser = XamlParser(DEFAULT_CONFIG)
        parse_results = []

        for xaml_file in xaml_files:
            result = parser.parse_file(xaml_file)
            if result.success:
                parse_results.append(result)

        if parse_results:
            return parse_results

    return []


@pytest.fixture(scope="module")
def test_parse_results():
    """Get test parse results."""
    results = get_test_workflows()
    if not results:
        pytest.skip("No test workflows available")
    return results


# ============================================================================
# Direct Pipeline Tests (No DTO Conversion)
# ============================================================================


class TestPipelineWithDicts:
    """Test pipeline with dict data (simulating normalized DTOs)."""

    def test_json_renderer_with_dict(self, tmp_path):
        """Test JSON renderer with dict data."""
        # Create simple workflow dict
        workflow_dict = {
            "id": "test_workflow_1",
            "name": "TestWorkflow",
            "activities": [
                {"id": "act1", "type_short": "Sequence", "display_name": "Main"}
            ],
            "edges": [],
            "arguments": [],
            "variables": [],
        }

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

        # Convert to minimal DTO-like structure
        from cpmf_uips_xaml.shared.model.dto import (
            WorkflowDto,
            SourceInfo,
            WorkflowMetadata,
        )

        workflow = WorkflowDto(
            schema_id="https://example.com/schema",
            schema_version="1.0",
            collected_at="2024-01-01T00:00:00Z",
            provenance=None,
            id="test_workflow_1",
            name="TestWorkflow",
            source=SourceInfo(
                path="Test.xaml", path_aliases=[], hash="abc", size_bytes=100, encoding="utf-8"
            ),
            metadata=WorkflowMetadata(annotation=None),
            variables=[],
            arguments=[],
            dependencies=[],
            activities=[],
            edges=[],
            invocations=[],
            issues=[],
            quality_metrics=None,
            anti_patterns=[],
        )

        output_dir = tmp_path / "json_test"
        result = pipeline.emit([workflow], output_dir, config)

        assert result.success
        assert len(result.locations) > 0

        # Verify JSON file
        json_file = Path(result.locations[0])
        assert json_file.exists()
        data = json.loads(json_file.read_text())
        assert data["id"] == "test_workflow_1"

    def test_mermaid_renderer_with_dict(self, tmp_path):
        """Test Mermaid renderer with dict data."""
        from cpmf_uips_xaml.shared.model.dto import (
            WorkflowDto,
            ActivityDto,
            SourceInfo,
            WorkflowMetadata,
        )

        workflow = WorkflowDto(
            schema_id="https://example.com/schema",
            schema_version="1.0",
            collected_at="2024-01-01T00:00:00Z",
            provenance=None,
            id="test_workflow_mermaid",
            name="TestMermaid",
            source=SourceInfo(
                path="Test.xaml", path_aliases=[], hash="abc", size_bytes=100, encoding="utf-8"
            ),
            metadata=WorkflowMetadata(annotation=None),
            variables=[],
            arguments=[],
            dependencies=[],
            activities=[
                ActivityDto(
                    id="act1",
                    type="System.Activities.Statements.Sequence",
                    type_short="Sequence",
                    type_namespace=None,
                    type_prefix=None,
                    display_name="Main Sequence",
                    parent_id=None,
                    children=[],
                    depth=0,
                    properties={},
                    in_args={},
                    out_args={},
                    annotation=None,
                    expressions=[],
                    variables_referenced=[],
                    selectors=None,
                )
            ],
            edges=[],
            invocations=[],
            issues=[],
            quality_metrics=None,
            anti_patterns=[],
        )

        pipeline = EmitPipeline(renderer=MermaidRenderer(), sink=FileSink())

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

        output_dir = tmp_path / "mermaid_test"
        result = pipeline.emit([workflow], output_dir, config)

        assert result.success
        assert len(result.locations) > 0

        # Verify Mermaid file
        mermaid_file = Path(result.locations[0])
        assert mermaid_file.exists()
        content = mermaid_file.read_text()
        assert "flowchart TD" in content
        assert "Main Sequence" in content

    def test_pipeline_with_filters(self, tmp_path):
        """Test pipeline with multiple filters."""
        from cpmf_uips_xaml.shared.model.dto import (
            WorkflowDto,
            SourceInfo,
            WorkflowMetadata,
        )

        workflow = WorkflowDto(
            schema_id="https://example.com/schema",
            schema_version="1.0",
            collected_at="2024-01-01T00:00:00Z",
            provenance=None,
            id="test_filtered",
            name="TestFiltered",
            source=SourceInfo(
                path="Test.xaml", path_aliases=[], hash="abc", size_bytes=100, encoding="utf-8"
            ),
            metadata=WorkflowMetadata(annotation=None),
            variables=[],
            arguments=[],
            dependencies=[],
            activities=[],
            edges=[],
            invocations=[],
            issues=[],
            quality_metrics=None,
            anti_patterns=[],
        )

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

        output_dir = tmp_path / "filtered_test"
        result = pipeline.emit([workflow], output_dir, config)

        assert result.success
        assert "none_filter" in result.filter_metadata
        assert "field_filter_minimal" in result.filter_metadata


# ============================================================================
# Summary Test
# ============================================================================


class TestPipelineEndToEnd:
    """End-to-end pipeline validation."""

    def test_pipeline_components_work_together(self, tmp_path):
        """Test all pipeline components integrate correctly."""
        from cpmf_uips_xaml.shared.model.dto import (
            WorkflowDto,
            ActivityDto,
            EdgeDto,
            SourceInfo,
            WorkflowMetadata,
        )

        # Create realistic workflow
        workflow = WorkflowDto(
            schema_id="https://example.com/schema",
            schema_version="1.0",
            collected_at="2024-01-01T00:00:00Z",
            provenance=None,
            id="integration_test",
            name="IntegrationTest",
            source=SourceInfo(
                path="Integration.xaml",
                path_aliases=[],
                hash="abc123",
                size_bytes=500,
                encoding="utf-8",
            ),
            metadata=WorkflowMetadata(annotation="Integration test workflow"),
            variables=[],
            arguments=[],
            dependencies=[],
            activities=[
                ActivityDto(
                    id="start",
                    type="System.Activities.Statements.Sequence",
                    type_short="Sequence",
                    type_namespace=None,
                    type_prefix=None,
                    display_name="Start",
                    parent_id=None,
                    children=["process", "end"],
                    depth=0,
                    properties={},
                    in_args={},
                    out_args={},
                    annotation=None,
                    expressions=[],
                    variables_referenced=[],
                    selectors=None,
                ),
                ActivityDto(
                    id="process",
                    type="System.Activities.Statements.Assign",
                    type_short="Assign",
                    type_namespace=None,
                    type_prefix=None,
                    display_name="Process Data",
                    parent_id="start",
                    children=[],
                    depth=1,
                    properties={},
                    in_args={},
                    out_args={},
                    annotation=None,
                    expressions=[],
                    variables_referenced=[],
                    selectors=None,
                ),
                ActivityDto(
                    id="end",
                    type="UiPath.Core.Activities.LogMessage",
                    type_short="LogMessage",
                    type_namespace=None,
                    type_prefix=None,
                    display_name="End",
                    parent_id="start",
                    children=[],
                    depth=1,
                    properties={},
                    in_args={},
                    out_args={},
                    annotation=None,
                    expressions=[],
                    variables_referenced=[],
                    selectors=None,
                ),
            ],
            edges=[
                EdgeDto(id="edge1", from_id="start", to_id="process", kind="sequence"),
                EdgeDto(id="edge2", from_id="process", to_id="end", kind="sequence"),
            ],
            invocations=[],
            issues=[],
            quality_metrics=None,
            anti_patterns=[],
        )

        # Test JSON output
        json_pipeline = EmitPipeline(
            renderer=JsonRenderer(),
            sink=FileSink(),
            filters=[NoneFilter()],
        )

        json_config = EmitterConfig(
            format="json",
            combine=False,
            pretty=True,
            exclude_none=True,
            field_profile="full",
            indent=2,
            encoding="utf-8",
            overwrite=True,
        )

        json_result = json_pipeline.emit([workflow], tmp_path / "json", json_config)
        assert json_result.success

        # Test Mermaid output
        mermaid_pipeline = EmitPipeline(
            renderer=MermaidRenderer(),
            sink=FileSink(),
        )

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

        mermaid_result = mermaid_pipeline.emit([workflow], tmp_path / "mermaid", mermaid_config)
        assert mermaid_result.success

        # Verify outputs
        json_file = Path(json_result.locations[0])
        assert json_file.exists()
        json_data = json.loads(json_file.read_text())
        assert json_data["id"] == "integration_test"
        assert len(json_data["activities"]) == 3

        mermaid_file = Path(mermaid_result.locations[0])
        assert mermaid_file.exists()
        mermaid_content = mermaid_file.read_text()
        assert "flowchart TD" in mermaid_content
        assert "Start" in mermaid_content
        assert "Process Data" in mermaid_content
        assert "End" in mermaid_content
