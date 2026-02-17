"""Configuration dataclasses for cpmf_uips_xaml.

All defaults are loaded from config files, not hardcoded here.
Field defaults only exist for truly optional fields (e.g., None values,
empty dicts). All boolean/int/string config values must come from configs.
"""

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass(frozen=True)
class ParserConfig:
    """Parser behavior configuration.

    Controls what the XAML parser extracts and how it behaves.
    """

    extract_expressions: bool
    extract_viewstate: bool
    extract_arguments: bool
    extract_variables: bool
    extract_activities: bool
    extract_namespaces: bool
    extract_assembly_references: bool
    preserve_raw_metadata: bool
    strict_mode: bool
    max_depth: int
    enable_profiling: bool
    parse_expressions: bool
    extract_variable_flow: bool
    expression_language: str


@dataclass(frozen=True)
class ProjectConfig:
    """Project parsing configuration.

    Controls how projects are discovered and traversed.
    """

    recursive: bool
    entry_points_only: bool


@dataclass(frozen=True)
class EmitterConfig:
    """Output emission configuration.

    Controls how parsed data is serialized and output.
    """

    format: Literal["json", "mermaid", "doc"]
    combine: bool
    pretty: bool
    exclude_none: bool
    field_profile: Literal["full", "minimal", "mcp", "datalake"]
    indent: int
    encoding: str
    overwrite: bool
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class NormalizerConfig:
    """DTO normalization configuration.

    Controls how ParseResult is normalized to WorkflowDto.
    """

    sort_output: bool
    calculate_metrics: bool
    detect_anti_patterns: bool


@dataclass(frozen=True)
class ViewConfig:
    """View rendering configuration.

    Controls how workflow views are generated and filtered.
    """

    view_type: Literal["nested", "execution", "slice"]
    max_depth: int
    # Execution view options
    entry_point: str | None = None
    # Slice view options
    focus: str | None = None
    radius: int | None = None


@dataclass(frozen=True)
class ProvenanceConfig:
    """Provenance and attribution configuration.

    Used for CC-BY-4.0 licensing and metadata generation.
    """

    author: str | None = None
    description: str | None = None


@dataclass(frozen=True)
class Config:
    """Root configuration object.

    Contains all configuration sections for the parser system.
    """

    parser: ParserConfig
    project: ProjectConfig
    emitter: EmitterConfig
    normalizer: NormalizerConfig
    view: ViewConfig
    provenance: ProvenanceConfig
