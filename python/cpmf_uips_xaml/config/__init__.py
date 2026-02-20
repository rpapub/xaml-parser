"""Configuration system for cpmf_uips_xaml.

This module provides a unified, typed configuration system with hierarchical loading:
- Library defaults (bundled config)
- Project config (.cpmf_uips_xaml.json)
- User config (~/.config/cpmf/cpmf_uips_xaml.json or ~/.cpmf_uips_xaml.json)
- Environment variables
- Explicit overrides

Usage:
    from cpmf_uips_xaml.config import load_config, Config

    # Load config with full hierarchy
    config = load_config()

    # Override specific values
    config = load_config(overrides={"parser": {"strict_mode": True}})

    # Access typed config
    if config.parser.strict_mode:
        # ...
"""

from .loader import load_config, config_to_dict
from .models import (
    Config,
    ParserConfig,
    ProjectConfig,
    EmitterConfig,
    NormalizerConfig,
    ViewConfig,
    ProvenanceConfig,
)

__all__ = [
    "Config",
    "ParserConfig",
    "ProjectConfig",
    "EmitterConfig",
    "NormalizerConfig",
    "ViewConfig",
    "ProvenanceConfig",
    "load_config",
    "config_to_dict",
]
