"""Configuration management functions.

Provides utilities for loading and managing parser configuration.
"""

from pathlib import Path
from typing import Any

from ..config import Config, load_config, config_to_dict


def load_default_config(start_path: Path | None = None) -> Config:
    """Load configuration with full hierarchy.

    Returns typed Config object with library defaults, project config,
    user config, and environment variable overrides applied.

    Args:
        start_path: Starting path for project config search (defaults to cwd)

    Returns:
        Typed Config object

    Example:
        from cpmf_uips_xaml.api import load_default_config

        # Load config with full hierarchy
        config = load_default_config()

        # Access typed config
        if config.parser.strict_mode:
            # ...
    """
    return load_config(start_path=start_path)


def get_config_dict(config: Config) -> dict[str, Any]:
    """Convert Config object to dict for serialization.

    Args:
        config: Config object

    Returns:
        Dict representation

    Example:
        config = load_default_config()
        config_dict = get_config_dict(config)
    """
    return config_to_dict(config)


__all__ = ["load_default_config", "get_config_dict"]
