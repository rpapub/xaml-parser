"""Project analysis and indexing functions.

Provides functions for building queryable indices and analyzing project structure.
"""

from pathlib import Path
from typing import Any, TYPE_CHECKING

from ..shared.model.dto import WorkflowDto

if TYPE_CHECKING:
    from ..stages.assemble.analyzer import ProjectAnalyzer
    from ..stages.assemble.index import ProjectIndex
    from ..stages.assemble.project import ProjectResult


def build_index(
    workflows: list[WorkflowDto],
    project_dir: Path | None = None,
    project_info: Any | None = None,
    collection_issues: list[Any] | None = None
) -> "ProjectIndex":
    """Build queryable index from workflows.

    Args:
        workflows: List of workflow DTOs
        project_dir: Project directory for path resolution
        project_info: Optional project metadata
        collection_issues: Optional collection-level issues

    Returns:
        ProjectIndex ready for querying
    """
    from ..stages.assemble.analyzer import ProjectAnalyzer

    analyzer = ProjectAnalyzer()
    return analyzer.analyze(
        workflows=workflows,
        project_dir=project_dir,
        project_info=project_info,
        collection_issues=collection_issues or []
    )


def analyze_project(
    project_result: "ProjectResult",
) -> tuple["ProjectAnalyzer", "ProjectIndex"]:
    """Analyze project and build graph + index.

    Wraps stages.assemble.project.analyze_project() for public API access.

    Args:
        project_result: ProjectResult from parse_project()

    Returns:
        Tuple of (ProjectAnalyzer, ProjectIndex) ready for querying

    Example:
        analyzer, index = analyze_project(project_result)
        workflows = index.get_all_workflows()
    """
    from ..stages.assemble.project import analyze_project as _analyze_project

    return _analyze_project(project_result)


__all__ = ["build_index", "analyze_project"]
