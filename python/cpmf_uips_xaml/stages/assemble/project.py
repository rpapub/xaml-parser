"""Project-level parsing for UiPath automation projects.

This module provides functionality to parse entire UiPath projects by:
1. Reading project.json configuration
2. Discovering workflows from entry points
3. Recursively following InvokeWorkflowFile references
4. Building dependency graphs
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .control_flow import ControlFlowExtractor
from ...shared.model.dto import EntryPointInfo, ProjectInfo, WorkflowCollectionDto
from ...stages.normalize.id_generation import IdGenerator
from ...shared.model.models import ParseResult, WorkflowContent
from ...shared.progress import NULL_REPORTER, ProgressEvent, ProgressReporter
from ...stages.normalize.normalizer import Normalizer
from ...stages.parsing.parser import XamlDialect, XamlParser

if TYPE_CHECKING:
    from .index import ProjectIndex

logger = logging.getLogger(__name__)


def _create_platform_config() -> XamlDialect:
    """Create platform configuration for automation projects.

    Returns:
        XamlDialect with all platform-specific constants and utilities
    """
    from ...platforms.uipath.dialect import create_uipath_dialect

    return create_uipath_dialect()


@dataclass
class ProjectConfig:
    """Configuration loaded from project.json."""

    name: str
    main: str | None = None
    description: str | None = None
    expression_language: str = "VisualBasic"
    entry_points: list[dict[str, Any]] = field(default_factory=list)
    dependencies: dict[str, str] = field(default_factory=dict)
    schema_version: str | None = None
    project_version: str | None = None
    raw_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowResult:
    """Result of parsing a single workflow in a project context."""

    file_path: Path
    relative_path: str
    parse_result: ParseResult
    invoked_workflows: list[str] = field(default_factory=list)
    is_entry_point: bool = False


@dataclass
class ProjectResult:
    """Result of parsing an entire project."""

    project_dir: Path
    project_config: ProjectConfig | None
    workflows: list[WorkflowResult] = field(default_factory=list)
    dependency_graph: dict[str, list[str]] = field(default_factory=dict)
    success: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    total_workflows: int = 0
    total_parse_time_ms: float = 0.0

    def get_workflow(self, relative_path: str) -> WorkflowResult | None:
        """Get workflow result by relative path."""
        for workflow in self.workflows:
            if workflow.relative_path == relative_path:
                return workflow
        return None

    def get_entry_points(self) -> list[WorkflowResult]:
        """Get all entry point workflows."""
        return [w for w in self.workflows if w.is_entry_point]

    def get_failed_workflows(self) -> list[WorkflowResult]:
        """Get workflows that failed to parse."""
        return [w for w in self.workflows if not w.parse_result.success]


class ProjectParser:
    """Parser for UiPath project structures.

    Discovers and parses all workflows in a project starting from
    entry points defined in project.json.
    """

    def __init__(self, parser_config: dict[str, Any] | None = None) -> None:
        """Initialize project parser.

        Args:
            parser_config: Configuration for individual XAML parser
        """
        self.parser_config = parser_config or {}
        platform_config = _create_platform_config()
        self.xaml_parser = XamlParser(platform_config=platform_config, config=parser_config)

    def parse_project(
        self,
        project_dir: Path,
        recursive: bool = True,
        entry_points_only: bool = False,
        reporter: ProgressReporter = NULL_REPORTER,
    ) -> ProjectResult:
        """Parse entire UiPath project.

        Args:
            project_dir: Path to project directory (containing project.json)
            recursive: Follow InvokeWorkflowFile references recursively
            entry_points_only: Only parse entry points, don't discover dependencies
            reporter: Progress reporter for event notifications (default: NullReporter)

        Returns:
            ProjectResult with all workflows and dependency information
        """
        project_dir = Path(project_dir)
        errors = []
        warnings = []

        logger.info("Parsing project: %s", project_dir.name)
        logger.debug(
            "Project directory: %s (recursive=%s, entry_points_only=%s)",
            project_dir,
            recursive,
            entry_points_only,
        )

        # Load project.json
        try:
            project_config = self._load_project_json(project_dir)
            logger.info("Loaded project.json for: %s", project_config.name)
        except Exception as e:
            logger.error("Failed to load project.json from %s: %s", project_dir, e)
            return ProjectResult(
                project_dir=project_dir,
                project_config=None,
                success=False,
                errors=[f"Failed to load project.json: {str(e)}"],
            )

        # Determine workflows to parse
        if entry_points_only:
            # Only parse entry points from project.json
            workflows_to_parse = self._get_entry_point_paths(project_config, project_dir)
            discovered_workflows: set[str] = set()
            logger.info("Entry points only mode: found %d entry points", len(workflows_to_parse))
        else:
            # Discover all workflows recursively
            workflows_to_parse, discovered_workflows = self._discover_workflows(
                project_config, project_dir, recursive=recursive
            )
            logger.info("Workflow discovery complete: %d workflows found", len(workflows_to_parse))

        # Parse all workflows with progress tracking
        workflow_results = []
        total_parse_time = 0.0

        # Emit start event
        reporter.report(
            ProgressEvent(
                stage="parse",
                message=f"Parsing {len(workflows_to_parse)} workflows",
                total=len(workflows_to_parse),
            )
        )

        for file_path in workflows_to_parse:
            # Determine if this is an entry point
            relative_path = self._make_relative_path(file_path, project_dir)
            is_entry = self._is_entry_point(relative_path, project_config)

            # Parse workflow
            parse_result = self.xaml_parser.parse_file(file_path)
            total_parse_time += parse_result.parse_time_ms

            # Extract invoked workflows
            invoked = []
            if parse_result.success and parse_result.content:
                invoked = self._extract_invoke_workflow_files(parse_result.content)

            workflow_result = WorkflowResult(
                file_path=file_path,
                relative_path=relative_path,
                parse_result=parse_result,
                invoked_workflows=invoked,
                is_entry_point=is_entry,
            )
            workflow_results.append(workflow_result)

            # Track errors and warnings
            if not parse_result.success:
                errors.append(f"{relative_path}: {', '.join(parse_result.errors[:2])}")
            warnings.extend(parse_result.warnings)

            # Emit progress event
            reporter.report(ProgressEvent(stage="parse", advance=1, item=relative_path))

        # Count successes for completion message
        success_count = sum(1 for wf in workflow_results if wf.parse_result.success)

        # Emit completion event
        reporter.report(
            ProgressEvent(
                stage="parse",
                message=f"Parsing complete: {success_count}/{len(workflow_results)} successful",
            )
        )

        # Build dependency graph
        dependency_graph = self._build_dependency_graph(workflow_results)

        failed_count = len(workflow_results) - success_count

        logger.info(
            "Project parsing complete: %d/%d workflows parsed successfully in %.2fms",
            success_count,
            len(workflow_results),
            total_parse_time,
        )

        if failed_count > 0:
            logger.warning("%d workflows failed to parse", failed_count)

        return ProjectResult(
            project_dir=project_dir,
            project_config=project_config,
            workflows=workflow_results,
            dependency_graph=dependency_graph,
            success=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            total_workflows=len(workflow_results),
            total_parse_time_ms=total_parse_time,
        )

    def _load_project_json(self, project_dir: Path) -> ProjectConfig:
        """Load and parse project.json file.

        Args:
            project_dir: Project directory path

        Returns:
            ProjectConfig with parsed configuration

        Raises:
            FileNotFoundError: If project.json doesn't exist
            json.JSONDecodeError: If project.json is invalid
        """
        project_json_path = project_dir / "project.json"

        if not project_json_path.exists():
            raise FileNotFoundError(f"project.json not found at {project_json_path}")

        with open(project_json_path, encoding="utf-8") as f:
            data = json.load(f)

        return ProjectConfig(
            name=data.get("name", "Unknown"),
            main=data.get("main"),
            description=data.get("description"),
            expression_language=data.get("expressionLanguage", "VisualBasic"),
            entry_points=data.get("entryPoints", []),
            dependencies=data.get("dependencies", {}),
            schema_version=data.get("schemaVersion"),
            project_version=data.get("projectVersion"),
            raw_data=data,
        )

    def _get_entry_point_paths(
        self, project_config: ProjectConfig, project_dir: Path
    ) -> list[Path]:
        """Get entry point file paths from project config.

        Args:
            project_config: Project configuration
            project_dir: Project directory

        Returns:
            List of entry point file paths
        """
        entry_paths = []

        # Add main workflow if specified
        if project_config.main:
            main_path = project_dir / project_config.main
            if main_path.exists():
                entry_paths.append(main_path)

        # Add explicit entry points
        for entry_point in project_config.entry_points:
            file_path = entry_point.get("filePath")
            if file_path:
                full_path = project_dir / file_path
                if full_path.exists() and full_path not in entry_paths:
                    entry_paths.append(full_path)

        return entry_paths

    def _discover_workflows(
        self, project_config: ProjectConfig, project_dir: Path, recursive: bool = True
    ) -> tuple[list[Path], set[str]]:
        """Discover all workflows starting from entry points.

        Args:
            project_config: Project configuration
            project_dir: Project directory
            recursive: Follow InvokeWorkflowFile references

        Returns:
            Tuple of (list of file paths to parse, set of discovered workflow names)
        """
        discovered = set()  # Relative paths of workflows to parse
        to_process = []  # Queue of workflows to analyze for dependencies

        # Start with entry points
        entry_paths = self._get_entry_point_paths(project_config, project_dir)
        for path in entry_paths:
            rel_path = self._make_relative_path(path, project_dir)
            discovered.add(rel_path)
            to_process.append(path)

        if not recursive:
            # Return just entry points
            return entry_paths, discovered

        # Recursively discover dependencies
        processed = set()

        while to_process:
            current_path = to_process.pop(0)

            # Skip if already processed
            rel_path = self._make_relative_path(current_path, project_dir)
            if rel_path in processed:
                continue
            processed.add(rel_path)

            # Parse workflow to find InvokeWorkflowFile references
            result = self.xaml_parser.parse_file(current_path)
            if not result.success or not result.content:
                continue

            # Extract invoked workflows
            invoked = self._extract_invoke_workflow_files(result.content)

            for invoked_path in invoked:
                # Resolve relative path
                full_path = self._resolve_workflow_path(invoked_path, current_path, project_dir)

                if full_path and full_path.exists():
                    rel = self._make_relative_path(full_path, project_dir)
                    if rel not in discovered:
                        discovered.add(rel)
                        to_process.append(full_path)

        # Convert discovered relative paths to full paths
        all_paths = []
        for rel_path in discovered:
            full_path = project_dir / rel_path
            if full_path.exists():
                all_paths.append(full_path)

        return all_paths, discovered

    def _extract_invoke_workflow_files(self, content: WorkflowContent) -> list[str]:
        """Extract InvokeWorkflowFile references from workflow.

        Args:
            content: Parsed workflow content

        Returns:
            List of workflow file paths referenced
        """
        invoked = []

        for activity in content.activities:
            # Check if this is InvokeWorkflowFile activity
            if "InvokeWorkflowFile" in activity.activity_type:
                # Look for WorkflowFileName in arguments or properties
                workflow_file = None

                # Check arguments
                if "WorkflowFileName" in activity.arguments:
                    workflow_file = activity.arguments["WorkflowFileName"]

                # Check properties
                if not workflow_file and "WorkflowFileName" in activity.properties:
                    workflow_file = activity.properties["WorkflowFileName"]

                # Check visible attributes (legacy)
                if not workflow_file and "WorkflowFileName" in activity.visible_attributes:
                    workflow_file = activity.visible_attributes["WorkflowFileName"]

                if workflow_file:
                    # Clean up expression syntax if present
                    workflow_file = str(workflow_file).strip('"').strip("'")
                    if workflow_file:
                        invoked.append(workflow_file)

        return invoked

    def _resolve_workflow_path(
        self, workflow_ref: str, current_workflow: Path, project_dir: Path
    ) -> Path | None:
        """Resolve workflow reference to absolute path.

        Args:
            workflow_ref: Workflow file reference (relative or absolute)
            current_workflow: Path of workflow containing the reference
            project_dir: Project root directory

        Returns:
            Resolved absolute path or None if cannot be resolved
        """
        # Try as relative to project root
        path1 = project_dir / workflow_ref
        if path1.exists():
            return path1

        # Try as relative to current workflow directory
        path2 = current_workflow.parent / workflow_ref
        if path2.exists():
            return path2

        # Try with .xaml extension if missing
        if not workflow_ref.endswith(".xaml"):
            return self._resolve_workflow_path(
                workflow_ref + ".xaml", current_workflow, project_dir
            )

        return None

    def _make_relative_path(self, file_path: Path, project_dir: Path) -> str:
        """Make path relative to project directory.

        Args:
            file_path: Absolute file path
            project_dir: Project directory

        Returns:
            Relative path string (POSIX format)
        """
        try:
            rel = file_path.relative_to(project_dir)
            return str(rel).replace("\\", "/")
        except ValueError:
            # File is outside project dir
            return str(file_path)

    def _is_entry_point(self, relative_path: str, project_config: ProjectConfig) -> bool:
        """Check if workflow is an entry point.

        Args:
            relative_path: Workflow path relative to project
            project_config: Project configuration

        Returns:
            True if workflow is an entry point
        """
        # Normalize path format
        rel_normalized = relative_path.replace("\\", "/")

        # Check main workflow
        if project_config.main:
            main_normalized = project_config.main.replace("\\", "/")
            if rel_normalized == main_normalized:
                return True

        # Check explicit entry points
        for entry_point in project_config.entry_points:
            ep_path = entry_point.get("filePath", "").replace("\\", "/")
            if rel_normalized == ep_path:
                return True

        return False

    def _build_dependency_graph(
        self, workflow_results: list[WorkflowResult]
    ) -> dict[str, list[str]]:
        """Build workflow dependency graph.

        Args:
            workflow_results: List of parsed workflows

        Returns:
            Dictionary mapping workflow paths to their dependencies
        """
        graph = {}

        for workflow in workflow_results:
            graph[workflow.relative_path] = workflow.invoked_workflows

        return graph


def analyze_project(project_result: ProjectResult) -> tuple["ProjectAnalyzer", "ProjectIndex"]:
    """Analyze project and build graph structures.

    This function normalizes all workflows to DTOs and then builds
    queryable graph structures using ProjectAnalyzer.

    Args:
        project_result: Result from ProjectParser.parse_project()

    Returns:
        Tuple of (ProjectAnalyzer, ProjectIndex) for multi-view output
        - ProjectAnalyzer: Contains DTOs and legacy Graph objects
        - ProjectIndex: LEAN index with IDs and adjacency lists only

    Example:
        >>> parser = ProjectParser()
        >>> result = parser.parse_project(Path("myproject"))
        >>> analyzer, index = analyze_project(result)
        >>> # Now use views to transform
        >>> from xaml_parser.views import FlatView
        >>> view = FlatView()
        >>> output = view.render(analyzer, index)
    """
    from .analyzer import ProjectAnalyzer

    # Convert ProjectResult → WorkflowDtos
    collection_dto = project_result_to_dto(project_result, sort_output=False)

    # Build graph structures from DTOs
    analyzer = ProjectAnalyzer()
    index = analyzer.analyze(
        workflows=collection_dto.workflows,
        project_dir=project_result.project_dir,
        project_info=collection_dto.project_info,
        collection_issues=collection_dto.issues,
    )
    return analyzer, index


def project_result_to_dto(
    project_result: ProjectResult,
    normalizer: Normalizer | None = None,
    sort_output: bool = False,
) -> WorkflowCollectionDto:
    """Convert ProjectResult to WorkflowCollectionDto with stable IDs and invocations.

    This function performs a two-pass conversion:
    1. First pass: Normalize all workflows to get stable IDs
    2. Second pass: Link invocations using the stable ID map

    Args:
        project_result: Result from ProjectParser.parse_project()
        normalizer: Optional Normalizer instance (creates new if None)
        sort_output: If True, sort all collections deterministically. If False (default),
                    preserve source file order.

    Returns:
        WorkflowCollectionDto with all workflows and linked invocations
    """
    # Create normalizer with shared ID generator for stability
    if normalizer is None:
        id_generator = IdGenerator()
        flow_extractor = ControlFlowExtractor(id_generator)
        normalizer = Normalizer(id_generator, flow_extractor)

    # First pass: Normalize all workflows and build path→ID map
    workflow_dtos = []
    path_to_id_map = {}

    for wf_result in project_result.workflows:
        # Skip failed parses
        if not wf_result.parse_result.success:
            continue

        # Derive workflow name from file path
        workflow_name = Path(wf_result.file_path).stem

        # Extract project dependencies if available
        project_deps = {}
        if project_result.project_config:
            project_deps = project_result.project_config.dependencies

        # Normalize to DTO (invocations will be empty for now)
        workflow_dto = normalizer.normalize(
            parse_result=wf_result.parse_result,
            workflow_name=workflow_name,
            workflow_id_map={},  # Empty for first pass
            sort_output=sort_output,
            project_dependencies=project_deps,
        )

        workflow_dtos.append(workflow_dto)

        # Map all path variations to this workflow's stable ID
        # Store both original and normalized paths
        path_to_id_map[wf_result.relative_path] = workflow_dto.id
        normalized_path = wf_result.relative_path.replace("\\", "/")
        path_to_id_map[normalized_path] = workflow_dto.id

    # Second pass: Re-extract invocations with stable ID map
    for wf_result in project_result.workflows:
        if not wf_result.parse_result.success or not wf_result.parse_result.content:
            continue

        # Extract invocations using the complete path→ID map
        invocations = normalizer._extract_invocations(
            activities=wf_result.parse_result.content.activities,
            workflow_id_map=path_to_id_map,
        )

        # Update the workflow DTO with linked invocations
        # Find the corresponding DTO (accounting for skipped failures)
        dto_index = sum(
            1
            for w in project_result.workflows[: project_result.workflows.index(wf_result)]
            if w.parse_result.success
        )
        if dto_index < len(workflow_dtos):
            workflow_dtos[dto_index].invocations = invocations

    # Build ProjectInfo if project config is available
    project_info = None
    if project_result.project_config:
        config = project_result.project_config

        # Map main workflow path to stable ID
        main_workflow_id = None
        if config.main:
            main_normalized = config.main.replace("\\", "/")
            main_workflow_id = path_to_id_map.get(main_normalized)

        # Map entry points to stable IDs
        entry_points_info = []
        for ep in config.entry_points:
            ep_path = ep.get("filePath", "")
            ep_normalized = ep_path.replace("\\", "/")
            ep_wf_id = path_to_id_map.get(ep_normalized)

            if ep_wf_id:
                entry_points_info.append(
                    EntryPointInfo(
                        workflow_id=ep_wf_id,
                        file_path=ep_path,
                        unique_id=ep.get("uniqueId"),
                    )
                )

        # Build ProjectInfo
        project_info = ProjectInfo(
            name=config.name,
            path=str(project_result.project_dir),
            project_id=config.raw_data.get("projectId"),
            description=config.description,
            project_version=config.project_version,
            schema_version=config.schema_version,
            studio_version=config.raw_data.get("studioVersion"),
            expression_language=config.expression_language,
            target_framework=config.raw_data.get("targetFramework"),
            main_workflow_id=main_workflow_id,
            entry_points=entry_points_info,
            dependencies=config.dependencies,
        )

    # Build collection-level issues from project errors
    collection_issues = []
    for error in project_result.errors:
        from .dto import IssueDto

        collection_issues.append(
            IssueDto(
                level="error",
                message=error,
                path=None,
                code="PROJECT_ERROR",
            )
        )
    for warning in project_result.warnings[:10]:  # Limit to first 10
        from .dto import IssueDto

        collection_issues.append(
            IssueDto(
                level="warning",
                message=warning,
                path=None,
                code="PROJECT_WARNING",
            )
        )

    # Create workflow collection DTO
    return WorkflowCollectionDto(
        schema_id="https://rpax.io/schemas/xaml-workflow-collection.json",
        schema_version="0.4.0",
        collected_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        project_info=project_info,
        workflows=workflow_dtos,
        issues=collection_issues,
    )
