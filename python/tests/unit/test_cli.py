"""Tests for CLI module.

Tests:
- Output formatters (pretty, arguments, activities, tree, summary)
- Project output formatters (project summary, dependency graph)
- File parsing with glob patterns
- Argument parsing and validation
- Mode detection (project vs file)
- Error handling and exit codes
- DTO output integration
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Mock stdout wrapping before importing cli module to avoid I/O conflicts with pytest
with patch("sys.stdout"), patch("sys.stderr"):
    from cpmf_xaml_parser.cli import (
        format_activities,
        format_arguments,
        format_dependency_graph,
        format_pretty,
        format_project_summary,
        format_summary,
        format_tree,
        main,
        parse_files,
    )

from cpmf_xaml_parser.models import (
    Activity,
    ParseResult,
    WorkflowArgument,
    WorkflowContent,
    WorkflowVariable,
)
from cpmf_xaml_parser.project import ProjectConfig, ProjectResult, WorkflowResult


class TestFormatPretty:
    """Test format_pretty function."""

    def test_format_pretty_success(self):
        """Test pretty formatting of successful parse result."""
        content = WorkflowContent(
            display_name="Main Workflow",
            root_annotation="Test workflow",
            arguments=[
                WorkflowArgument(
                    name="in_FilePath",
                    type="System.String",
                    direction="in",
                    annotation="Input file",
                )
            ],
            variables=[
                WorkflowVariable(
                    name="varCount", type="System.Int32", default_value="0", scope="workflow"
                )
            ],
            activities=[
                Activity(
                    activity_id="act1",
                    workflow_id="wf1",
                    activity_type="System.Activities.Statements.Sequence",
                    display_name="Main Sequence",
                )
            ],
        )

        result = ParseResult(content=content, success=True, parse_time_ms=15.5)

        output = format_pretty(result, "Main.xaml")

        # Verify key sections
        assert "File: Main.xaml" in output
        assert "[OK] Parsing succeeded" in output
        assert "Main Workflow" in output
        assert "Test workflow" in output
        assert "Arguments: 1" in output
        assert "Variables: 1" in output
        assert "Activities: 1" in output
        assert "Parse Time: 15.50ms" in output
        assert "IN: in_FilePath (System.String)" in output
        assert "Input file" in output

    def test_format_pretty_failed(self):
        """Test pretty formatting of failed parse result."""
        result = ParseResult(
            content=None,
            success=False,
            errors=["XML parsing failed", "Invalid element"],
            warnings=["Unrecognized attribute"],
        )

        output = format_pretty(result)

        assert "[!] Parsing FAILED" in output
        assert "Errors:" in output
        assert "XML parsing failed" in output
        assert "Invalid element" in output
        assert "Warnings:" in output
        assert "Unrecognized attribute" in output

    def test_format_pretty_no_content(self):
        """Test formatting when content is None."""
        result = ParseResult(content=None, success=True)
        output = format_pretty(result)

        # When content is None, output is empty (early return after adding "[OK]" if it exists)
        # Actually checking the code, it returns empty string when content is None
        assert output == ""

    def test_format_pretty_with_file_path(self):
        """Test formatting includes file path."""
        content = WorkflowContent()
        result = ParseResult(content=content, success=True)

        output = format_pretty(result, "workflows/Main.xaml")

        assert "File: workflows/Main.xaml" in output

    def test_format_pretty_many_variables(self):
        """Test formatting truncates variables over 10."""
        variables = [WorkflowVariable(name=f"var{i}", type="System.String") for i in range(15)]
        content = WorkflowContent(variables=variables)
        result = ParseResult(content=content, success=True)

        output = format_pretty(result)

        assert "Variables: (15 total)" in output
        assert "... and 5 more" in output

    def test_format_pretty_activity_types_summary(self):
        """Test formatting shows activity type counts."""
        activities = [
            Activity(
                activity_id=f"act{i}",
                workflow_id="wf1",
                activity_type="Sequence" if i < 5 else "Assign",
                display_name=f"Activity {i}",
            )
            for i in range(10)
        ]
        content = WorkflowContent(activities=activities)
        result = ParseResult(content=content, success=True)

        output = format_pretty(result)

        assert "Activities: (10 total)" in output
        assert "Sequence: 5" in output
        assert "Assign: 5" in output

    def test_format_pretty_with_warnings(self):
        """Test formatting includes warnings even on success."""
        content = WorkflowContent()
        result = ParseResult(
            content=content,
            success=True,
            warnings=["Unknown activity type: CustomActivity"],
        )

        output = format_pretty(result)

        assert "[OK] Parsing succeeded" in output
        assert "Warnings:" in output
        assert "Unknown activity type" in output


class TestFormatArguments:
    """Test format_arguments function."""

    def test_format_arguments_success(self):
        """Test formatting of arguments."""
        content = WorkflowContent(
            arguments=[
                WorkflowArgument(
                    name="in_FilePath",
                    type="System.String",
                    direction="in",
                    annotation="Input file path",
                    default_value="config.json",
                ),
                WorkflowArgument(
                    name="out_Result",
                    type="System.Int32",
                    direction="out",
                    annotation="Result code",
                ),
            ]
        )
        result = ParseResult(content=content, success=True)

        output = format_arguments(result)

        assert "IN: in_FilePath (System.String)" in output
        assert "Input file path" in output
        assert "Default: config.json" in output
        assert "OUT: out_Result (System.Int32)" in output
        assert "Result code" in output

    def test_format_arguments_no_arguments(self):
        """Test formatting when no arguments present."""
        content = WorkflowContent(arguments=[])
        result = ParseResult(content=content, success=True)

        output = format_arguments(result)

        assert output == "No arguments found"

    def test_format_arguments_failed_parse(self):
        """Test formatting when parse failed."""
        result = ParseResult(content=None, success=False, errors=["Failed to parse"])

        output = format_arguments(result)

        assert "Error: Failed to parse" in output

    def test_format_arguments_no_content(self):
        """Test formatting when content is None."""
        result = ParseResult(content=None, success=True)

        output = format_arguments(result)

        assert output == "No content"


class TestFormatActivities:
    """Test format_activities function."""

    def test_format_activities_success(self):
        """Test formatting of activities."""
        content = WorkflowContent(
            activities=[
                Activity(
                    activity_id="act1",
                    workflow_id="wf1",
                    activity_type="Sequence",
                    display_name="Main Sequence",
                    annotation="Main container",
                ),
                Activity(
                    activity_id="act2",
                    workflow_id="wf1",
                    activity_type="Assign",
                    display_name=None,
                ),
            ]
        )
        result = ParseResult(content=content, success=True)

        output = format_activities(result)

        assert "Sequence: Main Sequence" in output
        assert "Main container" in output
        assert "Assign: (unnamed)" in output

    def test_format_activities_no_activities(self):
        """Test formatting when no activities present."""
        content = WorkflowContent(activities=[])
        result = ParseResult(content=content, success=True)

        output = format_activities(result)

        assert output == "No activities found"

    def test_format_activities_failed_parse(self):
        """Test formatting when parse failed."""
        result = ParseResult(content=None, success=False, errors=["XML error"])

        output = format_activities(result)

        assert "Error: XML error" in output


class TestFormatTree:
    """Test format_tree function."""

    def test_format_tree_nested_activities(self):
        """Test tree formatting with nested activities."""
        content = WorkflowContent(
            activities=[
                Activity(
                    activity_id="act1",
                    workflow_id="wf1",
                    activity_type="Sequence",
                    display_name="Root",
                    depth=0,
                ),
                Activity(
                    activity_id="act2",
                    workflow_id="wf1",
                    activity_type="If",
                    display_name="Check Condition",
                    depth=1,
                    annotation="Test condition",
                ),
                Activity(
                    activity_id="act3",
                    workflow_id="wf1",
                    activity_type="Assign",
                    display_name="Set Value",
                    depth=2,
                ),
            ]
        )
        result = ParseResult(content=content, success=True)

        output = format_tree(result)

        lines = output.split("\n")
        assert "Sequence: Root" in lines[0]
        assert lines[1].startswith("  ")  # Indented
        assert "If: Check Condition" in lines[1]
        assert "Test condition" in lines[2]
        assert lines[3].startswith("    ")  # More indented
        assert "Assign: Set Value" in lines[3]

    def test_format_tree_no_activities(self):
        """Test tree formatting when no activities."""
        content = WorkflowContent(activities=[])
        result = ParseResult(content=content, success=True)

        output = format_tree(result)

        assert output == "No activities found"

    def test_format_tree_failed_parse(self):
        """Test tree formatting when parse failed."""
        result = ParseResult(content=None, success=False, errors=["Parse error"])

        output = format_tree(result)

        assert "Error: Parse error" in output


class TestFormatSummary:
    """Test format_summary function."""

    def test_format_summary_multiple_files(self):
        """Test summary formatting for multiple files."""
        content1 = WorkflowContent(
            arguments=[WorkflowArgument(name="arg1", type="String", direction="in")],
            variables=[WorkflowVariable(name="var1", type="Int32")],
            activities=[Activity(activity_id="act1", workflow_id="wf1", activity_type="Sequence")],
        )
        result1 = ParseResult(content=content1, success=True)

        content2 = WorkflowContent()
        result2 = ParseResult(content=content2, success=True)

        result3 = ParseResult(
            content=None, success=False, errors=["Parse error 1", "Parse error 2"]
        )

        results = [
            ("Main.xaml", result1),
            ("Sub.xaml", result2),
            ("Broken.xaml", result3),
        ]

        output = format_summary(results)

        assert "Processed 3 file(s)" in output
        assert "Succeeded: 2" in output
        assert "Failed: 1" in output
        assert "[OK] Main.xaml" in output
        assert "Arguments: 1, Variables: 1, Activities: 1" in output
        assert "[OK] Sub.xaml" in output
        assert "[!] Broken.xaml" in output
        assert "Parse error 1" in output

    def test_format_summary_all_success(self):
        """Test summary with all successful parses."""
        content = WorkflowContent()
        results = [
            ("File1.xaml", ParseResult(content=content, success=True)),
            ("File2.xaml", ParseResult(content=content, success=True)),
        ]

        output = format_summary(results)

        assert "Processed 2 file(s)" in output
        assert "Succeeded: 2" in output
        assert "Failed" not in output


class TestFormatProjectSummary:
    """Test format_project_summary function."""

    def test_format_project_summary_success(self):
        """Test project summary formatting."""
        project_config = ProjectConfig(
            name="TestProject",
            main="Main.xaml",
            expression_language="VisualBasic",
            dependencies={"UiPath.System.Activities": "[25.4.4]"},
        )

        workflow1 = WorkflowResult(
            file_path=Path("/project/Main.xaml"),
            relative_path="Main.xaml",
            parse_result=ParseResult(
                content=WorkflowContent(
                    arguments=[WorkflowArgument(name="arg1", type="String", direction="in")],
                    variables=[WorkflowVariable(name="var1", type="Int32")],
                    activities=[
                        Activity(
                            activity_id="act1",
                            workflow_id="wf1",
                            activity_type="Sequence",
                        )
                    ],
                ),
                success=True,
                parse_time_ms=10.0,
            ),
            is_entry_point=True,
        )

        workflow2 = WorkflowResult(
            file_path=Path("/project/Sub.xaml"),
            relative_path="Sub.xaml",
            parse_result=ParseResult(content=WorkflowContent(), success=True, parse_time_ms=5.0),
            is_entry_point=False,
        )

        project_result = ProjectResult(
            project_dir=Path("/project"),
            project_config=project_config,
            workflows=[workflow1, workflow2],
            success=True,
            total_workflows=2,
            total_parse_time_ms=15.0,
        )

        output = format_project_summary(project_result)

        assert "Project: TestProject" in output
        assert "Directory: /project" in output or "Directory: \\project" in output
        assert "[OK] Project parsing succeeded" in output
        assert "Main: Main.xaml" in output
        assert "Expression Language: VisualBasic" in output
        assert "Dependencies: 1" in output
        assert "Entry Points: (1 total)" in output
        assert "[OK] Main.xaml" in output
        assert "Workflows: (2 total)" in output
        assert "Successfully parsed: 2" in output
        assert "Total parse time: 15.00ms" in output
        assert "Args: 1, Vars: 1, Acts: 1" in output
        assert "(entry)" in output

    def test_format_project_summary_failed(self):
        """Test project summary for failed parse."""
        project_result = ProjectResult(
            project_dir=Path("/project"),
            project_config=None,
            workflows=[],
            success=False,
            errors=["Failed to load project.json", "Invalid format"],
        )

        output = format_project_summary(project_result)

        assert "Project: (config not loaded)" in output
        assert "[!] Project parsing FAILED" in output
        assert "Failed to load project.json" in output
        assert "Invalid format" in output

    def test_format_project_summary_with_failures(self):
        """Test project summary with some failed workflows."""
        project_config = ProjectConfig(name="TestProject")

        workflow_failed = WorkflowResult(
            file_path=Path("/project/Broken.xaml"),
            relative_path="Broken.xaml",
            parse_result=ParseResult(content=None, success=False, errors=["XML error"]),
            is_entry_point=False,
        )

        project_result = ProjectResult(
            project_dir=Path("/project"),
            project_config=project_config,
            workflows=[workflow_failed],
            success=True,
            total_workflows=1,
        )

        output = format_project_summary(project_result)

        assert "Successfully parsed: 0" in output
        assert "Failed to parse: 1" in output

    def test_format_project_summary_many_workflows(self):
        """Test project summary with >10 workflows shows truncation."""
        project_config = ProjectConfig(name="LargeProject")
        workflows = [
            WorkflowResult(
                file_path=Path(f"/project/Workflow{i}.xaml"),
                relative_path=f"Workflow{i}.xaml",
                parse_result=ParseResult(content=WorkflowContent(), success=True),
                is_entry_point=False,
            )
            for i in range(15)
        ]

        project_result = ProjectResult(
            project_dir=Path("/project"),
            project_config=project_config,
            workflows=workflows,
            success=True,
            total_workflows=15,
        )

        output = format_project_summary(project_result)

        assert "Workflows: (15 total)" in output
        assert "... and 5 more" in output

    def test_format_project_summary_with_warnings(self):
        """Test project summary includes warnings."""
        project_config = ProjectConfig(name="TestProject")
        project_result = ProjectResult(
            project_dir=Path("/project"),
            project_config=project_config,
            workflows=[],
            success=True,
            warnings=[
                "Warning 1",
                "Warning 2",
                "Warning 3",
                "Warning 4",
                "Warning 5",
                "Warning 6",
            ],
        )

        output = format_project_summary(project_result)

        assert "Warnings: (6 total, showing first 5)" in output
        assert "Warning 1" in output
        assert "Warning 5" in output
        assert "Warning 6" not in output  # Only shows first 5


class TestFormatDependencyGraph:
    """Test format_dependency_graph function."""

    def test_format_dependency_graph_with_dependencies(self):
        """Test dependency graph formatting."""
        project_config = ProjectConfig(name="TestProject")
        project_result = ProjectResult(
            project_dir=Path("/project"),
            project_config=project_config,
            workflows=[],
            dependency_graph={
                "Main.xaml": ["Sub.xaml", "Helper.xaml"],
                "Sub.xaml": ["Helper.xaml"],
                "Helper.xaml": [],
            },
        )

        output = format_dependency_graph(project_result)

        assert "Project: TestProject" in output
        assert "Dependency Graph:" in output
        assert "Main.xaml" in output
        assert "-> Sub.xaml" in output
        assert "-> Helper.xaml" in output
        assert "Sub.xaml" in output
        assert "(no dependencies)" in output

    def test_format_dependency_graph_empty(self):
        """Test dependency graph formatting when empty."""
        project_config = ProjectConfig(name="TestProject")
        project_result = ProjectResult(
            project_dir=Path("/project"),
            project_config=project_config,
            workflows=[],
            dependency_graph={},
        )

        output = format_dependency_graph(project_result)

        assert "Project: TestProject" in output
        assert "No dependencies found" in output

    def test_format_dependency_graph_no_config(self):
        """Test dependency graph with no project config."""
        project_result = ProjectResult(
            project_dir=Path("/project"),
            project_config=None,
            workflows=[],
            dependency_graph={},
        )

        output = format_dependency_graph(project_result)

        assert "Project: (unknown)" in output


class TestParseFiles:
    """Test parse_files function."""

    def test_parse_files_single_file(self, tmp_path):
        """Test parsing a single file."""
        xaml_file = tmp_path / "Main.xaml"
        xaml_file.write_text(
            """<?xml version="1.0"?>
<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities">
  <Sequence DisplayName="Test" />
</Activity>""",
            encoding="utf-8",
        )

        results = parse_files([str(xaml_file)], {})

        assert len(results) == 1
        file_path, result = results[0]
        assert file_path == str(xaml_file)
        assert result.success

    def test_parse_files_wildcard(self, tmp_path):
        """Test parsing with wildcard pattern."""
        for i in range(3):
            xaml_file = tmp_path / f"Workflow{i}.xaml"
            xaml_file.write_text(
                """<?xml version="1.0"?>
<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities" />""",
                encoding="utf-8",
            )

        pattern = str(tmp_path / "*.xaml")
        results = parse_files([pattern], {})

        assert len(results) == 3
        assert all(result.success for _, result in results)

    def test_parse_files_nonexistent(self):
        """Test parsing nonexistent file creates error result."""
        results = parse_files(["nonexistent.xaml"], {})

        assert len(results) == 1
        file_path, result = results[0]
        assert file_path == "nonexistent.xaml"
        assert not result.success
        assert "File not found" in result.errors[0]

    def test_parse_files_multiple_patterns(self, tmp_path):
        """Test parsing with multiple patterns."""
        file1 = tmp_path / "A.xaml"
        file2 = tmp_path / "B.xaml"
        file1.write_text(
            """<?xml version="1.0"?>
<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities" />""",
            encoding="utf-8",
        )
        file2.write_text(
            """<?xml version="1.0"?>
<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities" />""",
            encoding="utf-8",
        )

        results = parse_files([str(file1), str(file2)], {})

        assert len(results) == 2

    def test_parse_files_config_passed(self, tmp_path):
        """Test that config is passed to parser."""
        xaml_file = tmp_path / "Main.xaml"
        xaml_file.write_text(
            """<?xml version="1.0"?>
<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities">
  <Sequence />
</Activity>""",
            encoding="utf-8",
        )

        config = {"strict_mode": True, "max_depth": 10}
        results = parse_files([str(xaml_file)], config)

        # Just verify it doesn't crash with custom config
        assert len(results) == 1


class TestMain:
    """Test main function and CLI argument parsing."""

    def test_main_single_file_default(self, tmp_path, capsys):
        """Test main with single file uses pretty format."""
        xaml_file = tmp_path / "Main.xaml"
        xaml_file.write_text(
            """<?xml version="1.0"?>
<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities">
  <Sequence DisplayName="Test Sequence" />
</Activity>""",
            encoding="utf-8",
        )

        with patch.object(sys, "argv", ["xaml-parser", str(xaml_file)]):
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 0

        captured = capsys.readouterr()
        assert "[OK] Parsing succeeded" in captured.out

    def test_main_file_not_found(self, capsys):
        """Test main with nonexistent file."""
        with patch.object(sys, "argv", ["xaml-parser", "nonexistent.xaml"]):
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "File not found" in captured.out

    def test_main_json_output(self, tmp_path, capsys):
        """Test main with --json flag."""
        xaml_file = tmp_path / "Main.xaml"
        xaml_file.write_text(
            """<?xml version="1.0"?>
<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities">
  <Sequence />
</Activity>""",
            encoding="utf-8",
        )

        with patch.object(sys, "argv", ["xaml-parser", str(xaml_file), "--json"]):
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 0

        captured = capsys.readouterr()
        output_data = json.loads(captured.out)
        assert "success" in output_data
        assert output_data["success"] is True

    def test_main_arguments_flag(self, tmp_path, capsys):
        """Test main with --arguments flag."""
        xaml_file = tmp_path / "Main.xaml"
        xaml_file.write_text(
            """<?xml version="1.0"?>
<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
          xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
          xmlns:sap2010="http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation">
  <x:Members>
    <x:Property Name="in_Test" Type="InArgument(x:String)" />
  </x:Members>
  <Sequence />
</Activity>""",
            encoding="utf-8",
        )

        with patch.object(sys, "argv", ["xaml-parser", str(xaml_file), "--arguments"]):
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 0

        captured = capsys.readouterr()
        assert "in_Test" in captured.out

    def test_main_tree_flag(self, tmp_path, capsys):
        """Test main with --tree flag."""
        xaml_file = tmp_path / "Main.xaml"
        xaml_file.write_text(
            """<?xml version="1.0"?>
<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities">
  <Sequence DisplayName="Root">
    <Assign DisplayName="Child" />
  </Sequence>
</Activity>""",
            encoding="utf-8",
        )

        with patch.object(sys, "argv", ["xaml-parser", str(xaml_file), "--tree"]):
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 0

        captured = capsys.readouterr()
        # Check that output contains activities (the full type path may vary)
        assert "Sequence" in captured.out or "Root" in captured.out

    def test_main_output_file(self, tmp_path):
        """Test main with -o flag writes to file."""
        xaml_file = tmp_path / "Main.xaml"
        xaml_file.write_text(
            """<?xml version="1.0"?>
<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities">
  <Sequence />
</Activity>""",
            encoding="utf-8",
        )

        output_file = tmp_path / "output.txt"

        with patch.object(sys, "argv", ["xaml-parser", str(xaml_file), "-o", str(output_file)]):
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 0

        assert output_file.exists()
        content = output_file.read_text(encoding="utf-8")
        assert "[OK] Parsing succeeded" in content

    def test_main_strict_mode(self, tmp_path):
        """Test main with --strict flag."""
        xaml_file = tmp_path / "Main.xaml"
        xaml_file.write_text(
            """<?xml version="1.0"?>
<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities">
  <Sequence />
</Activity>""",
            encoding="utf-8",
        )

        with patch.object(sys, "argv", ["xaml-parser", str(xaml_file), "--strict"]):
            with pytest.raises(SystemExit) as exc_info:
                main()

            # Should succeed for valid XAML
            assert exc_info.value.code == 0

    def test_main_no_expressions_flag(self, tmp_path):
        """Test main with --no-expressions flag."""
        xaml_file = tmp_path / "Main.xaml"
        xaml_file.write_text(
            """<?xml version="1.0"?>
<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities">
  <Sequence />
</Activity>""",
            encoding="utf-8",
        )

        with patch.object(sys, "argv", ["xaml-parser", str(xaml_file), "--no-expressions"]):
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 0

    def test_main_project_mode_not_found(self, capsys):
        """Test main in project mode with nonexistent project.json."""
        with patch.object(sys, "argv", ["xaml-parser", "nonexistent/project.json"]):
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "File not found" in captured.err

    def test_main_project_mode_directory_no_project_json(self, tmp_path, capsys):
        """Test main with directory without project.json."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        with patch.object(sys, "argv", ["xaml-parser", str(empty_dir)]):
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "No project.json found" in captured.err

    def test_main_entry_points_only_without_project(self, capsys):
        """Test --entry-points-only flag requires project mode."""
        with patch.object(sys, "argv", ["xaml-parser", "Main.xaml", "--entry-points-only"]):
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "--entry-points-only only works with project.json" in captured.err

    def test_main_graph_without_project(self, capsys):
        """Test --graph flag requires project mode."""
        with patch.object(sys, "argv", ["xaml-parser", "Main.xaml", "--graph"]):
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "--graph only works with project.json" in captured.err

    def test_main_multiple_files_summary(self, tmp_path, capsys):
        """Test main with multiple files uses summary format."""
        for i in range(2):
            xaml_file = tmp_path / f"Workflow{i}.xaml"
            xaml_file.write_text(
                """<?xml version="1.0"?>
<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities" />""",
                encoding="utf-8",
            )

        pattern = str(tmp_path / "*.xaml")
        with patch.object(sys, "argv", ["xaml-parser", pattern]):
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 0

        captured = capsys.readouterr()
        assert "Processed 2 file(s)" in captured.out

    def test_main_summary_flag_explicit(self, tmp_path, capsys):
        """Test main with --summary flag."""
        xaml_file = tmp_path / "Main.xaml"
        xaml_file.write_text(
            """<?xml version="1.0"?>
<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities" />""",
            encoding="utf-8",
        )

        with patch.object(sys, "argv", ["xaml-parser", str(xaml_file), "--summary"]):
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 0

        captured = capsys.readouterr()
        assert "Processed 1 file(s)" in captured.out


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
