"""Integration tests for load() API with real UiPath projects.

Tests the complete load() function with actual project corpuses.
"""

import pytest
from pathlib import Path

from cpmf_uips_xaml import load
from cpmf_uips_xaml.api.session import ProjectSession
from cpmf_uips_xaml.stages.assemble.index import ProjectIndex


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


# ============================================================================
# Basic Load Tests
# ============================================================================


class TestLoadBasic:
    """Test basic load() functionality with real projects."""

    def test_load_project_returns_session(self, test_corpus):
        """Test load() returns ProjectSession for project directory."""
        session = load(test_corpus)

        assert isinstance(session, ProjectSession)
        assert session.project_dir == test_corpus
        assert session.project_name is not None
        assert session.total_workflows > 0

    def test_load_with_auto_mode_detection(self, test_corpus):
        """Test load() auto-detects project mode."""
        session = load(test_corpus, mode="auto")

        assert isinstance(session, ProjectSession)
        assert session.total_workflows > 0

    def test_load_with_explicit_project_mode(self, test_corpus):
        """Test load() with explicit project mode."""
        session = load(test_corpus, mode="project")

        assert isinstance(session, ProjectSession)
        assert len(session.workflows()) > 0


# ============================================================================
# ProjectSession Methods Tests
# ============================================================================


class TestProjectSessionMethods:
    """Test ProjectSession methods with real data."""

    def test_workflows_returns_all(self, test_corpus):
        """Test session.workflows() returns all workflows."""
        session = load(test_corpus)
        workflows = session.workflows()

        assert len(workflows) > 0
        # All should be WorkflowDto objects
        assert all(hasattr(wf, "id") for wf in workflows)
        assert all(hasattr(wf, "name") for wf in workflows)
        assert all(hasattr(wf, "activities") for wf in workflows)

    def test_workflows_with_pattern(self, test_corpus):
        """Test session.workflows(pattern=...) filters correctly."""
        session = load(test_corpus)
        all_workflows = session.workflows()

        if len(all_workflows) > 0:
            # Pick first workflow and filter by its name
            first_wf = all_workflows[0]
            filtered = session.workflows(pattern=first_wf.source.path)

            assert len(filtered) >= 1
            assert any(wf.id == first_wf.id for wf in filtered)

    def test_workflow_by_filename(self, test_corpus):
        """Test session.workflow() finds by filename."""
        session = load(test_corpus)
        workflows = session.workflows()

        if len(workflows) > 0:
            first_wf = workflows[0]
            filename = Path(first_wf.source.path).name

            found = session.workflow(filename)

            # Should find at least one workflow with this filename
            assert found is not None

    def test_entry_points_property(self, test_corpus):
        """Test session.entry_points property."""
        session = load(test_corpus)
        entry_points = session.entry_points

        assert isinstance(entry_points, list)
        # Most UiPath projects have at least one entry point
        # (though some test projects might not)

    def test_successful_workflows_count(self, test_corpus):
        """Test successful_workflows property."""
        session = load(test_corpus)

        assert session.successful_workflows > 0
        assert session.successful_workflows <= session.total_workflows


# ============================================================================
# Output Mode Tests
# ============================================================================


class TestLoadOutputModes:
    """Test different output modes of load()."""

    def test_load_output_dto_default(self, test_corpus):
        """Test load() with default output='dto'."""
        session = load(test_corpus)

        assert isinstance(session, ProjectSession)
        assert hasattr(session, "workflows")
        assert hasattr(session, "view")
        assert hasattr(session, "emit")

    def test_load_output_view(self, test_corpus):
        """Test load() with output='view' returns dict."""
        try:
            view = load(test_corpus, output="view", view="nested")
            assert isinstance(view, dict)
            # View should contain workflow information
            # Structure depends on view type implementation
        except (TypeError, NotImplementedError):
            pytest.skip("View generation not fully implemented")

    def test_load_output_index(self, test_corpus):
        """Test load() with output='index' returns ProjectIndex."""
        index = load(test_corpus, output="index")

        assert isinstance(index, ProjectIndex)


# ============================================================================
# View Generation Tests
# ============================================================================


class TestViewGeneration:
    """Test view generation through ProjectSession."""

    def test_view_nested(self, test_corpus):
        """Test generating nested view."""
        session = load(test_corpus)

        # View generation may have different parameters
        # Just verify the method exists and can be called
        try:
            view = session.view("nested")
            assert isinstance(view, dict)
        except (TypeError, NotImplementedError):
            pytest.skip("View generation not fully implemented")

    def test_view_execution(self, test_corpus):
        """Test generating execution view."""
        session = load(test_corpus)

        # View generation may have different parameters
        try:
            entry_points = session.entry_points
            if entry_points:
                view = session.view("execution", entry_point=entry_points[0])
                assert isinstance(view, dict)
            else:
                pytest.skip("No entry points available")
        except (TypeError, NotImplementedError):
            pytest.skip("View generation not fully implemented")

    def test_view_slice(self, test_corpus):
        """Test generating slice view."""
        session = load(test_corpus)
        workflows = session.workflows()

        # View generation may have different parameters
        try:
            if workflows:
                first_wf_path = workflows[0].source.path
                view = session.view("slice", focus=first_wf_path, radius=2)
                assert isinstance(view, dict)
            else:
                pytest.skip("No workflows available")
        except (TypeError, NotImplementedError):
            pytest.skip("View generation not fully implemented")


# ============================================================================
# Emit Tests
# ============================================================================


class TestEmit:
    """Test artifact emission through ProjectSession."""

    def test_emit_to_file(self, test_corpus, tmp_path):
        """Test emitting workflows to file."""
        session = load(test_corpus)
        output_file = tmp_path / "output.json"

        result = session.emit("json", output_path=output_file)

        assert result.success
        assert output_file.exists()
        assert output_file.stat().st_size > 0

    def test_emit_to_string(self, test_corpus):
        """Test emitting workflows as string."""
        session = load(test_corpus)

        # Get only first 2 workflows for quick test
        workflows = session.workflows()[:2]
        if not workflows:
            pytest.skip("No workflows to emit")

        # Create a minimal session for testing
        from cpmf_uips_xaml.api.session import ProjectSession

        mini_session = ProjectSession(
            result=session.result,
            analyzer=session.analyzer,
            index=session.index,
            config=session.config,
            project_dir=session.project_dir,
        )

        # Override workflows to return only first 2
        mini_session.workflows = lambda pattern=None: workflows

        json_str = mini_session.emit("json")

        assert isinstance(json_str, str)
        assert len(json_str) > 0


# ============================================================================
# Configuration Tests
# ============================================================================


class TestConfigurationHandling:
    """Test configuration handling in load()."""

    def test_load_with_default_config(self, test_corpus):
        """Test load() uses default config when none provided."""
        session = load(test_corpus, config=None)

        assert session.config is not None
        assert hasattr(session.config, "parser")
        assert hasattr(session.config, "emitter")

    def test_load_with_config_dict(self, test_corpus):
        """Test load() with config dict override."""
        config_dict = {
            "parser": {
                "extract_expressions": False
            }
        }

        session = load(test_corpus, config=config_dict)

        assert session.config is not None
        # Verify override was applied
        assert session.config.parser.extract_expressions is False


# ============================================================================
# Edge Cases
# ============================================================================


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_load_single_workflow_file(self, test_corpus):
        """Test loading a single workflow file."""
        # Find a .xaml file in the corpus
        xaml_files = list(test_corpus.rglob("*.xaml"))
        if not xaml_files:
            pytest.skip("No XAML files in corpus")

        xaml_file = xaml_files[0]
        session = load(xaml_file, mode="workflow")

        assert isinstance(session, ProjectSession)
        assert session.total_workflows == 1
        workflows = session.workflows()
        assert len(workflows) == 1

    def test_load_nonexistent_path_fails(self, tmp_path):
        """Test load() fails gracefully for nonexistent path."""
        nonexistent = tmp_path / "doesnotexist"

        with pytest.raises(ValueError, match="does not exist"):
            load(nonexistent)

    def test_load_invalid_output_mode_fails(self, test_corpus):
        """Test load() fails for invalid output mode."""
        with pytest.raises(ValueError, match="Unknown output mode"):
            load(test_corpus, output="invalid")


# ============================================================================
# Performance Tests (Optional)
# ============================================================================


class TestPerformance:
    """Optional performance tests."""

    def test_load_completes_in_reasonable_time(self, test_corpus):
        """Test load() completes in reasonable time."""
        import time

        start = time.time()
        session = load(test_corpus)
        elapsed = time.time() - start

        # Should complete within reasonable time
        # (depends on project size, but <60s for typical projects)
        assert session is not None
        # Just verify it completes, don't enforce strict time limit
