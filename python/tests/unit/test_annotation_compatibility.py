"""Test backward compatibility for annotations."""

import pytest

from cpmf_uips_xaml.shared.model.dto import AnnotationBlock
from cpmf_uips_xaml.shared.utils.annotations import parse_annotation


class TestBackwardCompatibility:
    """Ensure annotation_block doesn't break existing code."""

    def test_raw_annotation_still_available(self):
        """Test raw annotation field still populated."""
        text = "@author John Doe\n@module ProcessInvoice"
        block = parse_annotation(text)

        # Raw text preserved
        assert block.raw == text

        # Can still use raw text as before
        assert "John Doe" in block.raw
        assert "ProcessInvoice" in block.raw

    def test_none_annotation_handled(self):
        """Test None annotations handled gracefully."""
        block = parse_annotation(None)
        assert block is None

    def test_empty_annotation_handled(self):
        """Test empty annotations handled gracefully."""
        block = parse_annotation("")
        assert block is None

        block = parse_annotation("   ")
        assert block is None

    def test_plain_text_annotation_handled(self):
        """Test annotations without tags still work."""
        text = "This is a plain comment without any tags"
        block = parse_annotation(text)

        assert block.raw == text
        assert len(block.tags) == 0

        # Helper methods return safe defaults
        assert block.is_ignored is False
        assert block.is_public_api is False
        assert block.is_test is False
        assert block.is_unit is False
        assert block.is_module is False
        assert block.is_pathkeeper is False

    def test_get_tag_returns_none_when_not_found(self):
        """Test get_tag returns None for missing tags."""
        text = "@author John Doe"
        block = parse_annotation(text)

        # Existing tag
        assert block.get_tag("author") is not None

        # Non-existent tag
        assert block.get_tag("nonexistent") is None

    def test_get_tags_returns_empty_list_when_not_found(self):
        """Test get_tags returns empty list for missing tags."""
        text = "@author John Doe"
        block = parse_annotation(text)

        # Existing tag
        authors = block.get_tags("author")
        assert len(authors) == 1

        # Non-existent tag
        missing = block.get_tags("nonexistent")
        assert missing == []
        assert isinstance(missing, list)

    def test_has_tag_returns_false_when_not_found(self):
        """Test has_tag returns False for missing tags."""
        text = "@author John Doe"
        block = parse_annotation(text)

        # Existing tag
        assert block.has_tag("author") is True

        # Non-existent tag
        assert block.has_tag("nonexistent") is False

    def test_annotation_block_with_no_tags(self):
        """Test annotation block with just plain text has no tags."""
        text = "Just a plain comment"
        block = parse_annotation(text)

        assert block is not None
        assert block.raw == text
        assert len(block.tags) == 0
        assert block.get_tag("author") is None
        assert block.get_tags("author") == []
        assert block.has_tag("author") is False

    def test_annotation_block_properties_safe_on_empty(self):
        """Test boolean properties are safe on annotation blocks with no tags."""
        text = "Plain comment"
        block = parse_annotation(text)

        # All boolean properties should return False, not raise exceptions
        assert block.is_ignored is False
        assert block.is_public_api is False
        assert block.is_test is False
        assert block.is_unit is False
        assert block.is_module is False
        assert block.is_pathkeeper is False

    def test_annotation_value_can_be_none(self):
        """Test that tag values can be None for boolean flags."""
        text = "@test"
        block = parse_annotation(text)

        tag = block.get_tag("test")
        assert tag is not None
        assert tag.tag == "test"
        assert tag.value is None

    def test_whitespace_handling(self):
        """Test that leading/trailing whitespace is handled correctly."""
        text = "  @author John Doe  \n  @module ProcessInvoice  "
        block = parse_annotation(text)

        # Should strip outer whitespace
        assert len(block.tags) == 2

        author = block.get_tag("author")
        assert author.value == "John Doe"

        module = block.get_tag("module")
        assert module.value == "ProcessInvoice"

    def test_line_continuation_without_blank_lines(self):
        """Test multi-line values don't include blank continuation lines."""
        text = """@description First line

Second line

Third line
@author John"""
        block = parse_annotation(text)

        desc = block.get_tag("description")
        # Blank lines should be preserved in value
        assert "First line" in desc.value
        assert "Second line" in desc.value
        assert "Third line" in desc.value

    def test_case_sensitivity(self):
        """Test that tag names are case-sensitive."""
        text = "@Author John Doe\n@author Jane Smith"
        block = parse_annotation(text)

        # @Author (capitalized) is not a known tag, should become custom:Author
        custom_author = block.get_tag("custom:Author")
        assert custom_author is not None
        assert custom_author.value == "John Doe"

        # @author (lowercase) is a known tag
        author = block.get_tag("author")
        assert author is not None
        assert author.value == "Jane Smith"

    def test_colon_in_tag_value(self):
        """Test that colons in tag values are preserved."""
        text = "@description Process file: C:\\Path\\To\\File.txt"
        block = parse_annotation(text)

        desc = block.get_tag("description")
        assert desc is not None
        assert "C:\\Path\\To\\File.txt" in desc.value

    def test_special_characters_in_values(self):
        """Test that special characters in values are preserved."""
        text = "@description Uses special chars: @#$%^&*()"
        block = parse_annotation(text)

        desc = block.get_tag("description")
        assert desc is not None
        assert "@#$%^&*()" in desc.value

    def test_numeric_values(self):
        """Test tags with numeric values."""
        text = "@since 2.1.0\n@version 3"
        block = parse_annotation(text)

        since = block.get_tag("since")
        assert since is not None
        assert since.value == "2.1.0"

        version = block.get_tag("custom:version")
        assert version is not None
        assert version.value == "3"

    def test_empty_tag_value_after_colon(self):
        """Test tag with colon but no value."""
        text = "@module:"
        block = parse_annotation(text)

        module = block.get_tag("module")
        assert module is not None
        assert module.value is None or module.value == ""
