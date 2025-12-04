"""Tests for deterministic ordering utilities.

Tests:
- sort_by_id() with various ID formats
- sort_by_name() with string sorting
- sort_dict_by_key() with dictionary sorting
- sort_edges() with composite keys
- ensure_deterministic_order() for complete WorkflowDto
- verify_deterministic_order() for validation
- Locale independence (same results regardless of system locale)
"""

import pytest

from cpmf_xaml_parser.dto import (
    ActivityDto,
    ArgumentDto,
    EdgeDto,
    VariableDto,
    WorkflowDto,
)
from cpmf_xaml_parser.ordering import (
    ensure_deterministic_order,
    sort_by_id,
    sort_by_key,
    sort_by_name,
    sort_dict_by_key,
    sort_edges,
    verify_deterministic_order,
)


class TestSortById:
    """Test sort_by_id() function."""

    def test_sort_activities_by_id(self):
        """Test sorting activities by stable ID."""
        activities = [
            ActivityDto(id="act:sha256:def456", type="Sequence", type_short="Sequence"),
            ActivityDto(id="act:sha256:abc123", type="Assign", type_short="Assign"),
            ActivityDto(id="act:sha256:789ghi", type="If", type_short="If"),
        ]

        sorted_acts = sort_by_id(activities)

        assert sorted_acts[0].id == "act:sha256:789ghi"
        assert sorted_acts[1].id == "act:sha256:abc123"
        assert sorted_acts[2].id == "act:sha256:def456"

    def test_sort_empty_list(self):
        """Test sorting empty list."""
        result = sort_by_id([])
        assert result == []

    def test_sort_single_item(self):
        """Test sorting single item."""
        activities = [ActivityDto(id="act:sha256:abc123", type="Assign", type_short="Assign")]
        result = sort_by_id(activities)
        assert len(result) == 1
        assert result[0].id == "act:sha256:abc123"

    def test_sort_does_not_modify_input(self):
        """Test that sorting creates new list without modifying input."""
        activities = [
            ActivityDto(id="act:sha256:zzz", type="Sequence", type_short="Sequence"),
            ActivityDto(id="act:sha256:aaa", type="Assign", type_short="Assign"),
        ]
        original_order = [a.id for a in activities]

        sorted_acts = sort_by_id(activities)

        # Input list unchanged
        assert [a.id for a in activities] == original_order
        # Output list sorted
        assert sorted_acts[0].id == "act:sha256:aaa"


class TestSortByName:
    """Test sort_by_name() function."""

    def test_sort_arguments_by_name(self):
        """Test sorting arguments by name."""
        args = [
            ArgumentDto(id="arg1", name="out_Result", type="String", direction="Out"),
            ArgumentDto(id="arg2", name="in_FilePath", type="String", direction="In"),
            ArgumentDto(id="arg3", name="in_Config", type="Config", direction="In"),
        ]

        sorted_args = sort_by_name(args)

        assert sorted_args[0].name == "in_Config"
        assert sorted_args[1].name == "in_FilePath"
        assert sorted_args[2].name == "out_Result"

    def test_sort_variables_by_name(self):
        """Test sorting variables by name."""
        vars = [
            VariableDto(id="var1", name="varOutput", type="String"),
            VariableDto(id="var2", name="varInput", type="String"),
            VariableDto(id="var3", name="varConfig", type="Config"),
        ]

        sorted_vars = sort_by_name(vars)

        assert sorted_vars[0].name == "varConfig"
        assert sorted_vars[1].name == "varInput"
        assert sorted_vars[2].name == "varOutput"

    def test_case_sensitive_sorting(self):
        """Test that sorting is case-sensitive (uppercase before lowercase)."""
        items = [
            ArgumentDto(id="1", name="zTest", type="String", direction="In"),
            ArgumentDto(id="2", name="Test", type="String", direction="In"),
            ArgumentDto(id="3", name="aTest", type="String", direction="In"),
        ]

        sorted_items = sort_by_name(items)

        # Capital letters come before lowercase in ASCII/UTF-8
        assert sorted_items[0].name == "Test"
        assert sorted_items[1].name == "aTest"
        assert sorted_items[2].name == "zTest"


class TestSortDictByKey:
    """Test sort_dict_by_key() function."""

    def test_sort_properties_dict(self):
        """Test sorting property dictionary."""
        props = {"Value": "[expr]", "DisplayName": "Test", "To": "[var]"}

        sorted_props = sort_dict_by_key(props)

        keys = list(sorted_props.keys())
        assert keys == ["DisplayName", "To", "Value"]

    def test_sort_empty_dict(self):
        """Test sorting empty dictionary."""
        result = sort_dict_by_key({})
        assert result == {}

    def test_sort_preserves_values(self):
        """Test that sorting preserves all values."""
        props = {"c": 3, "a": 1, "b": 2}

        sorted_props = sort_dict_by_key(props)

        assert sorted_props == {"a": 1, "b": 2, "c": 3}


class TestSortEdges:
    """Test sort_edges() function."""

    def test_sort_edges_by_composite_key(self):
        """Test sorting edges by (from_id, to_id, kind)."""
        edges = [
            EdgeDto(
                id="edge3",
                from_id="act:sha256:bbb",
                to_id="act:sha256:ccc",
                kind="Then",
            ),
            EdgeDto(
                id="edge1",
                from_id="act:sha256:aaa",
                to_id="act:sha256:bbb",
                kind="Next",
            ),
            EdgeDto(
                id="edge2",
                from_id="act:sha256:aaa",
                to_id="act:sha256:ccc",
                kind="Else",
            ),
        ]

        sorted_edges = sort_edges(edges)

        # First by from_id, then to_id, then kind
        assert sorted_edges[0].id == "edge1"  # aaa -> bbb (Next)
        assert sorted_edges[1].id == "edge2"  # aaa -> ccc (Else)
        assert sorted_edges[2].id == "edge3"  # bbb -> ccc (Then)

    def test_sort_edges_kind_matters(self):
        """Test that edge kind affects sorting."""
        edges = [
            EdgeDto(
                id="edge1",
                from_id="act:sha256:aaa",
                to_id="act:sha256:bbb",
                kind="Then",
            ),
            EdgeDto(
                id="edge2",
                from_id="act:sha256:aaa",
                to_id="act:sha256:bbb",
                kind="Else",
            ),
        ]

        sorted_edges = sort_edges(edges)

        # "Else" comes before "Then" alphabetically
        assert sorted_edges[0].kind == "Else"
        assert sorted_edges[1].kind == "Then"


class TestSortByKey:
    """Test sort_by_key() with custom key functions."""

    def test_sort_with_custom_key(self):
        """Test sorting with custom key extraction."""
        items = [
            ArgumentDto(id="3", name="c", type="String", direction="In"),
            ArgumentDto(id="1", name="a", type="String", direction="In"),
            ArgumentDto(id="2", name="b", type="String", direction="In"),
        ]

        # Sort by id (as string)
        sorted_items = sort_by_key(items, lambda item: item.id)

        assert sorted_items[0].id == "1"
        assert sorted_items[1].id == "2"
        assert sorted_items[2].id == "3"


class TestEnsureDeterministicOrder:
    """Test ensure_deterministic_order() for complete WorkflowDto."""

    def test_sorts_all_collections(self):
        """Test that all collections are sorted deterministically."""
        # Create workflow with unsorted collections
        workflow = WorkflowDto(
            id="wf:sha256:test",
            name="Test",
            activities=[
                ActivityDto(id="act:sha256:zzz", type="Sequence", type_short="Sequence"),
                ActivityDto(id="act:sha256:aaa", type="Assign", type_short="Assign"),
            ],
            arguments=[
                ArgumentDto(id="arg1", name="out_Result", type="String", direction="Out"),
                ArgumentDto(id="arg2", name="in_Config", type="String", direction="In"),
            ],
            variables=[
                VariableDto(id="var1", name="varZ", type="String"),
                VariableDto(id="var2", name="varA", type="String"),
            ],
            edges=[
                EdgeDto(
                    id="edge2",
                    from_id="act:sha256:zzz",
                    to_id="act:sha256:aaa",
                    kind="Next",
                ),
                EdgeDto(
                    id="edge1",
                    from_id="act:sha256:aaa",
                    to_id="act:sha256:zzz",
                    kind="Next",
                ),
            ],
        )

        # Sort in-place
        ensure_deterministic_order(workflow)

        # Check all sorted
        assert workflow.activities[0].id == "act:sha256:aaa"
        assert workflow.activities[1].id == "act:sha256:zzz"
        assert workflow.arguments[0].name == "in_Config"
        assert workflow.arguments[1].name == "out_Result"
        assert workflow.variables[0].name == "varA"
        assert workflow.variables[1].name == "varZ"
        assert workflow.edges[0].from_id == "act:sha256:aaa"

    def test_sorts_activity_properties(self):
        """Test that properties within activities are sorted."""
        workflow = WorkflowDto(
            id="wf:sha256:test",
            name="Test",
            activities=[
                ActivityDto(
                    id="act:sha256:aaa",
                    type="Assign",
                    type_short="Assign",
                    properties={"Value": "x", "DisplayName": "Test", "To": "y"},
                    expressions=["expr2", "expr1"],
                    variables_referenced=["varB", "varA"],
                )
            ],
        )

        ensure_deterministic_order(workflow)

        # Check properties sorted
        props_keys = list(workflow.activities[0].properties.keys())
        assert props_keys == ["DisplayName", "To", "Value"]

        # Check lists sorted
        assert workflow.activities[0].expressions == ["expr1", "expr2"]
        assert workflow.activities[0].variables_referenced == ["varA", "varB"]

    def test_handles_none_collections(self):
        """Test that None collections are handled gracefully."""
        workflow = WorkflowDto(id="wf:sha256:test", name="Test")

        # Should not raise exception
        ensure_deterministic_order(workflow)

    def test_handles_empty_collections(self):
        """Test that empty collections are handled."""
        workflow = WorkflowDto(
            id="wf:sha256:test",
            name="Test",
            activities=[],
            arguments=[],
            variables=[],
        )

        # Should not raise exception
        ensure_deterministic_order(workflow)


class TestVerifyDeterministicOrder:
    """Test verify_deterministic_order() validation."""

    def test_detects_unsorted_activities(self):
        """Test detection of unsorted activities."""
        workflow = WorkflowDto(
            id="wf:sha256:test",
            name="Test",
            activities=[
                ActivityDto(id="act:sha256:zzz", type="Sequence", type_short="Sequence"),
                ActivityDto(id="act:sha256:aaa", type="Assign", type_short="Assign"),
            ],
        )

        warnings = verify_deterministic_order(workflow)

        assert len(warnings) > 0
        assert any("Activities" in w for w in warnings)

    def test_detects_unsorted_arguments(self):
        """Test detection of unsorted arguments."""
        workflow = WorkflowDto(
            id="wf:sha256:test",
            name="Test",
            arguments=[
                ArgumentDto(id="arg1", name="zArg", type="String", direction="In"),
                ArgumentDto(id="arg2", name="aArg", type="String", direction="In"),
            ],
        )

        warnings = verify_deterministic_order(workflow)

        assert len(warnings) > 0
        assert any("Arguments" in w for w in warnings)

    def test_passes_for_sorted_workflow(self):
        """Test that sorted workflow passes validation."""
        workflow = WorkflowDto(
            id="wf:sha256:test",
            name="Test",
            activities=[
                ActivityDto(id="act:sha256:aaa", type="Assign", type_short="Assign"),
                ActivityDto(id="act:sha256:zzz", type="Sequence", type_short="Sequence"),
            ],
            arguments=[
                ArgumentDto(id="arg1", name="aArg", type="String", direction="In"),
                ArgumentDto(id="arg2", name="zArg", type="String", direction="In"),
            ],
        )

        warnings = verify_deterministic_order(workflow)

        assert len(warnings) == 0


class TestLocaleIndependence:
    """Test that sorting is locale-independent."""

    def test_binary_collation(self):
        """Test that sorting uses binary collation (UTF-8 byte order).

        This ensures results are identical regardless of system locale.
        """
        # Mix of ASCII and special characters
        names = ["Übergang", "Test", "übergang", "test", "Ñoño", "noño"]
        items = [
            ArgumentDto(id=str(i), name=n, type="String", direction="In")
            for i, n in enumerate(names)
        ]

        sorted_items = sort_by_name(items)
        sorted_names = [item.name for item in sorted_items]

        # Binary UTF-8 collation:
        # Capital letters < lowercase letters < non-ASCII
        # Verify at least that sorting is deterministic
        assert len(sorted_names) == len(names)
        assert sorted(sorted_names) == sorted_names  # Should be already sorted


class TestDeterminismAcrossRuns:
    """Test that sorting produces identical results across multiple runs."""

    def test_sort_stability_100_runs(self):
        """Test that sorting is stable across 100 runs."""
        activities = [
            ActivityDto(id=f"act:sha256:{i:03d}", type="Test", type_short="Test")
            for i in range(100, 0, -1)  # Reverse order
        ]

        # Sort 100 times
        results = [sort_by_id(activities) for _ in range(100)]

        # All results should be identical
        first_result_ids = [a.id for a in results[0]]
        for result in results[1:]:
            assert [a.id for a in result] == first_result_ids


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
