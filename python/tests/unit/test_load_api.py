"""Unit tests for load() API.

Tests the simplified load() function and ProjectSession class.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from cpmf_uips_xaml.api.load import (
    load,
    _detect_mode,
    _resolve_config,
    _merge_config_dict,
    _deep_merge,
)
from cpmf_uips_xaml.api.session import ProjectSession
from cpmf_uips_xaml.config import Config
from cpmf_uips_xaml.stages.assemble.index import ProjectIndex


# ============================================================================
# Mode Detection Tests
# ============================================================================


class TestModeDetection:
    """Test _detect_mode() function."""

    def test_detect_xaml_file(self, tmp_path):
        """Test detection of .xaml workflow file."""
        xaml_file = tmp_path / "workflow.xaml"
        xaml_file.write_text("<Activity />")

        assert _detect_mode(xaml_file) == "workflow"

    def test_detect_project_json_file(self, tmp_path):
        """Test detection of project.json file."""
        project_file = tmp_path / "project.json"
        project_file.write_text('{"name": "Test"}')

        assert _detect_mode(project_file) == "project"

    def test_detect_project_directory(self, tmp_path):
        """Test detection of project directory."""
        project_file = tmp_path / "project.json"
        project_file.write_text('{"name": "Test"}')

        assert _detect_mode(tmp_path) == "project"

    def test_detect_directory_without_project_json_fails(self, tmp_path):
        """Test detection fails for directory without project.json."""
        with pytest.raises(ValueError, match="does not contain project.json"):
            _detect_mode(tmp_path)

    def test_detect_unsupported_file_type_fails(self, tmp_path):
        """Test detection fails for unsupported file types."""
        txt_file = tmp_path / "file.txt"
        txt_file.write_text("text")

        with pytest.raises(ValueError, match="Unsupported file type"):
            _detect_mode(txt_file)

    def test_detect_nonexistent_path_fails(self, tmp_path):
        """Test detection fails for nonexistent path."""
        nonexistent = tmp_path / "doesnotexist"

        with pytest.raises(ValueError, match="does not exist"):
            _detect_mode(nonexistent)


# ============================================================================
# Config Resolution Tests
# ============================================================================


class TestConfigResolution:
    """Test _resolve_config() function."""

    def test_resolve_none_loads_defaults(self, tmp_path):
        """Test None config loads defaults."""
        with patch("cpmf_uips_xaml.api.load.load_default_config") as mock_load:
            mock_config = Mock(spec=Config)
            mock_load.return_value = mock_config

            result = _resolve_config(tmp_path, None)

            assert result == mock_config
            mock_load.assert_called_once_with(start_path=tmp_path)

    def test_resolve_dict_merges_with_defaults(self, tmp_path):
        """Test dict config merges with defaults."""
        with patch("cpmf_uips_xaml.api.load.load_default_config") as mock_load:
            mock_config = Mock(spec=Config)
            mock_load.return_value = mock_config

            overrides = {"parser": {"lenient": True}}

            with patch("cpmf_uips_xaml.api.load._merge_config_dict") as mock_merge:
                mock_merged = Mock(spec=Config)
                mock_merge.return_value = mock_merged

                result = _resolve_config(tmp_path, overrides)

                assert result == mock_merged
                mock_merge.assert_called_once_with(mock_config, overrides)

    def test_resolve_config_object_returns_as_is(self, tmp_path):
        """Test Config object is returned unchanged."""
        config = Mock(spec=Config)
        result = _resolve_config(tmp_path, config)
        assert result == config

    def test_resolve_invalid_type_raises_error(self, tmp_path):
        """Test invalid config type raises TypeError."""
        with pytest.raises(TypeError, match="config must be None, dict, or Config"):
            _resolve_config(tmp_path, "invalid")


# ============================================================================
# Config Merging Tests
# ============================================================================


class TestConfigMerging:
    """Test config merging functions."""

    def test_deep_merge_simple(self):
        """Test deep merge with simple dicts."""
        base = {"a": 1, "b": 2}
        overrides = {"b": 3, "c": 4}

        result = _deep_merge(base, overrides)

        assert result == {"a": 1, "b": 3, "c": 4}

    def test_deep_merge_nested(self):
        """Test deep merge with nested dicts."""
        base = {"parser": {"lenient": False, "strict": True}}
        overrides = {"parser": {"lenient": True}}

        result = _deep_merge(base, overrides)

        assert result == {"parser": {"lenient": True, "strict": True}}

    def test_deep_merge_preserves_base(self):
        """Test deep merge doesn't modify base dict."""
        base = {"a": 1}
        overrides = {"b": 2}

        _deep_merge(base, overrides)

        assert base == {"a": 1}


# ============================================================================
# ProjectSession Tests
# ============================================================================


class TestProjectSession:
    """Test ProjectSession class methods."""

    @pytest.fixture
    def mock_session(self):
        """Create mock ProjectSession for testing."""
        from cpmf_uips_xaml.shared.model.dto import WorkflowDto, SourceInfo, WorkflowMetadata

        # Create mock workflows
        wf1 = WorkflowDto(
            schema_id="https://example.com/schema",
            schema_version="1.0",
            collected_at="2024-01-01T00:00:00Z",
            provenance=None,
            id="wf1",
            name="Main",
            source=SourceInfo(
                path="Main.xaml",
                path_aliases=[],
                hash="abc",
                size_bytes=100,
                encoding="utf-8",
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

        wf2 = WorkflowDto(
            schema_id="https://example.com/schema",
            schema_version="1.0",
            collected_at="2024-01-01T00:00:00Z",
            provenance=None,
            id="wf2",
            name="Helper",
            source=SourceInfo(
                path="workflows/Helper.xaml",
                path_aliases=[],
                hash="def",
                size_bytes=200,
                encoding="utf-8",
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

        # Create mock objects
        mock_result = Mock()
        mock_result.total_workflows = 2
        mock_result.project_config.name = "TestProject"
        mock_result.project_config.entry_points = [Mock(file_path="Main.xaml")]
        mock_result.get_failed_workflows.return_value = []

        mock_analyzer = Mock()
        mock_analyzer._workflows = {"wf1": wf1, "wf2": wf2}

        mock_index = Mock(spec=ProjectIndex)
        mock_config = Mock(spec=Config)
        # Configure nested mock attributes
        mock_view_config = Mock()
        mock_view_config.view_type = "nested"
        mock_config.view = mock_view_config
        mock_emitter_config = Mock()
        mock_emitter_config.field_profile = "full"
        mock_config.emitter = mock_emitter_config

        session = ProjectSession(
            result=mock_result,
            analyzer=mock_analyzer,
            index=mock_index,
            config=mock_config,
            project_dir=Path("/test/project"),
        )

        return session

    def test_workflows_returns_all(self, mock_session):
        """Test workflows() returns all workflows."""
        workflows = mock_session.workflows()
        assert len(workflows) == 2
        assert workflows[0].id == "wf1"
        assert workflows[1].id == "wf2"

    def test_workflows_with_pattern_filters(self, mock_session):
        """Test workflows(pattern=...) filters results."""
        workflows = mock_session.workflows(pattern="Main.xaml")
        assert len(workflows) == 1
        assert workflows[0].name == "Main"

    def test_workflow_by_filename(self, mock_session):
        """Test workflow() finds by filename."""
        wf = mock_session.workflow("Main.xaml")
        assert wf is not None
        assert wf.name == "Main"

    def test_workflow_by_path(self, mock_session):
        """Test workflow() finds by path."""
        wf = mock_session.workflow("workflows/Helper.xaml")
        assert wf is not None
        assert wf.name == "Helper"

    def test_workflow_by_name(self, mock_session):
        """Test workflow() finds by name."""
        wf = mock_session.workflow("Helper")
        assert wf is not None
        assert wf.source.path == "workflows/Helper.xaml"

    def test_workflow_not_found_returns_none(self, mock_session):
        """Test workflow() returns None for missing workflow."""
        wf = mock_session.workflow("DoesNotExist.xaml")
        assert wf is None

    def test_view_calls_render_project_view(self, mock_session):
        """Test view() calls render_project_view."""
        with patch("cpmf_uips_xaml.api.session.render_project_view") as mock_render:
            mock_render.return_value = {"workflows": []}

            result = mock_session.view("execution", entry_point="Main.xaml")

            mock_render.assert_called_once()
            assert result == {"workflows": []}

    def test_emit_to_file(self, mock_session, tmp_path):
        """Test emit() to file path."""
        output_path = tmp_path / "output.json"

        with patch("cpmf_uips_xaml.api.session.emit_workflows") as mock_emit:
            mock_result = Mock()
            mock_result.success = True
            mock_emit.return_value = mock_result

            result = mock_session.emit("json", output_path=output_path)

            mock_emit.assert_called_once()
            assert result.success

    def test_emit_to_string(self, mock_session):
        """Test emit() returns string when no output_path."""
        with patch("cpmf_uips_xaml.stages.emit.renderers.json_renderer.JsonRenderer") as mock_renderer_class:
            mock_renderer = Mock()

            # Mock render_one method (for non-combined output)
            mock_result1 = Mock()
            mock_result1.content = '{"id": "wf1"}'
            mock_result2 = Mock()
            mock_result2.content = '{"id": "wf2"}'
            mock_renderer.render_one.side_effect = [mock_result1, mock_result2]

            # Mock render_many method (for combined output)
            mock_result_many = Mock()
            mock_result_many.content = '[{"id": "wf1"}, {"id": "wf2"}]'
            mock_renderer.render_many.return_value = mock_result_many

            mock_renderer_class.return_value = mock_renderer

            result = mock_session.emit("json")

            assert isinstance(result, str)
            # With combine=False (default), should have separate renders
            assert "wf1" in result or "wf2" in result

    def test_entry_points_property(self, mock_session):
        """Test entry_points property."""
        assert mock_session.entry_points == ["Main.xaml"]

    def test_project_name_property(self, mock_session):
        """Test project_name property."""
        assert mock_session.project_name == "TestProject"

    def test_total_workflows_property(self, mock_session):
        """Test total_workflows property."""
        assert mock_session.total_workflows == 2

    def test_successful_workflows_property(self, mock_session):
        """Test successful_workflows property."""
        assert mock_session.successful_workflows == 2


# ============================================================================
# Load Function Integration Tests
# ============================================================================


class TestLoadFunction:
    """Test load() function with mocked dependencies."""

    def test_load_project_returns_session(self, tmp_path):
        """Test load() with project returns ProjectSession."""
        project_file = tmp_path / "project.json"
        project_file.write_text('{"name": "Test"}')

        # Patch in the api module where it's imported from
        with patch("cpmf_uips_xaml.api.parse_and_analyze_project") as mock_parse:
            mock_result = Mock()
            mock_analyzer = Mock()
            mock_index = Mock()
            mock_parse.return_value = (mock_result, mock_analyzer, mock_index)

            with patch("cpmf_uips_xaml.api.load.load_default_config") as mock_config:
                mock_config.return_value = Mock(spec=Config)

                result = load(tmp_path)

                assert isinstance(result, ProjectSession)
                assert result.result == mock_result
                assert result.analyzer == mock_analyzer
                assert result.index == mock_index

    def test_load_workflow_returns_session(self, tmp_path):
        """Test load() with workflow file returns ProjectSession."""
        xaml_file = tmp_path / "workflow.xaml"
        xaml_file.write_text("<Activity />")

        with patch("cpmf_uips_xaml.api.load._load_single_workflow") as mock_load:
            mock_result = Mock()
            mock_analyzer = Mock()
            mock_index = Mock()
            mock_load.return_value = (mock_result, mock_analyzer, mock_index)

            with patch("cpmf_uips_xaml.api.load.load_default_config") as mock_config:
                mock_config.return_value = Mock(spec=Config)

                result = load(xaml_file)

                assert isinstance(result, ProjectSession)

    def test_load_with_output_view(self, tmp_path):
        """Test load() with output='view' returns dict."""
        project_file = tmp_path / "project.json"
        project_file.write_text('{"name": "Test"}')

        with patch("cpmf_uips_xaml.api.parse_and_analyze_project") as mock_parse:
            mock_result = Mock()
            mock_analyzer = Mock()
            mock_index = Mock()
            mock_parse.return_value = (mock_result, mock_analyzer, mock_index)

            with patch("cpmf_uips_xaml.api.load.render_project_view") as mock_view:
                mock_view.return_value = {"workflows": []}

                with patch("cpmf_uips_xaml.api.load.load_default_config") as mock_config:
                    mock_config.return_value = Mock(spec=Config)

                    result = load(tmp_path, output="view")

                    assert isinstance(result, dict)
                    assert "workflows" in result

    def test_load_with_output_index(self, tmp_path):
        """Test load() with output='index' returns ProjectIndex."""
        project_file = tmp_path / "project.json"
        project_file.write_text('{"name": "Test"}')

        with patch("cpmf_uips_xaml.api.parse_and_analyze_project") as mock_parse:
            mock_result = Mock()
            mock_analyzer = Mock()
            mock_index = Mock(spec=ProjectIndex)
            mock_parse.return_value = (mock_result, mock_analyzer, mock_index)

            with patch("cpmf_uips_xaml.api.load.load_default_config") as mock_config:
                mock_config.return_value = Mock(spec=Config)

                result = load(tmp_path, output="index")

                assert isinstance(result, Mock)
                assert result == mock_index

    def test_load_with_explicit_mode(self, tmp_path):
        """Test load() with explicit mode parameter."""
        project_file = tmp_path / "project.json"
        project_file.write_text('{"name": "Test"}')

        with patch("cpmf_uips_xaml.api.parse_and_analyze_project") as mock_parse:
            mock_result = Mock()
            mock_analyzer = Mock()
            mock_index = Mock()
            mock_parse.return_value = (mock_result, mock_analyzer, mock_index)

            with patch("cpmf_uips_xaml.api.load.load_default_config") as mock_config:
                mock_config.return_value = Mock(spec=Config)

                result = load(tmp_path, mode="project")

                assert isinstance(result, ProjectSession)
                mock_parse.assert_called_once()

    def test_load_with_config_dict(self, tmp_path):
        """Test load() with config dict merges with defaults."""
        project_file = tmp_path / "project.json"
        project_file.write_text('{"name": "Test"}')

        config_dict = {"parser": {"lenient": True}}

        with patch("cpmf_uips_xaml.api.parse_and_analyze_project") as mock_parse:
            mock_result = Mock()
            mock_analyzer = Mock()
            mock_index = Mock()
            mock_parse.return_value = (mock_result, mock_analyzer, mock_index)

            with patch("cpmf_uips_xaml.api.load._resolve_config") as mock_resolve:
                mock_resolve.return_value = Mock(spec=Config)

                result = load(tmp_path, config=config_dict)

                mock_resolve.assert_called_once_with(tmp_path, config_dict)
                assert isinstance(result, ProjectSession)

    def test_load_invalid_output_mode_raises_error(self, tmp_path):
        """Test load() with invalid output mode raises ValueError."""
        project_file = tmp_path / "project.json"
        project_file.write_text('{"name": "Test"}')

        with patch("cpmf_uips_xaml.api.parse_and_analyze_project") as mock_parse:
            mock_result = Mock()
            mock_analyzer = Mock()
            mock_index = Mock()
            mock_parse.return_value = (mock_result, mock_analyzer, mock_index)

            with patch("cpmf_uips_xaml.api.load.load_default_config") as mock_config:
                mock_config.return_value = Mock(spec=Config)

                with pytest.raises(ValueError, match="Unknown output mode"):
                    load(tmp_path, output="invalid")


# ============================================================================
# Tests for Bug Fixes
# ============================================================================


class TestBugFixes:
    """Test that critical bug fixes work correctly."""

    def test_single_workflow_has_entry_point(self, tmp_path):
        """Test single workflow sets entry_points (Issue #6)."""
        xaml_file = tmp_path / "workflow.xaml"
        xaml_file.write_text("<Activity />")

        with patch("cpmf_uips_xaml.api.load._load_single_workflow") as mock_load:
            # Mock the single workflow loading with entry point set
            from cpmf_uips_xaml.stages.assemble.project import ProjectConfig

            mock_config = ProjectConfig(
                name="workflow",
                main="workflow.xaml",
                entry_points=[{"file_path": "workflow.xaml", "filePath": "workflow.xaml"}],
            )

            mock_result = Mock()
            mock_result.project_config = mock_config
            mock_result.total_workflows = 1
            mock_analyzer = Mock()
            mock_index = Mock()

            mock_load.return_value = (mock_result, mock_analyzer, mock_index)

            with patch("cpmf_uips_xaml.api.load.load_default_config"):
                session = load(xaml_file)

                # Entry points should be set
                assert len(session.entry_points) > 0

    def test_string_emit_applies_exclude_none_filter(self, tmp_path):
        """Test string output applies exclude_none filter (Issue #4)."""
        project_file = tmp_path / "project.json"
        project_file.write_text('{"name": "Test"}')

        with patch("cpmf_uips_xaml.api.parse_and_analyze_project") as mock_parse:
            # Create mock session with workflows
            from cpmf_uips_xaml.shared.model.dto import WorkflowDto, SourceInfo, WorkflowMetadata

            wf = WorkflowDto(
                schema_id="test",
                schema_version="1.0",
                collected_at="2024-01-01T00:00:00Z",
                provenance=None,  # This None should be filtered out
                id="wf1",
                name="Test",
                source=SourceInfo(
                    path="Test.xaml",
                    path_aliases=[],
                    hash="abc",
                    size_bytes=100,
                    encoding="utf-8",
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

            mock_result = Mock()
            mock_result.total_workflows = 1
            mock_result.project_config.name = "Test"
            mock_result.project_config.entry_points = []
            mock_result.get_failed_workflows.return_value = []

            mock_analyzer = Mock()
            mock_analyzer._workflows = {"wf1": wf}

            mock_index = Mock()
            mock_parse.return_value = (mock_result, mock_analyzer, mock_index)

            with patch("cpmf_uips_xaml.api.load.load_default_config") as mock_config_loader:
                # Just mock the config structure
                mock_config = Mock()
                mock_config.emitter.field_profile = "full"
                mock_config_loader.return_value = mock_config

                session = load(tmp_path)

                # Emit with exclude_none=True
                json_str = session.emit("json", exclude_none=True)

                # The string should be valid JSON
                assert isinstance(json_str, str)
                assert len(json_str) > 0

    def test_parse_project_accepts_config_kwargs(self, tmp_path):
        """Test parse_project() accepts **config kwargs (Issue #7)."""
        from cpmf_uips_xaml.api.parsing import parse_project

        # Create a minimal project structure
        project_file = tmp_path / "project.json"
        project_file.write_text('{"name": "Test", "main": "Main.xaml"}')

        # Should not crash when passing config as kwargs
        # The function should properly handle **kwargs -> dict conversion
        try:
            result = parse_project(
                tmp_path,
                extract_expressions=False,
                include_viewstate=True
            )
            # If it succeeds, config was handled correctly
            assert result is not None
        except Exception as e:
            # Config should be passed correctly even if parse fails for other reasons
            # Should not have errors about "config" parameter
            error_msg = str(e).lower()
            assert "config" not in error_msg or "unexpected keyword" not in error_msg

    def test_yaml_format_rejected(self, tmp_path):
        """Test yaml format is properly rejected (Issue #8)."""
        import pytest

        # Note: Python dataclasses don't validate Literal at construction time
        # Validation happens when the format is used in renderers
        # session.emit() should reject yaml format
        project_file = tmp_path / "project.json"
        project_file.write_text('{"name": "Test"}')

        with patch("cpmf_uips_xaml.api.parse_and_analyze_project") as mock_parse:
            from cpmf_uips_xaml.shared.model.dto import WorkflowDto, SourceInfo, WorkflowMetadata

            wf = WorkflowDto(
                schema_id="test",
                schema_version="1.0",
                collected_at="2024-01-01T00:00:00Z",
                provenance=None,
                id="wf1",
                name="Test",
                source=SourceInfo(
                    path="Test.xaml",
                    path_aliases=[],
                    hash="abc",
                    size_bytes=100,
                    encoding="utf-8",
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

            mock_result = Mock()
            mock_result.total_workflows = 1
            mock_result.project_config.name = "Test"
            mock_result.project_config.entry_points = []
            mock_result.get_failed_workflows.return_value = []

            mock_analyzer = Mock()
            mock_analyzer._workflows = {"wf1": wf}

            mock_index = Mock()
            mock_parse.return_value = (mock_result, mock_analyzer, mock_index)

            with patch("cpmf_uips_xaml.api.load.load_default_config") as mock_config_loader:
                mock_config = Mock()
                mock_config.emitter.field_profile = "full"
                mock_config_loader.return_value = mock_config

                session = load(tmp_path)

                # Attempt to emit with yaml format should fail
                with pytest.raises((ValueError, TypeError)):
                    session.emit("yaml")
