"""Emit pipeline orchestration: normalize → filter → render → sink.

The pipeline coordinates the full emit workflow:
1. Normalize: DTO → dict (dataclasses.asdict)
2. Filter: Apply field profiles, None filtering, etc.
3. Render: dict → output format (JSON/Mermaid/Markdown)
4. Sink: output → destination (file/stdout/stream)
"""

import dataclasses
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ...config.models import EmitterConfig
from ...shared.model.dto import WorkflowDto
from .filters.base import Filter
from .renderers.base import Renderer
from .sinks.base import Sink


@dataclass
class PipelineResult:
    """Result of full emit pipeline execution.

    Attributes:
        success: Whether pipeline execution succeeded
        locations: Where data was written (file paths, "stdout", etc.)
        render_metadata: Metadata from renderer
        filter_metadata: Metadata from filters
        sink_metadata: Metadata from sink
        errors: List of error messages
        warnings: List of warning messages
    """

    success: bool
    locations: list[Path | str] = field(default_factory=list)
    render_metadata: dict[str, Any] = field(default_factory=dict)
    filter_metadata: dict[str, Any] = field(default_factory=dict)
    sink_metadata: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class EmitPipeline:
    """Orchestrate emit pipeline: DTO → Filter → Render → Sink.

    Coordinates the transformation from WorkflowDto objects to
    rendered output written to a destination.

    Example:
        pipeline = EmitPipeline(
            renderer=JsonRenderer(),
            sink=FileSink(),
            filters=[FieldFilter("minimal"), NoneFilter()],
        )
        result = pipeline.emit(workflows, Path("output/"), config)
    """

    def __init__(
        self, renderer: Renderer, sink: Sink, filters: list[Filter] | None = None
    ):
        """Initialize emit pipeline.

        Args:
            renderer: Renderer to use (JsonRenderer, MermaidRenderer, etc.)
            sink: Sink to use (FileSink, StdoutSink, etc.)
            filters: Optional filters to apply before rendering
        """
        self.renderer = renderer
        self.sink = sink
        self.filters = filters or []

    def emit(
        self,
        workflows: list[WorkflowDto],
        destination: Path | str,
        config: EmitterConfig,
    ) -> PipelineResult:
        """Execute full emit pipeline: DTO → filter → render → sink.

        Pipeline stages:
        1. Normalize: Convert DTOs to dicts (dataclasses.asdict)
        2. Filter: Apply field profiles, None filtering, etc.
        3. Render: Convert to output format (JSON/Mermaid/Markdown)
        4. Sink: Write to destination (file/stdout/stream)

        Args:
            workflows: Workflows to emit
            destination: Output destination (file path or directory)
            config: Emitter configuration

        Returns:
            PipelineResult with all stage metadata

        Example:
            pipeline = EmitPipeline(JsonRenderer(), FileSink())
            result = pipeline.emit(workflows, Path("output/"), config)
            if result.success:
                print(f"Written to: {result.locations}")
        """
        errors = []
        warnings = []

        # Stage 1: Normalize (DTO → dict)
        workflow_dicts = [dataclasses.asdict(wf) for wf in workflows]

        # Stage 2: Filter (dict → filtered dict)
        filter_metadata = {}
        if self.filters:
            # Convert EmitterConfig to dict for filters
            config_dict = dataclasses.asdict(config)

            filtered_dicts = []
            for wf_dict in workflow_dicts:
                current_dict = wf_dict
                # Apply each filter in sequence
                for filter_obj in self.filters:
                    if filter_obj.can_handle(current_dict):
                        result = filter_obj.apply(current_dict, config_dict)
                        current_dict = result.data
                        filter_metadata[filter_obj.name] = result.metadata
                filtered_dicts.append(current_dict)
            workflow_dicts = filtered_dicts

        # Stage 3: Render (filtered dict → output format)
        render_result = self.renderer.render_many(workflow_dicts, config)

        if not render_result.success:
            errors.extend(render_result.errors)
            return PipelineResult(
                success=False,
                locations=[],
                render_metadata=render_result.metadata,
                filter_metadata=filter_metadata,
                sink_metadata={},
                errors=errors,
                warnings=warnings,
            )

        # Stage 4: Sink (output format → destination)
        content = render_result.content

        if isinstance(content, dict):
            # Multi-file output (dict of filename → content)
            sink_result = self.sink.write_many(content, destination, config.overwrite)
        else:
            # Single-file output (str or bytes)
            sink_result = self.sink.write_one(content, destination, config.overwrite)

        if not sink_result.success:
            errors.extend(sink_result.errors)

        return PipelineResult(
            success=sink_result.success,
            locations=sink_result.locations,
            render_metadata=render_result.metadata,
            filter_metadata=filter_metadata,
            sink_metadata={"bytes_written": sink_result.bytes_written},
            errors=errors,
            warnings=warnings,
        )


__all__ = ["EmitPipeline", "PipelineResult"]
