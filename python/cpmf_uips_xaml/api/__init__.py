"""Public API facade for orchestrating parsing, analysis, and output.

This module provides the stable boundary for external consumers.
All orchestration logic (component wiring, workflow coordination) lives here.

The API is modularized into focused submodules:
- parsing: Parse XAML files and projects, normalize to DTOs
- analysis: Build indices and analyze project structure
- views: Render projects in different view transformations
- emit: Output workflows in various formats
- config: Load and manage parser configuration

All functions are re-exported from __init__.py for backward compatibility.
"""

from pathlib import Path
from typing import Any, Literal

# Re-export config types
from ..config import Config, ParserConfig, EmitterConfig

# Re-export all public types
from ..shared.model.dto import WorkflowCollectionDto, WorkflowDto
from ..shared.model.models import ParseResult
from ..shared.progress import NULL_REPORTER, ProgressReporter
from ..stages.assemble.index import ProjectIndex
from ..stages.assemble.analyzer import ProjectAnalyzer
from ..stages.assemble.project import ProjectResult

# Re-export all functions from submodules
from .parsing import (
    parse_file,
    create_parse_error,
    parse_project,
    parse_file_to_dto,
    normalize_parse_results,
)
from .analysis import build_index, analyze_project
from .views import render_project_view
from .emit import emit_workflows, render_json, create_pipeline
from .config import load_default_config, get_config_dict
from .load import load
from .session import ProjectSession


# ============================================================================
# High-Level Orchestration Functions
# ============================================================================
# These orchestration functions stay in __init__.py as they coordinate
# multiple submodules and represent the primary API entry points.


def parse_and_analyze_project(
    project_dir: Path,
    recursive: bool = True,
    entry_points_only: bool = False,
    reporter: ProgressReporter = NULL_REPORTER,
    config: Config | dict[str, Any] | None = None,
) -> tuple[ProjectResult, ProjectAnalyzer, ProjectIndex]:
    """Parse project and build queryable index.

    Orchestrates the complete project parsing and analysis pipeline:
    1. ProjectParser.parse_project() - Parse all XAML files
    2. analyze_project() - Build graphs and index

    Args:
        project_dir: Path to project directory (containing project.json)
        recursive: Follow InvokeWorkflowFile references
        entry_points_only: Only parse entry points (no recursive discovery)
        reporter: Progress reporter for event notifications (default: NullReporter)
        config: Configuration (Config object, dict, or None for defaults)

    Returns:
        Tuple of (ProjectResult, ProjectAnalyzer, ProjectIndex) with parse results,
        analyzer, and index ready for querying or view rendering

    Example:
        # Use default config
        result, analyzer, index = parse_and_analyze_project(Path("./MyProject"))

        # Use typed config
        from cpmf_uips_xaml.config import load_config
        config = load_config()
        result, analyzer, index = parse_and_analyze_project(Path("./MyProject"), config=config)
    """
    from ..config import load_config as _load_config
    from ..stages.assemble.project import ProjectParser

    # Normalize config to dict for ProjectParser (until ProjectParser is updated)
    if config is None:
        full_config = _load_config(start_path=project_dir)
        parser_config_dict = get_config_dict(full_config)["parser"]
    elif isinstance(config, dict):
        parser_config_dict = config
    else:
        # Config object - extract parser section as dict
        parser_config_dict = get_config_dict(config)["parser"]

    parser = ProjectParser(parser_config_dict)
    project_result = parser.parse_project(
        project_dir,
        recursive=recursive,
        entry_points_only=entry_points_only,
        reporter=reporter,
    )

    if not project_result.success:
        raise ValueError(f"Project parsing failed: {project_result.errors}")

    # Use analyze_project from api.analysis (which wraps stages.assemble.project.analyze_project)
    analyzer, index = analyze_project(project_result)
    return project_result, analyzer, index


# ============================================================================
# Public API Exports
# ============================================================================

__all__ = [
    # Configuration types
    "Config",
    "ParserConfig",
    "EmitterConfig",
    # High-level orchestration
    "load",  # NEW: Primary API entry point
    "ProjectSession",  # NEW: Session object
    "parse_and_analyze_project",
    # Parsing functions (from api.parsing)
    "parse_file",
    "create_parse_error",
    "parse_project",
    "parse_file_to_dto",
    "normalize_parse_results",
    # Analysis functions (from api.analysis)
    "build_index",
    "analyze_project",
    # View functions (from api.views)
    "render_project_view",
    # Emit functions (from api.emit)
    "emit_workflows",
    "render_json",
    "create_pipeline",
    # Config functions (from api.config)
    "load_default_config",
    # Types
    "ParseResult",
    "ProjectResult",
    "WorkflowDto",
    "WorkflowCollectionDto",
    "ProjectAnalyzer",
    "ProjectIndex",
    "ProgressReporter",
    "NULL_REPORTER",
]
