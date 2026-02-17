"""Unit tests for emitter renderers (pure functions, no I/O)."""

import pytest
from pathlib import Path
from dataclasses import dataclass

from cpmf_uips_xaml.stages.emit.renderers.json_renderer import JsonRenderer
from cpmf_uips_xaml.stages.emit.renderers.mermaid_renderer import MermaidRenderer
from cpmf_uips_xaml.stages.emit.renderers.doc_renderer import DocRenderer
from cpmf_uips_xaml.stages.emit.renderers.base import RenderResult


# Test config helpers
@dataclass
class MockEmitterConfig:
    """Mock config for testing renderers."""

    pretty: bool = True
    indent: int = 2
    combine: bool = False
    extra: dict = None

    def __post_init__(self):
        if self.extra is None:
            self.extra = {}


# ============================================================================
# JsonRenderer Tests
# ============================================================================


class TestJsonRenderer:
    """Test JsonRenderer pure function behavior."""

    def test_name_and_extension(self):
        """Test renderer metadata."""
        renderer = JsonRenderer()
        assert renderer.name == "json"
        assert renderer.output_extension == ".json"

    def test_render_one_simple_workflow(self):
        """Test rendering single workflow to JSON string."""
        renderer = JsonRenderer()
        workflow_dict = {
            "id": "wf1",
            "name": "TestWorkflow",
            "activities": [],
            "arguments": [],
        }
        config = MockEmitterConfig(pretty=True, indent=2)

        result = renderer.render_one(workflow_dict, config)

        assert isinstance(result, RenderResult)
        assert result.success is True
        assert isinstance(result.content, str)
        assert "TestWorkflow" in result.content
        assert '"id": "wf1"' in result.content  # Pretty formatted
        assert result.metadata["suggested_filename"] == "TestWorkflow.json"
        assert result.errors == []

    def test_render_one_compact_json(self):
        """Test compact JSON rendering (pretty=False)."""
        renderer = JsonRenderer()
        workflow_dict = {"id": "wf1", "name": "Test"}
        config = MockEmitterConfig(pretty=False)

        result = renderer.render_one(workflow_dict, config)

        assert result.success
        # No indentation in compact mode
        assert "\n" not in result.content or result.content.count("\n") == 0

    def test_render_one_with_unicode(self):
        """Test JSON rendering preserves unicode characters."""
        renderer = JsonRenderer()
        workflow_dict = {"id": "wf1", "name": "Test中文"}
        config = MockEmitterConfig()

        result = renderer.render_one(workflow_dict, config)

        assert result.success
        assert "Test中文" in result.content  # Unicode preserved (ensure_ascii=False)

    def test_render_one_error_handling(self):
        """Test error handling for unserializable data."""
        renderer = JsonRenderer()
        # Create unserializable data (set is not JSON serializable)
        workflow_dict = {"id": "wf1", "data": {1, 2, 3}}
        config = MockEmitterConfig()

        result = renderer.render_one(workflow_dict, config)

        assert result.success is False
        assert result.content == ""
        assert len(result.errors) > 0
        assert "Failed to render workflow" in result.errors[0]

    def test_render_many_combined(self):
        """Test rendering multiple workflows into single JSON."""
        renderer = JsonRenderer()
        workflows = [
            {"id": "wf1", "name": "Workflow1"},
            {"id": "wf2", "name": "Workflow2"},
        ]
        config = MockEmitterConfig(combine=True)

        result = renderer.render_many(workflows, config)

        assert result.success
        assert isinstance(result.content, str)
        assert "Workflow1" in result.content
        assert "Workflow2" in result.content
        assert "workflows" in result.content  # Collection wrapper
        assert result.metadata["suggested_filename"] == "workflows.json"

    def test_render_many_separate(self):
        """Test rendering multiple workflows as separate files."""
        renderer = JsonRenderer()
        workflows = [
            {"id": "wf1", "name": "Workflow1"},
            {"id": "wf2", "name": "Workflow2"},
        ]
        config = MockEmitterConfig(combine=False)

        result = renderer.render_many(workflows, config)

        assert result.success
        assert isinstance(result.content, dict)
        assert "Workflow1.json" in result.content
        assert "Workflow2.json" in result.content
        assert "Workflow1" in result.content["Workflow1.json"]
        assert result.metadata["count"] == 2


# ============================================================================
# MermaidRenderer Tests
# ============================================================================


class TestMermaidRenderer:
    """Test MermaidRenderer pure function behavior."""

    def test_name_and_extension(self):
        """Test renderer metadata."""
        renderer = MermaidRenderer()
        assert renderer.name == "mermaid"
        assert renderer.output_extension == ".mmd"

    def test_render_one_empty_workflow(self):
        """Test rendering empty workflow."""
        renderer = MermaidRenderer()
        workflow_dict = {
            "id": "wf1",
            "name": "EmptyWorkflow",
            "activities": [],
            "edges": [],
        }
        config = MockEmitterConfig()

        result = renderer.render_one(workflow_dict, config)

        assert result.success
        assert isinstance(result.content, str)
        assert "flowchart TD" in result.content
        assert "EmptyWorkflow" in result.content
        assert result.metadata["suggested_filename"] == "EmptyWorkflow.mmd"

    def test_render_one_with_activities(self):
        """Test rendering workflow with activities."""
        renderer = MermaidRenderer()
        workflow_dict = {
            "id": "wf1",
            "name": "TestWorkflow",
            "activities": [
                {
                    "id": "activity_1",
                    "display_name": "Log Message",
                    "type_short": "LogMessage",
                    "depth": 0,
                },
                {
                    "id": "activity_2",
                    "display_name": "Assign",
                    "type_short": "Assign",
                    "depth": 0,
                },
            ],
            "edges": [
                {"from_id": "activity_1", "to_id": "activity_2", "kind": "sequence"}
            ],
        }
        config = MockEmitterConfig()

        result = renderer.render_one(workflow_dict, config)

        assert result.success
        assert "flowchart TD" in result.content
        assert "Log Message" in result.content
        assert "Assign" in result.content
        assert "activity_1" in result.content
        assert "-->" in result.content  # Edge

    def test_render_one_with_decision_node(self):
        """Test diamond shape for decision nodes."""
        renderer = MermaidRenderer()
        workflow_dict = {
            "id": "wf1",
            "name": "DecisionWorkflow",
            "activities": [
                {
                    "id": "if_1",
                    "display_name": "Check Value",
                    "type_short": "If",
                    "depth": 0,
                }
            ],
            "edges": [],
        }
        config = MockEmitterConfig()

        result = renderer.render_one(workflow_dict, config)

        assert result.success
        # Diamond shape for If activity
        assert "{" in result.content and "}" in result.content

    def test_render_one_with_container_node(self):
        """Test rounded rectangle for container nodes."""
        renderer = MermaidRenderer()
        workflow_dict = {
            "id": "wf1",
            "name": "ContainerWorkflow",
            "activities": [
                {
                    "id": "seq_1",
                    "display_name": "Main Sequence",
                    "type_short": "Sequence",
                    "depth": 0,
                }
            ],
            "edges": [],
        }
        config = MockEmitterConfig()

        result = renderer.render_one(workflow_dict, config)

        assert result.success
        # Rounded rectangle for Sequence
        assert '(["' in result.content and '"])' in result.content

    def test_render_one_max_depth_filtering(self):
        """Test max_depth filtering of activities."""
        renderer = MermaidRenderer()
        workflow_dict = {
            "id": "wf1",
            "name": "DeepWorkflow",
            "activities": [
                {"id": "a1", "display_name": "Root", "type_short": "Sequence", "depth": 0},
                {"id": "a2", "display_name": "Level1", "type_short": "Assign", "depth": 1},
                {"id": "a3", "display_name": "Level3", "type_short": "Assign", "depth": 3},
                {"id": "a4", "display_name": "Level10", "type_short": "Assign", "depth": 10},
            ],
            "edges": [],
        }
        config = MockEmitterConfig(extra={"max_depth": 2})

        result = renderer.render_one(workflow_dict, config)

        assert result.success
        assert "Root" in result.content
        assert "Level1" in result.content
        assert "Level3" not in result.content  # Depth 3 > max_depth 2
        assert "Level10" not in result.content

    def test_sanitize_id(self):
        """Test ID sanitization for Mermaid compatibility."""
        renderer = MermaidRenderer()

        # Test various problematic IDs
        assert renderer._sanitize_id("normal_id").startswith("normal_id")
        assert renderer._sanitize_id("123_starts_with_digit").startswith("n123")  # Prefixed
        assert "_" in renderer._sanitize_id("has-dashes-and.dots")  # Replaced
        assert renderer._sanitize_id("").startswith("node")  # Fallback

    def test_format_label_truncation(self):
        """Test label truncation for long names."""
        renderer = MermaidRenderer()
        activity = {
            "display_name": "A" * 50,  # Very long name
            "type_short": "Assign",
        }

        label = renderer._format_label(activity)

        # Name is truncated to 37 chars + "..." + "\n(Assign)" = about 50 chars
        assert "..." in label
        assert label.startswith("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")  # 37 A's

    def test_format_label_escape_quotes(self):
        """Test escaping of quotes in labels."""
        renderer = MermaidRenderer()
        activity = {
            "display_name": 'Message with "quotes"',
            "type_short": "LogMessage",
        }

        label = renderer._format_label(activity)

        assert '\\"' in label  # Quotes escaped

    def test_edge_styles(self):
        """Test different edge styles for different kinds."""
        renderer = MermaidRenderer()

        # Error edge (thick)
        assert renderer._get_edge_style({"kind": "catch"}) == ("==>", "")

        # Conditional edge (dotted)
        assert renderer._get_edge_style({"kind": "then"}) == ("-.->", "")
        assert renderer._get_edge_style({"kind": "else"}) == ("-.->", "")

        # Default edge (solid)
        assert renderer._get_edge_style({"kind": "sequence"}) == ("-->", "")
        assert renderer._get_edge_style({}) == ("-->", "")

    def test_generate_styling(self):
        """Test CSS styling generation."""
        renderer = MermaidRenderer()
        activities = [
            {"id": "if_1", "type_short": "If"},
            {"id": "seq_1", "type_short": "Sequence"},
            {"id": "try_1", "type_short": "TryCatch"},
        ]

        styles = renderer._generate_styling(activities)

        styles_str = "\n".join(styles)
        assert "decisionStyle" in styles_str  # If node
        assert "containerStyle" in styles_str  # Sequence node
        assert "errorStyle" in styles_str  # TryCatch node
        assert "#6495ED" in styles_str  # Blue for decisions
        assert "#90EE90" in styles_str  # Green for containers
        assert "#FFA500" in styles_str  # Orange for error handling

    def test_render_many_separate(self):
        """Test rendering multiple workflows as separate Mermaid files."""
        renderer = MermaidRenderer()
        workflows = [
            {"id": "wf1", "name": "Workflow1", "activities": [], "edges": []},
            {"id": "wf2", "name": "Workflow2", "activities": [], "edges": []},
        ]
        config = MockEmitterConfig()

        result = renderer.render_many(workflows, config)

        assert result.success
        assert isinstance(result.content, dict)
        assert "Workflow1.mmd" in result.content
        assert "Workflow2.mmd" in result.content
        assert "flowchart TD" in result.content["Workflow1.mmd"]
        assert result.metadata["count"] == 2


# ============================================================================
# DocRenderer Tests
# ============================================================================


class TestDocRenderer:
    """Test DocRenderer stub implementation."""

    def test_name_and_extension(self):
        """Test renderer metadata."""
        renderer = DocRenderer()
        assert renderer.name == "doc"
        assert renderer.output_extension == ".md"

    def test_render_one_stub(self):
        """Test stub implementation returns placeholder."""
        renderer = DocRenderer()
        workflow_dict = {"id": "wf1", "name": "TestWorkflow"}
        config = MockEmitterConfig()

        result = renderer.render_one(workflow_dict, config)

        assert result.success
        assert isinstance(result.content, str)
        assert "TestWorkflow" in result.content
        assert result.metadata["suggested_filename"] == "TestWorkflow.md"

    def test_render_many_stub(self):
        """Test stub implementation for multiple workflows."""
        renderer = DocRenderer()
        workflows = [{"id": "wf1", "name": "Test"}]
        config = MockEmitterConfig()

        result = renderer.render_many(workflows, config)

        assert result.success
        assert isinstance(result.content, dict)


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


class TestRendererEdgeCases:
    """Test edge cases and error handling across renderers."""

    def test_json_renderer_empty_dict(self):
        """Test JSON renderer with empty workflow."""
        renderer = JsonRenderer()
        result = renderer.render_one({}, MockEmitterConfig())
        assert result.success
        assert result.content == "{}"

    def test_mermaid_renderer_missing_fields(self):
        """Test Mermaid renderer with missing optional fields."""
        renderer = MermaidRenderer()
        workflow_dict = {
            "name": "MinimalWorkflow",
            # Missing activities, edges
        }
        config = MockEmitterConfig()

        result = renderer.render_one(workflow_dict, config)

        assert result.success
        assert "flowchart TD" in result.content
        assert "MinimalWorkflow" in result.content

    def test_mermaid_renderer_activity_without_display_name(self):
        """Test Mermaid label generation when display_name is missing."""
        renderer = MermaidRenderer()
        activity = {
            "id": "a1",
            "type_short": "Assign",
            # Missing display_name
        }

        label = renderer._format_label(activity)

        assert "Assign" in label  # Falls back to type_short

    def test_mermaid_renderer_workflow_without_name(self):
        """Test suggested filename when workflow name is missing."""
        renderer = MermaidRenderer()
        workflow_dict = {
            "id": "wf1",
            # Missing name
            "activities": [],
            "edges": [],
        }
        config = MockEmitterConfig()

        result = renderer.render_one(workflow_dict, config)

        assert result.success
        # Fallback filename
        assert result.metadata["suggested_filename"] in ["workflow.mmd", "Untitled.mmd"]
