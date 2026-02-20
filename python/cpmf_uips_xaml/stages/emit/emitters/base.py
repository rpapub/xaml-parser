"""Base emitter class with helper methods."""

from abc import ABC
from collections.abc import Callable
from pathlib import Path

from ....shared.model.dto import WorkflowDto
from . import EmitResult, Emitter, EmitterConfig
from ..utils import ensure_dir, sanitize_filename, write_text


class BaseEmitter(Emitter, ABC):
    """Base emitter with helper methods for common emission patterns."""

    def emit_many(
        self,
        workflows: list[WorkflowDto],
        output_dir: Path,
        config: EmitterConfig,
        render_one: Callable[[WorkflowDto, EmitterConfig], str],
        fallback_name: str = "untitled",
    ) -> EmitResult:
        """Helper for per-workflow emission pattern.

        Args:
            workflows: Workflows to emit
            output_dir: Output directory
            config: Emitter configuration
            render_one: Function to render single workflow to string
                       Signature: (workflow, config) -> str
            fallback_name: Fallback filename if sanitization fails

        Returns:
            EmitResult with files written and errors
        """
        ensure_dir(output_dir)

        files_written = []
        errors = []

        for workflow in workflows:
            try:
                filename = sanitize_filename(workflow.name, fallback=fallback_name)
                filename += self.output_extension
                file_path = output_dir / filename

                content = render_one(workflow, config)
                write_text(file_path, content)

                files_written.append(file_path)

            except Exception as e:
                errors.append(f"Failed to emit {workflow.name}: {e}")

        return EmitResult(
            success=len(errors) == 0,
            files_written=files_written,
            errors=errors,
            warnings=[],
        )
