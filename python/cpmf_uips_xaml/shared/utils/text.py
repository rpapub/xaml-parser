"""Text processing utilities for XAML parsing operations.

This module provides helper functions for text cleaning, path normalization,
and type signature extraction.
"""

import html
import re


class TextUtils:
    """Text processing utilities."""

    @staticmethod
    def clean_annotation(text: str) -> str:
        """Clean annotation text by decoding HTML entities and normalizing whitespace.

        Args:
            text: Raw annotation text

        Returns:
            Cleaned annotation text
        """
        if not text:
            return ""

        # Decode HTML entities
        cleaned = html.unescape(text)

        # Normalize whitespace
        cleaned = re.sub(r"\s+", " ", cleaned.strip())

        # Convert HTML line breaks
        cleaned = cleaned.replace("&#xA;", "\n").replace("&#xa;", "\n")
        cleaned = cleaned.replace("<br>", "\n").replace("<br/>", "\n")

        return cleaned

    @staticmethod
    def extract_type_name(type_signature: str) -> str:
        """Extract simple type name from full .NET type signature.

        Args:
            type_signature: Full type signature like 'InArgument(x:String)'

        Returns:
            Simple type name like 'String'
        """
        if not type_signature:
            return "Object"

        # Extract from generic type syntax: Type(InnerType)
        match = re.search(r"\(([^)]+)\)", type_signature)
        if match:
            inner_type = match.group(1)
            # Remove namespace prefix if present
            if ":" in inner_type:
                inner_type = inner_type.split(":")[-1]
            return inner_type

        # Remove namespace prefix
        if ":" in type_signature:
            return type_signature.split(":")[-1]

        return type_signature

    @staticmethod
    def normalize_path(path: str) -> str:
        """Normalize file path to POSIX format.

        Args:
            path: File path (Windows or POSIX)

        Returns:
            POSIX-normalized path
        """
        return path.replace("\\", "/") if path else ""

    @staticmethod
    def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
        """Truncate text to maximum length.

        Args:
            text: Text to truncate
            max_length: Maximum allowed length
            suffix: Suffix to add if truncated

        Returns:
            Truncated text with suffix if needed
        """
        if not text or len(text) <= max_length:
            return text

        return text[: max_length - len(suffix)] + suffix
