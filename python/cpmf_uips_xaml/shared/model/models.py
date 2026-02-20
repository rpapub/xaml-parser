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
    # Expression language: "VisualBasic" or "CSharp"
    expression_language: str | None = None

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
    annotation: str | None = None  # sap2010:Annotation.AnnotationText (raw text)
    annotation_block: Any = None  # Structured annotation with parsed tags
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

    annotation: str | None = None  # Activity annotation (raw text)
    annotation_block: Any = None  # Structured annotation with parsed tags
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
class QualityMetrics:
    """Quality and complexity metrics for a workflow (v0.2.10)."""

    # Complexity metrics
    cyclomatic_complexity: int = 0  # Count of decision points + 1
    cognitive_complexity: int = 0  # Includes nesting penalties
    max_nesting_depth: int = 0  # Maximum activity depth

    # Size metrics
    total_activities: int = 0
    control_flow_activities: int = 0  # If, While, ForEach, etc.
    ui_automation_activities: int = 0  # Click, Type, Get activities
    data_activities: int = 0  # Assign, Invoke, Read/Write
    total_variables: int = 0
    total_expressions: int = 0
    complex_expressions: int = 0  # Expressions longer than 100 chars

    # Quality indicators
    has_error_handling: bool = False  # Has at least one TryCatch
    empty_catch_blocks: int = 0  # TryCatch with no error handling
    hardcoded_strings: int = 0  # Hardcoded paths, URLs, credentials
    unreachable_activities: int = 0  # Code after Throw/TerminateWorkflow
    unused_variables: int = 0  # Declared but never referenced

    # Overall quality score (0-100)
    quality_score: float = 0.0


@dataclass
class AntiPattern:
    """Detected anti-pattern or code smell in workflow (v0.2.10)."""

    pattern_type: str  # 'empty_catch' | 'hardcoded_value' | 'unreachable_code' | etc.
    severity: str  # 'error' | 'warning' | 'info'
    activity_id: str | None = None  # Activity where detected
    message: str = ""  # Human-readable description
    suggestion: str | None = None  # How to fix
    location: str | None = None  # Context (e.g., 'TryCatch.Catch', 'Assign.Value')


@dataclass
class ParseDiagnostic:
    """Individual diagnostic message from parsing (error, warning, or info)."""

    level: str  # "error", "warning", "info"
    message: str
    line: int | None = None
    column: int | None = None
    element: str | None = None  # Element that caused the issue
    suggestion: str | None = None  # How to fix

    def __str__(self) -> str:
        """Format diagnostic as readable string."""
        loc = f" at line {self.line}" if self.line else ""
        return f"[{self.level.upper()}]{loc}: {self.message}"


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
    # Individual diagnostic messages (errors/warnings/info)
    messages: list["ParseDiagnostic"] = field(default_factory=list)


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
