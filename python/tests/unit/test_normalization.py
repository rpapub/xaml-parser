"""Tests for normalization layer.

Tests:
- ParseResult → WorkflowDto transformation
- Activity transformation with all fields
- Argument transformation with stable IDs
- Variable transformation with stable IDs
- Dependency extraction from assembly references
- Edge integration from ControlFlowExtractor
- Issue collection from parse errors/warnings
- Metadata generation
- Deterministic sorting
- Empty/failed parse result handling
"""

import pytest

from xaml_parser.models import (
    Activity,
    ParseDiagnostics,
    ParseResult,
    WorkflowArgument,
    WorkflowContent,
    WorkflowVariable,
)
from xaml_parser.normalization import Normalizer


class TestNormalizer:
    """Test Normalizer class."""

    def test_normalize_simple_workflow(self):
        """Test normalization of simple workflow with activities."""
        # Create parse result
        content = WorkflowContent(
            arguments=[
                WorkflowArgument(
                    name="in_FilePath",
                    type="System.String",
                    direction="in",
                    annotation="Input file path",
                ),
            ],
            variables=[
                WorkflowVariable(
                    name="varCount",
                    type="System.Int32",
                    default_value="0",
                    scope="workflow",
                ),
            ],
            activities=[
                Activity(
                    activity_id="act:sha256:abc123",
                    workflow_id="wf:sha256:test",
                    activity_type="System.Activities.Statements.Sequence",
                    display_name="Main Sequence",
                    node_id="seq1",
                    depth=0,
                    properties={"DisplayName": "Main Sequence"},
                ),
            ],
            assembly_references=["UiPath.System.Activities, Version=23.10.0"],
            expression_language="VisualBasic",
        )

        parse_result = ParseResult(
            content=content,
            success=True,
            file_path="Main.xaml",
            diagnostics=ParseDiagnostics(file_size_bytes=1234),
        )

        # Normalize
        normalizer = Normalizer()
        workflow_dto = normalizer.normalize(parse_result, workflow_name="Main")

        # Verify DTO structure
        assert workflow_dto.schema_id == "https://rpax.io/schemas/xaml-workflow.json"
        assert workflow_dto.schema_version == "1.0.0"
        assert workflow_dto.name == "Main"
        assert workflow_dto.collected_at  # Should have timestamp

        # Verify content
        assert len(workflow_dto.arguments) == 1
        assert workflow_dto.arguments[0].name == "in_FilePath"
        assert workflow_dto.arguments[0].direction == "In"  # Normalized to title case

        assert len(workflow_dto.variables) == 1
        assert workflow_dto.variables[0].name == "varCount"

        assert len(workflow_dto.activities) == 1
        assert workflow_dto.activities[0].id == "act:sha256:abc123"
        assert workflow_dto.activities[0].type_short == "Sequence"

        # Dependencies come from project_dependencies parameter, not assembly_references
        assert len(workflow_dto.dependencies) == 0

    def test_normalize_with_edges(self):
        """Test that edges are extracted during normalization."""
        # Create sequence with children
        content = WorkflowContent(
            activities=[
                Activity(
                    activity_id="act:sha256:seq",
                    workflow_id="wf:sha256:test",
                    activity_type="Sequence",
                    node_id="seq",
                    child_activities=["act:sha256:111", "act:sha256:222"],
                ),
                Activity(
                    activity_id="act:sha256:111",
                    workflow_id="wf:sha256:test",
                    activity_type="Assign",
                    node_id="act1",
                ),
                Activity(
                    activity_id="act:sha256:222",
                    workflow_id="wf:sha256:test",
                    activity_type="Log",
                    node_id="act2",
                ),
            ]
        )

        parse_result = ParseResult(content=content, success=True)

        # Normalize
        normalizer = Normalizer()
        workflow_dto = normalizer.normalize(parse_result)

        # Verify edges were extracted
        assert len(workflow_dto.edges) == 1  # One "Next" edge
        edge = workflow_dto.edges[0]
        assert edge.from_id == "act:sha256:111"
        assert edge.to_id == "act:sha256:222"
        assert edge.kind == "Next"

    def test_transform_activity_with_all_fields(self):
        """Test activity transformation preserves all fields."""
        normalizer = Normalizer()

        activity = Activity(
            activity_id="act:sha256:test123",
            workflow_id="wf:sha256:test",
            activity_type="UiPath.Core.Activities.Click",
            display_name="Click Button",
            node_id="click1",
            parent_activity_id="act:sha256:parent",
            depth=2,
            properties={
                "DisplayName": "Click Button",
                "CursorPosition": "Center",
            },
            arguments={"Target": "[btnSubmit]", "MouseButton": "Left"},
            expressions=["[btnSubmit]", '["Left"]'],
            variables_referenced=["btnSubmit"],
            selectors={"Selector": "<html><button id='submit'/>"},
            annotation="Click the submit button",
        )

        activity_dto = normalizer._transform_activity(activity)

        # Verify all fields mapped
        assert activity_dto.id == "act:sha256:test123"
        assert activity_dto.type == "UiPath.Core.Activities.Click"
        assert activity_dto.type_short == "Click"
        assert activity_dto.display_name == "Click Button"
        assert activity_dto.parent_id == "act:sha256:parent"
        assert activity_dto.depth == 2
        assert activity_dto.properties["DisplayName"] == "Click Button"
        assert activity_dto.in_args["Target"] == "[btnSubmit]"
        assert activity_dto.expressions == ["[btnSubmit]", '["Left"]']
        assert activity_dto.variables_referenced == ["btnSubmit"]
        assert activity_dto.selectors == {"Selector": "<html><button id='submit'/>"}
        assert activity_dto.annotation == "Click the submit button"

    def test_transform_argument(self):
        """Test argument transformation with stable ID."""
        normalizer = Normalizer()

        argument = WorkflowArgument(
            name="in_FilePath",
            type="System.String",
            direction="in",
            annotation="Input file path",
            default_value="config.json",
        )

        arg_dto = normalizer._transform_argument(argument)

        # Verify fields
        assert arg_dto.name == "in_FilePath"
        assert arg_dto.type == "System.String"
        assert arg_dto.direction == "In"  # Normalized to title case
        assert arg_dto.annotation == "Input file path"
        assert arg_dto.default_value == "config.json"

        # Verify stable ID
        assert arg_dto.id.startswith("arg:sha256:")

        # Verify determinism
        arg_dto2 = normalizer._transform_argument(argument)
        assert arg_dto.id == arg_dto2.id

    def test_transform_variable(self):
        """Test variable transformation with stable ID."""
        normalizer = Normalizer()

        variable = WorkflowVariable(
            name="varCount",
            type="System.Int32",
            default_value="0",
            scope="workflow",
        )

        var_dto = normalizer._transform_variable(variable)

        # Verify fields
        assert var_dto.name == "varCount"
        assert var_dto.type == "System.Int32"
        assert var_dto.default_value == "0"
        assert var_dto.scope == "workflow"

        # Verify stable ID
        assert var_dto.id.startswith("var:sha256:")

        # Verify determinism
        var_dto2 = normalizer._transform_variable(variable)
        assert var_dto.id == var_dto2.id

    def test_transform_dependencies(self):
        """Test dependency extraction from assembly references."""
        normalizer = Normalizer()

        assembly_refs = [
            "UiPath.System.Activities, Version=23.10.0, Culture=neutral",
            "UiPath.UIAutomation.Activities, Version=23.10.1",
            "System.Activities, Version=4.0.0.0, Culture=neutral, PublicKeyToken=31bf3856ad364e35",
        ]

        dependencies = normalizer._transform_dependencies(assembly_refs)

        assert len(dependencies) == 3

        # Check first dependency
        assert dependencies[0].package == "UiPath.System.Activities"
        assert dependencies[0].version == "23.10.0"

        # Check second dependency
        assert dependencies[1].package == "UiPath.UIAutomation.Activities"
        assert dependencies[1].version == "23.10.1"

        # Check third dependency
        assert dependencies[2].package == "System.Activities"
        assert dependencies[2].version == "4.0.0.0"

    def test_normalize_collects_issues(self):
        """Test that normalization collects issues from parse result."""
        content = WorkflowContent()

        parse_result = ParseResult(
            content=content,
            success=False,
            errors=["Failed to parse element: InvalidActivity"],
            warnings=["Unknown activity type: CustomActivity"],
            file_path="Broken.xaml",
        )

        normalizer = Normalizer()
        workflow_dto = normalizer.normalize(parse_result)

        # Verify issues collected
        assert len(workflow_dto.issues) == 2

        # Check error
        error_issue = next(i for i in workflow_dto.issues if i.level == "error")
        assert "Failed to parse element" in error_issue.message
        assert error_issue.path == "Broken.xaml"
        assert error_issue.code == "PARSE_ERROR"

        # Check warning
        warning_issue = next(i for i in workflow_dto.issues if i.level == "warning")
        assert "Unknown activity type" in warning_issue.message
        assert warning_issue.code == "PARSE_WARNING"

    def test_normalize_handles_empty_parse_result(self):
        """Test normalization of empty/failed parse result."""
        parse_result = ParseResult(
            content=None,
            success=False,
            file_path="Failed.xaml",
        )

        normalizer = Normalizer()
        workflow_dto = normalizer.normalize(parse_result)

        # Should create minimal DTO with error issue
        assert workflow_dto.collected_at  # Has timestamp
        assert len(workflow_dto.issues) == 1
        assert workflow_dto.issues[0].level == "error"
        assert "Parse failed" in workflow_dto.issues[0].message

    def test_deterministic_sorting(self):
        """Test that collections are sorted deterministically when sort_output=True."""
        content = WorkflowContent(
            arguments=[
                WorkflowArgument(name="zed", type="System.String", direction="in"),
                WorkflowArgument(name="alfa", type="System.String", direction="in"),
                WorkflowArgument(name="bravo", type="System.String", direction="in"),
            ],
            variables=[
                WorkflowVariable(name="varZ", type="System.Int32"),
                WorkflowVariable(name="varA", type="System.Int32"),
                WorkflowVariable(name="varB", type="System.Int32"),
            ],
            activities=[
                Activity(
                    activity_id="act:sha256:zzz",
                    workflow_id="wf:sha256:test",
                    activity_type="Assign",
                    node_id="act3",
                ),
                Activity(
                    activity_id="act:sha256:aaa",
                    workflow_id="wf:sha256:test",
                    activity_type="Assign",
                    node_id="act1",
                ),
                Activity(
                    activity_id="act:sha256:bbb",
                    workflow_id="wf:sha256:test",
                    activity_type="Assign",
                    node_id="act2",
                ),
            ],
        )

        parse_result = ParseResult(content=content, success=True)

        normalizer = Normalizer()
        workflow_dto = normalizer.normalize(parse_result, sort_output=True)

        # Verify arguments sorted by name
        assert workflow_dto.arguments[0].name == "alfa"
        assert workflow_dto.arguments[1].name == "bravo"
        assert workflow_dto.arguments[2].name == "zed"

        # Verify variables sorted by name
        assert workflow_dto.variables[0].name == "varA"
        assert workflow_dto.variables[1].name == "varB"
        assert workflow_dto.variables[2].name == "varZ"

        # Verify activities sorted by ID
        assert workflow_dto.activities[0].id == "act:sha256:aaa"
        assert workflow_dto.activities[1].id == "act:sha256:bbb"
        assert workflow_dto.activities[2].id == "act:sha256:zzz"

    def test_source_order_preservation(self):
        """Test that source order is preserved by default (sort_output=False)."""
        content = WorkflowContent(
            arguments=[
                WorkflowArgument(name="zed", type="System.String", direction="in"),
                WorkflowArgument(name="alfa", type="System.String", direction="in"),
                WorkflowArgument(name="bravo", type="System.String", direction="in"),
            ],
            variables=[
                WorkflowVariable(name="varZ", type="System.Int32"),
                WorkflowVariable(name="varA", type="System.Int32"),
                WorkflowVariable(name="varB", type="System.Int32"),
            ],
            activities=[
                Activity(
                    activity_id="act:sha256:zzz",
                    workflow_id="wf:sha256:test",
                    activity_type="Assign",
                    node_id="act3",
                ),
                Activity(
                    activity_id="act:sha256:aaa",
                    workflow_id="wf:sha256:test",
                    activity_type="Assign",
                    node_id="act1",
                ),
                Activity(
                    activity_id="act:sha256:bbb",
                    workflow_id="wf:sha256:test",
                    activity_type="Assign",
                    node_id="act2",
                ),
            ],
        )

        parse_result = ParseResult(content=content, success=True)

        normalizer = Normalizer()
        workflow_dto = normalizer.normalize(parse_result)  # sort_output=False by default

        # Verify source order preserved (NOT sorted)
        assert workflow_dto.arguments[0].name == "zed"
        assert workflow_dto.arguments[1].name == "alfa"
        assert workflow_dto.arguments[2].name == "bravo"

        assert workflow_dto.variables[0].name == "varZ"
        assert workflow_dto.variables[1].name == "varA"
        assert workflow_dto.variables[2].name == "varB"

        assert workflow_dto.activities[0].id == "act:sha256:zzz"
        assert workflow_dto.activities[1].id == "act:sha256:aaa"
        assert workflow_dto.activities[2].id == "act:sha256:bbb"

    def test_normalize_metadata(self):
        """Test that metadata is properly populated."""
        content = WorkflowContent(
            root_annotation="This is the main workflow",
            display_name="Main Workflow",
            description="Processes incoming files",
            expression_language="CSharp",
        )

        parse_result = ParseResult(content=content, success=True)

        normalizer = Normalizer()
        workflow_dto = normalizer.normalize(parse_result, workflow_name="Main")

        # Verify metadata
        assert workflow_dto.metadata.annotation == "This is the main workflow"
        assert workflow_dto.metadata.display_name == "Main Workflow"
        assert workflow_dto.metadata.description == "Processes incoming files"
        assert workflow_dto.metadata.expression_language == "CSharp"

    def test_normalize_source_info(self):
        """Test that source info is populated."""
        content = WorkflowContent()

        parse_result = ParseResult(
            content=content,
            success=True,
            file_path="workflows/Main.xaml",
            diagnostics=ParseDiagnostics(file_size_bytes=5678),
        )

        normalizer = Normalizer()
        workflow_dto = normalizer.normalize(parse_result)

        # Verify source info
        assert workflow_dto.source.path == "workflows/Main.xaml"
        assert workflow_dto.source.size_bytes == 5678
        assert workflow_dto.source.encoding == "utf-8"

    def test_normalize_custom_timestamp(self):
        """Test using custom collected_at timestamp."""
        content = WorkflowContent()
        parse_result = ParseResult(content=content, success=True)

        normalizer = Normalizer()
        custom_timestamp = "2025-10-11T12:00:00Z"
        workflow_dto = normalizer.normalize(parse_result, collected_at=custom_timestamp)

        # Verify custom timestamp used
        assert workflow_dto.collected_at == custom_timestamp

    def test_parse_project_dependencies_exact_version(self):
        """Test parsing exact version constraints [X.Y.Z]."""
        normalizer = Normalizer()
        deps = {
            "UiPath.Excel.Activities": "[3.0.1]",
            "UiPath.System.Activities": "[25.4.4]",
        }

        result = normalizer._parse_project_dependencies(deps)

        assert len(result) == 2
        assert result[0].package == "UiPath.Excel.Activities"
        assert result[0].version == "3.0.1"
        assert result[1].package == "UiPath.System.Activities"
        assert result[1].version == "25.4.4"

    def test_parse_project_dependencies_range(self):
        """Test parsing version ranges."""
        normalizer = Normalizer()
        deps = {"SomePackage": "[3.0,4.0)", "AnotherPackage": "[2.0,)"}

        result = normalizer._parse_project_dependencies(deps)

        assert len(result) == 2
        assert result[0].version == "3.0"  # Takes first version from range
        assert result[1].version == "2.0"

    def test_parse_project_dependencies_plain_version(self):
        """Test parsing plain version without brackets."""
        normalizer = Normalizer()
        deps = {"PlainPackage": "1.2.3"}

        result = normalizer._parse_project_dependencies(deps)

        assert len(result) == 1
        assert result[0].package == "PlainPackage"
        assert result[0].version == "1.2.3"

    def test_normalize_with_project_dependencies(self):
        """Test that project dependencies are included in workflow DTO."""
        content = WorkflowContent()
        parse_result = ParseResult(content=content, success=True)

        normalizer = Normalizer()
        project_deps = {"UiPath.Excel.Activities": "[3.0.1]"}

        # Execute
        workflow_dto = normalizer.normalize(parse_result, project_dependencies=project_deps)

        # Verify
        assert len(workflow_dto.dependencies) == 1
        assert workflow_dto.dependencies[0].package == "UiPath.Excel.Activities"
        assert workflow_dto.dependencies[0].version == "3.0.1"

    def test_normalize_without_project_dependencies(self):
        """Test backward compatibility when project_dependencies is None."""
        content = WorkflowContent()
        parse_result = ParseResult(content=content, success=True)

        normalizer = Normalizer()

        # Execute (no project_dependencies parameter)
        workflow_dto = normalizer.normalize(parse_result)

        # Verify - should have empty dependencies
        assert workflow_dto.dependencies == []

    def test_normalize_with_multiple_project_dependencies(self):
        """Test parsing multiple project dependencies."""
        content = WorkflowContent()
        parse_result = ParseResult(content=content, success=True)

        normalizer = Normalizer()
        project_deps = {
            "UiPath.Excel.Activities": "[3.0.1]",
            "UiPath.System.Activities": "[25.4.4]",
            "UiPath.UIAutomation.Activities": "[23.10.0]",
        }

        workflow_dto = normalizer.normalize(parse_result, project_dependencies=project_deps)

        # Verify all dependencies present
        assert len(workflow_dto.dependencies) == 3
        packages = {dep.package for dep in workflow_dto.dependencies}
        assert "UiPath.Excel.Activities" in packages
        assert "UiPath.System.Activities" in packages
        assert "UiPath.UIAutomation.Activities" in packages

        # Verify versions parsed correctly
        for dep in workflow_dto.dependencies:
            assert not dep.version.startswith("[")
            assert not dep.version.endswith("]")
            assert dep.version != "unknown"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
