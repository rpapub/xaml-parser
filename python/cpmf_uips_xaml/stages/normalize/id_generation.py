"""Stable ID generation for XAML workflows and activities.

This module provides deterministic, content-hash based IDs that survive file
renames and minor XML formatting changes. IDs use W3C XML Canonicalization (C14N)
for normalization before hashing to ensure stability.

ID Format:
- Workflows: wf:sha256:abc123def456... (16 hex chars)
- Activities: act:sha256:abc123def456... (16 hex chars)
- Edges: edge:sha256:abc123def456... (16 hex chars)

Design: ADR-DTO-DESIGN.md
"""

import hashlib
import xml.etree.ElementTree as ET
from typing import Any


class IdGenerator:
    """Generate stable, deterministic IDs for workflow entities.

    Uses W3C XML Canonicalization (C14N) for normalization before hashing
    to ensure minor XML formatting changes don't affect IDs.
    """

    def generate_workflow_id(self, xml_content: str) -> str:
        """Generate stable workflow ID from XML content.

        Args:
            xml_content: Complete XAML workflow file content

        Returns:
            Workflow ID: wf:sha256:abc123def456... (16 hex chars)

        Example:
            >>> gen = IdGenerator()
            >>> wf_id = gen.generate_workflow_id("<Activity>...</Activity>")
            >>> wf_id
            'wf:sha256:abc123def456...'
        """
        content_hash = self._hash_xml_span(xml_content)
        return f"wf:{content_hash}"

    def generate_activity_id(self, xml_span: str) -> str:
        """Generate stable activity ID from XML span.

        Args:
            xml_span: XML substring representing the activity element

        Returns:
            Activity ID: act:sha256:abc123def456... (16 hex chars)

        Example:
            >>> gen = IdGenerator()
            >>> act_id = gen.generate_activity_id("<Sequence>...</Sequence>")
            >>> act_id
            'act:sha256:abc123def456...'
        """
        span_hash = self._hash_xml_span(xml_span)
        return f"act:{span_hash}"

    def generate_edge_id(self, from_id: str, to_id: str, kind: str) -> str:
        """Generate stable edge ID from source, target, and kind.

        Args:
            from_id: Source activity ID
            to_id: Target activity ID
            kind: Edge kind (Then, Else, Next, etc.)

        Returns:
            Edge ID: edge:sha256:abc123def456... (16 hex chars)

        Example:
            >>> gen = IdGenerator()
            >>> edge_id = gen.generate_edge_id("act:sha256:abc123", "act:sha256:def456", "Then")
            >>> edge_id
            'edge:sha256:...'
        """
        # Deterministic edge ID based on endpoints and kind
        edge_repr = f"{from_id}→{to_id}:{kind}"
        edge_hash = hashlib.sha256(edge_repr.encode("utf-8")).hexdigest()[:16]
        return f"edge:sha256:{edge_hash}"

    def _hash_xml_span(self, xml_span: str) -> str:
        """Generate SHA-256 hash of normalized XML.

        Args:
            xml_span: XML content to hash

        Returns:
            Hash with format: sha256:abc123def456... (16 hex chars)

        The hash is truncated to 16 hex chars (64 bits) for readability
        while maintaining collision resistance for typical projects.
        """
        try:
            normalized = self._normalize_xml(xml_span)
        except (ET.ParseError, ValueError, TypeError) as e:
            # If normalization fails, use raw content
            # This handles non-XML strings or malformed XML
            import warnings
            warnings.warn(f"XML normalization failed: {e}, using raw content", stacklevel=2)
            normalized = xml_span

        hash_full = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        hash_short = hash_full[:16]  # 64 bits, collision-resistant
        return f"sha256:{hash_short}"

    def _normalize_xml(self, xml: str) -> str:
        """Normalize XML for deterministic hashing using W3C C14N.

        Implements subset of https://www.w3.org/TR/xml-c14n for deterministic hashing:
        1. Parse XML to tree (handle encoding, strip BOM)
        2. Normalize namespace declarations (prefix → URI map)
        3. Sort attributes lexicographically by namespace URI then local name
        4. Remove insignificant whitespace (inter-element whitespace)
        5. Serialize deterministically (UTF-8, LF line endings, no XML declaration)

        This ensures minor serialization differences don't flip hashes.

        Args:
            xml: XML string to normalize

        Returns:
            Normalized XML string (UTF-8, LF line endings)

        Notes:
            - Uses xml.etree C14N support
            - Handles namespace prefixes deterministically
            - Strips insignificant inter-element whitespace
            - Removes XML declaration and doctype
        """
        # Strip BOM if present
        if xml.startswith("\ufeff"):
            xml = xml[1:]

        # Normalize line endings first
        xml = xml.replace("\r\n", "\n").replace("\r", "\n")

        # Parse XML
        try:
            root = ET.fromstring(xml)
        except ET.ParseError:
            # If parsing fails, return cleaned raw content
            # This handles XML fragments or malformed XML
            return self._fallback_normalize(xml)

        # Strip insignificant whitespace (inter-element whitespace only)
        self._strip_whitespace(root)

        # Apply C14N canonicalization
        # ET.canonicalize() is available in Python 3.8+
        try:
            from xml.etree.ElementTree import canonicalize

            # Serialize element to string first
            xml_str = ET.tostring(root, encoding="unicode")

            # Then canonicalize with proper named arguments
            canonical: str = canonicalize(
                xml_data=xml_str,
                strip_text=True,  # Strip whitespace-only text nodes
            )
            return canonical
        except (ImportError, ValueError, TypeError) as e:
            # Fallback: serialize with ET if canonicalize is unavailable or fails
            import warnings
            warnings.warn(f"XML canonicalization failed ({type(e).__name__}: {e}), using fallback serialization", stacklevel=2)
            return ET.tostring(root, encoding="unicode")

    def _strip_whitespace(self, elem: Any) -> None:
        """Strip insignificant whitespace from element tree.

        Args:
            elem: XML element to process (modifies in-place)
        """
        # Strip leading/trailing whitespace from text
        if elem.text is not None:
            stripped = elem.text.strip()
            elem.text = stripped if stripped else None

        # Strip tail (text after element)
        if elem.tail is not None:
            stripped = elem.tail.strip()
            elem.tail = stripped if stripped else None

        # Recursively process children
        for child in elem:
            self._strip_whitespace(child)

    def _fallback_normalize(self, xml: str) -> str:
        """Fallback normalization when C14N is unavailable or fails.

        Args:
            xml: XML string to normalize

        Returns:
            Normalized XML string with:
            - UTF-8 encoding
            - LF line endings
            - Trimmed whitespace
        """
        # Normalize line endings
        xml = xml.replace("\r\n", "\n").replace("\r", "\n")

        # Trim leading/trailing whitespace
        xml = xml.strip()

        return xml

    def compute_full_hash(self, xml_content: str) -> str:
        """Compute full SHA-256 hash (64 hex chars) for SourceInfo.

        This is used for the `source.hash` field which stores the complete
        hash for audit trails and verification.

        Args:
            xml_content: Complete XAML workflow content

        Returns:
            Full hash with format: sha256:abc123...def789 (64 hex chars)

        Example:
            >>> gen = IdGenerator()
            >>> full_hash = gen.compute_full_hash("<Activity>...</Activity>")
            >>> len(full_hash)
            71  # 'sha256:' + 64 hex chars
        """
        try:
            normalized = self._normalize_xml(xml_content)
        except (ET.ParseError, ValueError, TypeError) as e:
            import warnings
            warnings.warn(f"XML normalization failed: {e}, using raw content", stacklevel=2)
            normalized = xml_content

        hash_full = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        return f"sha256:{hash_full}"


def generate_stable_id(prefix: str, content: Any) -> str:
    """Convenience function to generate stable ID from any content.

    Args:
        prefix: ID prefix (wf, act, edge, arg, var)
        content: Content to hash (string or object)

    Returns:
        Stable ID: prefix:sha256:abc123def456...

    Example:
        >>> generate_stable_id("arg", "in_FilePath")
        'arg:sha256:abc123def456...'
    """
    # Convert content to string representation
    if isinstance(content, str):
        content_str = content
    else:
        content_str = str(content)

    # Generate hash
    hash_full = hashlib.sha256(content_str.encode("utf-8")).hexdigest()
    hash_short = hash_full[:16]

    return f"{prefix}:sha256:{hash_short}"
