"""Tests for project-level parsing functionality."""

from pathlib import Path

from cpmf_xaml_parser.project import ProjectConfig, ProjectParser, WorkflowResult


class TestProjectParser:
    """Test project parser functionality."""

    def test_parse_simple_project(self, corpus_dir):
        """Test parsing simple project with entry points."""
        project_dir = corpus_dir / "simple_project"

        parser = ProjectParser()
        result = parser.parse_project(project_dir)

        assert result.success, f"Project parsing should succeed: {result.errors}"
        assert result.project_config is not None
        assert result.project_config.name == "SimpleTestProject"
        assert result.project_config.main == "Main.xaml"
        assert result.project_config.expression_language == "VisualBasic"

    def test_project_entry_points(self, corpus_dir):
        """Test entry point detection."""
        project_dir = corpus_dir / "simple_project"

        parser = ProjectParser()
        result = parser.parse_project(project_dir)

        entry_points = result.get_entry_points()
        assert len(entry_points) == 1
        assert entry_points[0].relative_path == "Main.xaml"
        assert entry_points[0].is_entry_point is True

    def test_workflow_discovery(self, corpus_dir):
        """Test recursive workflow discovery."""
        project_dir = corpus_dir / "simple_project"

        parser = ProjectParser()
        result = parser.parse_project(project_dir, recursive=True)

        # Should discover Main.xaml and invoked workflows
        assert result.total_workflows >= 2

        # Check Main.xaml was parsed
        main_workflow = result.get_workflow("Main.xaml")
        assert main_workflow is not None
        assert main_workflow.parse_result.success

        # Check GetConfig.xaml was discovered and parsed
        get_config = result.get_workflow("workflows/GetConfig.xaml")
        assert get_config is not None
        assert get_config.parse_result.success

    def test_entry_points_only_mode(self, corpus_dir):
        """Test parsing only entry points without discovery."""
        project_dir = corpus_dir / "simple_project"

        parser = ProjectParser()
        result = parser.parse_project(project_dir, entry_points_only=True)

        # Should only parse Main.xaml
        assert result.total_workflows == 1
        assert result.workflows[0].relative_path == "Main.xaml"
        assert result.workflows[0].is_entry_point is True

    def test_dependency_graph(self, corpus_dir):
        """Test dependency graph construction."""
        project_dir = corpus_dir / "simple_project"

        parser = ProjectParser()
        result = parser.parse_project(project_dir, recursive=True)

        # Check dependency graph exists
        assert result.dependency_graph is not None
        assert "Main.xaml" in result.dependency_graph

        # Main.xaml should invoke GetConfig.xaml
        main_deps = result.dependency_graph["Main.xaml"]
        assert any("GetConfig.xaml" in dep for dep in main_deps)

    def test_invoke_workflow_file_extraction(self, corpus_dir):
        """Test extraction of InvokeWorkflowFile references."""
        project_dir = corpus_dir / "simple_project"

        parser = ProjectParser()
        result = parser.parse_project(project_dir)

        # Find Main.xaml workflow
        main_workflow = result.get_workflow("Main.xaml")
        assert main_workflow is not None

        # Check invoked workflows were extracted
        assert len(main_workflow.invoked_workflows) > 0

    def test_project_config_loading(self, corpus_dir):
        """Test project.json loading."""
        project_dir = corpus_dir / "simple_project"

        parser = ProjectParser()
        result = parser.parse_project(project_dir)

        config = result.project_config
        assert config.name == "SimpleTestProject"
        assert config.schema_version == "4.0"
        assert config.dependencies is not None
        assert len(config.dependencies) >= 2  # UiPath dependencies
        assert len(config.entry_points) >= 1

    def test_missing_project_json(self, tmp_path):
        """Test error handling when project.json is missing."""
        parser = ProjectParser()
        result = parser.parse_project(tmp_path)

        assert result.success is False
        assert len(result.errors) > 0
        assert "project.json" in result.errors[0].lower()

    def test_workflow_parsing_errors(self, corpus_dir):
        """Test handling of workflow parsing errors."""
        # Use edge_cases directory which has malformed.xaml
        project_dir = corpus_dir / "edge_cases"

        # Create a minimal project.json for testing
        project_json = project_dir / "project.json"
        if not project_json.exists():
            import json

            project_json.write_text(
                json.dumps(
                    {
                        "name": "EdgeCasesProject",
                        "main": "malformed.xaml",
                        "expressionLanguage": "VisualBasic",
                    }
                )
            )

        parser = ProjectParser()
        result = parser.parse_project(project_dir, entry_points_only=True)

        # Project parsing may fail or succeed depending on how we handle errors
        # At minimum, we should get parsing errors
        failed_workflows = result.get_failed_workflows()
        assert len(failed_workflows) > 0 or len(result.errors) > 0

    def test_parse_time_accumulation(self, corpus_dir):
        """Test that parse times are accumulated correctly."""
        project_dir = corpus_dir / "simple_project"

        parser = ProjectParser()
        result = parser.parse_project(project_dir)

        assert result.total_parse_time_ms > 0

        # Total should be sum of individual workflow parse times
        individual_total = sum(w.parse_result.parse_time_ms for w in result.workflows)
        assert abs(result.total_parse_time_ms - individual_total) < 0.01

    def test_relative_path_resolution(self, corpus_dir):
        """Test that relative paths are correctly resolved."""
        project_dir = corpus_dir / "simple_project"

        parser = ProjectParser()
        result = parser.parse_project(project_dir)

        # All workflows should have POSIX-style relative paths
        for workflow in result.workflows:
            assert "\\" not in workflow.relative_path or "/" in workflow.relative_path
            # Should not be absolute
            assert not Path(workflow.relative_path).is_absolute()

    def test_custom_parser_config(self, corpus_dir):
        """Test that parser config is passed to XAML parser."""
        project_dir = corpus_dir / "simple_project"

        # Use config with no expression extraction
        parser = ProjectParser({"extract_expressions": False})
        result = parser.parse_project(project_dir)

        assert result.success
        # Config should have been used
        for workflow in result.workflows:
            if workflow.parse_result.success:
                assert workflow.parse_result.config_used is not None

    def test_get_workflow_method(self, corpus_dir):
        """Test get_workflow method."""
        project_dir = corpus_dir / "simple_project"

        parser = ProjectParser()
        result = parser.parse_project(project_dir)

        # Should find existing workflow
        main = result.get_workflow("Main.xaml")
        assert main is not None
        assert main.relative_path == "Main.xaml"

        # Should return None for non-existent
        nonexistent = result.get_workflow("NonExistent.xaml")
        assert nonexistent is None

    def test_project_dependencies_in_dto_output(self, corpus_dir):
        """Test that project.json dependencies appear in workflow DTOs."""
        from cpmf_xaml_parser.project import project_result_to_dto

        project_dir = corpus_dir / "simple_project"

        # Parse project
        parser = ProjectParser()
        result = parser.parse_project(project_dir)

        assert result.success, f"Project parsing should succeed: {result.errors}"
        assert result.project_config is not None
        assert len(result.project_config.dependencies) > 0, "Project should have dependencies"

        # Convert to DTOs
        collection_dto = project_result_to_dto(result)

        # Verify dependencies are populated in ALL workflows
        assert len(collection_dto.workflows) > 0, "Should have at least one workflow"

        for workflow_dto in collection_dto.workflows:
            # Each workflow should inherit project dependencies
            assert (
                len(workflow_dto.dependencies) > 0
            ), f"Workflow {workflow_dto.name} should have dependencies"

            # Check that versions are parsed correctly (not raw constraint format)
            for dep in workflow_dto.dependencies:
                # Version should not have brackets
                assert not dep.version.startswith(
                    "["
                ), f"Version should be parsed, not raw: {dep.version}"
                assert not dep.version.endswith("]"), f"Version should be parsed: {dep.version}"
                assert dep.version != "unknown", f"Version should be known: {dep.package}"

            # Check for common UiPath packages
            packages = {dep.package for dep in workflow_dto.dependencies}
            # Simple project should have System.Activities at minimum
            assert any(
                "System.Activities" in pkg or "UiPath" in pkg for pkg in packages
            ), f"Should have UiPath/System packages, got: {packages}"


class TestProjectConfig:
    """Test ProjectConfig model."""

    def test_project_config_creation(self):
        """Test creating ProjectConfig."""
        config = ProjectConfig(
            name="TestProject",
            main="Main.xaml",
            expression_language="CSharp",
            entry_points=[{"filePath": "Main.xaml"}],
        )

        assert config.name == "TestProject"
        assert config.main == "Main.xaml"
        assert config.expression_language == "CSharp"
        assert len(config.entry_points) == 1


class TestWorkflowResult:
    """Test WorkflowResult model."""

    def test_workflow_result_creation(self, parser):
        """Test creating WorkflowResult."""
        from cpmf_xaml_parser.models import ParseResult, WorkflowContent

        parse_result = ParseResult(content=WorkflowContent(), success=True)

        workflow = WorkflowResult(
            file_path=Path("Main.xaml"),
            relative_path="Main.xaml",
            parse_result=parse_result,
            invoked_workflows=["GetConfig.xaml"],
            is_entry_point=True,
        )

        assert workflow.relative_path == "Main.xaml"
        assert workflow.is_entry_point is True
        assert len(workflow.invoked_workflows) == 1
