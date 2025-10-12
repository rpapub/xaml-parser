"""Standalone XAML workflow parser for automation projects.

This package provides complete XAML workflow parsing capabilities with zero
external dependencies, designed for reuse across different projects.

Basic usage:
    from xaml_parser import XamlParser

    parser = XamlParser()
    result = parser.parse_file(Path("workflow.xaml"))

    if result.success:
        content = result.content
        print(f"Found {len(content.arguments)} arguments")
        print(f"Found {len(content.activities)} activities")
"""

from pathlib import Path

from .__version__ import __author__, __description__, __version__
from .analyzer import ProjectAnalyzer, ProjectIndex
from .constants import CORE_VISUAL_ACTIVITIES, DEFAULT_CONFIG, SKIP_ELEMENTS, STANDARD_NAMESPACES
from .extractors import (
    ActivityExtractor,
    AnnotationExtractor,
    ArgumentExtractor,
    MetadataExtractor,
    VariableExtractor,
)
from .graph import Graph
from .models import (
    Activity,
    Expression,
    ParseDiagnostics,
    ParseResult,
    ViewStateData,
    WorkflowArgument,
    WorkflowContent,
    WorkflowVariable,
)
from .parser import XamlParser
from .project import ProjectConfig, ProjectParser, ProjectResult, WorkflowResult, analyze_project
from .utils import DataUtils, DebugUtils, TextUtils, ValidationUtils, XmlUtils
from .validation import OutputValidator, ValidationError, get_validator, validate_output
from .views import ExecutionView, FlatView, SliceView, View

# Public API
__all__ = [
    # Version info
    "__version__",
    "__author__",
    "__description__",
    # Main parser
    "XamlParser",
    # Data models
    "WorkflowContent",
    "WorkflowArgument",
    "WorkflowVariable",
    "Activity",
    "Expression",
    "ViewStateData",
    "ParseResult",
    "ParseDiagnostics",
    # Graph data structure
    "Graph",
    # Analysis
    "ProjectIndex",
    "ProjectAnalyzer",
    # Views
    "View",
    "FlatView",
    "ExecutionView",
    "SliceView",
    # Specialized extractors
    "ArgumentExtractor",
    "VariableExtractor",
    "ActivityExtractor",
    "AnnotationExtractor",
    "MetadataExtractor",
    # Utilities
    "XmlUtils",
    "TextUtils",
    "ValidationUtils",
    "DataUtils",
    "DebugUtils",
    # Output validation
    "OutputValidator",
    "ValidationError",
    "validate_output",
    "get_validator",
    # Constants
    "STANDARD_NAMESPACES",
    "CORE_VISUAL_ACTIVITIES",
    "SKIP_ELEMENTS",
    "DEFAULT_CONFIG",
    # Project parsing
    "ProjectParser",
    "ProjectConfig",
    "ProjectResult",
    "WorkflowResult",
    "analyze_project",
]


def create_parser(config: dict | None = None) -> XamlParser:
    """Convenience function to create parser with configuration.

    Args:
        config: Optional configuration dictionary

    Returns:
        Configured XamlParser instance
    """
    return XamlParser(config)


def parse_xaml_file(file_path: str | Path, config: dict | None = None) -> ParseResult:
    """Convenience function to parse XAML file directly.

    Args:
        file_path: Path to XAML file (string or Path object)
        config: Optional parser configuration

    Returns:
        ParseResult with workflow content
    """
    from pathlib import Path

    parser = XamlParser(config)
    return parser.parse_file(Path(file_path))


def parse_xaml_content(content: str, config: dict | None = None) -> ParseResult:
    """Convenience function to parse XAML content string.

    Args:
        content: XAML content as string
        config: Optional parser configuration

    Returns:
        ParseResult with workflow content
    """
    parser = XamlParser(config)
    return parser.parse_content(content)


# Package metadata for potential PyPI publishing
def get_package_info() -> dict:
    """Get package information dictionary."""
    return {
        "name": "xaml_parser",
        "version": __version__,
        "author": __author__,
        "description": __description__,
        "python_requires": ">=3.9",
        "dependencies": [],  # Zero dependencies
        "keywords": ["xaml", "workflow", "automation", "uipath", "parsing"],
        "classifiers": [
            "Development Status :: 4 - Beta",
            "Intended Audience :: Developers",
            "License :: OSI Approved :: MIT License",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3.9",
            "Programming Language :: Python :: 3.10",
            "Programming Language :: Python :: 3.11",
            "Programming Language :: Python :: 3.12",
            "Topic :: Software Development :: Libraries :: Python Modules",
            "Topic :: Text Processing :: Markup :: XML",
        ],
    }
