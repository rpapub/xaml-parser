"""JSON renderer for pure dict → JSON string conversion.

Extracts rendering logic from JsonEmitter, removing all I/O operations.
This is a pure function that transforms dicts to JSON strings.
"""

import json
from datetime import UTC, datetime
from typing import Any

from ..utils import sanitize_filename
from .base import Renderer, RenderResult


class JsonRenderer(Renderer):
    """Render dicts to JSON string (pure, no I/O).

    Converts workflow dicts to JSON format WITHOUT writing to files.
    All I/O is handled by sinks.
    """

    @property
    def name(self) -> str:
        """Renderer name.

        Returns:
            'json'
        """
        return "json"

    @property
    def output_extension(self) -> str:
        """Output file extension.

        Returns:
            '.json'
        """
        return ".json"

    def render_one(self, workflow_dict: dict[str, Any], config: Any) -> RenderResult:
        """Render single workflow dict to JSON string.

        Args:
            workflow_dict: Workflow data as dict (already filtered)
            config: Renderer configuration (must have: pretty, indent attrs)

        Returns:
            RenderResult with JSON string

        Example:
            renderer = JsonRenderer()
            result = renderer.render_one(workflow_dict, config)
            json_string = result.content  # Pure string, no file written
        """
        try:
            # Serialize to JSON string
            content = json.dumps(
                workflow_dict,
                indent=config.indent if config.pretty else None,
                ensure_ascii=False,
            )

            # Suggest filename from workflow name
            workflow_name = workflow_dict.get("name", "workflow")
            suggested_filename = sanitize_filename(workflow_name, fallback="Untitled") + ".json"

            return RenderResult(
                success=True,
                content=content,
                metadata={"suggested_filename": suggested_filename},
                errors=[],
                warnings=[],
            )

        except Exception as e:
            workflow_name = workflow_dict.get("name", "unknown")
            return RenderResult(
                success=False,
                content="",
                metadata={},
                errors=[f"Failed to render workflow {workflow_name}: {e}"],
                warnings=[],
            )

    def render_many(
        self, workflow_dicts: list[dict[str, Any]], config: Any
    ) -> RenderResult:
        """Render multiple workflows (combined or per-workflow).

        Args:
            workflow_dicts: List of workflow dicts (already filtered)
            config: Renderer configuration (must have: combine, pretty, indent attrs)

        Returns:
            RenderResult with:
            - Single JSON string if config.combine=True
            - Dict of filename → JSON string if config.combine=False

        Example:
            # Combined mode
            result = renderer.render_many(workflows, config)
            json_string = result.content  # Single string

            # Per-workflow mode
            result = renderer.render_many(workflows, config)
            file_map = result.content  # Dict of filename → JSON
        """
        if config.combine:
            return self._render_combined(workflow_dicts, config)
        else:
            return self._render_per_workflow(workflow_dicts, config)

    def _render_combined(
        self, workflow_dicts: list[dict[str, Any]], config: Any
    ) -> RenderResult:
        """Render all workflows into single JSON string.

        Args:
            workflow_dicts: List of workflow dicts
            config: Renderer configuration

        Returns:
            RenderResult with single JSON string
        """
        try:
            # Create collection structure
            collection = {
                "schema_id": "https://rpax.io/schemas/xaml-workflow-collection.json",
                "schema_version": "0.4.0",
                "collected_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "project_info": None,  # Set by caller if needed
                "workflows": workflow_dicts,
                "issues": [],
            }

            # Serialize to JSON string
            content = json.dumps(
                collection,
                indent=config.indent if config.pretty else None,
                ensure_ascii=False,
            )

            return RenderResult(
                success=True,
                content=content,
                metadata={"suggested_filename": "workflows.json"},
                errors=[],
                warnings=[],
            )

        except Exception as e:
            return RenderResult(
                success=False,
                content="",
                metadata={},
                errors=[f"Failed to render workflow collection: {e}"],
                warnings=[],
            )

    def _render_per_workflow(
        self, workflow_dicts: list[dict[str, Any]], config: Any
    ) -> RenderResult:
        """Render workflows as dict of filename → JSON string.

        Args:
            workflow_dicts: List of workflow dicts
            config: Renderer configuration

        Returns:
            RenderResult with dict of filename → JSON string
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
            content=content_map,  # Dict for multi-file output
            metadata={"count": len(content_map)},
            errors=errors,
            warnings=[],
        )


__all__ = ["JsonRenderer"]
