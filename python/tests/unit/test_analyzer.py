"""Tests for analyzer module."""

from pathlib import Path

from cpmf_xaml_parser.analyzer import ProjectAnalyzer
from cpmf_xaml_parser.dto import ActivityDto, EdgeDto, InvocationDto, SourceInfo, WorkflowDto


def test_analyze_empty():
    """Test analyzing empty workflow list."""
    analyzer = ProjectAnalyzer()
    index = analyzer.analyze([], None)

    assert index.total_workflows == 0
    assert index.total_activities == 0
    assert index.workflows.node_count() == 0
    assert index.activities.node_count() == 0


def test_analyze_single_workflow():
    """Test analyzing single workflow."""
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
                properties={},
            )
        ],
        edges=[],
        invocations=[],
    )

    analyzer = ProjectAnalyzer()
    index = analyzer.analyze([workflow], Path("."))

    assert index.total_workflows == 1
    assert index.total_activities == 1
    assert index.workflows.has_node("wf:test")
    assert index.activities.has_node("act:1")
    assert index.get_workflow("wf:test") == workflow
    assert index.get_activity("act:1") == workflow.activities[0]


def test_analyze_workflow_with_hierarchy():
    """Test analyzing workflow with activity hierarchy."""
    workflow = WorkflowDto(
        id="wf:test",
        name="TestWorkflow",
        source=SourceInfo(path="Test.xaml", hash="abc123"),
        arguments=[],
        variables=[],
        activities=[
            ActivityDto(
                id="act:parent",
                type="System.Activities.Statements.Sequence",
                type_short="Sequence",
                display_name="Sequence",
                parent_id=None,
                children=["act:child1", "act:child2"],
                properties={},
            ),
            ActivityDto(
                id="act:child1",
                type="System.Activities.Statements.WriteLine",
                type_short="WriteLine",
                display_name="Write 1",
                parent_id="act:parent",
                children=[],
                properties={},
            ),
            ActivityDto(
                id="act:child2",
                type="System.Activities.Statements.WriteLine",
                type_short="WriteLine",
                display_name="Write 2",
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

    # Check activity hierarchy
    assert index.activities.has_edge("act:parent", "act:child1")
    assert index.activities.has_edge("act:parent", "act:child2")
    assert index.activities.successors("act:parent") == ["act:child1", "act:child2"]
    assert index.activities.predecessors("act:child1") == ["act:parent"]


def test_analyze_workflow_invocations():
    """Test analyzing workflow invocations (call graph)."""
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
        activities=[],
        edges=[],
        invocations=[],
    )

    analyzer = ProjectAnalyzer()
    index = analyzer.analyze([main_workflow, helper_workflow])

    # Check call graph
    assert index.call_graph.has_edge("wf:main", "wf:helper")
    assert index.call_graph.successors("wf:main") == ["wf:helper"]
    assert index.call_graph.predecessors("wf:helper") == ["wf:main"]


def test_analyze_control_flow():
    """Test analyzing control flow edges."""
    workflow = WorkflowDto(
        id="wf:test",
        name="TestWorkflow",
        source=SourceInfo(path="Test.xaml", hash="abc123"),
        arguments=[],
        variables=[],
        activities=[
            ActivityDto(
                id="act:1",
                type="System.Activities.Statements.If",
                type_short="If",
                display_name="If",
                parent_id=None,
                children=[],
                properties={},
            ),
            ActivityDto(
                id="act:2",
                type="System.Activities.Statements.WriteLine",
                type_short="WriteLine",
                display_name="Then",
                parent_id=None,
                children=[],
                properties={},
            ),
            ActivityDto(
                id="act:3",
                type="System.Activities.Statements.WriteLine",
                type_short="WriteLine",
                display_name="Else",
                parent_id=None,
                children=[],
                properties={},
            ),
        ],
        edges=[
            EdgeDto(
                id="edge:1",
                from_id="act:1",
                to_id="act:2",
                kind="Then",
            ),
            EdgeDto(
                id="edge:2",
                from_id="act:1",
                to_id="act:3",
                kind="Else",
            ),
        ],
        invocations=[],
    )

    analyzer = ProjectAnalyzer()
    index = analyzer.analyze([workflow])

    # Check control flow graph
    assert index.control_flow.has_edge("act:1", "act:2")
    assert index.control_flow.has_edge("act:1", "act:3")


def test_workflow_by_path_lookup():
    """Test workflow by path lookup."""
    workflow = WorkflowDto(
        id="wf:test",
        name="TestWorkflow",
        source=SourceInfo(path="subfolder/Test.xaml", hash="abc123"),
        arguments=[],
        variables=[],
        activities=[],
        edges=[],
        invocations=[],
    )

    analyzer = ProjectAnalyzer()
    index = analyzer.analyze([workflow])

    assert index.workflow_by_path["subfolder/Test.xaml"] == "wf:test"


def test_activity_to_workflow_lookup():
    """Test activity to workflow lookup."""
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
    index = analyzer.analyze([workflow])

    assert index.activity_to_workflow["act:1"] == "wf:test"
    assert index.get_workflow_for_activity("act:1") == workflow


def test_slice_context():
    """Test context slicing around focal activity."""
    workflow = WorkflowDto(
        id="wf:test",
        name="TestWorkflow",
        source=SourceInfo(path="Test.xaml", hash="abc123"),
        arguments=[],
        variables=[],
        activities=[
            ActivityDto(
                id="act:root",
                type="System.Activities.Statements.Sequence",
                type_short="Sequence",
                display_name="Root",
                parent_id=None,
                children=["act:child1"],
                properties={},
            ),
            ActivityDto(
                id="act:child1",
                type="System.Activities.Statements.Sequence",
                type_short="Sequence",
                display_name="Child 1",
                parent_id="act:root",
                children=["act:grandchild"],
                properties={},
            ),
            ActivityDto(
                id="act:grandchild",
                type="System.Activities.Statements.WriteLine",
                type_short="WriteLine",
                display_name="Grandchild",
                parent_id="act:child1",
                children=[],
                properties={},
            ),
        ],
        edges=[],
        invocations=[],
    )

    analyzer = ProjectAnalyzer()
    index = analyzer.analyze([workflow])

    # Slice with radius=1 from grandchild
    context = index.slice_context("act:grandchild", radius=1)

    assert "act:grandchild" in context
    assert "act:child1" in context  # Parent (1 level up)
    assert "act:root" not in context  # Too far (2 levels up)


def test_find_call_cycles():
    """Test call cycle detection."""
    wf1 = WorkflowDto(
        id="wf:1",
        name="WF1",
        source=SourceInfo(path="WF1.xaml", hash="1"),
        arguments=[],
        variables=[],
        activities=[],
        edges=[],
        invocations=[
            InvocationDto(
                callee_id="wf:2",
                callee_path="WF2.xaml",
                via_activity_id="act:inv1",
            )
        ],
    )

    wf2 = WorkflowDto(
        id="wf:2",
        name="WF2",
        source=SourceInfo(path="WF2.xaml", hash="2"),
        arguments=[],
        variables=[],
        activities=[],
        edges=[],
        invocations=[
            InvocationDto(
                callee_id="wf:1",
                callee_path="WF1.xaml",
                via_activity_id="act:inv2",
            )
        ],
    )

    analyzer = ProjectAnalyzer()
    index = analyzer.analyze([wf1, wf2])

    cycles = index.find_call_cycles()
    assert len(cycles) > 0
    assert "wf:1" in cycles[0]
    assert "wf:2" in cycles[0]


def test_get_execution_order():
    """Test topological sort for execution order."""
    wf1 = WorkflowDto(
        id="wf:1",
        name="Main",
        source=SourceInfo(path="Main.xaml", hash="1"),
        arguments=[],
        variables=[],
        activities=[],
        edges=[],
        invocations=[
            InvocationDto(
                callee_id="wf:2",
                callee_path="Helper.xaml",
                via_activity_id="act:inv",
            )
        ],
    )

    wf2 = WorkflowDto(
        id="wf:2",
        name="Helper",
        source=SourceInfo(path="Helper.xaml", hash="2"),
        arguments=[],
        variables=[],
        activities=[],
        edges=[],
        invocations=[],
    )

    analyzer = ProjectAnalyzer()
    index = analyzer.analyze([wf1, wf2])

    order = index.get_execution_order()
    assert len(order) == 2
    # Main should come before Helper (Main calls Helper, so Main has no dependencies)
    assert order.index("wf:1") < order.index("wf:2")
