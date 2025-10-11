"""Tests for control flow extraction.

Tests:
- Sequence edge extraction (Next edges)
- If activity edge extraction (Then/Else edges)
- Switch activity edge extraction (Case/Default edges)
- FlowDecision edge extraction (True/False edges)
- TryCatch edge extraction (Try/Catch/Finally edges)
- Parallel edge extraction (Branch edges)
- Edge ID stability and determinism
"""

import pytest

from xaml_parser.control_flow import ControlFlowExtractor
from xaml_parser.models import Activity


class TestSequenceEdges:
    """Test extraction of sequential 'Next' edges."""

    def test_extract_sequence_edges(self):
        """Test that Sequence activities produce Next edges."""
        # Create a Sequence with three child activities
        act1_id = "act:sha256:111"
        act2_id = "act:sha256:222"
        act3_id = "act:sha256:333"

        sequence = Activity(
            activity_id="act:sha256:seq",
            workflow_id="wf:sha256:test",
            activity_type="Sequence",
            display_name="Main Sequence",
            node_id="seq",
            child_activities=[act1_id, act2_id, act3_id],
        )

        # Create child activities
        act1 = Activity(
            activity_id=act1_id,
            workflow_id="wf:sha256:test",
            activity_type="Assign",
            node_id="act1",
        )
        act2 = Activity(
            activity_id=act2_id,
            workflow_id="wf:sha256:test",
            activity_type="Log",
            node_id="act2",
        )
        act3 = Activity(
            activity_id=act3_id,
            workflow_id="wf:sha256:test",
            activity_type="Assign",
            node_id="act3",
        )

        activities = [sequence, act1, act2, act3]

        # Extract edges
        extractor = ControlFlowExtractor()
        edges = extractor.extract_edges(activities)

        # Should have 2 Next edges (act1→act2, act2→act3)
        assert len(edges) == 2

        # Check first edge
        assert edges[0].from_id == act1_id
        assert edges[0].to_id == act2_id
        assert edges[0].kind == "Next"

        # Check second edge
        assert edges[1].from_id == act2_id
        assert edges[1].to_id == act3_id
        assert edges[1].kind == "Next"

    def test_empty_sequence_no_edges(self):
        """Test that empty Sequence produces no edges."""
        sequence = Activity(
            activity_id="act:sha256:seq",
            workflow_id="wf:sha256:test",
            activity_type="Sequence",
            node_id="seq",
            child_activities=[],
        )

        extractor = ControlFlowExtractor()
        edges = extractor.extract_edges([sequence])

        assert len(edges) == 0

    def test_single_child_sequence_no_edges(self):
        """Test that Sequence with single child produces no edges."""
        sequence = Activity(
            activity_id="act:sha256:seq",
            workflow_id="wf:sha256:test",
            activity_type="Sequence",
            node_id="seq",
            child_activities=["act:sha256:111"],
        )

        extractor = ControlFlowExtractor()
        edges = extractor.extract_edges([sequence])

        assert len(edges) == 0


class TestIfEdges:
    """Test extraction of If activity Then/Else edges."""

    def test_extract_if_edges(self):
        """Test that If activities produce Then and Else edges."""
        then_id = "act:sha256:then"
        else_id = "act:sha256:else"

        if_activity = Activity(
            activity_id="act:sha256:if",
            workflow_id="wf:sha256:test",
            activity_type="If",
            node_id="if",
            properties={"Condition": "[x > 10]"},
            configuration={"Then": then_id, "Else": else_id},
            child_activities=[then_id, else_id],
        )

        then_act = Activity(
            activity_id=then_id,
            workflow_id="wf:sha256:test",
            activity_type="Assign",
            display_name="Then",
            node_id="then",
        )

        else_act = Activity(
            activity_id=else_id,
            workflow_id="wf:sha256:test",
            activity_type="Log",
            display_name="Else",
            node_id="else",
        )

        activities = [if_activity, then_act, else_act]

        # Extract edges
        extractor = ControlFlowExtractor()
        edges = extractor.extract_edges(activities)

        # Should have Then and Else edges
        assert len(edges) == 2

        # Find Then edge
        then_edge = next((e for e in edges if e.kind == "Then"), None)
        assert then_edge is not None
        assert then_edge.from_id == "act:sha256:if"
        assert then_edge.to_id == then_id
        assert then_edge.condition == "[x > 10]"
        assert then_edge.label == "Then"

        # Find Else edge
        else_edge = next((e for e in edges if e.kind == "Else"), None)
        assert else_edge is not None
        assert else_edge.from_id == "act:sha256:if"
        assert else_edge.to_id == else_id
        assert else_edge.label == "Else"

    def test_if_without_else(self):
        """Test If activity with only Then branch."""
        then_id = "act:sha256:then"

        if_activity = Activity(
            activity_id="act:sha256:if",
            workflow_id="wf:sha256:test",
            activity_type="If",
            node_id="if",
            configuration={"Then": then_id},
            child_activities=[then_id],
        )

        activities = [if_activity]

        extractor = ControlFlowExtractor()
        edges = extractor.extract_edges(activities)

        # Should have only Then edge
        assert len(edges) == 1
        assert edges[0].kind == "Then"


class TestSwitchEdges:
    """Test extraction of Switch activity Case edges."""

    def test_extract_switch_edges(self):
        """Test that Switch activities produce Case edges."""
        case1_id = "act:sha256:case1"
        case2_id = "act:sha256:case2"
        default_id = "act:sha256:default"

        switch_activity = Activity(
            activity_id="act:sha256:switch",
            workflow_id="wf:sha256:test",
            activity_type="Switch",
            node_id="switch",
            properties={"Expression": "[status]"},
            configuration={
                "Cases": {
                    "Active": case1_id,
                    "Inactive": case2_id,
                },
                "Default": default_id,
            },
            child_activities=[case1_id, case2_id, default_id],
        )

        activities = [switch_activity]

        # Extract edges
        extractor = ControlFlowExtractor()
        edges = extractor.extract_edges(activities)

        # Should have 2 Case edges + 1 Default edge
        assert len(edges) == 3

        # Find Case edges
        case_edges = [e for e in edges if e.kind == "Case"]
        assert len(case_edges) == 2

        # Check Active case
        active_edge = next((e for e in case_edges if e.label == "Active"), None)
        assert active_edge is not None
        assert active_edge.to_id == case1_id
        assert "[status] == Active" in active_edge.condition

        # Check Default edge
        default_edge = next((e for e in edges if e.kind == "Default"), None)
        assert default_edge is not None
        assert default_edge.to_id == default_id
        assert default_edge.label == "Default"


class TestFlowDecisionEdges:
    """Test extraction of FlowDecision True/False edges."""

    def test_extract_flow_decision_edges(self):
        """Test that FlowDecision produces True and False edges."""
        true_id = "act:sha256:true"
        false_id = "act:sha256:false"

        flow_decision = Activity(
            activity_id="act:sha256:decision",
            workflow_id="wf:sha256:test",
            activity_type="FlowDecision",
            node_id="decision",
            properties={"Condition": "[count > 0]"},
            configuration={"True": true_id, "False": false_id},
            child_activities=[true_id, false_id],
        )

        activities = [flow_decision]

        # Extract edges
        extractor = ControlFlowExtractor()
        edges = extractor.extract_edges(activities)

        # Should have True and False edges
        assert len(edges) == 2

        # Check True edge
        true_edge = next((e for e in edges if e.kind == "True"), None)
        assert true_edge is not None
        assert true_edge.to_id == true_id
        assert true_edge.condition == "[count > 0]"

        # Check False edge
        false_edge = next((e for e in edges if e.kind == "False"), None)
        assert false_edge is not None
        assert false_edge.to_id == false_id


class TestTryCatchEdges:
    """Test extraction of TryCatch Try/Catch/Finally edges."""

    def test_extract_try_catch_edges(self):
        """Test that TryCatch produces Try/Catch/Finally edges."""
        try_id = "act:sha256:try"
        catch_id = "act:sha256:catch"
        finally_id = "act:sha256:finally"

        try_catch = Activity(
            activity_id="act:sha256:trycatch",
            workflow_id="wf:sha256:test",
            activity_type="TryCatch",
            node_id="trycatch",
            configuration={
                "Try": try_id,
                "Catches": [{"ExceptionType": "System.Exception", "Activity": catch_id}],
                "Finally": finally_id,
            },
            child_activities=[try_id, catch_id, finally_id],
        )

        activities = [try_catch]

        # Extract edges
        extractor = ControlFlowExtractor()
        edges = extractor.extract_edges(activities)

        # Should have Try + Catch + Finally edges
        assert len(edges) == 3

        # Check Try edge
        try_edge = next((e for e in edges if e.kind == "Try"), None)
        assert try_edge is not None
        assert try_edge.to_id == try_id

        # Check Catch edge
        catch_edge = next((e for e in edges if e.kind == "Catch"), None)
        assert catch_edge is not None
        assert catch_edge.to_id == catch_id
        assert "Exception" in catch_edge.label

        # Check Finally edge
        finally_edge = next((e for e in edges if e.kind == "Finally"), None)
        assert finally_edge is not None
        assert finally_edge.to_id == finally_id


class TestParallelEdges:
    """Test extraction of Parallel Branch edges."""

    def test_extract_parallel_edges(self):
        """Test that Parallel activities produce Branch edges."""
        branch1_id = "act:sha256:branch1"
        branch2_id = "act:sha256:branch2"

        parallel = Activity(
            activity_id="act:sha256:parallel",
            workflow_id="wf:sha256:test",
            activity_type="Parallel",
            node_id="parallel",
            child_activities=[branch1_id, branch2_id],
        )

        activities = [parallel]

        # Extract edges
        extractor = ControlFlowExtractor()
        edges = extractor.extract_edges(activities)

        # Should have 2 Branch edges
        assert len(edges) == 2
        assert all(e.kind == "Branch" for e in edges)
        assert edges[0].to_id == branch1_id
        assert edges[1].to_id == branch2_id


class TestEdgeDeterminism:
    """Test edge ID stability and determinism."""

    def test_edge_id_determinism(self):
        """Test that same activities produce same edge IDs."""
        act1_id = "act:sha256:111"
        act2_id = "act:sha256:222"

        sequence = Activity(
            activity_id="act:sha256:seq",
            workflow_id="wf:sha256:test",
            activity_type="Sequence",
            node_id="seq",
            child_activities=[act1_id, act2_id],
        )

        activities = [sequence]

        # Extract edges twice
        extractor1 = ControlFlowExtractor()
        edges1 = extractor1.extract_edges(activities)

        extractor2 = ControlFlowExtractor()
        edges2 = extractor2.extract_edges(activities)

        # Edge IDs should be identical
        assert len(edges1) == len(edges2)
        assert edges1[0].id == edges2[0].id

    def test_different_edges_different_ids(self):
        """Test that different edges produce different IDs."""
        seq1 = Activity(
            activity_id="act:sha256:seq1",
            workflow_id="wf:sha256:test",
            activity_type="Sequence",
            node_id="seq1",
            child_activities=["act:sha256:111", "act:sha256:222"],
        )

        seq2 = Activity(
            activity_id="act:sha256:seq2",
            workflow_id="wf:sha256:test",
            activity_type="Sequence",
            node_id="seq2",
            child_activities=["act:sha256:333", "act:sha256:444"],
        )

        activities = [seq1, seq2]

        extractor = ControlFlowExtractor()
        edges = extractor.extract_edges(activities)

        # Should have 2 edges with different IDs
        assert len(edges) == 2
        assert edges[0].id != edges[1].id


class TestNonControlFlowActivities:
    """Test that non-control-flow activities produce no edges."""

    def test_assign_no_edges(self):
        """Test that Assign activity produces no edges."""
        assign = Activity(
            activity_id="act:sha256:assign",
            workflow_id="wf:sha256:test",
            activity_type="Assign",
            node_id="assign",
        )

        extractor = ControlFlowExtractor()
        edges = extractor.extract_edges([assign])

        assert len(edges) == 0

    def test_log_no_edges(self):
        """Test that Log activity produces no edges."""
        log = Activity(
            activity_id="act:sha256:log",
            workflow_id="wf:sha256:test",
            activity_type="WriteLine",
            node_id="log",
        )

        extractor = ControlFlowExtractor()
        edges = extractor.extract_edges([log])

        assert len(edges) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
