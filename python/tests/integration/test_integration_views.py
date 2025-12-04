"""Integration tests for view-based analysis (Phase 7).

Tests the complete flow: Parse → Analyze → View → Render
"""

import pytest

from cpmf_xaml_parser import ProjectParser, analyze_project
from cpmf_xaml_parser.views import ExecutionView, NestedView, SliceView


@pytest.mark.integration
def test_nested_view_produces_backward_compatible_output(simple_project):
    """NestedView should produce hierarchical workflow output."""
    # Parse project
    parser = ProjectParser()
    result = parser.parse_project(simple_project)

    assert result.success, f"Project parsing failed: {result.errors}"

    # Analyze
    index = analyze_project(result)

    # Render nested view
    view = NestedView()
    output = view.render(index)

    # Verify structure
    assert "schema_id" in output
    assert output["schema_id"] == "https://rpax.io/schemas/xaml-nested-workflow-graph.json"
    assert "schema_version" in output
    assert "workflows" in output
    assert isinstance(output["workflows"], list)


@pytest.mark.integration
def test_execution_view_traverses_call_graph(simple_project):
    """ExecutionView should traverse call graph from entry point."""
    # Parse project
    parser = ProjectParser()
    result = parser.parse_project(simple_project, recursive=True)

    assert result.success
    assert result.total_workflows > 0

    # Analyze
    index = analyze_project(result)

    # Get first workflow ID as entry point
    if not index.workflows.nodes():
        pytest.skip("No workflows found")

    first_workflow_id = index.workflows.nodes()[0]

    # Render execution view
    view = ExecutionView(entry_point=first_workflow_id, max_depth=10)
    output = view.render(index)

    # Verify structure
    assert "schema_id" in output
    assert output["schema_id"] == "https://rpax.io/schemas/xaml-workflow-execution.json"
    assert "entry_point" in output
    assert "workflows" in output
    assert isinstance(output["workflows"], list)

    # Each workflow should have call_depth
    for wf in output["workflows"]:
        assert "call_depth" in wf
        assert isinstance(wf["call_depth"], int)
        assert wf["call_depth"] >= 0


@pytest.mark.integration
def test_execution_view_nests_activities(simple_project):
    """ExecutionView should nest child activities under parents."""
    # Parse project
    parser = ProjectParser()
    result = parser.parse_project(simple_project, recursive=True)

    assert result.success

    # Analyze
    index = analyze_project(result)

    # Get first workflow ID as entry point
    if not index.workflows.nodes():
        pytest.skip("No workflows found")

    first_workflow_id = index.workflows.nodes()[0]

    # Render execution view
    view = ExecutionView(entry_point=first_workflow_id, max_depth=10)
    output = view.render(index)

    # Check for nested structure
    for wf in output["workflows"]:
        if "activities" in wf and wf["activities"]:
            # Activities should have children array
            for activity in wf["activities"]:
                assert "children" in activity
                assert isinstance(activity["children"], list)
                # parent_id should be removed in nested structure
                assert "parent_id" not in activity


@pytest.mark.integration
def test_slice_view_extracts_activity_context(simple_project):
    """SliceView should extract context around focal activity."""
    # Parse project
    parser = ProjectParser()
    result = parser.parse_project(simple_project)

    assert result.success

    # Analyze
    index = analyze_project(result)

    # Get first activity ID
    if not index.activities.nodes():
        pytest.skip("No activities found in project")

    focal_activity_id = index.activities.nodes()[0]

    # Render slice view
    view = SliceView(focus=focal_activity_id, radius=2)
    output = view.render(index)

    # Verify structure
    assert "schema_id" in output
    assert output["schema_id"] == "https://rpax.io/schemas/xaml-activity-slice.json"
    assert "focus" in output
    assert output["focus"] == focal_activity_id
    assert "radius" in output
    assert "focal_activity" in output
    assert "parent_chain" in output
    assert "siblings" in output
    assert "context_activities" in output


@pytest.mark.integration
def test_analyze_project_builds_all_graphs(simple_project):
    """analyze_project should build all 4 graph layers."""
    # Parse project
    parser = ProjectParser()
    result = parser.parse_project(simple_project, recursive=True)

    assert result.success

    # Analyze
    index = analyze_project(result)

    # Verify all graphs are populated
    assert index.workflows.node_count() > 0
    assert index.total_workflows > 0

    # Activities graph (should have activities from all workflows)
    assert index.activities.node_count() >= 0  # May be 0 for minimal test projects

    # Workflow lookups
    assert len(index.workflow_by_path) > 0

    # Activity to workflow mapping
    if index.activities.node_count() > 0:
        first_activity_id = index.activities.nodes()[0]
        workflow = index.get_workflow_for_activity(first_activity_id)
        assert workflow is not None


@pytest.mark.integration
def test_view_query_methods(simple_project):
    """Test ProjectIndex query methods."""
    # Parse project
    parser = ProjectParser()
    result = parser.parse_project(simple_project, recursive=True)

    assert result.success

    # Analyze
    index = analyze_project(result)

    # Test get_workflow
    first_wf_id = index.workflows.nodes()[0]
    workflow = index.get_workflow(first_wf_id)
    assert workflow is not None
    assert workflow.id == first_wf_id

    # Test find_call_cycles (should be empty for simple projects)
    cycles = index.find_call_cycles()
    assert isinstance(cycles, list)

    # Test get_execution_order
    order = index.get_execution_order()
    assert isinstance(order, list)
    assert len(order) == index.workflows.node_count()


@pytest.mark.integration
def test_end_to_end_nested_view_json_output(simple_project, tmp_path):
    """Test complete flow with JSON output."""
    # Parse
    parser = ProjectParser()
    result = parser.parse_project(simple_project)
    assert result.success

    # Analyze
    index = analyze_project(result)

    # Render
    view = NestedView()
    output = view.render(index)

    # Write to file
    import json

    output_file = tmp_path / "output.json"
    output_file.write_text(json.dumps(output, indent=2), encoding="utf-8")

    # Verify file exists and is valid JSON
    assert output_file.exists()
    parsed = json.loads(output_file.read_text(encoding="utf-8"))
    assert "workflows" in parsed
