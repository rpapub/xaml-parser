"""Parsing and normalization functions.

Provides functions for parsing XAML files and projects, and normalizing
ParseResults to WorkflowDtos.
"""

from pathlib import Path
from typing import Any, TYPE_CHECKING

from ..shared.model.dto import WorkflowDto
from ..shared.model.models import ParseResult

if TYPE_CHECKING:
    from ..stages.assemble.project import ProjectResult


def parse_file(xaml_path: Path, **config) -> ParseResult:
    """Parse a single XAML workflow file.

    Args:
        xaml_path: Path to XAML file
        **config: Parser configuration options

    Returns:
        ParseResult with workflow content or errors
    """
    from .. import XamlParser

    # XamlParser expects config as dict or None
    # If config is empty dict, pass None instead
    parser_config = config if config else None
    parser = XamlParser(parser_config)
    return parser.parse_file(xaml_path)


def create_parse_error(
    file_path: str,
    error_message: str,
    config: dict[str, Any]
) -> ParseResult:
    """Create an error ParseResult for failed operations.

    Args:
        file_path: File path that failed
        error_message: Error description
        config: Parser configuration used

    Returns:
        ParseResult with success=False
    """
    return ParseResult(
        content=None,
        success=False,
        errors=[error_message],
        warnings=[],
        parse_time_ms=0.0,
        file_path=file_path,
        diagnostics=None,
        config_used=config,
    )


def parse_project(project_path: Path, **config) -> "ProjectResult":
    """Parse entire UiPath project.

    Args:
        project_path: Path to project directory or project.json
        **config: Parser configuration options

    Returns:
        ProjectResult with all workflows and metadata
    """
    from ..stages.assemble.project import ProjectParser

    # ProjectParser expects config as dict or None
    # If config is empty dict, pass None instead
    parser_config = config if config else None
    parser = ProjectParser(parser_config)
    return parser.parse_project(project_path)


def parse_file_to_dto(
    xaml_path: Path,
    project_dir: Path | None = None,
    **config
) -> WorkflowDto:
    """Parse single XAML file and normalize to DTO.

    Orchestrates single-file parsing and normalization:
    1. XamlParser.parse_file() - Parse XAML
    2. Normalizer.normalize() - Convert to DTO

    Args:
        xaml_path: Path to XAML file
        project_dir: Project directory for relative paths
        **config: Parser configuration

    Returns:
        WorkflowDto ready for analysis or emission

    Example:
        workflow = parse_file_to_dto(
            Path("./Main.xaml"),
            project_dir=Path("./MyProject")
        )
    """
    from ..stages.normalize.id_generation import IdGenerator
    from ..stages.normalize.normalizer import Normalizer
    from ..stages.assemble.control_flow import ControlFlowExtractor
    from .. import XamlParser

    # Parse XAML
    parser = XamlParser(**config)
    parse_result = parser.parse_file(xaml_path)

    if not parse_result.success:
        raise ValueError(f"Parse failed: {parse_result.errors}")

    # Normalize to DTO
    id_generator = IdGenerator()
    flow_extractor = ControlFlowExtractor(id_generator)
    normalizer = Normalizer(id_generator, flow_extractor)

    return normalizer.normalize(parse_result, project_dir=project_dir)


def normalize_parse_results(
    parse_results: list[ParseResult],
    project_dir: Path | None = None,
    **options
) -> list[WorkflowDto]:
    """Normalize ParseResults to WorkflowDtos.

    Orchestrates the normalization pipeline:
    1. Create IdGenerator for stable IDs
    2. Create ControlFlowExtractor for edge detection
    3. Create Normalizer with generators
    4. Normalize each ParseResult to WorkflowDto

    Args:
        parse_results: List of ParseResult objects from parsing
        project_dir: Project directory for relative paths
        **options: Normalization options

    Returns:
        List of normalized WorkflowDto objects

    Example:
        workflows = normalize_parse_results(
            [result1, result2],
            project_dir=Path("./MyProject")
        )
    """
    from ..stages.normalize.id_generation import IdGenerator
    from ..stages.normalize.normalizer import Normalizer
    from ..stages.assemble.control_flow import ControlFlowExtractor

    id_generator = IdGenerator()
    flow_extractor = ControlFlowExtractor(id_generator)
    normalizer = Normalizer(id_generator, flow_extractor)

    workflows = []
    for parse_result in parse_results:
        if parse_result.success and parse_result.content:
            workflow_dto = normalizer.normalize(
                parse_result, project_dir=project_dir, **options
            )
            workflows.append(workflow_dto)

    return workflows


__all__ = [
    "parse_file",
    "create_parse_error",
    "parse_project",
    "parse_file_to_dto",
    "normalize_parse_results",
]
