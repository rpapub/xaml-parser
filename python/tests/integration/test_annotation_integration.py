"""Integration tests for annotation parsing in real workflows."""

import pytest
from pathlib import Path

from cpmf_uips_xaml import load


@pytest.fixture
def test_corpus():
    """Test corpus with annotations."""
    return Path("/mnt/d/github.com/rpapub/rpax-corpuses/c25v001_CORE_00000011/")


class TestAnnotationIntegration:
    """Test annotation parsing with real UiPath projects."""

    def test_parse_workflow_annotations(self, test_corpus):
        """Test parsing workflow-level annotations."""
        if not test_corpus.exists():
            pytest.skip("Test corpus not available")

        session = load(test_corpus)

        # Check for workflows with annotations
        workflows_with_annotations = [
            wf
            for wf in session.workflows()
            if wf.metadata.annotation_block is not None
        ]

        if workflows_with_annotations:
            wf = workflows_with_annotations[0]
            block = wf.metadata.annotation_block

            # Verify structured parsing
            assert block.raw is not None
            assert isinstance(block.tags, list)

            # Check helper methods work
            assert isinstance(block.is_ignored, bool)
            assert isinstance(block.is_public_api, bool)
            assert isinstance(block.is_test, bool)
            assert isinstance(block.is_unit, bool)
            assert isinstance(block.is_module, bool)
            assert isinstance(block.is_pathkeeper, bool)

    def test_parse_activity_annotations(self, test_corpus):
        """Test parsing activity-level annotations."""
        if not test_corpus.exists():
            pytest.skip("Test corpus not available")

        session = load(test_corpus)

        for wf in session.workflows():
            activities_with_annotations = [
                act for act in wf.activities if act.annotation_block is not None
            ]

            if activities_with_annotations:
                act = activities_with_annotations[0]
                block = act.annotation_block

                # Verify backward compatibility
                assert act.annotation is not None
                assert act.annotation == block.raw

                # Verify structured tags
                assert isinstance(block.tags, list)
                break

    def test_parse_argument_annotations(self, test_corpus):
        """Test parsing argument-level annotations."""
        if not test_corpus.exists():
            pytest.skip("Test corpus not available")

        session = load(test_corpus)

        for wf in session.workflows():
            arguments_with_annotations = [
                arg for arg in wf.arguments if arg.annotation_block is not None
            ]

            if arguments_with_annotations:
                arg = arguments_with_annotations[0]
                block = arg.annotation_block

                # Verify backward compatibility
                assert arg.annotation is not None
                assert arg.annotation == block.raw

                # Verify structured tags
                assert isinstance(block.tags, list)
                break

    def test_module_grouping(self, test_corpus):
        """Test grouping workflows by @module tag."""
        if not test_corpus.exists():
            pytest.skip("Test corpus not available")

        session = load(test_corpus)
        modules = session.modules()

        # Should have at least _uncategorized
        assert "_uncategorized" in modules or len(modules) > 0

        # All values should be lists of WorkflowDto
        for module_name, workflows in modules.items():
            assert isinstance(workflows, list)
            assert isinstance(module_name, str)

    def test_filter_by_tag(self, test_corpus):
        """Test filtering workflows by tag."""
        if not test_corpus.exists():
            pytest.skip("Test corpus not available")

        session = load(test_corpus)

        # Test various tag filters
        public_workflows = session.workflows_with_tag("public")
        test_workflows = session.workflows_with_tag("test")
        unit_workflows = session.workflows_with_tag("unit")
        module_workflows = session.workflows_with_tag("module")
        pathkeeper_workflows = session.workflows_with_tag("pathkeeper")

        # Results should be lists (may be empty)
        assert isinstance(public_workflows, list)
        assert isinstance(test_workflows, list)
        assert isinstance(unit_workflows, list)
        assert isinstance(module_workflows, list)
        assert isinstance(pathkeeper_workflows, list)

    def test_annotation_query(self, test_corpus):
        """Test annotation query API."""
        if not test_corpus.exists():
            pytest.skip("Test corpus not available")

        session = load(test_corpus)

        # Get all annotations
        all_annotations = session.annotations()
        assert isinstance(all_annotations, dict)

        # Get specific tags
        author_annotations = session.annotations(tag="author")
        assert isinstance(author_annotations, dict)

        unit_annotations = session.annotations(tag="unit")
        assert isinstance(unit_annotations, dict)

        module_annotations = session.annotations(tag="module")
        assert isinstance(module_annotations, dict)

        pathkeeper_annotations = session.annotations(tag="pathkeeper")
        assert isinstance(pathkeeper_annotations, dict)

    def test_annotation_workflow_filtering(self, test_corpus):
        """Test filtering workflows with specific annotation combinations."""
        if not test_corpus.exists():
            pytest.skip("Test corpus not available")

        session = load(test_corpus)

        # Find workflows with unit tag
        unit_workflows = session.workflows_with_tag("unit")
        if unit_workflows:
            # Verify they have annotation_block
            for wf in unit_workflows:
                assert wf.metadata.annotation_block is not None
                assert wf.metadata.annotation_block.is_unit

        # Find workflows with pathkeeper tag
        pathkeeper_workflows = session.workflows_with_tag("pathkeeper")
        if pathkeeper_workflows:
            for wf in pathkeeper_workflows:
                assert wf.metadata.annotation_block is not None
                assert wf.metadata.annotation_block.is_pathkeeper

    def test_backward_compatibility(self, test_corpus):
        """Test that raw annotation field still works alongside annotation_block."""
        if not test_corpus.exists():
            pytest.skip("Test corpus not available")

        session = load(test_corpus)

        for wf in session.workflows():
            # If annotation_block exists, raw annotation should also exist and match
            if wf.metadata.annotation_block:
                assert wf.metadata.annotation is not None
                assert wf.metadata.annotation == wf.metadata.annotation_block.raw

            # Check activities
            for act in wf.activities:
                if act.annotation_block:
                    assert act.annotation is not None
                    assert act.annotation == act.annotation_block.raw

            # Check arguments
            for arg in wf.arguments:
                if arg.annotation_block:
                    assert arg.annotation is not None
                    assert arg.annotation == arg.annotation_block.raw

    def test_emit_json_with_annotations(self, test_corpus, tmp_path):
        """Test that JSON emission includes annotation_block."""
        if not test_corpus.exists():
            pytest.skip("Test corpus not available")

        session = load(test_corpus)

        # Emit to JSON
        import json

        json_output = session.emit("json", field_profile="mcp")
        data = json.loads(json_output)

        # Check that workflows can have annotation_block
        if "workflows" in data:
            for wf_data in data["workflows"]:
                if "metadata" in wf_data and "annotation_block" in wf_data["metadata"]:
                    block = wf_data["metadata"]["annotation_block"]
                    assert "raw" in block
                    assert "tags" in block
                    assert isinstance(block["tags"], list)

    def test_field_profile_minimal_excludes_annotation_block(self, test_corpus):
        """Test that minimal profile excludes annotation_block."""
        if not test_corpus.exists():
            pytest.skip("Test corpus not available")

        session = load(test_corpus)

        # Emit with minimal profile
        import json

        json_output = session.emit("json", field_profile="minimal")
        data = json.loads(json_output)

        # Check that annotation_block is not in minimal output
        if "workflows" in data:
            for wf_data in data["workflows"]:
                # Metadata might not be in minimal profile at all
                if "metadata" in wf_data:
                    # annotation_block should not be included
                    assert "annotation_block" not in wf_data["metadata"]

                # Activities in minimal profile should not have annotation_block
                if "activities" in wf_data:
                    for act_data in wf_data["activities"]:
                        assert "annotation_block" not in act_data

    def test_field_profile_mcp_includes_annotation_block(self, test_corpus):
        """Test that mcp profile includes annotation_block."""
        if not test_corpus.exists():
            pytest.skip("Test corpus not available")

        session = load(test_corpus)

        # Emit with mcp profile
        import json

        json_output = session.emit("json", field_profile="mcp")
        data = json.loads(json_output)

        # Check that workflows with annotations include annotation_block in mcp profile
        if "workflows" in data:
            for wf_data in data["workflows"]:
                if "metadata" in wf_data:
                    # If there's an annotation, annotation_block should be present
                    if wf_data["metadata"].get("annotation"):
                        # In mcp profile, annotation_block should be included if it exists
                        # (it may be None if no annotation exists)
                        assert (
                            "annotation_block" in wf_data["metadata"]
                        ), f"annotation_block missing from workflow {wf_data.get('name')}"
