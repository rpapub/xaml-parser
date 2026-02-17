"""XML processing utilities for XAML parsing operations.

This module provides helper functions for XML element processing,
namespace handling, and safe XML parsing operations.
"""

import re
import xml.etree.ElementTree as ET


class XmlUtils:
    """XML processing utilities."""

    @staticmethod
    def safe_parse(content: str, encoding: str = "utf-8") -> ET.Element | None:
        """Safely parse XML content with error handling.

        Args:
            content: Raw XML string
            encoding: Text encoding to use

        Returns:
            Parsed root element or None if parsing failed
        """
        try:
            return ET.fromstring(content)
        except ET.ParseError:
            # Try with encoding declaration removed
            try:
                # Remove XML declaration that might have wrong encoding
                clean_content = re.sub(r"<\?xml[^>]*\?>", "", content, count=1)
                return ET.fromstring(clean_content)
            except ET.ParseError:
                return None

    @staticmethod
    def get_element_text(elem: ET.Element, default: str = "") -> str:
        """Get element text content safely.

        Args:
            elem: XML element
            default: Default value if no text

        Returns:
            Element text or default value
        """
        return elem.text.strip() if elem.text else default

    @staticmethod
    def find_elements_by_attribute(
        root: ET.Element, attr_name: str, attr_value: str | None = None
    ) -> list[ET.Element]:
        """Find all elements with specific attribute.

        Args:
            root: Root element to search from
            attr_name: Attribute name to search for
            attr_value: Specific attribute value (None = any value)

        Returns:
            List of matching elements
        """
        matches = []
        for elem in root.iter():
            if attr_name in elem.attrib:
                if attr_value is None or elem.get(attr_name) == attr_value:
                    matches.append(elem)
        return matches

    @staticmethod
    def get_namespace_prefix(tag: str) -> str | None:
        """Extract namespace prefix from qualified tag name.

        Args:
            tag: Tag name (possibly namespaced)

        Returns:
            Namespace prefix or None
        """
        if "}" in tag:
            namespace = tag.split("}")[0][1:]  # Remove { and }
            return namespace
        return None

    @staticmethod
    def get_local_name(tag: str) -> str:
        """Extract local name from qualified tag.

        Args:
            tag: Tag name (possibly namespaced)

        Returns:
            Local tag name without namespace
        """
        return tag.split("}")[-1] if "}" in tag else tag

    @staticmethod
    def get_prefix_for_uri(namespaces: dict[str, str], uri: str) -> str | None:
        """Find prefix for a namespace URI (reverse lookup).

        Args:
            namespaces: Prefix → URI mapping
            uri: Namespace URI to find

        Returns:
            Prefix string or None if not found
        """
        for prefix, ns_uri in namespaces.items():
            if ns_uri == uri:
                return prefix
        return None

    @staticmethod
    def get_prefixes_for_uri(namespaces: dict[str, str], uri: str) -> list[str]:
        """Find all prefixes for a namespace URI (handles aliasing).

        Args:
            namespaces: Prefix → URI mapping
            uri: Namespace URI to find

        Returns:
            List of prefixes that map to the given URI
        """
        return [prefix for prefix, ns_uri in namespaces.items() if ns_uri == uri]

    @staticmethod
    def find_elements_by_local_name(
        root: ET.Element,
        local_name: str,
        namespace_uri: str | None = None,
    ) -> list[ET.Element]:
        """Find elements by local name, optionally filtered by namespace.

        Handles case where elements might have different prefixes but same local name.

        Args:
            root: Root element to search from
            local_name: Local element name to find
            namespace_uri: Optional namespace URI filter

        Returns:
            List of matching elements
        """
        results = []
        for elem in root.iter():
            # Extract local name and namespace from tag
            if "}" in elem.tag:
                ns, name = elem.tag[1:].split("}", 1)
            else:
                ns, name = None, elem.tag

            if name == local_name:
                if namespace_uri is None or ns == namespace_uri:
                    results.append(elem)

        return results
