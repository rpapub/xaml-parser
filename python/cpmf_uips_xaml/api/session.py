"""ProjectSession - Unified API for working with parsed UiPath projects.

Provides an intuitive interface for accessing workflows, generating views,
and emitting artifacts. Wraps the ProjectResult/ProjectAnalyzer/ProjectIndex
tuple in a single, discoverable object.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from ..config import Config
from ..shared.model.dto import AnnotationBlock, AnnotationTag, WorkflowDto
from ..stages.assemble.analyzer import ProjectAnalyzer
from ..stages.assemble.index import ProjectIndex
from ..stages.assemble.project import ProjectResult
from ..stages.emit.pipeline import PipelineResult
from .emit import emit_workflows
from .views import render_project_view


@dataclass
class ProjectSession:
    """Unified project session providing discoverable API for workflow access.

    Wraps ProjectResult, ProjectAnalyzer, and ProjectIndex in a single object
    with intuitive methods for common operations.

    Attributes:
        result: ProjectResult with raw parse data
        analyzer: ProjectAnalyzer with graphs and DTO storage
        index: ProjectIndex with queryable workflow data
        config: Resolved configuration
        project_dir: Project root directory

    Example:
        >>> from cpmf_uips_xaml import load
        >>> session = load(Path("./MyProject"))
        >>> workflows = session.workflows()
        >>> wf = session.workflow("Main.xaml")
        >>> view = session.view("execution", entry_point="Main.xaml")
    """

    result: ProjectResult
    analyzer: ProjectAnalyzer
    index: ProjectIndex
    config: Config
    project_dir: Path

    # ========================================================================
    # Workflow Access
    # ========================================================================

    def workflows(self, *, pattern: str | None = None) -> list[WorkflowDto]:
        """Get all workflows, optionally filtered by glob pattern.

        Args:
            pattern: Optional glob pattern (e.g., "Main.xaml", "Framework/**/*.xaml")

        Returns:
            List of WorkflowDto objects for successfully parsed workflows

        Example:
            >>> all_wfs = session.workflows()
            >>> test_wfs = session.workflows(pattern="Test_*.xaml")
            >>> framework_wfs = session.workflows(pattern="Framework/**/*.xaml")
        """
        # Get all successfully parsed workflows from analyzer
        all_workflows = [
            wf for wf in self.analyzer._workflows.values()
        ]

        if pattern is None:
            return all_workflows

        # Filter by glob pattern
        from fnmatch import fnmatch

        filtered = []
        for wf in all_workflows:
            # Try matching against source path
            source_path = wf.source.path
            if fnmatch(source_path, pattern):
                filtered.append(wf)
                continue

            # Try matching against workflow name
            if fnmatch(wf.name, pattern):
                filtered.append(wf)
                continue

        return filtered

    def workflow(self, id_or_path: str) -> WorkflowDto | None:
        """Find workflow by ID, path, or name.

        Searches for workflows using multiple strategies:
        1. Exact source path match
        2. Filename match (e.g., "Main.xaml")
        3. Workflow name match
        4. Workflow ID match

        Args:
            id_or_path: Workflow ID, relative path, filename, or display name

        Returns:
            WorkflowDto if found, None otherwise

        Example:
            >>> wf = session.workflow("Main.xaml")
            >>> wf = session.workflow("framework/GetConfig.xaml")
            >>> wf = session.workflow("My Workflow Name")
        """
        workflows = self.analyzer._workflows.values()

        # Try exact path match first
        for wf in workflows:
            if wf.source.path == id_or_path:
                return wf

        # Try filename match
        for wf in workflows:
            source_path = Path(wf.source.path)
            if source_path.name == id_or_path:
                return wf

        # Try by workflow name or ID
        for wf in workflows:
            if wf.name == id_or_path or wf.id == id_or_path:
                return wf

        return None

    # ========================================================================
    # View Generation
    # ========================================================================

    def view(
        self,
        view_type: Literal["nested", "execution", "slice"] | None = None,
        *,
        entry_point: str | None = None,
        focus: str | None = None,
        radius: int = 2,
    ) -> dict[str, Any]:
        """Generate view projection of the project.

        Args:
            view_type: Type of view (defaults to config.view.view_type).
                - "nested": Hierarchical workflow structure
                - "execution": Execution flow from entry point
                - "slice": Focused view around specific workflow
            entry_point: Starting workflow for execution view
            focus: Center workflow for slice view
            radius: Depth for slice view (default: 2)

        Returns:
            Dictionary with view projection data

        Example:
            >>> view = session.view("execution", entry_point="Main.xaml")
            >>> slice_view = session.view("slice", focus="ProcessData.xaml", radius=3)
        """
        if view_type is None:
            view_type = self.config.view.view_type

        return render_project_view(
            self.analyzer,
            self.index,
            view_type=view_type,
            entry_point=entry_point,
            focus=focus,
            radius=radius,
        )

    # ========================================================================
    # Artifact Emission
    # ========================================================================

    def emit(
        self,
        format: Literal["json", "yaml", "mermaid", "doc"] = "json",
        output_path: Path | None = None,
        **options: Any,
    ) -> PipelineResult | str:
        """Emit workflows to specified format.

        Args:
            format: Output format (json, yaml, mermaid, doc)
            output_path: Output file/directory path (None = return string)
            **options: Additional emitter options:
                - combine: Combine all workflows into single file (default: False)
                - pretty: Pretty-print output (default: True)
                - exclude_none: Remove None values (default: False)
                - field_profile: Field filtering profile (default: from config)
                - indent: Indentation spaces (default: 2)
                - encoding: Output encoding (default: "utf-8")
                - overwrite: Overwrite existing files (default: True)

        Returns:
            PipelineResult if output_path provided, string otherwise

        Example:
            >>> # Write to file
            >>> result = session.emit("json", output_path=Path("output.json"))
            >>> # Get as string
            >>> json_str = session.emit("json")
            >>> # Emit combined output
            >>> session.emit("json", Path("all.json"), combine=True)
        """
        from ..config.models import EmitterConfig

        workflows = self.workflows()

        # Build EmitterConfig from options
        emitter_config = EmitterConfig(
            format=format,
            combine=options.get("combine", False),
            pretty=options.get("pretty", True),
            exclude_none=options.get("exclude_none", False),
            field_profile=options.get("field_profile", self.config.emitter.field_profile),
            indent=options.get("indent", 2),
            encoding=options.get("encoding", "utf-8"),
            overwrite=options.get("overwrite", True),
        )

        if output_path is None:
            # Return string with filters applied (same as file output)
            import dataclasses
            from ..stages.emit.renderers.json_renderer import JsonRenderer
            from ..stages.emit.renderers.mermaid_renderer import MermaidRenderer
            from ..stages.emit.filters.field_filter import FieldFilter
            from ..stages.emit.filters.none_filter import NoneFilter

            # Build renderer based on format
            if format == "json":
                renderer = JsonRenderer()
            elif format == "mermaid":
                renderer = MermaidRenderer()
            elif format == "doc":
                from ..stages.emit.renderers.doc_renderer import DocRenderer
                renderer = DocRenderer()
            else:
                raise ValueError(f"Unsupported format for string output: {format}")

            # Convert workflows to dicts
            workflow_dicts = [dataclasses.asdict(wf) for wf in workflows]

            # Apply filters (same as pipeline does)
            filters = []
            if emitter_config.exclude_none:
                filters.append(NoneFilter())
            if emitter_config.field_profile != "full":
                filters.append(FieldFilter(profile=emitter_config.field_profile))

            if filters:
                # Apply filters to each workflow
                filtered_dicts = []
                config_dict = dataclasses.asdict(emitter_config)
                for wf_dict in workflow_dicts:
                    filtered = wf_dict
                    for filter_obj in filters:
                        if filter_obj.can_handle(filtered):
                            filter_result = filter_obj.apply(filtered, config_dict)
                            filtered = filter_result.data
                    filtered_dicts.append(filtered)
                workflow_dicts = filtered_dicts

            # Render to string
            if emitter_config.combine:
                result = renderer.render_many(workflow_dicts, emitter_config)
            else:
                # For non-combined, join individual renders
                results = [renderer.render_one(wf, emitter_config) for wf in workflow_dicts]
                combined_content = "\n\n".join(r.content for r in results)
                return combined_content

            return result.content if isinstance(result.content, str) else str(result.content)
        else:
            # Write to file
            return emit_workflows(workflows, output_path, emitter_config)

    # ========================================================================
    # Properties for Direct Access
    # ========================================================================

    @property
    def entry_points(self) -> list[str]:
        """List of entry point workflow paths from project.json.

        Returns:
            List of relative paths to entry point workflows

        Example:
            >>> session.entry_points
            ['Main.xaml', 'Framework/Init.xaml']
        """
        entry_points = self.result.project_config.entry_points
        if not entry_points:
            return []

        # Handle both dict and object formats
        result = []
        for ep in entry_points:
            if isinstance(ep, dict):
                result.append(ep.get("file_path", ep.get("filePath", "")))
            else:
                result.append(ep.file_path)
        return result

    @property
    def project_name(self) -> str:
        """Project name from project.json.

        Returns:
            Project name string

        Example:
            >>> session.project_name
            'MyUiPathProject'
        """
        return self.result.project_config.name

    @property
    def total_workflows(self) -> int:
        """Total number of workflows discovered in the project.

        Returns:
            Count of all discovered workflows (including failed parses)

        Example:
            >>> session.total_workflows
            42
        """
        return self.result.total_workflows

    @property
    def failed_workflows(self) -> list[Any]:
        """List of workflows that failed to parse.

        Returns:
            List of workflows with parsing errors

        Example:
            >>> failed = session.failed_workflows
            >>> if failed:
            ...     print(f"Failed to parse {len(failed)} workflows")
        """
        return self.result.get_failed_workflows()

    @property
    def successful_workflows(self) -> int:
        """Count of successfully parsed workflows.

        Returns:
            Number of workflows that parsed successfully

        Example:
            >>> session.successful_workflows
            40
        """
        return len(self.analyzer._workflows)

    # ========================================================================
    # Annotation Access
    # ========================================================================

    def annotations(
        self,
        *,
        tag: str | None = None,
        include_activities: bool = True,
        include_arguments: bool = True,
    ) -> dict[str, list[AnnotationTag]]:
        """Get all structured annotations from workflows.

        Args:
            tag: Filter by specific tag name (e.g., "module", "author", "unit", "pathkeeper")
            include_activities: Include activity annotations
            include_arguments: Include argument annotations

        Returns:
            Dictionary mapping workflow ID → list of annotation tags

        Example:
            >>> annotations = session.annotations(tag="module")
            >>> annotations["wf:sha256:abc123"]
            [AnnotationTag(tag='module', value='ProcessInvoice', ...)]
            >>> pathkeeper_annotations = session.annotations(tag="pathkeeper")
            >>> unit_annotations = session.annotations(tag="unit")
        """
        result = {}

        for wf in self.workflows():
            tags = []

            # Workflow-level annotations
            if wf.metadata.annotation_block:
                if tag:
                    tags.extend(wf.metadata.annotation_block.get_tags(tag))
                else:
                    tags.extend(wf.metadata.annotation_block.tags)

            # Activity annotations
            if include_activities:
                for activity in wf.activities:
                    if activity.annotation_block:
                        if tag:
                            tags.extend(activity.annotation_block.get_tags(tag))
                        else:
                            tags.extend(activity.annotation_block.tags)

            # Argument annotations
            if include_arguments:
                for argument in wf.arguments:
                    if argument.annotation_block:
                        if tag:
                            tags.extend(argument.annotation_block.get_tags(tag))
                        else:
                            tags.extend(argument.annotation_block.tags)

            if tags:
                result[wf.id] = tags

        return result

    def workflows_with_tag(self, tag: str) -> list[WorkflowDto]:
        """Get workflows that have a specific annotation tag.

        Args:
            tag: Tag name to search for (e.g., "public", "test", "ignore", "unit", "module", "pathkeeper")

        Returns:
            List of WorkflowDto objects with the tag

        Example:
            >>> public_workflows = session.workflows_with_tag("public")
            >>> test_workflows = session.workflows_with_tag("test")
            >>> unit_workflows = session.workflows_with_tag("unit")
            >>> pathkeeper_workflows = session.workflows_with_tag("pathkeeper")
            >>> module_workflows = session.workflows_with_tag("module")
        """
        result = []
        for wf in self.workflows():
            if wf.metadata.annotation_block and wf.metadata.annotation_block.has_tag(tag):
                result.append(wf)
        return result

    def modules(self) -> dict[str, list[WorkflowDto]]:
        """Group workflows by @module tag.

        Returns:
            Dictionary mapping module name → list of workflows

        Example:
            >>> modules = session.modules()
            >>> modules["ProcessInvoice"]
            [WorkflowDto(...), WorkflowDto(...)]
            >>> modules["_uncategorized"]
            [WorkflowDto(...)]
        """
        from collections import defaultdict
        result = defaultdict(list)

        for wf in self.workflows():
            if wf.metadata.annotation_block:
                module_tag = wf.metadata.annotation_block.get_tag("module")
                if module_tag and module_tag.value:
                    result[module_tag.value].append(wf)
                else:
                    result["_uncategorized"].append(wf)
            else:
                result["_uncategorized"].append(wf)

        return dict(result)
