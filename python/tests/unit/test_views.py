"""Tests for views module."""

from xaml_parser.analyzer import ProjectAnalyzer
from xaml_parser.dto import ActivityDto, InvocationDto, SourceInfo, WorkflowDto
from xaml_parser.views import ExecutionView, NestedView, SliceView


def test_nested_view_empty():
    """Test nested view with empty project."""
    analyzer = ProjectAnalyzer()
    index = analyzer.analyze([])

    view = NestedView()
    result = view.render(index)

    assert result["schema_id"] == "https://rpax.io/schemas/xaml-nested-workflow-graph.json"
    assert result["schema_version"] == "0.4.0"
    assert "collected_at" in result
    assert result["workflows"] == []
    assert result["issues"] == []


def test_nested_view_single_workflow():
    """Test nested view with single workflow."""
    workflow = WorkflowDto(
        id="wf:test",
        name="TestWorkflow",
        source=SourceInfo(path="Test.xaml", hash="abc123"),
        arguments=[],
        variables=[],
        activities=[
            ActivityDto(
                id="act:1",
                type="System.Activities.Statements.WriteLine",
                type_short="WriteLine",
                display_name="Write Line",
                parent_id=None,
                children=[],
                properties={"Text": "Hello"},
            )
        ],
        edges=[],
        invocations=[],
    )

    analyzer = ProjectAnalyzer()
    index = analyzer.analyze([workflow])

    view = NestedView()
    result = view.render(index)

    assert len(result["workflows"]) == 1
    wf_dict = result["workflows"][0]
    assert wf_dict["id"] == "wf:test"
    assert wf_dict["name"] == "TestWorkflow"
    assert len(wf_dict["activities"]) == 1
    assert wf_dict["activities"][0]["type_short"] == "WriteLine"


def test_execution_view_entry_not_found():
    """Test execution view with non-existent entry point."""
    analyzer = ProjectAnalyzer()
    index = analyzer.analyze([])

    view = ExecutionView(entry_point="wf:nonexistent")
    result = view.render(index)

    assert "error" in result
    assert "not found" in result["error"]


def test_execution_view_single_workflow():
    """Test execution view with single workflow."""
    workflow = WorkflowDto(
        id="wf:main",
        name="Main",
        source=SourceInfo(path="Main.xaml", hash="main123"),
        arguments=[],
        variables=[],
        activities=[
            ActivityDto(
                id="act:1",
                type="System.Activities.Statements.WriteLine",
                type_short="WriteLine",
                display_name="Write Line",
                parent_id=None,
                children=[],
                properties={},
            )
        ],
        edges=[],
        invocations=[],
    )

    analyzer = ProjectAnalyzer()
    index = analyzer.analyze([workflow])

    view = ExecutionView(entry_point="wf:main")
    result = view.render(index)

    assert result["schema_id"] == "https://rpax.io/schemas/xaml-workflow-execution.json"
    assert result["schema_version"] == "0.4.0"
    assert result["entry_point"] == "wf:main"
    assert result["max_depth"] == 10
    assert len(result["workflows"]) == 1
    assert result["workflows"][0]["id"] == "wf:main"
    assert result["workflows"][0]["call_depth"] == 0


def test_execution_view_with_invocation():
    """Test execution view with workflow invocation."""
    main_workflow = WorkflowDto(
        id="wf:main",
        name="Main",
        source=SourceInfo(path="Main.xaml", hash="main123"),
        arguments=[],
        variables=[],
        activities=[
            ActivityDto(
                id="act:invoke",
                type="UiPath.Core.Activities.InvokeWorkflowFile",
                type_short="InvokeWorkflowFile",
                display_name="Invoke Helper",
                parent_id=None,
                children=[],
                properties={"WorkflowFileName": "Helper.xaml"},
            )
        ],
        edges=[],
        invocations=[
            InvocationDto(
                callee_id="wf:helper",
                callee_path="Helper.xaml",
                via_activity_id="act:invoke",
            )
        ],
    )

    helper_workflow = WorkflowDto(
        id="wf:helper",
        name="Helper",
        source=SourceInfo(path="Helper.xaml", hash="help123"),
        arguments=[],
        variables=[],
        activities=[
            ActivityDto(
                id="act:write",
                type="System.Activities.Statements.WriteLine",
                type_short="WriteLine",
                display_name="Write",
                parent_id=None,
                children=[],
                properties={},
            )
        ],
        edges=[],
        invocations=[],
    )

    analyzer = ProjectAnalyzer()
    index = analyzer.analyze([main_workflow, helper_workflow])

    view = ExecutionView(entry_point="wf:main", max_depth=5)
    result = view.render(index)

    # Should have both workflows
    assert len(result["workflows"]) == 2

    # Main workflow should be first
    main_wf = result["workflows"][0]
    assert main_wf["id"] == "wf:main"
    assert main_wf["call_depth"] == 0

    # Helper workflow should be second
    helper_wf = result["workflows"][1]
    assert helper_wf["id"] == "wf:helper"
    assert helper_wf["call_depth"] == 1


def test_execution_view_nested_activities():
    """Test execution view with nested activity structure."""
    workflow = WorkflowDto(
        id="wf:test",
        name="Test",
        source=SourceInfo(path="Test.xaml", hash="test123"),
        arguments=[],
        variables=[],
        activities=[
            ActivityDto(
                id="act:seq",
                type="System.Activities.Statements.Sequence",
                type_short="Sequence",
                display_name="Sequence",
                parent_id=None,
                children=["act:child"],
                properties={},
            ),
            ActivityDto(
                id="act:child",
                type="System.Activities.Statements.WriteLine",
                type_short="WriteLine",
                display_name="Child",
                parent_id="act:seq",
                children=[],
                properties={},
            ),
        ],
        edges=[],
        invocations=[],
    )

    analyzer = ProjectAnalyzer()
    index = analyzer.analyze([workflow])

    view = ExecutionView(entry_point="wf:test")
    result = view.render(index)

    # Check nested structure
    wf = result["workflows"][0]
    activities = wf["activities"]

    # Should only have root activity (Sequence)
    assert len(activities) == 1
    seq = activities[0]
    assert seq["id"] == "act:seq"

    # Sequence should have child nested
    assert len(seq["children"]) == 1
    child = seq["children"][0]
    assert child["id"] == "act:child"

    # parent_id should be removed in nested structure
    assert "parent_id" not in seq
    assert "parent_id" not in child


def test_execution_view_resolve_entry_by_path():
    """Test execution view resolving entry point by path."""
    workflow = WorkflowDto(
        id="wf:main",
        name="Main",
        source=SourceInfo(path="Main.xaml", hash="main123"),
        arguments=[],
        variables=[],
        activities=[],
        edges=[],
        invocations=[],
    )

    analyzer = ProjectAnalyzer()
    index = analyzer.analyze([workflow])

    # Resolve by path instead of ID
    view = ExecutionView(entry_point="Main.xaml")
    result = view.render(index)

    assert result["entry_point"] == "wf:main"
    assert len(result["workflows"]) == 1


def test_slice_view_activity_not_found():
    """Test slice view with non-existent activity."""
    analyzer = ProjectAnalyzer()
    index = analyzer.analyze([])

    view = SliceView(focus="act:nonexistent")
    result = view.render(index)

    assert "error" in result
    assert "not found" in result["error"]


def test_slice_view_single_activity():
    """Test slice view with single activity."""
    workflow = WorkflowDto(
        id="wf:test",
        name="Test",
        source=SourceInfo(path="Test.xaml", hash="test123"),
        arguments=[],
        variables=[],
        activities=[
            ActivityDto(
                id="act:focal",
                type="System.Activities.Statements.WriteLine",
                type_short="WriteLine",
                display_name="Focal",
                parent_id=None,
                children=[],
                properties={},
            )
        ],
        edges=[],
        invocations=[],
    )

    analyzer = ProjectAnalyzer()
    index = analyzer.analyze([workflow])

    view = SliceView(focus="act:focal", radius=2)
    result = view.render(index)

    assert result["schema_id"] == "https://rpax.io/schemas/xaml-activity-slice.json"
    assert result["schema_version"] == "0.4.0"
    assert result["focus"] == "act:focal"
    assert result["radius"] == 2
    assert result["workflow"]["id"] == "wf:test"
    assert result["focal_activity"]["id"] == "act:focal"
    assert result["parent_chain"] == []
    assert result["siblings"] == []
    assert len(result["context_activities"]) == 1


def test_slice_view_with_parent_chain():
    """Test slice view with parent chain."""
    workflow = WorkflowDto(
        id="wf:test",
        name="Test",
        source=SourceInfo(path="Test.xaml", hash="test123"),
        arguments=[],
        variables=[],
        activities=[
            ActivityDto(
                id="act:root",
                type="System.Activities.Statements.Sequence",
                type_short="Sequence",
                display_name="Root",
                parent_id=None,
                children=["act:child"],
                properties={},
            ),
            ActivityDto(
                id="act:child",
                type="System.Activities.Statements.Sequence",
                type_short="Sequence",
                display_name="Child",
                parent_id="act:root",
                children=["act:focal"],
                properties={},
            ),
            ActivityDto(
                id="act:focal",
                type="System.Activities.Statements.WriteLine",
                type_short="WriteLine",
                display_name="Focal",
                parent_id="act:child",
                children=[],
                properties={},
            ),
        ],
        edges=[],
        invocations=[],
    )

    analyzer = ProjectAnalyzer()
    index = analyzer.analyze([workflow])

    view = SliceView(focus="act:focal", radius=2)
    result = view.render(index)

    # Should have parent chain: root -> child
    assert len(result["parent_chain"]) == 2
    assert result["parent_chain"][0]["id"] == "act:root"
    assert result["parent_chain"][1]["id"] == "act:child"


def test_slice_view_with_siblings():
    """Test slice view with sibling activities."""
    workflow = WorkflowDto(
        id="wf:test",
        name="Test",
        source=SourceInfo(path="Test.xaml", hash="test123"),
        arguments=[],
        variables=[],
        activities=[
            ActivityDto(
                id="act:parent",
                type="System.Activities.Statements.Sequence",
                type_short="Sequence",
                display_name="Parent",
                parent_id=None,
                children=["act:focal", "act:sibling1", "act:sibling2"],
                properties={},
            ),
            ActivityDto(
                id="act:focal",
                type="System.Activities.Statements.WriteLine",
                type_short="WriteLine",
                display_name="Focal",
                parent_id="act:parent",
                children=[],
                properties={},
            ),
            ActivityDto(
                id="act:sibling1",
                type="System.Activities.Statements.WriteLine",
                type_short="WriteLine",
                display_name="Sibling 1",
                parent_id="act:parent",
                children=[],
                properties={},
            ),
            ActivityDto(
                id="act:sibling2",
                type="System.Activities.Statements.WriteLine",
                type_short="WriteLine",
                display_name="Sibling 2",
                parent_id="act:parent",
                children=[],
                properties={},
            ),
        ],
        edges=[],
        invocations=[],
    )

    analyzer = ProjectAnalyzer()
    index = analyzer.analyze([workflow])

    view = SliceView(focus="act:focal", radius=2)
    result = view.render(index)

    # Should have 2 siblings
    assert len(result["siblings"]) == 2
    sibling_ids = {s["id"] for s in result["siblings"]}
    assert "act:sibling1" in sibling_ids
    assert "act:sibling2" in sibling_ids
    assert "act:focal" not in sibling_ids  # Focal not in siblings
