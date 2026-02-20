"""Output emission functions using the new pipeline architecture.

Provides high-level API for emitting workflows using the pipeline:
normalize → filter → render → sink
"""

from pathlib import Path

from ..config.models import EmitterConfig
from ..shared.model.dto import WorkflowDto
from ..stages.emit.filters import FieldFilter, NoneFilter
from ..stages.emit.pipeline import EmitPipeline, PipelineResult
from ..stages.emit.renderers import DocRenderer, JsonRenderer, MermaidRenderer, RecordRenderer
from ..stages.emit.sinks import FileSink, StdoutSink


def emit_workflows(
    workflows: list[WorkflowDto],
    output_path: Path,
    config: EmitterConfig,
) -> PipelineResult:
    """Emit workflows using the new pipeline architecture.

    Orchestrates the full pipeline: normalize → filter → render → sink

    Args:
        workflows: Workflows to emit
        output_path: Output destination (Path or "-" for stdout)
        config: Emitter configuration (from unified config system)

    Returns:
        PipelineResult with success status and locations

    Example:
        from cpmf_uips_xaml.api import emit_workflows
        from cpmf_uips_xaml.config import load_config

        config = load_config()
        result = emit_workflows(workflows, Path("output/"), config.emitter)

        if result.success:
            print(f"Written to: {result.locations}")
    """
    # Choose renderer based on format
    if config.format == "json":
        renderer = JsonRenderer()
    elif config.format == "mermaid":
        renderer = MermaidRenderer()
    elif config.format == "doc":
        renderer = DocRenderer()
    elif config.format == "record":
        renderer = RecordRenderer()
    else:
        raise ValueError(f"Unknown format: {config.format}. Valid: json, mermaid, doc, record")

    # Choose sink (stdout if path is "-")
    if str(output_path) == "-":
        sink = StdoutSink()
        destination = "-"
    else:
        sink = FileSink()
        destination = output_path

    # Build filter chain
    # CRITICAL: Bypass filters for record format to prevent schema validation failures
    # Record payloads are curated and must match schemas exactly
    filters = []
    if config.format != "record":
        if config.field_profile != "full":
            filters.append(FieldFilter(profile=config.field_profile))
        if config.exclude_none:
            filters.append(NoneFilter())

    # Create and execute pipeline
    pipeline = EmitPipeline(
        renderer=renderer,
        sink=sink,
        filters=filters if filters else None,
    )

    return pipeline.emit(workflows, destination, config)


def render_json(workflow_dict: dict, pretty: bool = True, indent: int = 2) -> str:
    """Pure JSON rendering (no I/O).

    Low-level API for rendering a single workflow dict to JSON string
    without any file I/O.

    Args:
        workflow_dict: Workflow data as dict
        pretty: Whether to pretty-print
        indent: Indentation level

    Returns:
        JSON string

    Example:
        from cpmf_uips_xaml.api import render_json
        import dataclasses

        wf_dict = dataclasses.asdict(workflow)
        json_str = render_json(wf_dict)
        # Use json_str however you want (send to API, store in DB, etc.)
    """
    renderer = JsonRenderer()

    # Create simple config object
    class SimpleConfig:
        pass

    config = SimpleConfig()
    config.pretty = pretty
    config.indent = indent

    result = renderer.render_one(workflow_dict, config)

    if not result.success:
        raise RuntimeError(f"JSON rendering failed: {result.errors}")

    return result.content


def create_pipeline(
    format: str = "json",
    sink_type: str = "file",
    field_profile: str = "full",
    exclude_none: bool = False,
) -> EmitPipeline:
    """Create a custom emit pipeline.

    Low-level API for building custom pipelines with specific components.

    Args:
        format: Renderer format (json, mermaid, doc)
        sink_type: Sink type (file, stdout)
        field_profile: Field profile (full, minimal, mcp, datalake)
        exclude_none: Whether to exclude None values

    Returns:
        EmitPipeline ready for use

    Example:
        from cpmf_uips_xaml.api import create_pipeline

        # Custom pipeline with minimal profile and stdout sink
        pipeline = create_pipeline(
            format="json",
            sink_type="stdout",
            field_profile="minimal",
            exclude_none=True,
        )

        result = pipeline.emit(workflows, "-", config)
    """
    # Choose renderer
    if format == "json":
        renderer = JsonRenderer()
    elif format == "mermaid":
        renderer = MermaidRenderer()
    elif format == "doc":
        renderer = DocRenderer()
    elif format == "record":
        renderer = RecordRenderer()
    else:
        raise ValueError(f"Unknown format: {format}")

    # Choose sink
    if sink_type == "stdout":
        sink = StdoutSink()
    elif sink_type == "file":
        sink = FileSink()
    else:
        raise ValueError(f"Unknown sink type: {sink_type}")

    # Build filters
    # CRITICAL: Bypass filters for record format to prevent schema validation failures
    filters = []
    if format != "record":
        if field_profile != "full":
            filters.append(FieldFilter(profile=field_profile))
        if exclude_none:
            filters.append(NoneFilter())

    return EmitPipeline(
        renderer=renderer,
        sink=sink,
        filters=filters if filters else None,
    )


__all__ = [
    "emit_workflows",      # High-level orchestration
    "render_json",         # Pure rendering function
    "create_pipeline",     # Custom pipeline builder
    "EmitPipeline",        # Direct pipeline access
    "PipelineResult",      # Result type
]
