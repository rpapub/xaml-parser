"""Provenance generation for CC-BY attribution.

This module provides utilities for generating provenance metadata
for outputs, including author information from configuration.
"""

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ...config.models import ProvenanceConfig

from ...shared.model.dto import ProvenanceInfo


def get_parser_version() -> str:
    """Get xaml-parser version.

    Returns:
        Version string (e.g., "0.5.0") or "dev" if not installed
    """
    try:
        from importlib.metadata import version, PackageNotFoundError

        return version("cpmf-uips-xaml")
    except (PackageNotFoundError, ImportError):
        # Package not installed or importlib.metadata not available
        return "dev"


def load_config(start_path: Path | None = None) -> dict[str, Any]:
    """DEPRECATED: Load configuration from repository config file.

    This function is deprecated. Use config.loader.load_config() instead
    for full config hierarchy support (library defaults, project, user, env).

    This legacy function only loads project config, not the full hierarchy.

    Args:
        start_path: Starting directory (defaults to cwd)

    Returns:
        Configuration dict (empty if no config found)
    """
    import warnings
    warnings.warn(
        "provenance.load_config() is deprecated. "
        "Use config.loader.load_config() for full config hierarchy.",
        DeprecationWarning,
        stacklevel=2,
    )

    from ...config.loader import load_project_config
    return load_project_config(start_path)


def get_author_from_config(provenance_config: "ProvenanceConfig | None" = None) -> str | None:
    """Get author name from provenance configuration.

    Priority:
    1. Environment variable XAML_PARSER_AUTHOR
    2. ProvenanceConfig.author
    3. Config hierarchy (if provenance_config not provided)
    4. None

    Args:
        provenance_config: Optional ProvenanceConfig (loads from hierarchy if None)

    Returns:
        Author name or None
    """
    # Check environment variable first
    env_author = os.environ.get("XAML_PARSER_AUTHOR")
    if env_author:
        return env_author.strip()

    # Load from config hierarchy if not provided
    if provenance_config is None:
        from ...config import load_config as load_full_config
        full_config = load_full_config()
        provenance_config = full_config.provenance

    return provenance_config.author


def create_provenance(
    author: str | None = None,
    timestamp: str | None = None,
    provenance_config: "ProvenanceConfig | None" = None,
) -> ProvenanceInfo:
    """Create provenance metadata using config hierarchy.

    Args:
        author: Author name (overrides config if provided)
        timestamp: ISO 8601 timestamp (uses current time if None)
        provenance_config: ProvenanceConfig (loads from hierarchy if None)

    Returns:
        ProvenanceInfo with all fields populated
    """
    if author is None:
        author = get_author_from_config(provenance_config)

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
