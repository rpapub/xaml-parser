"""Shared utilities for emitters."""

from pathlib import Path


def sanitize_filename(name: str, max_length: int = 200, fallback: str = "untitled") -> str:
    """Sanitize workflow name for use as safe filename.

    Args:
        name: Original filename (without extension)
        max_length: Maximum filename length (default: 200)
        fallback: Fallback name if empty after sanitization

    Returns:
        Safe filename without extension

    Behavior changes from previous per-emitter implementations:
        - MermaidEmitter/DocEmitter: Now strips `. _` (dots, spaces, underscores)
          Previously only stripped spaces. This is a BREAKING CHANGE if workflows
          have leading/trailing dots or underscores in names.
        - All emitters: Consistent length limit (200 chars) and fallback behavior
    """
    if not name:
        return fallback

    # Replace invalid filesystem chars with underscore
    invalid_chars = r'<>:"/\|?*'
    sanitized = name
    for char in invalid_chars:
        sanitized = sanitized.replace(char, "_")

    # Strip leading/trailing dots, spaces, underscores
    # NOTE: This is a behavior change for Mermaid/Doc emitters
    sanitized = sanitized.strip(". _")

    # Limit length
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length].rstrip(". _")

    return sanitized or fallback


def ensure_dir(path: Path) -> None:
    """Ensure directory exists.

    Args:
        path: Directory path to create
    """
    path.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    """Write text to file.

    Args:
        path: File path
        text: Content to write
        encoding: Text encoding (default: utf-8)
    """
    path.write_text(text, encoding=encoding)
