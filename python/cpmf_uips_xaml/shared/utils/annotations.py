"""Annotation parsing utilities for structured tag extraction.

Parses UiPath XAML annotation text (from sap2010:Annotation.AnnotationText)
into structured tags following the format:

    @tag value
    @tag: value
    @tag

Supported tags include @module, @description, @author, @since, @todo, @public,
@test, @ignore, and more. Unknown tags are automatically prefixed with custom:.

Example:
    >>> text = "@author John Doe\\n@module ProcessInvoice"
    >>> block = parse_annotation(text)
    >>> block.get_tag("author").value
    'John Doe'
    >>> block.has_tag("module")
    True
"""

import html
import re
from typing import Pattern

from ..model.dto import AnnotationBlock, AnnotationTag


# Compile regex patterns once at module load
# Tag name can contain: alphanumeric, underscore, hyphen, and colon (for custom:tags)
# BUT: trailing colon is treated as a separator, not part of tag name
# Matches:
#   @tagname          → tag without value
#   @tagname value    → tag with value (space separator)
#   @tagname: value   → tag with value (colon separator)
#   @custom:tag value → custom tag with value
#   @custom:tag: val  → custom tag with colon separator
# Pattern: tag name can have colons internally, but NOT as the last character before separator
TAG_PATTERN: Pattern = re.compile(
    r"^@([a-zA-Z_][a-zA-Z0-9_-]*(?::[a-zA-Z_][a-zA-Z0-9_-]*)*)(?:\s*:\s*|\s+)(.*)$|^@([a-zA-Z_][a-zA-Z0-9_:-]+)$"
)


def parse_annotation(text: str | None) -> AnnotationBlock | None:
    """Parse annotation text into structured tags.

    HTML entities are automatically decoded before parsing.

    Args:
        text: Raw annotation text (may contain HTML entities like &amp; &#xA;)

    Returns:
        AnnotationBlock with parsed tags, or None if text is empty/None

    Example:
        >>> text = "@author John Doe\\n@module ProcessInvoice"
        >>> block = parse_annotation(text)
        >>> block.get_tag("author").value
        'John Doe'
        >>> block.tags
        [AnnotationTag(tag='author', value='John Doe', ...),
         AnnotationTag(tag='module', value='ProcessInvoice', ...)]
    """
    if not text or not text.strip():
        return None

    # Decode HTML entities (e.g., &amp; → &, &#xA; → \n)
    decoded_text = html.unescape(text)

    # Preserve decoded text exactly (don't strip)
    raw_text = decoded_text
    lines = raw_text.split("\n")
    tags = []

    current_tag = None
    current_value_lines = []
    current_start_line = 0

    for line_num, line in enumerate(lines, start=1):
        line_stripped = line.strip()

        # Skip empty lines that are not part of a tag value
        if not line_stripped and not current_tag:
            continue

        # Check if line starts with @tag
        match = TAG_PATTERN.match(line_stripped)

        if match:
            # Save previous tag if exists
            if current_tag:
                # Preserve blank lines in multi-line values
                value = "\n".join(current_value_lines) if current_value_lines else None
                if value:
                    value = value.strip()  # Only strip the final value
                tags.append(
                    AnnotationTag(
                        tag=current_tag,
                        value=value if value else None,
                        raw=f"@{current_tag}" + (f": {value}" if value else ""),
                        line_number=current_start_line,
                    )
                )

            # Extract tag name and value from regex groups
            # Group 1 and 2 are for tag with value, Group 3 is for tag without value
            if match.group(1):  # Tag with value or separator
                tag_name = match.group(1)
                tag_value = match.group(2) if match.group(2) else ""
            else:  # Tag without value (group 3)
                tag_name = match.group(3)
                tag_value = ""

            # Handle custom tags (convert unknown to custom:tagname)
            # But only if it doesn't already start with "custom:"
            if not _is_known_tag(tag_name) and not tag_name.startswith("custom:"):
                tag_name = f"custom:{tag_name}"

            current_tag = tag_name
            current_value_lines = [tag_value] if tag_value else []
            current_start_line = line_num

        elif current_tag:
            # Continuation of current tag value (preserve all lines, including blank)
            current_value_lines.append(line_stripped)

    # Save last tag
    if current_tag:
        value = "\n".join(current_value_lines) if current_value_lines else None
        if value:
            value = value.strip()
        tags.append(
            AnnotationTag(
                tag=current_tag,
                value=value if value else None,
                raw=f"@{current_tag}" + (f": {value}" if value else ""),
                line_number=current_start_line,
            )
        )

    return AnnotationBlock(raw=raw_text, tags=tags)


def _is_known_tag(tag_name: str) -> bool:
    """Check if tag is in known/standard tags list.

    Based on workflow-annotation-syntax.md for UiPath Workflow Analyzer.

    Args:
        tag_name: Tag name without @ prefix

    Returns:
        True if tag is standard/known, False otherwise
    """
    known_tags = {
        # Workflow Classification
        "unit",
        "module",
        "process",
        "dispatcher",
        "performer",
        "test",
        "deprecated",
        "pathkeeper",
        # Rule Control
        "ignore",
        "ignore-all",
        "strict",
        "nowarn",
        # Documentation & Intent
        "author",
        "description",
        "since",
        "see",
        "todo",
        "review",
        # Architectural Constraints
        "pure",
        "idempotent",
        "transactional",
        "internal",
        "public",
        # Custom tags
        "custom",
    }
    return tag_name in known_tags or tag_name.startswith("custom:")


def extract_module_name(block: AnnotationBlock | None) -> str | None:
    """Extract module name from annotation block.

    Args:
        block: AnnotationBlock to extract from

    Returns:
        Module name, or None if not present

    Example:
        >>> block = parse_annotation("@module ProcessInvoice\\n@author John")
        >>> extract_module_name(block)
        'ProcessInvoice'
    """
    if not block:
        return None
    tag = block.get_tag("module")
    return tag.value if tag else None


def extract_description(block: AnnotationBlock | None) -> str | None:
    """Extract description from annotation block.

    Args:
        block: AnnotationBlock to extract from

    Returns:
        Description text, or None if not present

    Example:
        >>> block = parse_annotation("@description Processes invoices")
        >>> extract_description(block)
        'Processes invoices'
    """
    if not block:
        return None
    tag = block.get_tag("description")
    return tag.value if tag else None


def extract_authors(block: AnnotationBlock | None) -> list[str]:
    """Extract all authors from annotation block.

    Args:
        block: AnnotationBlock to extract from

    Returns:
        List of author names (may be empty)

    Example:
        >>> text = "@author John Doe\\n@author Jane Smith"
        >>> block = parse_annotation(text)
        >>> extract_authors(block)
        ['John Doe', 'Jane Smith']
    """
    if not block:
        return []
    return [tag.value for tag in block.get_tags("author") if tag.value]


__all__ = [
    "parse_annotation",
    "extract_module_name",
    "extract_description",
    "extract_authors",
]
