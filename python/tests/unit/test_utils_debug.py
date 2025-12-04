"""Tests for DebugUtils utility functions."""

import xml.etree.ElementTree as ET

from cpmf_xaml_parser.utils import DebugUtils


class TestElementInfo:
    """Tests for DebugUtils.element_info()."""

    def test_element_info_simple_element(self):
        """Test getting info from simple element."""
        elem = ET.fromstring("<root>text content</root>")
        info = DebugUtils.element_info(elem)

        assert info["tag"] == "root"
        assert info["local_name"] == "root"
        assert info["namespace"] is None
        assert info["attributes"] == {}
        assert info["text"] == "text content"
        assert info["children_count"] == 0
        assert info["child_tags"] == []

    def test_element_info_with_namespace(self):
        """Test getting info from namespaced element."""
        elem = ET.fromstring('<root xmlns="http://example.com">text</root>')
        info = DebugUtils.element_info(elem)

        assert info["local_name"] == "root"
        assert info["namespace"] == "http://example.com"
        assert "{http://example.com}root" in info["tag"]

    def test_element_info_with_attributes(self):
        """Test getting info from element with attributes."""
        elem = ET.fromstring('<root id="123" type="test">content</root>')
        info = DebugUtils.element_info(elem)

        assert info["attributes"] == {"id": "123", "type": "test"}
        assert info["text"] == "content"

    def test_element_info_with_children(self):
        """Test getting info from element with children."""
        elem = ET.fromstring("<root><child1 /><child2 /><child3 /></root>")
        info = DebugUtils.element_info(elem)

        assert info["children_count"] == 3
        assert info["child_tags"] == ["child1", "child2", "child3"]
        assert info["text"] is None

    def test_element_info_empty_element(self):
        """Test getting info from empty element."""
        elem = ET.fromstring("<root />")
        info = DebugUtils.element_info(elem)

        assert info["tag"] == "root"
        assert info["text"] is None
        assert info["children_count"] == 0
        assert info["child_tags"] == []

    def test_element_info_with_whitespace_text(self):
        """Test that whitespace in text is stripped."""
        elem = ET.fromstring("<root>   text with spaces   </root>")
        info = DebugUtils.element_info(elem)

        assert info["text"] == "text with spaces"

    def test_element_info_namespaced_children(self):
        """Test getting info from element with namespaced children."""
        xml = """
        <root xmlns:x="http://example.com">
            <x:child1 />
            <x:child2 />
        </root>
        """
        elem = ET.fromstring(xml)
        info = DebugUtils.element_info(elem)

        assert info["children_count"] == 2
        # Local names should be extracted
        assert "child1" in info["child_tags"]
        assert "child2" in info["child_tags"]

    def test_element_info_mixed_content(self):
        """Test element with mixed text and children."""
        elem = ET.fromstring("<root>text<child />more</root>")
        info = DebugUtils.element_info(elem)

        assert info["text"] == "text"  # Only direct text content
        assert info["children_count"] == 1
        assert info["child_tags"] == ["child"]


class TestSummarizeParsingStats:
    """Tests for DebugUtils.summarize_parsing_stats()."""

    def test_summarize_empty_content(self):
        """Test summarizing empty workflow content."""
        content = {
            "arguments": [],
            "variables": [],
            "activities": [],
            "namespaces": {},
            "expression_language": "VisualBasic",
        }
        stats = DebugUtils.summarize_parsing_stats(content)

        assert stats["total_arguments"] == 0
        assert stats["total_variables"] == 0
        assert stats["total_activities"] == 0
        assert stats["total_namespaces"] == 0
        assert stats["has_root_annotation"] is False
        assert stats["expression_language"] == "VisualBasic"

    def test_summarize_with_counts(self):
        """Test summarizing with basic counts."""
        content = {
            "arguments": [{"name": "arg1"}, {"name": "arg2"}],
            "variables": [{"name": "var1"}, {"name": "var2"}, {"name": "var3"}],
            "activities": [{"tag": "Sequence"}],
            "namespaces": {"x": "http://example.com", "y": "http://other.com"},
            "expression_language": "CSharp",
        }
        stats = DebugUtils.summarize_parsing_stats(content)

        assert stats["total_arguments"] == 2
        assert stats["total_variables"] == 3
        assert stats["total_activities"] == 1
        assert stats["total_namespaces"] == 2
        assert stats["expression_language"] == "CSharp"

    def test_summarize_with_root_annotation(self):
        """Test detecting root annotation presence."""
        content = {
            "arguments": [],
            "variables": [],
            "activities": [],
            "namespaces": {},
            "root_annotation": "This is a workflow description",
            "expression_language": "VisualBasic",
        }
        stats = DebugUtils.summarize_parsing_stats(content)

        assert stats["has_root_annotation"] is True

    def test_summarize_activity_types_distribution(self):
        """Test activity type distribution calculation."""
        content = {
            "arguments": [],
            "variables": [],
            "activities": [
                {"tag": "Sequence"},
                {"tag": "Assign"},
                {"tag": "Sequence"},
                {"tag": "If"},
                {"tag": "Sequence"},
                {"tag": "Assign"},
            ],
            "namespaces": {},
            "expression_language": "VisualBasic",
        }
        stats = DebugUtils.summarize_parsing_stats(content)

        assert "activity_types" in stats
        assert stats["activity_types"]["Sequence"] == 3
        assert stats["activity_types"]["Assign"] == 2
        assert stats["activity_types"]["If"] == 1

    def test_summarize_argument_directions(self):
        """Test argument direction distribution calculation."""
        content = {
            "arguments": [
                {"name": "arg1", "direction": "in"},
                {"name": "arg2", "direction": "out"},
                {"name": "arg3", "direction": "in"},
                {"name": "arg4", "direction": "inout"},
                {"name": "arg5", "direction": "in"},
            ],
            "variables": [],
            "activities": [],
            "namespaces": {},
            "expression_language": "VisualBasic",
        }
        stats = DebugUtils.summarize_parsing_stats(content)

        assert "argument_directions" in stats
        assert stats["argument_directions"]["in"] == 3
        assert stats["argument_directions"]["out"] == 1
        assert stats["argument_directions"]["inout"] == 1

    def test_summarize_missing_expression_language(self):
        """Test handling missing expression_language field."""
        content = {"arguments": [], "variables": [], "activities": [], "namespaces": {}}
        stats = DebugUtils.summarize_parsing_stats(content)

        assert stats["expression_language"] == "Unknown"

    def test_summarize_missing_optional_fields(self):
        """Test handling missing optional fields."""
        content = {
            "arguments": [],
            "variables": [],
            "activities": [],
            "namespaces": {},
        }
        stats = DebugUtils.summarize_parsing_stats(content)

        # Should not crash, should use defaults
        assert stats["has_root_annotation"] is False
        assert "activity_types" not in stats  # No activities
        assert "argument_directions" not in stats  # No arguments

    def test_summarize_complex_workflow(self):
        """Test summarizing complex workflow with all features."""
        content = {
            "arguments": [
                {"name": "in1", "direction": "in"},
                {"name": "out1", "direction": "out"},
                {"name": "in2", "direction": "in"},
            ],
            "variables": [{"name": "var1"}, {"name": "var2"}],
            "activities": [
                {"tag": "Sequence"},
                {"tag": "Flowchart"},
                {"tag": "Assign"},
                {"tag": "Sequence"},
                {"tag": "If"},
            ],
            "namespaces": {
                "x": "http://schemas.microsoft.com/netfx/2009/xaml/activities",
                "sap": "http://schemas.microsoft.com/netfx/2009/xaml/activities/presentation",
                "ui": "http://schemas.uipath.com/workflow/activities",
            },
            "root_annotation": "Main workflow",
            "expression_language": "VisualBasic",
        }
        stats = DebugUtils.summarize_parsing_stats(content)

        assert stats["total_arguments"] == 3
        assert stats["total_variables"] == 2
        assert stats["total_activities"] == 5
        assert stats["total_namespaces"] == 3
        assert stats["has_root_annotation"] is True
        assert stats["expression_language"] == "VisualBasic"
        assert stats["activity_types"]["Sequence"] == 2
        assert stats["activity_types"]["Flowchart"] == 1
        assert stats["activity_types"]["Assign"] == 1
        assert stats["activity_types"]["If"] == 1
        assert stats["argument_directions"]["in"] == 2
        assert stats["argument_directions"]["out"] == 1

    def test_summarize_arguments_without_direction(self):
        """Test handling arguments without direction field."""
        content = {
            "arguments": [{"name": "arg1"}, {"name": "arg2", "direction": "in"}],
            "variables": [],
            "activities": [],
            "namespaces": {},
        }
        stats = DebugUtils.summarize_parsing_stats(content)

        assert "argument_directions" in stats
        assert stats["argument_directions"].get("unknown", 0) == 1
        assert stats["argument_directions"].get("in", 0) == 1

    def test_summarize_activities_without_tag(self):
        """Test handling activities without tag field."""
        content = {
            "arguments": [],
            "variables": [],
            "activities": [{"activity_id": "act1"}, {"tag": "Sequence"}],
            "namespaces": {},
        }
        stats = DebugUtils.summarize_parsing_stats(content)

        assert "activity_types" in stats
        assert stats["activity_types"].get("Unknown", 0) == 1
        assert stats["activity_types"].get("Sequence", 0) == 1
