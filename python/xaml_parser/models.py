"""Data models for XAML workflow parsing using only Python stdlib.

All models use dataclasses to avoid external dependencies, making this package
completely self-contained and reusable in any Python project.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class WorkflowContent:
    """Complete parsed workflow content from XAML file.

    This is the main result object containing all extracted metadata
    from a workflow XAML file.
    """

    # Core workflow elements
    arguments: list["WorkflowArgument"] = field(default_factory=list)
    variables: list["WorkflowVariable"] = field(default_factory=list)
    activities: list["Activity"] = field(default_factory=list)

    # Workflow metadata
    root_annotation: str | None = None
    display_name: str | None = None
    description: str | None = None

    # XAML technical metadata
    xaml_class: str | None = None  # x:Class attribute from root Activity element
    xmlns_declarations: dict[str, str] = field(default_factory=dict)  # xmlns prefix → URI
    namespaces: dict[str, str] = field(default_factory=dict)  # Alias for xmlns_declarations
    # TextExpression.NamespacesForImplementation
    imported_namespaces: list[str] = field(default_factory=list)
    # TextExpression.ReferencesForImplementation
    assembly_references: list[str] = field(default_factory=list)

    # Raw metadata for future extensions
    metadata: dict[str, Any] = field(default_factory=dict)

    # Statistics
    total_activities: int = 0
    total_arguments: int = 0
    total_variables: int = 0


@dataclass
class WorkflowArgument:
    """Workflow argument definition from x:Members section."""

    name: str
    type: str  # Full .NET type signature
    direction: str  # 'in', 'out', 'inout'
    annotation: str | None = None  # sap2010:Annotation.AnnotationText
    default_value: str | None = None  # From default attribute or this: prefix


@dataclass
class WorkflowVariable:
    """Variable definition from workflow scope."""

    name: str
    type: str  # Full .NET type signature
    default_value: str | None = None  # Default value expression
    scope: str = "workflow"  # Which element scope owns this variable


@dataclass
class Activity:
    """Complete activity instance with full business logic configuration.

    This model represents first-class Activity entities as specified in ADR-009,
    serving as the atomic units of interest for MCP/LLM consumption.
    """

    # Core identification (ActivityInstance requirements)
    activity_id: str  # Unique activity identifier
    workflow_id: str  # Parent workflow
    activity_type: str  # Full type with namespace: {http://...}LocalName
    activity_type_short: str = ""  # LocalName only
    activity_namespace: str | None = None  # Namespace URI
    activity_prefix: str | None = None  # Namespace prefix (ui, s, etc.)
    display_name: str | None = None  # User-visible name
    node_id: str = ""  # Hierarchical path
    parent_activity_id: str | None = None  # Parent in hierarchy
    depth: int = 0  # Nesting level

    # Complete business logic extraction
    arguments: dict[str, Any] = field(default_factory=dict)  # All activity arguments
    configuration: dict[str, Any] = field(default_factory=dict)  # Nested objects (Target, etc.)
    properties: dict[str, Any] = field(default_factory=dict)  # All visible properties
    metadata: dict[str, Any] = field(default_factory=dict)  # ViewState, IdRef, etc.

    # Business logic analysis
    expressions: list[str] = field(default_factory=list)  # UiPath expressions found
    variables_referenced: list[str] = field(default_factory=list)  # Variables used
    selectors: dict[str, str] = field(default_factory=dict)  # UI selectors

    annotation: str | None = None  # Activity annotation
    is_visible: bool = True  # Visual designer visibility
    container_type: str | None = None  # Parent container type

    # Legacy fields for backward compatibility
    visible_attributes: dict[str, str] = field(default_factory=dict)  # User-visible config (legacy)
    invisible_attributes: dict[str, str] = field(
        default_factory=dict
    )  # ViewState, technical (legacy)
    variables: list[WorkflowVariable] = field(
        default_factory=list
    )  # Activity-scoped variables (legacy)
    child_activities: list[str] = field(default_factory=list)  # Legacy hierarchy
    expression_objects: list["Expression"] = field(
        default_factory=list
    )  # Detailed expression objects (legacy)

    # XML span for stable ID generation (Phase 1)
    xml_span: str | None = None  # Raw XML substring for this activity


@dataclass
class Expression:
    """Expression found in XAML (VB.NET or C# syntax)."""

    content: str  # Raw expression text
    expression_type: str  # 'assignment', 'condition', 'message', etc.
    language: str = "VisualBasic"  # Expression language
    context: str | None = None  # Which activity property contains this
    contains_variables: list[str] = field(default_factory=list)  # Variable references
    contains_methods: list[str] = field(default_factory=list)  # Method calls detected


@dataclass
class ViewStateData:
    """ViewState information (invisible UI metadata)."""

    is_expanded: bool | None = None
    is_pinned: bool | None = None
    is_annotation_docked: bool | None = None
    hint_size: str | None = None
    other_properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class ParseDiagnostics:
    """Detailed diagnostic information about parsing operation."""

    total_elements_processed: int = 0
    activities_found: int = 0
    arguments_found: int = 0
    variables_found: int = 0
    annotations_found: int = 0
    expressions_found: int = 0
    namespaces_detected: int = 0
    skipped_elements: int = 0
    xml_depth: int = 0
    file_size_bytes: int = 0
    encoding_detected: str | None = None
    root_element_tag: str | None = None
    processing_steps: list[str] = field(default_factory=list)
    performance_metrics: dict[str, float] = field(default_factory=dict)


@dataclass
class ParseResult:
    """Complete parsing result with success/error information and diagnostics."""

    content: WorkflowContent | None = None
    success: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    parse_time_ms: float = 0.0
    file_path: str | None = None
    # Raw XML content for content-based ID generation
    raw_xml: str | None = None
    # Full SHA-256 hash of normalized XML (hex)
    content_hash: str | None = None
    # Enhanced diagnostics for troubleshooting
    diagnostics: ParseDiagnostics | None = None
    config_used: dict[str, Any] = field(default_factory=dict)
