"""Configuration loading with hierarchy support.

Load order (later overrides earlier):
1. Library defaults (bundled cpmf-uips-xaml.json)
2. Project config (.cpmf-uips-xaml.json in project or ancestors)
3. User config (~/.config/cpmf/cpmf-uips-xaml.json or ~/.cpmf-uips-xaml.json)
4. Environment variables (XAML_PARSER_*)
5. Explicit parameters (CLI args or API calls)

Example:
    from cpmf_uips_xaml.config import load_config

    # Load with full hierarchy
    config = load_config()

    # Override from CLI args
    config = load_config(overrides={"parser": {"strict_mode": True}})

    # Start search from specific directory
    config = load_config(start_path=Path("/path/to/project"))
"""

import json
import os
from pathlib import Path
from typing import Any

from .models import (
    Config,
    ParserConfig,
    ProjectConfig,
    EmitterConfig,
    NormalizerConfig,
    ViewConfig,
    ProvenanceConfig,
)


def load_library_defaults() -> dict[str, Any]:
    """Load bundled default config from package resources.

    Returns:
        Default configuration dict

    Raises:
        FileNotFoundError: If cpmf-uips-xaml.json is missing from package
    """
    # Use importlib.resources for Python 3.9+ compatibility
    try:
        from importlib.resources import files

        config_file = files("cpmf_uips_xaml.config") / "cpmf-uips-xaml.json"
        config_text = config_file.read_text(encoding="utf-8")
    except (ImportError, AttributeError):
        # Fallback for older Python or dev environment
        try:
            import pkg_resources

            config_text = pkg_resources.resource_string(
                "cpmf_uips_xaml.config", "cpmf-uips-xaml.json"
            ).decode("utf-8")
        except Exception:
            # Last resort: direct file access for development
            default_path = Path(__file__).parent / "cpmf-uips-xaml.json"
            if default_path.exists():
                config_text = default_path.read_text(encoding="utf-8")
            else:
                raise FileNotFoundError(
                    "Could not load cpmf-uips-xaml.json from package resources"
                )

    return json.loads(config_text)


def load_project_config(start_path: Path | None = None) -> dict[str, Any]:
    """Load project config from .cpmf-uips-xaml.json.

    Searches upward from start_path to repository root (.git).

    Args:
        start_path: Starting directory (defaults to cwd)

    Returns:
        Project config dict (empty if not found)
    """
    if start_path is None:
        start_path = Path.cwd()

    current = start_path.resolve()
    while current != current.parent:
        config_file = current / ".cpmf-uips-xaml.json"
        if config_file.exists():
            try:
                with open(config_file, encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError, UnicodeDecodeError) as e:
                import warnings

                warnings.warn(
                    f"Failed to load project config from {config_file}: {e}",
                    stacklevel=2,
                )

        # Stop at repository root
        if (current / ".git").exists():
            break

        current = current.parent

    return {}


def load_user_config() -> dict[str, Any]:
    """Load user profile config.

    Checks (in order):
    1. ~/.config/cpmf/cpmf-uips-xaml.json (XDG-compliant)
    2. ~/.cpmf-uips-xaml.json (fallback)

    Returns:
        User config dict (empty if not found)
    """
    home = Path.home()

    # Try XDG location first (all CPMF tools under ~/.config/cpmf/)
    xdg_config = home / ".config" / "cpmf" / "cpmf-uips-xaml.json"
    if xdg_config.exists():
        try:
            with open(xdg_config, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError, UnicodeDecodeError):
            pass

    # Try home directory location
    home_config = home / ".cpmf-uips-xaml.json"
    if home_config.exists():
        try:
            with open(home_config, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError, UnicodeDecodeError):
            pass

    return {}


def load_env_overrides() -> dict[str, Any]:
    """Load config overrides from environment variables.

    Supported variables:
    - XAML_PARSER_AUTHOR: provenance.author
    - XAML_PARSER_STRICT: parser.strict_mode (true/false)
    - XAML_PARSER_MAX_DEPTH: parser.max_depth (int)
    - XAML_PARSER_PROFILE: emitter.field_profile

    Returns:
        Config overrides dict
    """
    overrides: dict[str, Any] = {}

    # Provenance author
    if author := os.environ.get("XAML_PARSER_AUTHOR"):
        overrides.setdefault("provenance", {})["author"] = author.strip()

    # Parser strict mode
    if strict := os.environ.get("XAML_PARSER_STRICT"):
        overrides.setdefault("parser", {})["strict_mode"] = strict.lower() in (
            "true",
            "1",
            "yes",
        )

    # Parser max depth
    if max_depth := os.environ.get("XAML_PARSER_MAX_DEPTH"):
        try:
            overrides.setdefault("parser", {})["max_depth"] = int(max_depth)
        except ValueError:
            pass

    # Emitter profile
    if profile := os.environ.get("XAML_PARSER_PROFILE"):
        overrides.setdefault("emitter", {})["field_profile"] = profile.strip()

    return overrides


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep merge two config dicts.

    Args:
        base: Base configuration
        override: Overriding configuration

    Returns:
        Merged configuration (override values take precedence)
    """
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value

    return result


def load_config(
    start_path: Path | None = None,
    overrides: dict[str, Any] | None = None,
) -> Config:
    """Load configuration with full hierarchy.

    Load order (later overrides earlier):
    1. Library defaults
    2. Project config
    3. User config
    4. Environment variables
    5. Explicit overrides

    Args:
        start_path: Starting path for project config search
        overrides: Explicit config overrides (e.g., from CLI args)

    Returns:
        Fully resolved Config object

    Example:
        # Load with defaults
        config = load_config()

        # Override from CLI
        config = load_config(overrides={"parser": {"strict_mode": True}})
    """
    # Start with library defaults
    config_dict = load_library_defaults()

    # Merge project config
    project_config = load_project_config(start_path)
    if project_config:
        config_dict = deep_merge(config_dict, project_config)

    # Merge user config
    user_config = load_user_config()
    if user_config:
        config_dict = deep_merge(config_dict, user_config)

    # Merge environment overrides
    env_config = load_env_overrides()
    if env_config:
        config_dict = deep_merge(config_dict, env_config)

    # Merge explicit overrides
    if overrides:
        config_dict = deep_merge(config_dict, overrides)

    # Convert to dataclass
    return Config(
        parser=ParserConfig(**config_dict["parser"]),
        project=ProjectConfig(**config_dict["project"]),
        emitter=EmitterConfig(**config_dict["emitter"]),
        normalizer=NormalizerConfig(**config_dict["normalizer"]),
        view=ViewConfig(**config_dict["view"]),
        provenance=ProvenanceConfig(**config_dict["provenance"]),
    )


def config_to_dict(config: Config) -> dict[str, Any]:
    """Convert Config object to dict for serialization.

    Args:
        config: Config object

    Returns:
        Dict representation suitable for JSON serialization

    Example:
        config = load_config()
        config_dict = config_to_dict(config)
        with open("config.json", "w") as f:
            json.dump(config_dict, f, indent=2)
    """
    from dataclasses import asdict

    return asdict(config)
