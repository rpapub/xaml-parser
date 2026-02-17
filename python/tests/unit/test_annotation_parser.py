"""Unit tests for annotation parser."""

import pytest

from cpmf_uips_xaml.shared.model.dto import AnnotationBlock, AnnotationTag
from cpmf_uips_xaml.shared.utils.annotations import parse_annotation


class TestAnnotationParser:
    """Test annotation parsing logic."""

    def test_parse_single_tag_with_value(self):
        """Test parsing single tag with value."""
        text = "@author John Doe"
        block = parse_annotation(text)

        assert block is not None
        assert block.raw == "@author John Doe"
        assert len(block.tags) == 1

        tag = block.tags[0]
        assert tag.tag == "author"
        assert tag.value == "John Doe"

    def test_parse_tag_with_colon_separator(self):
        """Test @tag: value format."""
        text = "@module: ProcessInvoice"
        block = parse_annotation(text)

        tag = block.get_tag("module")
        assert tag is not None
        assert tag.value == "ProcessInvoice"

    def test_parse_boolean_flag_tag(self):
        """Test tags without values."""
        text = "@public\n@test"
        block = parse_annotation(text)

        assert len(block.tags) == 2
        assert block.has_tag("public")
        assert block.has_tag("test")
        assert block.tags[0].value is None
        assert block.tags[1].value is None

    def test_parse_multiline_tag_value(self):
        """Test multi-line tag values."""
        text = """@description This is a long description
that spans multiple lines
and continues here"""
        block = parse_annotation(text)

        tag = block.get_tag("description")
        assert tag is not None
        assert "multiple lines" in tag.value
        assert tag.value.count("\n") == 2

    def test_parse_multiple_tags(self):
        """Test multiple tags in order."""
        text = """@module ProcessInvoice
@author John Doe
@since 2.1.0
@description Processes invoices"""
        block = parse_annotation(text)

        assert len(block.tags) == 4
        assert block.tags[0].tag == "module"
        assert block.tags[1].tag == "author"
        assert block.tags[2].tag == "since"
        assert block.tags[3].tag == "description"

    def test_parse_repeated_tags(self):
        """Test repeated tags (e.g., multiple @author)."""
        text = """@author John Doe
@author Jane Smith"""
        block = parse_annotation(text)

        authors = block.get_tags("author")
        assert len(authors) == 2
        assert authors[0].value == "John Doe"
        assert authors[1].value == "Jane Smith"

    def test_parse_unknown_tag_becomes_custom(self):
        """Test unknown tags prefixed with custom:"""
        text = "@myCustomTag some value"
        block = parse_annotation(text)

        tag = block.get_tag("custom:myCustomTag")
        assert tag is not None
        assert tag.value == "some value"

    def test_parse_empty_annotation(self):
        """Test empty annotation returns None."""
        assert parse_annotation(None) is None
        assert parse_annotation("") is None
        assert parse_annotation("   ") is None

    def test_parse_text_without_tags(self):
        """Test plain text without tags."""
        text = "This is just plain text without tags"
        block = parse_annotation(text)

        assert block.raw == text
        assert len(block.tags) == 0

    def test_ignore_flag_detection(self):
        """Test @ignore and @ignore-all detection."""
        block1 = parse_annotation("@ignore")
        assert block1.is_ignored is True

        block2 = parse_annotation("@ignore-all")
        assert block2.is_ignored is True

        block3 = parse_annotation("@author John")
        assert block3.is_ignored is False

    def test_public_api_detection(self):
        """Test @public flag detection."""
        block = parse_annotation("@public\n@description Public API")
        assert block.is_public_api is True

    def test_test_workflow_detection(self):
        """Test @test flag detection."""
        block = parse_annotation("@test\n@author John")
        assert block.is_test is True

    def test_unit_detection(self):
        """Test @unit flag detection."""
        block = parse_annotation("@unit\n@description Atomic unit of work")
        assert block.is_unit is True
        assert block.has_tag("unit")

    def test_module_detection(self):
        """Test @module flag detection."""
        block = parse_annotation("@module ProcessInvoice")
        assert block.is_module is True
        assert block.has_tag("module")
        module_tag = block.get_tag("module")
        assert module_tag.value == "ProcessInvoice"

    def test_pathkeeper_detection(self):
        """Test @pathkeeper flag detection."""
        block = parse_annotation("@pathkeeper\n@description Object Repository traversal")
        assert block.is_pathkeeper is True
        assert block.has_tag("pathkeeper")

    def test_workflow_classification_tags(self):
        """Test all workflow classification tags are recognized."""
        classification_tags = [
            "unit",
            "module",
            "process",
            "dispatcher",
            "performer",
            "test",
            "deprecated",
            "pathkeeper",
        ]

        for tag_name in classification_tags:
            text = f"@{tag_name}"
            block = parse_annotation(text)
            assert block is not None
            assert block.has_tag(tag_name)
            # Should not be converted to custom:
            assert not any(t.tag.startswith("custom:") for t in block.tags)

    def test_rule_control_tags(self):
        """Test rule control tags are recognized."""
        rule_tags = ["ignore", "ignore-all", "strict", "nowarn"]

        for tag_name in rule_tags:
            text = f"@{tag_name}"
            block = parse_annotation(text)
            assert block is not None
            assert block.has_tag(tag_name)
            # Should not be converted to custom:
            assert not any(t.tag.startswith("custom:") for t in block.tags)

    def test_architectural_constraint_tags(self):
        """Test architectural constraint tags are recognized."""
        constraint_tags = ["pure", "idempotent", "transactional", "internal", "public"]

        for tag_name in constraint_tags:
            text = f"@{tag_name}"
            block = parse_annotation(text)
            assert block is not None
            assert block.has_tag(tag_name)
            # Should not be converted to custom:
            assert not any(t.tag.startswith("custom:") for t in block.tags)

    def test_line_numbers_preserved(self):
        """Test line numbers are tracked."""
        text = """@author John
@module ProcessInvoice
@since 2.1.0"""
        block = parse_annotation(text)

        assert block.tags[0].line_number == 1
        assert block.tags[1].line_number == 2
        assert block.tags[2].line_number == 3

    def test_complex_annotation(self):
        """Test complex annotation with multiple tag types."""
        text = """@unit
@module ProcessInvoice
@pathkeeper
@author John Doe
@since 2.0.0
@description Processes vendor invoices and updates ERP
with retry logic and error handling
@public
@idempotent"""
        block = parse_annotation(text)

        # Check all tags parsed
        assert len(block.tags) == 8

        # Check workflow classification
        assert block.is_unit
        assert block.is_module
        assert block.is_pathkeeper

        # Check documentation
        authors = block.get_tags("author")
        assert len(authors) == 1
        assert authors[0].value == "John Doe"

        # Check architectural constraints
        assert block.is_public_api
        assert block.has_tag("idempotent")

        # Check multi-line description
        desc = block.get_tag("description")
        assert desc is not None
        assert "vendor invoices" in desc.value
        assert "retry logic" in desc.value

    def test_custom_tag_with_colon(self):
        """Test explicit custom:tagname format."""
        text = "@custom:reviewed-by Jane Smith"
        block = parse_annotation(text)

        assert len(block.tags) == 1
        tag = block.tags[0]
        assert tag.tag == "custom:reviewed-by"
        assert tag.value == "Jane Smith"

    def test_custom_tag_with_colon_separator(self):
        """Test custom:tag: value format."""
        text = "@custom:priority: high"
        block = parse_annotation(text)

        assert len(block.tags) == 1
        tag = block.tags[0]
        assert tag.tag == "custom:priority"
        assert tag.value == "high"

    def test_preserve_blank_lines_in_multiline_values(self):
        """Test that blank lines within tag values are preserved."""
        text = """@description First paragraph

Second paragraph after blank line

Third paragraph"""
        block = parse_annotation(text)

        desc = block.get_tag("description")
        assert desc is not None
        # Blank lines should be in the value
        lines = desc.value.split("\n")
        assert len(lines) >= 3
        assert "First paragraph" in desc.value
        assert "Second paragraph" in desc.value
        assert "Third paragraph" in desc.value

    def test_preserve_raw_text_whitespace(self):
        """Test that raw annotation text preserves leading/trailing whitespace."""
        text = "  @author John Doe  \n  @module Test  "
        block = parse_annotation(text)

        # Raw text should preserve original whitespace
        assert block.raw == text

        # But parsed tags should still work
        assert len(block.tags) == 2
        assert block.get_tag("author").value == "John Doe"

    def test_multiple_custom_tags(self):
        """Test multiple custom tags in one annotation."""
        text = """@custom:priority high
@custom:reviewed-by Jane
@custom:ticket-id JIRA-123"""
        block = parse_annotation(text)

        assert len(block.tags) == 3
        assert block.get_tag("custom:priority").value == "high"
        assert block.get_tag("custom:reviewed-by").value == "Jane"
        assert block.get_tag("custom:ticket-id").value == "JIRA-123"

    def test_mixed_standard_and_custom_tags(self):
        """Test mixing standard tags with custom: tags."""
        text = """@author John Doe
@custom:priority high
@module ProcessInvoice
@custom:reviewed-by Jane"""
        block = parse_annotation(text)

        assert len(block.tags) == 4
        # Standard tags
        assert block.get_tag("author").value == "John Doe"
        assert block.get_tag("module").value == "ProcessInvoice"
        # Custom tags (explicit custom: format)
        assert block.get_tag("custom:priority").value == "high"
        assert block.get_tag("custom:reviewed-by").value == "Jane"

    def test_html_entity_decoding(self):
        """Test that HTML entities are automatically decoded."""
        # Text with HTML entities as it appears in XML
        text = "@author John &amp; Jane&#xA;@description Process &lt;data&gt;"
        block = parse_annotation(text)

        assert len(block.tags) == 2
        # Ampersand should be decoded
        author = block.get_tag("author")
        assert author.value == "John & Jane"
        # Angle brackets should be decoded
        desc = block.get_tag("description")
        assert desc.value == "Process <data>"
        # Raw text should also be decoded
        assert "&amp;" not in block.raw
        assert "&" in block.raw

    def test_html_entity_in_raw_text(self):
        """Test that raw text is stored as decoded."""
        text = "@module Test&amp;Module"
        block = parse_annotation(text)

        # Raw should be decoded
        assert block.raw == "@module Test&Module"
        # Tag value should be decoded
        assert block.get_tag("module").value == "Test&Module"
