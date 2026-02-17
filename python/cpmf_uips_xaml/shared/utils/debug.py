"""Debugging utilities for XAML parsing operations.

This module provides helper functions for diagnostic information,
element inspection, and parsing statistics.
"""

import xml.etree.ElementTree as ET
from typing import Any

from .xml import XmlUtils


class DebugUtils:
    """Debugging and diagnostic utilities."""

    @staticmethod
    def element_info(elem: ET.Element) -> dict[str, Any]:
        """Get diagnostic information about XML element.

        Args:
            elem: XML element

        Returns:
            Dictionary with element information
        """
        return {
            "tag": elem.tag,
            "local_name": XmlUtils.get_local_name(elem.tag),
            "namespace": XmlUtils.get_namespace_prefix(elem.tag),
            "attributes": dict(elem.attrib),
            "text": elem.text.strip() if elem.text else None,
            "children_count": len(elem),
            "child_tags": [XmlUtils.get_local_name(child.tag) for child in elem],
        }

    @staticmethod
    def summarize_parsing_stats(content: dict[str, Any]) -> dict[str, Any]:
        """Generate parsing statistics summary.

        Args:
            content: Parsed workflow content

        Returns:
            Statistics summary
        """
        stats = {
            "total_arguments": len(content.get("arguments", [])),
            "total_variables": len(content.get("variables", [])),
            "total_activities": len(content.get("activities", [])),
            "total_namespaces": len(content.get("namespaces", {})),
            "has_root_annotation": bool(content.get("root_annotation")),
            "expression_language": content.get("expression_language", "Unknown"),
        }

        # Activity type distribution
        activities = content.get("activities", [])
        if activities:
            activity_types: dict[str, int] = {}
            for activity in activities:
                tag = activity.get("tag", "Unknown")
                activity_types[tag] = activity_types.get(tag, 0) + 1
            stats["activity_types"] = activity_types

        # Argument directions
        arguments = content.get("arguments", [])
        if arguments:
            directions: dict[str, int] = {}
            for arg in arguments:
                direction = arg.get("direction", "unknown")
                directions[direction] = directions.get(direction, 0) + 1
            stats["argument_directions"] = directions

        return stats
