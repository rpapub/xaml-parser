"""Provenance generation for CC-BY attribution.

This module provides utilities for generating provenance metadata
for outputs, including author information from configuration.
"""

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .dto import ProvenanceInfo


def get_parser_version() -> str:
    """Get xaml-parser version.

    Returns:
        Version string (e.g., "0.5.0") or "dev" if not installed
    """
    try:
        from importlib.metadata import version

        return version("xaml-parser")
    except Exception:
        return "dev"


def load_config(start_path: Path | None = None) -> dict[str, Any]:
    """Load configuration from repository .xaml-parser.json file.

    Searches for .xaml-parser.json starting from start_path and walking up
    to repository root (directory containing .git).

    Args:
        start_path: Starting directory (defaults to cwd)

    Returns:
        Configuration dict (empty if no config found)
    """
    if start_path is None:
        start_path = Path.cwd()

    # Walk up directory tree looking for .xaml-parser.json
    current = start_path.resolve()
    while current != current.parent:
        config_file = current / ".xaml-parser.json"
        if config_file.exists():
            try:
                with open(config_file, encoding="utf-8") as f:
                    config_data: dict[str, Any] = json.load(f)
                    return config_data
            except Exception:
                pass  # Ignore malformed config

        # Stop at repository root (has .git directory)
        if (current / ".git").exists():
            break

        current = current.parent

    return {}


def get_author_from_config(config: dict[str, Any] | None = None) -> str | None:
    """Get author name from configuration.

    Priority:
    1. Environment variable XAML_PARSER_AUTHOR
    2. Config dict 'author' key
    3. Config file (if config not provided)
    4. None

    Args:
        config: Optional config dict (will load from file if None)

    Returns:
        Author name or None
    """
    # Check environment variable first
    env_author = os.environ.get("XAML_PARSER_AUTHOR")
    if env_author:
        return env_author.strip()

    # Check provided config
    if config is None:
        config = load_config()

    author = config.get("author")
    if author and isinstance(author, str):
        return str(author).strip()

    return None


def create_provenance(author: str | None = None, timestamp: str | None = None) -> ProvenanceInfo:
    """Create provenance metadata.

    Args:
        author: Author name (will attempt to load from config if None)
        timestamp: ISO 8601 timestamp (uses current time if None)

    Returns:
        ProvenanceInfo with all fields populated
    """
    if author is None:
        author = get_author_from_config()

    if timestamp is None:
        timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    version = get_parser_version()

    authors = [author] if author else []

    return ProvenanceInfo(
        generated_by=f"xaml-parser/{version}",
        generated_at=timestamp,
        generator_url="https://github.com/rpapub/xaml-parser",
        authors=authors,
        license="CC-BY-4.0",
        license_url="https://creativecommons.org/licenses/by/4.0/",
    )
