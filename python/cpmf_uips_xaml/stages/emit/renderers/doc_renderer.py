"""Documentation renderer for pure dict → Markdown string conversion.

TODO: Extract template rendering logic from DocEmitter.
This is a placeholder implementation that will be completed in a future phase.
"""

from typing import Any

from ..utils import sanitize_filename
from .base import Renderer, RenderResult


class DocRenderer(Renderer):
    """Render workflow to Markdown string using Jinja2 (pure, no I/O).

    Generates Markdown documentation WITHOUT writing to files.
    All I/O is handled by sinks.

    TODO: Extract Jinja2 template rendering from DocEmitter.
    """

    @property
    def name(self) -> str:
        """Renderer name.

        Returns:
            'doc'
        """
        return "doc"

    @property
    def output_extension(self) -> str:
        """Output file extension.

        Returns:
            '.md'
        """
        return ".md"

    def render_one(self, workflow_dict: dict[str, Any], config: Any) -> RenderResult:
        """Render workflow dict to Markdown string.

        Args:
            workflow_dict: Workflow data as dict
            config: Renderer configuration

        Returns:
            RenderResult with Markdown string

        TODO: Implement Jinja2 template rendering
        """
        # TODO: Extract Jinja2 rendering from DocEmitter
        content = self._render_markdown(workflow_dict, config)

        workflow_name = workflow_dict.get("name", "workflow")
        suggested_filename = sanitize_filename(workflow_name, fallback="Untitled") + ".md"

        return RenderResult(
            success=True,
            content=content,
            metadata={"suggested_filename": suggested_filename},
            errors=[],
            warnings=[],
        )

    def render_many(
        self, workflow_dicts: list[dict[str, Any]], config: Any
    ) -> RenderResult:
        """Render multiple workflows as dict of filename → Markdown.

        Args:
            workflow_dicts: List of workflow dicts
            config: Renderer configuration

        Returns:
            RenderResult with dict of filename → Markdown
        """
        content_map = {}
        errors = []

        for wf_dict in workflow_dicts:
            result = self.render_one(wf_dict, config)

            if result.success:
                filename = result.metadata["suggested_filename"]
                content_map[filename] = result.content
            else:
                errors.extend(result.errors)

        return RenderResult(
            success=len(errors) == 0,
            content=content_map,
            metadata={"count": len(content_map)},
            errors=errors,
            warnings=[],
        )

    def _render_markdown(self, workflow_dict: dict[str, Any], config: Any) -> str:
        """Render workflow to Markdown string.

        TODO: Extract Jinja2 template rendering from DocEmitter

        Args:
            workflow_dict: Workflow data
            config: Renderer configuration

        Returns:
            Markdown string
        """
        # Placeholder implementation
        workflow_name = workflow_dict.get("name", "Workflow")
        workflow_id = workflow_dict.get("id", "unknown")
        activities = workflow_dict.get("activities", [])

        lines = [
            f"# {workflow_name}",
            "",
            f"**ID:** {workflow_id}",
            "",
            "## Activities",
            "",
        ]

        # List activities (simplified)
        for activity in activities:
            display_name = activity.get("display_name", "Untitled")
            activity_type = activity.get("type_short", "Unknown")
            lines.append(f"- **{display_name}** ({activity_type})")

        # TODO: Add more sections (arguments, variables, etc.)

        return "\n".join(lines)


__all__ = ["DocRenderer"]
