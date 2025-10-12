"""Tests for Markdown documentation emitter."""

from pathlib import Path

from xaml_parser.dto import (
    ActivityDto,
    ArgumentDto,
    EdgeDto,
    IssueDto,
    VariableDto,
    WorkflowDto,
)
from xaml_parser.emitters import EmitterConfig
from xaml_parser.emitters.doc_emitter import DocEmitter


class TestDocEmitter:
    """Test documentation emitter."""

    def test_emitter_properties(self) -> None:
        """Test emitter basic properties."""
        emitter = DocEmitter()
        assert emitter.name == "doc"
        assert emitter.output_extension == ".md"

    def test_emit_single_workflow(self, tmp_path: Path) -> None:
        """Test emitting documentation for a single workflow."""
        workflow = WorkflowDto(
            schema_id="https://rpax.io/schemas/xaml-workflow.json",
            schema_version="1.0.0",
            collected_at="2025-10-11T10:00:00Z",
            id="wf:sha256:abc123",
            name="TestWorkflow",
            source={
                "path": "test.xaml",
                "path_aliases": [],
                "hash": "",
                "size_bytes": 100,
                "encoding": "utf-8",
            },
            metadata={
                "expression_language": "VisualBasic",
                "annotation": "This is a test workflow",
            },
            variables=[],
            arguments=[],
            dependencies=[],
            activities=[
                ActivityDto(
                    id="act:sha256:111",
                    type="Sequence",
                    type_short="Sequence",
                    display_name="Main Sequence",
                    parent_id=None,
                    children=[],
                    depth=1,
                    properties={},
                    in_args={},
                    out_args={},
                    annotation=None,
                    expressions=[],
                    variables_referenced=[],
                )
            ],
            edges=[],
            invocations=[],
            issues=[],
        )

        output_dir = tmp_path / "docs"
        config = EmitterConfig()

        emitter = DocEmitter()
        result = emitter.emit([workflow], output_dir, config)

        assert result.success
        assert len(result.files_written) == 2  # workflow doc + index

        # Check workflow doc exists
        workflow_doc = output_dir / "workflows" / "TestWorkflow.md"
        assert workflow_doc in result.files_written
        assert workflow_doc.exists()

        content = workflow_doc.read_text()
        assert "# TestWorkflow" in content
        assert "This is a test workflow" in content
        assert "Main Sequence" in content

        # Check index exists
        index = output_dir / "index.md"
        assert index in result.files_written
        assert index.exists()

    def test_emit_multiple_workflows(self, tmp_path: Path) -> None:
        """Test emitting documentation for multiple workflows."""
        workflows = [
            WorkflowDto(
                schema_id="https://rpax.io/schemas/xaml-workflow.json",
                schema_version="1.0.0",
                collected_at="2025-10-11T10:00:00Z",
                id=f"wf:sha256:abc{i}",
                name=f"Workflow{i}",
                source={
                    "path": f"test{i}.xaml",
                    "path_aliases": [],
                    "hash": "",
                    "size_bytes": 100,
                    "encoding": "utf-8",
                },
                metadata={"expression_language": "VisualBasic"},
                variables=[],
                arguments=[],
                dependencies=[],
                activities=[],
                edges=[],
                invocations=[],
                issues=[],
            )
            for i in range(3)
        ]

        output_dir = tmp_path / "docs"
        config = EmitterConfig()

        emitter = DocEmitter()
        result = emitter.emit(workflows, output_dir, config)

        assert result.success
        assert len(result.files_written) == 4  # 3 workflow docs + index

        for i in range(3):
            workflow_doc = output_dir / "workflows" / f"Workflow{i}.md"
            assert workflow_doc in result.files_written
            assert workflow_doc.exists()

    def test_workflow_with_arguments(self, tmp_path: Path) -> None:
        """Test documentation includes arguments."""
        workflow = WorkflowDto(
            schema_id="https://rpax.io/schemas/xaml-workflow.json",
            schema_version="1.0.0",
            collected_at="2025-10-11T10:00:00Z",
            id="wf:sha256:test",
            name="TestArgs",
            source={
                "path": "test.xaml",
                "path_aliases": [],
                "hash": "",
                "size_bytes": 100,
                "encoding": "utf-8",
            },
            metadata={"expression_language": "VisualBasic"},
            variables=[],
            arguments=[
                ArgumentDto(
                    id="arg:sha256:1",
                    name="in_FilePath",
                    type="InArgument(x:String)",
                    direction="In",
                    annotation="Input file path",
                ),
                ArgumentDto(
                    id="arg:sha256:2",
                    name="out_Result",
                    type="OutArgument(x:String)",
                    direction="Out",
                    annotation=None,
                ),
            ],
            dependencies=[],
            activities=[],
            edges=[],
            invocations=[],
            issues=[],
        )

        output_dir = tmp_path / "docs"
        config = EmitterConfig()

        emitter = DocEmitter()
        result = emitter.emit([workflow], output_dir, config)

        assert result.success

        workflow_doc = output_dir / "workflows" / "TestArgs.md"
        content = workflow_doc.read_text()
        assert "## Arguments" in content
        assert "in_FilePath" in content
        assert "Input file path" in content
        assert "out_Result" in content

    def test_workflow_with_variables(self, tmp_path: Path) -> None:
        """Test documentation includes variables."""
        workflow = WorkflowDto(
            schema_id="https://rpax.io/schemas/xaml-workflow.json",
            schema_version="1.0.0",
            collected_at="2025-10-11T10:00:00Z",
            id="wf:sha256:test",
            name="TestVars",
            source={
                "path": "test.xaml",
                "path_aliases": [],
                "hash": "",
                "size_bytes": 100,
                "encoding": "utf-8",
            },
            metadata={"expression_language": "VisualBasic"},
            variables=[
                VariableDto(
                    id="var:sha256:1",
                    name="varCount",
                    type="Int32",
                    scope="workflow",
                    default_value="0",
                ),
                VariableDto(
                    id="var:sha256:2",
                    name="varMessage",
                    type="String",
                    scope="workflow",
                    default_value=None,
                ),
            ],
            arguments=[],
            dependencies=[],
            activities=[],
            edges=[],
            invocations=[],
            issues=[],
        )

        output_dir = tmp_path / "docs"
        config = EmitterConfig()

        emitter = DocEmitter()
        result = emitter.emit([workflow], output_dir, config)

        assert result.success

        workflow_doc = output_dir / "workflows" / "TestVars.md"
        content = workflow_doc.read_text()
        assert "## Variables" in content
        assert "varCount" in content
        assert "varMessage" in content

    def test_workflow_with_edges(self, tmp_path: Path) -> None:
        """Test documentation includes control flow edges."""
        workflow = WorkflowDto(
            schema_id="https://rpax.io/schemas/xaml-workflow.json",
            schema_version="1.0.0",
            collected_at="2025-10-11T10:00:00Z",
            id="wf:sha256:test",
            name="TestEdges",
            source={
                "path": "test.xaml",
                "path_aliases": [],
                "hash": "",
                "size_bytes": 100,
                "encoding": "utf-8",
            },
            metadata={"expression_language": "VisualBasic"},
            variables=[],
            arguments=[],
            dependencies=[],
            activities=[
                ActivityDto(
                    id="act:sha256:1",
                    type="If",
                    type_short="If",
                    display_name="Check",
                    parent_id=None,
                    children=[],
                    depth=1,
                    properties={},
                    in_args={},
                    out_args={},
                    annotation=None,
                    expressions=[],
                    variables_referenced=[],
                ),
                ActivityDto(
                    id="act:sha256:2",
                    type="Assign",
                    type_short="Assign",
                    display_name="Set Value",
                    parent_id=None,
                    children=[],
                    depth=2,
                    properties={},
                    in_args={},
                    out_args={},
                    annotation=None,
                    expressions=[],
                    variables_referenced=[],
                ),
            ],
            edges=[
                EdgeDto(
                    id="edge:sha256:1",
                    from_id="act:sha256:1",
                    to_id="act:sha256:2",
                    kind="Then",
                    condition="varCount > 0",
                    label=None,
                )
            ],
            invocations=[],
            issues=[],
        )

        output_dir = tmp_path / "docs"
        config = EmitterConfig()

        emitter = DocEmitter()
        result = emitter.emit([workflow], output_dir, config)

        assert result.success

        workflow_doc = output_dir / "workflows" / "TestEdges.md"
        content = workflow_doc.read_text()
        assert "## Control Flow" in content
        assert "Then" in content
        assert "varCount > 0" in content

    def test_workflow_with_issues(self, tmp_path: Path) -> None:
        """Test documentation includes issues."""
        workflow = WorkflowDto(
            schema_id="https://rpax.io/schemas/xaml-workflow.json",
            schema_version="1.0.0",
            collected_at="2025-10-11T10:00:00Z",
            id="wf:sha256:test",
            name="TestIssues",
            source={
                "path": "test.xaml",
                "path_aliases": [],
                "hash": "",
                "size_bytes": 100,
                "encoding": "utf-8",
            },
            metadata={"expression_language": "VisualBasic"},
            variables=[],
            arguments=[],
            dependencies=[],
            activities=[],
            edges=[],
            invocations=[],
            issues=[
                IssueDto(
                    level="warning",
                    message="Unknown activity type",
                    path=None,
                    code=None,
                )
            ],
        )

        output_dir = tmp_path / "docs"
        config = EmitterConfig()

        emitter = DocEmitter()
        result = emitter.emit([workflow], output_dir, config)

        assert result.success

        workflow_doc = output_dir / "workflows" / "TestIssues.md"
        content = workflow_doc.read_text()
        assert "## Issues" in content
        assert "WARNING" in content
        assert "Unknown activity type" in content

    def test_index_generation(self, tmp_path: Path) -> None:
        """Test index generation with project metadata."""
        workflows = [
            WorkflowDto(
                schema_id="https://rpax.io/schemas/xaml-workflow.json",
                schema_version="1.0.0",
                collected_at="2025-10-11T10:00:00Z",
                id=f"wf:sha256:abc{i}",
                name=f"Workflow{i}",
                source={
                    "path": f"test{i}.xaml",
                    "path_aliases": [],
                    "hash": "",
                    "size_bytes": 100,
                    "encoding": "utf-8",
                },
                metadata={"expression_language": "VisualBasic"},
                variables=[],
                arguments=[],
                dependencies=[],
                activities=[
                    ActivityDto(
                        id=f"act:sha256:{i}",
                        type="Sequence",
                        type_short="Sequence",
                        display_name=f"Sequence {i}",
                        parent_id=None,
                        children=[],
                        depth=1,
                        properties={},
                        in_args={},
                        out_args={},
                        annotation=None,
                        expressions=[],
                        variables_referenced=[],
                    )
                ],
                edges=[],
                invocations=[],
                issues=[],
            )
            for i in range(2)
        ]

        output_dir = tmp_path / "docs"
        config = EmitterConfig(
            extra={
                "project_name": "TestProject",
                "project_path": "/path/to/project",
                "main_workflow": "Workflow0",
            }
        )

        emitter = DocEmitter()
        result = emitter.emit(workflows, output_dir, config)

        assert result.success

        index = output_dir / "index.md"
        content = index.read_text()
        assert "TestProject" in content
        assert "/path/to/project" in content
        assert "Workflow0" in content
        assert "**Total Workflows:** 2" in content
        assert "**Total Activities:** 2" in content

    def test_sanitize_filename(self) -> None:
        """Test filename sanitization."""
        emitter = DocEmitter()

        assert emitter._sanitize_filename("My Workflow") == "My_Workflow"
        assert emitter._sanitize_filename("Test/Invalid:Name") == "TestInvalidName"
        assert emitter._sanitize_filename("  Trimmed  ") == "__Trimmed__"

    def test_custom_template_directory(self, tmp_path: Path) -> None:
        """Test using custom template directory."""
        # Create custom template
        custom_templates = tmp_path / "custom_templates"
        custom_templates.mkdir()

        custom_workflow_template = custom_templates / "workflow.md.j2"
        custom_workflow_template.write_text(
            "# Custom Template\n{{ workflow.name }}\n", encoding="utf-8"
        )

        custom_index_template = custom_templates / "index.md.j2"
        custom_index_template.write_text(
            "# Custom Index\nTotal: {{ workflows|length }}\n", encoding="utf-8"
        )

        # Create workflow
        workflow = WorkflowDto(
            schema_id="https://rpax.io/schemas/xaml-workflow.json",
            schema_version="1.0.0",
            collected_at="2025-10-11T10:00:00Z",
            id="wf:sha256:test",
            name="TestCustom",
            source={
                "path": "test.xaml",
                "path_aliases": [],
                "hash": "",
                "size_bytes": 100,
                "encoding": "utf-8",
            },
            metadata={"expression_language": "VisualBasic"},
            variables=[],
            arguments=[],
            dependencies=[],
            activities=[],
            edges=[],
            invocations=[],
            issues=[],
        )

        output_dir = tmp_path / "docs"
        config = EmitterConfig()

        emitter = DocEmitter(template_dir=custom_templates)
        result = emitter.emit([workflow], output_dir, config)

        assert result.success

        workflow_doc = output_dir / "workflows" / "TestCustom.md"
        content = workflow_doc.read_text()
        assert "# Custom Template" in content
        assert "TestCustom" in content

        index = output_dir / "index.md"
        index_content = index.read_text()
        assert "# Custom Index" in index_content
        assert "Total: 1" in index_content
