"""Simplified load() API for UiPath project parsing.

Provides an intuitive, unified entry point for loading UiPath projects
and workflows with flexible output modes.
"""

from pathlib import Path
from typing import Any, Literal

from ..config import Config
from ..shared.progress import NULL_REPORTER, ProgressReporter
from ..stages.assemble.index import ProjectIndex
from .session import ProjectSession
from .parsing import parse_file, normalize_parse_results
from .views import render_project_view
from .config import load_default_config, get_config_dict


def load(
    path: Path | str,
    *,
    # Mode control
    mode: Literal["auto", "project", "workflow"] = "auto",
    # Output control
    output: Literal["dto", "view", "index"] = "dto",
    # View parameters (when output="view")
    view: Literal["nested", "execution", "slice"] = "nested",
    entry_point: str | None = None,
    focus: str | None = None,
    radius: int = 2,
    # Configuration
    config: dict[str, Any] | Config | None = None,
    recursive: bool = True,
    entry_points_only: bool = False,
    reporter: ProgressReporter = NULL_REPORTER,
) -> ProjectSession | dict[str, Any] | ProjectIndex:
    """Load UiPath project or workflow with flexible output modes.

    This is the primary entry point for the cpmf_uips_xaml API. It provides
    a simplified interface that auto-detects the input type and returns
    the appropriate data structure.

    Args:
        path: Path to UiPath project directory, project.json, or workflow .xaml file
        mode: Loading mode - "auto" (detect), "project" (full project), or "workflow" (single file)
        output: Output mode:
            - "dto": Return ProjectSession with full API (default)
            - "view": Return dict with view projection
            - "index": Return ProjectIndex for querying
        view: View type for output="view" (nested, execution, slice)
        entry_point: Starting workflow for execution view
        focus: Center workflow for slice view
        radius: Depth for slice view (default: 2)
        config: Configuration (None=auto-load, dict=merge, Config=use directly)
        recursive: Follow InvokeWorkflowFile references (default: True)
        entry_points_only: Only parse entry points, no recursive discovery (default: False)
        reporter: Progress reporter for events (default: NULL_REPORTER)

    Returns:
        - ProjectSession if output="dto" (default) - full API for working with project
        - dict if output="view" - view projection
        - ProjectIndex if output="index" - queryable index

    Examples:
        >>> # Simple: Load and get workflows
        >>> session = load(Path("./MyProject"))
        >>> workflows = session.workflows()

        >>> # Get specific view
        >>> view = load(
        ...     Path("./MyProject"),
        ...     output="view",
        ...     view="execution",
        ...     entry_point="Main.xaml"
        ... )

        >>> # Single workflow
        >>> session = load(Path("./MyProject/workflows/Main.xaml"))
        >>> wf = session.workflow("Main.xaml")

        >>> # Get index for querying
        >>> index = load(Path("./MyProject"), output="index")
        >>> wf_info = index.get_workflow("Main.xaml")

    Raises:
        ValueError: If path cannot be auto-detected or is invalid
        ValueError: If parsing fails
    """
    # 1. Normalize path
    path = Path(path)

    # 2. Detect mode if auto
    if mode == "auto":
        mode = _detect_mode(path)

    # 3. Load configuration
    resolved_config = _resolve_config(path, config)

    # 4. Parse based on mode
    if mode == "project":
        # Import here to avoid circular dependency
        from . import parse_and_analyze_project

        result, analyzer, index = parse_and_analyze_project(
            path if path.is_dir() else path.parent,
            config=resolved_config,
            reporter=reporter,
            recursive=recursive,
            entry_points_only=entry_points_only,
        )
    elif mode == "workflow":
        # Single workflow: parse file, create minimal project context
        result, analyzer, index = _load_single_workflow(
            path, resolved_config, reporter
        )
    else:
        raise ValueError(f"Unknown mode: {mode}")

    # 5. Return based on output mode
    if output == "dto":
        return ProjectSession(
            result=result,
            analyzer=analyzer,
            index=index,
            config=resolved_config,
            project_dir=path if path.is_dir() else path.parent,
        )
    elif output == "view":
        return render_project_view(
            analyzer,
            index,
            view_type=view,
            entry_point=entry_point,
            focus=focus,
            radius=radius,
        )
    elif output == "index":
        return index
    else:
        raise ValueError(f"Unknown output mode: {output}")


# ============================================================================
# Helper Functions
# ============================================================================


def _detect_mode(path: Path) -> Literal["project", "workflow"]:
    """Auto-detect loading mode from path.

    Args:
        path: Path to detect mode for

    Returns:
        "project" or "workflow"

    Raises:
        ValueError: If mode cannot be detected
    """
    if not path.exists():
        raise ValueError(f"Path does not exist: {path}")

    if path.is_file():
        if path.suffix.lower() == ".xaml":
            return "workflow"
        elif path.name.lower() == "project.json":
            return "project"
        else:
            raise ValueError(f"Unsupported file type: {path}. Expected .xaml or project.json")

    elif path.is_dir():
        if (path / "project.json").exists():
            return "project"
        else:
            raise ValueError(
                f"Directory does not contain project.json: {path}. "
                "Cannot auto-detect as project. Specify mode='project' or provide path to .xaml file."
            )

    raise ValueError(f"Cannot detect mode for path: {path}")


def _resolve_config(path: Path, config: dict | Config | None) -> Config:
    """Resolve configuration from parameter and defaults.

    Args:
        path: Base path for config resolution
        config: User-provided config (None, dict, or Config)

    Returns:
        Resolved Config object

    Raises:
        TypeError: If config is not None, dict, or Config
    """
    if config is None:
        # Load default config from project directory
        return load_default_config(start_path=path if path.is_dir() else path.parent)

    elif isinstance(config, dict):
        # Merge dict overrides into default config
        base_config = load_default_config(start_path=path if path.is_dir() else path.parent)
        return _merge_config_dict(base_config, config)

    elif isinstance(config, Config):
        return config

    else:
        raise TypeError(f"config must be None, dict, or Config, got {type(config)}")


def _merge_config_dict(base: Config, overrides: dict) -> Config:
    """Merge dict overrides into Config object.

    Args:
        base: Base Config object
        overrides: Dict with override values

    Returns:
        New Config object with merged values
    """
    # Convert Config to dict, deep merge, convert back
    base_dict = get_config_dict(base)
    merged = _deep_merge(base_dict, overrides)

    # Reconstruct Config from merged dict
    from ..config import (
        ParserConfig,
        ProjectConfig,
        EmitterConfig,
        NormalizerConfig,
        ViewConfig,
        ProvenanceConfig,
    )

    return Config(
        parser=ParserConfig(**merged.get("parser", {})),
        project=ProjectConfig(**merged.get("project", {})),
        emitter=EmitterConfig(**merged.get("emitter", {})),
        normalizer=NormalizerConfig(**merged.get("normalizer", {})),
        view=ViewConfig(**merged.get("view", {})),
        provenance=ProvenanceConfig(**merged.get("provenance", {})),
    )


def _deep_merge(base: dict, overrides: dict) -> dict:
    """Deep merge two dictionaries.

    Args:
        base: Base dictionary
        overrides: Override dictionary

    Returns:
        Merged dictionary
    """
    result = base.copy()
    for key, value in overrides.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _load_single_workflow(
    workflow_path: Path,
    config: Config,
    reporter: ProgressReporter,
) -> tuple[Any, Any, Any]:
    """Load single workflow file and create minimal project context.

    Args:
        workflow_path: Path to .xaml workflow file
        config: Resolved configuration
        reporter: Progress reporter

    Returns:
        Tuple of (ProjectResult, ProjectAnalyzer, ProjectIndex) for the single workflow

    Raises:
        ValueError: If workflow parsing fails
    """
    from ..stages.assemble.project import ProjectResult, ProjectConfig as ProjConfig
    from ..stages.assemble.analyzer import ProjectAnalyzer
    from ..stages.assemble.index import ProjectIndex

    # Parse single workflow file with config
    # Extract parser config dict from Config object and pass as kwargs
    parser_config_dict = get_config_dict(config)["parser"]
    parse_result = parse_file(workflow_path, **parser_config_dict)

    if not parse_result.success:
        raise ValueError(f"Failed to parse workflow: {workflow_path}\nErrors: {parse_result.errors}")

    # Create minimal ProjectConfig for single workflow
    project_dir = workflow_path.parent
    project_config = ProjConfig(
        name=workflow_path.stem,
        main=workflow_path.name,
        description=f"Single workflow: {workflow_path.name}",
        expression_language="VisualBasic",
        entry_points=[{
            "file_path": workflow_path.name,
            "filePath": workflow_path.name,  # Both formats for compatibility
        }],
        dependencies={},
        project_version="1.0.0",
    )

    # Create minimal ProjectResult with single workflow
    from ..stages.assemble.project import WorkflowResult

    workflow_result = WorkflowResult(
        file_path=workflow_path,
        relative_path=workflow_path.name,
        parse_result=parse_result,
        invoked_workflows=[],
        is_entry_point=True,
    )

    project_result = ProjectResult(
        success=True,
        workflows=[workflow_result],
        project_config=project_config,
        project_dir=project_dir,
        total_workflows=1,
        errors=[],
    )

    # Build analyzer and index
    from .analysis import analyze_project

    analyzer, index = analyze_project(project_result)

    return project_result, analyzer, index
