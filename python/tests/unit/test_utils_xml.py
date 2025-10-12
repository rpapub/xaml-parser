"""Tests for XmlUtils utility functions."""

import xml.etree.ElementTree as ET

import pytest

from xaml_parser.utils import XmlUtils


class TestXmlUtilsSafeParse:
    """Tests for XmlUtils.safe_parse()."""

    def test_safe_parse_valid_xml(self):
        """Test parsing valid XML."""
        xml = '<?xml version="1.0"?><root><child /></root>'
        result = XmlUtils.safe_parse(xml)
        assert result is not None
        assert result.tag == "root"

    def test_safe_parse_simple_xml_without_declaration(self):
        """Test parsing XML without declaration."""
        xml = "<root><child /></root>"
        result = XmlUtils.safe_parse(xml)
        assert result is not None
        assert result.tag == "root"

    def test_safe_parse_invalid_xml(self):
        """Test parsing invalid XML returns None."""
        xml = "<root><unclosed>"
        result = XmlUtils.safe_parse(xml)
        assert result is None

    def test_safe_parse_with_encoding_declaration(self):
        """Test parsing XML with encoding declaration."""
        xml = '<?xml version="1.0" encoding="utf-8"?><root />'
        result = XmlUtils.safe_parse(xml)
        assert result is not None
        assert result.tag == "root"

    def test_safe_parse_removes_bad_encoding_declaration(self):
        """Test recovery by removing encoding declaration."""
        xml = '<?xml version="1.0" encoding="bad"?><root>test</root>'
        result = XmlUtils.safe_parse(xml)
        # Should parse successfully after removing declaration
        assert result is not None
        assert result.tag == "root"

    def test_safe_parse_with_namespaces(self):
        """Test parsing XML with namespaces."""
        xml = '<root xmlns="http://example.com"><child /></root>'
        result = XmlUtils.safe_parse(xml)
        assert result is not None

    def test_safe_parse_empty_element(self):
        """Test parsing empty element."""
        xml = "<root />"
        result = XmlUtils.safe_parse(xml)
        assert result is not None
        assert result.tag == "root"


class TestXmlUtilsElementText:
    """Tests for XmlUtils.get_element_text()."""

    def test_get_element_text_with_text(self):
        """Test getting text from element with content."""
        elem = ET.fromstring("<root>Hello</root>")
        result = XmlUtils.get_element_text(elem)
        assert result == "Hello"

    def test_get_element_text_empty(self):
        """Test getting text from empty element."""
        elem = ET.fromstring("<root></root>")
        result = XmlUtils.get_element_text(elem)
        assert result == ""

    def test_get_element_text_with_default(self):
        """Test getting text with custom default."""
        elem = ET.fromstring("<root></root>")
        result = XmlUtils.get_element_text(elem, default="N/A")
        assert result == "N/A"

    def test_get_element_text_strips_whitespace(self):
        """Test that whitespace is stripped."""
        elem = ET.fromstring("<root>  text  </root>")
        result = XmlUtils.get_element_text(elem)
        assert result == "text"

    def test_get_element_text_multiline(self):
        """Test getting text with newlines."""
        elem = ET.fromstring("<root>Line1\nLine2</root>")
        result = XmlUtils.get_element_text(elem)
        assert "Line1" in result
        assert "Line2" in result

    def test_get_element_text_none_with_default(self):
        """Test None text returns default."""
        elem = ET.Element("root")
        elem.text = None
        result = XmlUtils.get_element_text(elem, default="default_value")
        assert result == "default_value"


class TestXmlUtilsFindElements:
    """Tests for XmlUtils.find_elements_by_attribute()."""

    @pytest.fixture
    def sample_tree(self):
        """Sample XML tree for testing."""
        xml = """
        <root>
            <child id="1" type="A" />
            <child id="2" type="B" />
            <child id="3" type="A" />
            <nested>
                <child id="4" type="C" />
            </nested>
        </root>
        """
        return ET.fromstring(xml)

    def test_find_by_attribute_any_value(self, sample_tree):
        """Test finding all elements with attribute."""
        results = XmlUtils.find_elements_by_attribute(sample_tree, "id")
        assert len(results) == 4  # All child elements have id

    def test_find_by_attribute_specific_value(self, sample_tree):
        """Test finding elements with specific attribute value."""
        results = XmlUtils.find_elements_by_attribute(sample_tree, "type", "A")
        assert len(results) == 2

    def test_find_by_attribute_no_matches(self, sample_tree):
        """Test finding with no matches."""
        results = XmlUtils.find_elements_by_attribute(sample_tree, "nonexistent")
        assert len(results) == 0

    def test_find_by_attribute_single_match(self, sample_tree):
        """Test finding single matching element."""
        results = XmlUtils.find_elements_by_attribute(sample_tree, "type", "C")
        assert len(results) == 1
        assert results[0].get("id") == "4"

    def test_find_by_attribute_empty_value(self, sample_tree):
        """Test finding with empty string value (should not match None)."""
        # Add element with empty attribute
        elem = ET.Element("child")
        elem.set("empty", "")
        sample_tree.append(elem)
        results = XmlUtils.find_elements_by_attribute(sample_tree, "empty", "")
        assert len(results) == 1


class TestXmlUtilsNamespace:
    """Tests for namespace extraction."""

    def test_get_namespace_prefix_with_namespace(self):
        """Test extracting namespace from qualified tag."""
        tag = "{http://schemas.microsoft.com/netfx/2009/xaml/activities}Sequence"
        result = XmlUtils.get_namespace_prefix(tag)
        assert result == "http://schemas.microsoft.com/netfx/2009/xaml/activities"

    def test_get_namespace_prefix_no_namespace(self):
        """Test extracting from unqualified tag."""
        tag = "Sequence"
        result = XmlUtils.get_namespace_prefix(tag)
        assert result is None

    def test_get_namespace_prefix_empty_namespace(self):
        """Test extracting from tag with empty namespace."""
        tag = "{}Sequence"
        result = XmlUtils.get_namespace_prefix(tag)
        assert result == ""

    def test_get_local_name_with_namespace(self):
        """Test extracting local name from qualified tag."""
        tag = "{http://example.com}Sequence"
        result = XmlUtils.get_local_name(tag)
        assert result == "Sequence"

    def test_get_local_name_without_namespace(self):
        """Test extracting local name from unqualified tag."""
        tag = "Sequence"
        result = XmlUtils.get_local_name(tag)
        assert result == "Sequence"

    def test_get_local_name_complex_namespace(self):
        """Test local name extraction with complex namespace URI."""
        tag = "{http://schemas.microsoft.com/winfx/2006/xaml}Class"
        result = XmlUtils.get_local_name(tag)
        assert result == "Class"

    def test_get_local_name_multiple_braces(self):
        """Test local name with multiple braces in tag (edge case)."""
        tag = "{http://example.com}Tag}WithBrace"
        result = XmlUtils.get_local_name(tag)
        # Should return everything after the first }
        assert "WithBrace" in result
