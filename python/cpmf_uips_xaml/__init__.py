"""Standalone XAML workflow parser for automation projects.

This package provides complete XAML workflow parsing capabilities with minimal
external dependencies, designed for reuse across different projects.

Quick Start - Single File Parsing:
    from pathlib import Path
    from cpmf_uips_xaml import XamlParser

    parser = XamlParser()
    result = parser.parse_file(Path("workflow.xaml"))

    if result.success:
        content = result.content
        print(f"Found {len(content.arguments)} arguments")
        print(f"Found {len(content.activities)} activities")

Library API - Project Analysis (v0.3.0+):
    from pathlib import Path
    from cpmf_uips_xaml import load

    # Simple: Load and get workflows
    session = load(Path("./MyProject"))
    workflows = session.workflows()

    # Get specific view
    view = session.view("execution", entry_point="Main.xaml")

    # Export workflows
    session.emit("json", output_path=Path("output.json"))

    # Alternative: Legacy API (still supported)
    from cpmf_uips_xaml.api import parse_and_analyze_project
    project_result, analyzer, index = parse_and_analyze_project(Path("./MyProject"))

For complete documentation, see README.md or the "Library API" section.
"""

from pathlib import Path
from typing import Any

# Version info
from .__version__ import __author__, __description__, __version__

# API functions (orchestration layer)
from .api import (
    build_index,
    create_parse_error,
    create_pipeline,
    emit_workflows,
    load,
    load_default_config,
    normalize_parse_results,
    parse_and_analyze_project,
    parse_file,
    parse_file_to_dto,
    parse_project,
    ProjectSession,
    render_json,
    render_project_view,
)

# DTO models (stable data contracts)
from .shared.model.dto import (
    ActivityDto,
    AntiPattern,
    ArgumentDto,
    DependencyDto,
    EdgeDto,
    EntryPointInfo,
    InvocationDto,
    IssueDto,
    ProjectInfo,
    ProvenanceInfo,
    QualityMetrics,
    SourceInfo,
    VariableDto,
    VariableFlowDto,
    WorkflowCollectionDto,
    WorkflowDto,
    WorkflowMetadata,
)

# Parse models (parsing results)
from .shared.model.models import (
    Activity,
    Expression,
    ParseDiagnostics,
    ParseResult,
    ViewStateData,
    WorkflowArgument,
    WorkflowContent,
    WorkflowVariable,
)

# Project parsing
from .stages.assemble.project import (
    ProjectConfig,
    ProjectParser,
    ProjectResult,
    WorkflowResult,
    analyze_project,
)

# Analysis and indexing
from .stages.assemble.index import ProjectIndex
from .stages.assemble.analyzer import ProjectAnalyzer

# Views (output transformations)
from .stages.emit.views import ExecutionView, NestedView, SliceView, View

# Platform constants (for backward compatibility)
from .platforms.uipath.constants import (
    CORE_VISUAL_ACTIVITIES,
    DEFAULT_CONFIG,
    SKIP_ELEMENTS,
    STANDARD_NAMESPACES,
)

# Internal imports for XamlParser implementation
from .stages.parsing.parser import XamlParser as CoreXamlParser
from .stages.assemble.project import _create_platform_config


# Platform-configured XamlParser for public API
class XamlParser:
    """XAML workflow parser configured for automation platforms.

    This is a convenience wrapper around the core parser with platform-specific
    configuration pre-applied.

    Example:
        parser = XamlParser()
        result = parser.parse_file(Path("workflow.xaml"))
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """Initialize parser with optional configuration.

        Args:
            config: Parser configuration dict (merged with platform defaults)
        """
        platform_config = _create_platform_config()
        self._parser = CoreXamlParser(platform_config=platform_config, config=config)

    def parse_file(self, file_path: Path) -> ParseResult:
        """Parse XAML workflow file.

        Args:
            file_path: Path to XAML file

        Returns:
            ParseResult with extracted content or error information
        """
        return self._parser.parse_file(file_path)

    def parse_content(self, xml_content: str, file_path: str = "<string>") -> ParseResult:
        """Parse XAML content from string.

        Args:
            xml_content: Raw XAML content
            file_path: Virtual file path for error reporting

        Returns:
            ParseResult with extracted content or error information
        """
        return self._parser.parse_content(xml_content, file_path)

    @property
    def config(self) -> dict[str, Any]:
        """Get parser configuration."""
        return self._parser.config

    @property
    def profiler(self):
        """Get profiler instance."""
        return self._parser.profiler


# Public API
__all__ = [
    # ============================================================================
    # Version Info
    # ============================================================================
    "__version__",
    "__author__",
    "__description__",
    # ============================================================================
    # Main Parser
    # ============================================================================
    "XamlParser",
    # ============================================================================
    # API Functions (Orchestration Layer)
    # ============================================================================
    # Primary API (v0.4.0)
    "load",
    "ProjectSession",
    # Original API
    "parse_file",
    "create_parse_error",
    "parse_project",
    "build_index",
    "emit",
    # New orchestration functions (v0.3.0)
    "parse_and_analyze_project",
    "render_project_view",
    "normalize_parse_results",
    "emit_workflows",
    "parse_file_to_dto",
    "load_default_config",
    "create_emitter_config",
    # ============================================================================
    # DTO Models (Stable Data Contracts)
    # ============================================================================
    "WorkflowDto",
    "WorkflowCollectionDto",
    "ActivityDto",
    "ArgumentDto",
    "VariableDto",
    "EdgeDto",
    "DependencyDto",
    "InvocationDto",
    "IssueDto",
    "VariableFlowDto",
    "WorkflowMetadata",
    "ProjectInfo",
    "EntryPointInfo",
    "SourceInfo",
    "ProvenanceInfo",
    "QualityMetrics",
    "AntiPattern",
    # ============================================================================
    # Parse Models (Parsing Results)
    # ============================================================================
    "ParseResult",
    "WorkflowContent",
    "Activity",
    "WorkflowArgument",
    "WorkflowVariable",
    "Expression",
    "ViewStateData",
    "ParseDiagnostics",
    # ============================================================================
    # Project Parsing
    # ============================================================================
    "ProjectParser",
    "ProjectConfig",
    "ProjectResult",
    "WorkflowResult",
    "analyze_project",
    # ============================================================================
    # Analysis and Indexing
    # ============================================================================
    "ProjectIndex",
    "ProjectAnalyzer",
    # ============================================================================
    # Views (Output Transformations)
    # ============================================================================
    "View",
    "NestedView",
    "ExecutionView",
    "SliceView",
    # ============================================================================
    # Platform Constants (Backward Compatibility)
    # ============================================================================
    "STANDARD_NAMESPACES",
    "CORE_VISUAL_ACTIVITIES",
    "SKIP_ELEMENTS",
    "DEFAULT_CONFIG",
]


def create_parser(config: dict[str, Any] | None = None) -> XamlParser:
    """Convenience function to create parser with configuration.

    Args:
        config: Optional configuration dictionary

    Returns:
        Configured XamlParser instance with platform defaults
    """
    return XamlParser(config)


def parse_xaml_file(file_path: str | Path, config: dict[str, Any] | None = None) -> ParseResult:
    """Convenience function to parse XAML file directly.

    Args:
        file_path: Path to XAML file (string or Path object)
        config: Optional parser configuration

    Returns:
        ParseResult with workflow content
    """
    parser = create_parser(config)
    return parser.parse_file(Path(file_path))


def parse_xaml_content(content: str, config: dict[str, Any] | None = None) -> ParseResult:
    """Convenience function to parse XAML content string.

    Args:
        content: XAML content as string
        config: Optional parser configuration

    Returns:
        ParseResult with workflow content
    """
    parser = create_parser(config)
    return parser.parse_content(content)


# Package metadata for potential PyPI publishing
def get_package_info() -> dict[str, Any]:
    """Get package information dictionary."""
    return {
        "name": "cpmf_uips_xaml",
        "version": __version__,
        "author": __author__,
        "description": __description__,
        "python_requires": ">=3.11",
        "dependencies": ["defusedxml>=0.7.1"],
        "keywords": ["xaml", "workflow", "automation", "uipath", "parsing", "cprima-forge"],
        "classifiers": [
            "Development Status :: 4 - Beta",
            "Intended Audience :: Developers",
            "Operating System :: OS Independent",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3.11",
            "Programming Language :: Python :: 3.12",
            "Programming Language :: Python :: 3.13",
            "Topic :: Software Development :: Libraries :: Python Modules",
            "Topic :: Text Processing :: Markup :: XML",
        ],
    }
