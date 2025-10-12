"""Markdown documentation emitter for workflows."""

import re
from datetime import UTC, datetime
from pathlib import Path

try:
    from jinja2 import (  # type: ignore[import-not-found]
        Environment,
        PackageLoader,
        select_autoescape,
    )

    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False

from ..dto import WorkflowDto
from . import EmitResult, Emitter, EmitterConfig


class DocEmitter(Emitter):
    """Generate Markdown documentation from workflows using Jinja2 templates."""

    def __init__(self, template_dir: Path | None = None) -> None:
        """Initialize doc emitter.

        Args:
            template_dir: Optional custom template directory. If None, uses built-in templates.

        Raises:
            ImportError: If jinja2 is not installed
        """
        if not JINJA2_AVAILABLE:
            msg = (
                "jinja2 is required for doc emitter. "
                "Install with: pip install 'xaml-parser[docs]'"
            )
            raise ImportError(msg)

        if template_dir:
            from jinja2 import FileSystemLoader

            self.env = Environment(
                loader=FileSystemLoader(template_dir),
                autoescape=select_autoescape(["html", "xml"]),
                trim_blocks=True,
                lstrip_blocks=True,
            )
        else:
            self.env = Environment(
                loader=PackageLoader("xaml_parser", "templates"),
                autoescape=select_autoescape(["html", "xml"]),
                trim_blocks=True,
                lstrip_blocks=True,
            )

    @property
    def name(self) -> str:
        """Emitter name."""
        return "doc"

    @property
    def output_extension(self) -> str:
        """Output file extension."""
        return ".md"

    def emit(
        self, workflows: list[WorkflowDto], output_path: Path, config: EmitterConfig
    ) -> EmitResult:
        """Generate Markdown documentation for workflows.

        Args:
            workflows: List of workflow DTOs
            output_path: Output directory path
            config: Emitter configuration

        Returns:
            EmitResult with success status and files written
        """
        try:
            # Ensure output directory exists
            output_path.mkdir(parents=True, exist_ok=True)
            workflows_dir = output_path / "workflows"
            workflows_dir.mkdir(exist_ok=True)

            files_written = []

            # Generate per-workflow docs
            for workflow in workflows:
                doc = self._generate_workflow_doc(workflow, config)
                filename = self._sanitize_filename(workflow.name) + ".md"
                file_path = workflows_dir / filename
                file_path.write_text(doc, encoding="utf-8")
                files_written.append(file_path)

            # Generate index
            index = self._generate_index(workflows, config)
            index_path = output_path / "index.md"
            index_path.write_text(index, encoding="utf-8")
            files_written.append(index_path)

            return EmitResult(
                success=True,
                files_written=files_written,
                errors=[],
                warnings=[],
            )
        except Exception as e:
            return EmitResult(success=False, files_written=[], errors=[str(e)], warnings=[])

    def _generate_workflow_doc(self, workflow: WorkflowDto, config: EmitterConfig) -> str:
        """Generate documentation for a single workflow.

        Args:
            workflow: Workflow DTO
            config: Emitter configuration

        Returns:
            Markdown documentation as string
        """
        template = self.env.get_template("workflow.md.j2")
        return str(template.render(workflow=workflow))

    def _generate_index(self, workflows: list[WorkflowDto], config: EmitterConfig) -> str:
        """Generate index documentation for all workflows.

        Args:
            workflows: List of workflow DTOs
            config: Emitter configuration

        Returns:
            Markdown index as string
        """
        template = self.env.get_template("index.md.j2")

        # Extract project info from config or workflows
        project_name = config.extra.get("project_name")
        project_path = config.extra.get("project_path")
        main_workflow = config.extra.get("main_workflow")

        # Calculate totals
        total_activities = sum(len(wf.activities) for wf in workflows)
        total_variables = sum(len(wf.variables) for wf in workflows)
        total_arguments = sum(len(wf.arguments) for wf in workflows)

        # Check for invocations and issues
        has_invocations = any(wf.invocations for wf in workflows)
        has_issues = any(wf.issues for wf in workflows)

        # Get current timestamp
        collected_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")

        return str(
            template.render(
                workflows=workflows,
                project_name=project_name,
                project_path=project_path,
                main_workflow=main_workflow,
                total_activities=total_activities,
                total_variables=total_variables,
                total_arguments=total_arguments,
                has_invocations=has_invocations,
                has_issues=has_issues,
                collected_at=collected_at,
            )
        )

    def _sanitize_filename(self, name: str) -> str:
        """Sanitize workflow name for use as filename.

        Args:
            name: Workflow name

        Returns:
            Safe filename (without extension)
        """
        # Replace spaces with underscores, remove invalid chars
        safe = re.sub(r'[<>:"/\\|?*]', "", name)
        safe = safe.replace(" ", "_")
        # Trim whitespace
        safe = safe.strip()
        return safe or "workflow"

    def validate_config(self, config: EmitterConfig) -> list[str]:
        """Validate emitter configuration.

        Args:
            config: Emitter configuration

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Check if jinja2 is available
        if not JINJA2_AVAILABLE:
            errors.append("jinja2 is not installed (required for doc emitter)")

        return errors
