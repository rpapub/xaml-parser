"""Tests for Mermaid diagram emitter."""

from pathlib import Path

from xaml_parser.dto import ActivityDto, EdgeDto, WorkflowDto
from xaml_parser.emitters import EmitterConfig
from xaml_parser.emitters.mermaid_emitter import MermaidEmitter


class TestMermaidEmitter:
    """Test Mermaid emitter."""

    def test_emitter_properties(self) -> None:
        """Test emitter basic properties."""
        emitter = MermaidEmitter()
        assert emitter.name == "mermaid"

    def test_emit_single_workflow(self, tmp_path: Path) -> None:
        """Test emitting a single workflow to a file."""
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
            metadata={"expression_language": "VisualBasic"},
            variables=[],
            arguments=[],
            dependencies=[],
            activities=[
                ActivityDto(
                    id="act:sha256:111",
                    type="Sequence",
                    type_short="Sequence",
                    display_name="Main Sequence",
                    location=None,
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

        output_file = tmp_path / "test.mmd"
        config = EmitterConfig()

        emitter = MermaidEmitter()
        result = emitter.emit([workflow], output_file, config)

        assert result.success
        assert len(result.files_written) == 1
        assert result.files_written[0] == output_file
        assert output_file.exists()

        content = output_file.read_text()
        assert "flowchart TD" in content
        assert "Main Sequence" in content
        assert "Sequence" in content

    def test_emit_multiple_workflows(self, tmp_path: Path) -> None:
        """Test emitting multiple workflows to a directory."""
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

        output_dir = tmp_path / "diagrams"
        config = EmitterConfig()

        emitter = MermaidEmitter()
        result = emitter.emit(workflows, output_dir, config)

        assert result.success
        assert len(result.files_written) == 3
        assert output_dir.exists()

        for i in range(3):
            file_path = output_dir / f"Workflow{i}.mmd"
            assert file_path in result.files_written
            assert file_path.exists()

    def test_node_shapes(self, tmp_path: Path) -> None:
        """Test different node shapes based on activity type."""
        workflow = WorkflowDto(
            schema_id="https://rpax.io/schemas/xaml-workflow.json",
            schema_version="1.0.0",
            collected_at="2025-10-11T10:00:00Z",
            id="wf:sha256:abc123",
            name="ShapeTest",
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
                    id="act:sha256:if1",
                    type="If",
                    type_short="If",
                    display_name="Condition",
                    location=None,
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
                    id="act:sha256:seq1",
                    type="Sequence",
                    type_short="Sequence",
                    display_name="Actions",
                    location=None,
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
                    id="act:sha256:assign1",
                    type="Assign",
                    type_short="Assign",
                    display_name="Set Value",
                    location=None,
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
            ],
            edges=[],
            invocations=[],
            issues=[],
        )

        output_file = tmp_path / "shapes.mmd"
        config = EmitterConfig()

        emitter = MermaidEmitter()
        result = emitter.emit([workflow], output_file, config)

        assert result.success

        content = output_file.read_text()
        # Decision nodes use curly braces (diamond shape)
        assert "{" in content and "}" in content  # If node
        # Container nodes use ([...])
        assert "([" in content and "])" in content  # Sequence node
        # Regular activities use square brackets
        assert "[" in content  # Assign node

    def test_edge_generation(self, tmp_path: Path) -> None:
        """Test edge generation with different kinds."""
        workflow = WorkflowDto(
            schema_id="https://rpax.io/schemas/xaml-workflow.json",
            schema_version="1.0.0",
            collected_at="2025-10-11T10:00:00Z",
            id="wf:sha256:abc123",
            name="EdgeTest",
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
                    location=None,
                    parent_id=None,
                    children=["act:sha256:2", "act:sha256:3"],
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
                    display_name="Then",
                    location=None,
                    parent_id="act:sha256:1",
                    children=[],
                    depth=2,
                    properties={},
                    in_args={},
                    out_args={},
                    annotation=None,
                    expressions=[],
                    variables_referenced=[],
                ),
                ActivityDto(
                    id="act:sha256:3",
                    type="Assign",
                    type_short="Assign",
                    display_name="Else",
                    location=None,
                    parent_id="act:sha256:1",
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
                    id="edge:sha256:then",
                    from_id="act:sha256:1",
                    to_id="act:sha256:2",
                    kind="Then",
                    condition=None,
                    label=None,
                ),
                EdgeDto(
                    id="edge:sha256:else",
                    from_id="act:sha256:1",
                    to_id="act:sha256:3",
                    kind="Else",
                    condition=None,
                    label=None,
                ),
            ],
            invocations=[],
            issues=[],
        )

        output_file = tmp_path / "edges.mmd"
        config = EmitterConfig()

        emitter = MermaidEmitter()
        result = emitter.emit([workflow], output_file, config)

        assert result.success

        content = output_file.read_text()
        # Check for edge labels
        assert "|Then|" in content
        assert "|Else|" in content
        # Conditional edges use dotted arrows
        assert "-.->|" in content

    def test_max_depth_filtering(self, tmp_path: Path) -> None:
        """Test filtering activities by max depth."""
        workflow = WorkflowDto(
            schema_id="https://rpax.io/schemas/xaml-workflow.json",
            schema_version="1.0.0",
            collected_at="2025-10-11T10:00:00Z",
            id="wf:sha256:abc123",
            name="DepthTest",
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
                    id="act:sha256:d1",
                    type="Sequence",
                    type_short="Sequence",
                    display_name="Depth 1",
                    location=None,
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
                    id="act:sha256:d5",
                    type="Assign",
                    type_short="Assign",
                    display_name="Depth 5",
                    location=None,
                    parent_id=None,
                    children=[],
                    depth=5,
                    properties={},
                    in_args={},
                    out_args={},
                    annotation=None,
                    expressions=[],
                    variables_referenced=[],
                ),
                ActivityDto(
                    id="act:sha256:d10",
                    type="Assign",
                    type_short="Assign",
                    display_name="Depth 10",
                    location=None,
                    parent_id=None,
                    children=[],
                    depth=10,
                    properties={},
                    in_args={},
                    out_args={},
                    annotation=None,
                    expressions=[],
                    variables_referenced=[],
                ),
            ],
            edges=[],
            invocations=[],
            issues=[],
        )

        output_file = tmp_path / "depth.mmd"
        config = EmitterConfig(extra={"max_depth": 5})

        emitter = MermaidEmitter()
        result = emitter.emit([workflow], output_file, config)

        assert result.success

        content = output_file.read_text()
        assert "Depth 1" in content
        assert "Depth 5" in content
        assert "Depth 10" not in content

    def test_sanitize_id(self) -> None:
        """Test ID sanitization for Mermaid."""
        emitter = MermaidEmitter()

        # Test special characters
        assert emitter._sanitize_id("act:sha256:abc123") == "act_sha256_abc123"
        assert emitter._sanitize_id("wf:123-456") == "wf_123_456"

        # Test starting with letter
        result = emitter._sanitize_id("123abc")
        assert result[0].isalpha()
        assert result == "n123abc"

    def test_sanitize_filename(self) -> None:
        """Test filename sanitization."""
        emitter = MermaidEmitter()

        assert emitter._sanitize_filename("My Workflow") == "My Workflow"
        assert emitter._sanitize_filename("Test/Invalid:Name") == "Test_Invalid_Name"
        assert emitter._sanitize_filename("  Trimmed  ") == "Trimmed"

    def test_error_handling(self, tmp_path: Path) -> None:
        """Test error handling in emitter."""
        emitter = MermaidEmitter()

        # Test with invalid path (parent doesn't exist if we try to write to a readonly location)
        # For now, we'll just verify the emitter handles workflows properly
        workflow = WorkflowDto(
            schema_id="https://rpax.io/schemas/xaml-workflow.json",
            schema_version="1.0.0",
            collected_at="2025-10-11T10:00:00Z",
            id="wf:sha256:test",
            name="Test",
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

        output_file = tmp_path / "test.mmd"
        config = EmitterConfig()

        result = emitter.emit([workflow], output_file, config)
        assert result.success is True
        assert len(result.errors) == 0


class TestMermaidFormatting:
    """Test Mermaid diagram formatting."""

    def test_label_truncation(self) -> None:
        """Test that long labels are truncated."""
        emitter = MermaidEmitter()

        activity = ActivityDto(
            id="act:sha256:long",
            type="Assign",
            type_short="Assign",
            display_name="A" * 100,  # Very long name
            location=None,
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

        label = emitter._format_label(activity)
        # Should be truncated
        assert len(label) < 100
        assert "..." in label

    def test_label_escaping(self) -> None:
        """Test that special characters are escaped in labels."""
        emitter = MermaidEmitter()

        activity = ActivityDto(
            id="act:sha256:escape",
            type="Assign",
            type_short="Assign",
            display_name='Name with "quotes"',
            location=None,
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

        label = emitter._format_label(activity)
        # Quotes should be escaped
        assert '\\"' in label

    def test_annotation_in_comments(self, tmp_path: Path) -> None:
        """Test that workflow annotations appear as comments."""
        workflow = WorkflowDto(
            schema_id="https://rpax.io/schemas/xaml-workflow.json",
            schema_version="1.0.0",
            collected_at="2025-10-11T10:00:00Z",
            id="wf:sha256:annotated",
            name="AnnotatedWorkflow",
            source={
                "path": "test.xaml",
                "path_aliases": [],
                "hash": "",
                "size_bytes": 100,
                "encoding": "utf-8",
            },
            metadata={
                "expression_language": "VisualBasic",
                "annotation": "This is a test workflow annotation",
            },
            variables=[],
            arguments=[],
            dependencies=[],
            activities=[],
            edges=[],
            invocations=[],
            issues=[],
        )

        output_file = tmp_path / "annotated.mmd"
        config = EmitterConfig()

        emitter = MermaidEmitter()
        result = emitter.emit([workflow], output_file, config)

        assert result.success

        content = output_file.read_text()
        assert "%% Workflow: AnnotatedWorkflow" in content
        assert "%% This is a test workflow annotation" in content
