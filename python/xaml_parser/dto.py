"""Data Transfer Objects (DTOs) for XAML workflow parsing.

These DTOs represent the self-describing, stable output format of the parser.
They are separate from internal parsing models to allow independent evolution
of parsing implementation and output schema.

All DTOs are designed for:
- Deterministic serialization (stable IDs, sorted fields)
- Schema versioning ($schema, schemaVersion)
- Rename stability (content-hash based IDs, not path-based)
- Complete business logic capture

Schema: https://rpax.io/schemas/xaml-workflow-1.0.0.json
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SourceInfo:
    """Source file information for a workflow.

    Attributes:
        path: Current relative path (POSIX format)
        path_aliases: Historical paths for rename tracking
        hash: Full SHA-256 hash of normalized XML content
        size_bytes: File size in bytes
        encoding: Character encoding (always 'utf-8')
    """

    path: str = ""
    path_aliases: list[str] = field(default_factory=list)
    hash: str = ""  # sha256:...
    size_bytes: int = 0
    encoding: str = "utf-8"


@dataclass
class WorkflowMetadata:
    """Workflow-level XAML metadata.

    Captures XAML Workflow Foundation structure metadata, not business logic.
    Business logic (arguments, variables, activities) is stored separately.

    Attributes:
        xaml_class: XAML class name from x:Class attribute (e.g., "Main")
        xmlns_declarations: XML namespace prefix → URI mappings
        imported_namespaces: .NET namespaces from TextExpression.NamespacesForImplementation
        assembly_references: Assembly names from TextExpression.ReferencesForImplementation
        annotation: Root workflow annotation
        display_name: User-visible workflow name
        description: Workflow description
    """

    xaml_class: str | None = None
    xmlns_declarations: dict[str, str] = field(default_factory=dict)
    imported_namespaces: list[str] = field(default_factory=list)
    assembly_references: list[str] = field(default_factory=list)
    annotation: str | None = None
    display_name: str | None = None
    description: str | None = None


@dataclass
class ArgumentDto:
    """Workflow argument definition.

    Attributes:
        id: Stable argument ID
        name: Argument name
        type: Full .NET type signature
        direction: 'In', 'Out', or 'InOut'
        annotation: Annotation text
        default_value: Default value expression
    """

    id: str
    name: str
    type: str
    direction: str  # In, Out, InOut
    annotation: str | None = None
    default_value: str | None = None


@dataclass
class VariableDto:
    """Variable definition.

    Attributes:
        id: Stable variable ID
        name: Variable name
        type: Full .NET type signature
        scope: Scope ID (workflow or activity)
        default_value: Default value expression
    """

    id: str
    name: str
    type: str
    scope: str = "workflow"
    default_value: str | None = None


@dataclass
class DependencyDto:
    """Package dependency.

    Attributes:
        package: Package name
        version: Package version
    """

    package: str
    version: str


@dataclass
class ActivityDto:
    """Activity instance with complete business logic.

    This represents a first-class Activity entity as specified in ADR-009,
    serving as the atomic unit of interest for MCP/LLM consumption.

    Attributes:
        id: Stable content-hash based ID (act:sha256:...)
        type: Fully-qualified type name with namespace ({http://...}LocalName or prefix:LocalName)
        type_short: Short type name (LocalName only)
        type_namespace: Namespace URI (e.g., http://schemas.uipath.com/workflow/activities)
        type_prefix: Namespace prefix if any (e.g., ui, s)
        display_name: User-visible name
        parent_id: Parent activity ID
        children: Child activity IDs
        depth: Nesting depth level
        properties: All activity properties
        in_args: Input arguments (name → value/variable reference)
        out_args: Output arguments (name → variable reference)
        annotation: Activity annotation text
        expressions: List of expressions found
        variables_referenced: Variable names referenced
        selectors: UI selectors (for UI automation activities)
    """

    id: str  # act:sha256:abc123...
    type: str  # {http://schemas.uipath.com/workflow/activities}LogMessage or ui:LogMessage
    type_short: str  # LogMessage
    type_namespace: str | None = None  # http://schemas.uipath.com/workflow/activities
    type_prefix: str | None = None  # ui
    display_name: str | None = None

    # Hierarchy
    parent_id: str | None = None
    children: list[str] = field(default_factory=list)
    depth: int = 0

    # Configuration
    properties: dict[str, Any] = field(default_factory=dict)
    in_args: dict[str, str] = field(default_factory=dict)
    out_args: dict[str, str] = field(default_factory=dict)

    # Analysis
    annotation: str | None = None
    expressions: list[str] = field(default_factory=list)
    variables_referenced: list[str] = field(default_factory=list)

    # UI Activities
    selectors: dict[str, str] | None = None


@dataclass
class EdgeDto:
    """Control flow edge.

    Represents explicit control flow between activities.

    Attributes:
        id: Stable edge ID (edge:sha256:...)
        from_id: Source activity ID
        to_id: Target activity ID
        kind: Edge kind (Then, Else, Next, True, False, Case, Default,
              Catch, Finally, Link, Transition, Branch, Retry, Timeout, Done, Trigger)
        condition: Condition expression for conditional edges
        label: Display label for edge
    """

    id: str  # edge:sha256:...
    from_id: str
    to_id: str
    kind: str
    condition: str | None = None
    label: str | None = None


@dataclass
class InvocationDto:
    """Workflow invocation reference.

    Represents a call from one workflow to another.

    Attributes:
        callee_id: Target workflow ID (wf:sha256:...)
        callee_path: Original reference path (e.g., "./Sub.xaml")
        via_activity_id: InvokeWorkflowFile activity ID
        arguments_passed: Argument mappings (name → value/variable)
    """

    callee_id: str  # wf:sha256:...
    callee_path: str
    via_activity_id: str  # act:sha256:...
    arguments_passed: dict[str, str] = field(default_factory=dict)


@dataclass
class IssueDto:
    """Parsing or validation issue.

    Attributes:
        level: Issue severity (error, warning, info)
        message: Human-readable message
        path: Location path (workflow/activity path)
        code: Issue code for programmatic handling
    """

    level: str  # error, warning, info
    message: str
    path: str | None = None
    code: str | None = None


@dataclass
class WorkflowDto:
    """Self-describing workflow DTO.

    This is the primary output format for parsed workflows, designed to be
    stable, deterministic, and self-describing.

    Attributes:
        schema_id: JSON Schema URL
        schema_version: Schema version (semver)
        collected_at: Collection timestamp (ISO 8601 UTC)
        id: Stable workflow ID (wf:sha256:...)
        name: Workflow name
        source: Source file information
        metadata: Workflow metadata
        variables: Variable definitions
        arguments: Argument definitions
        dependencies: Package dependencies
        activities: Activity instances
        edges: Control flow edges
        invocations: Workflow invocations
        issues: Parsing/validation issues
    """

    # Schema metadata
    schema_id: str = "https://rpax.io/schemas/xaml-workflow.json"
    schema_version: str = "1.0.0"
    collected_at: str = ""  # ISO 8601

    # Identity
    id: str = ""  # wf:sha256:abc123...
    name: str = ""
    source: SourceInfo = field(default_factory=lambda: SourceInfo())

    # Metadata
    metadata: WorkflowMetadata = field(default_factory=lambda: WorkflowMetadata())

    # Content
    variables: list[VariableDto] = field(default_factory=list)
    arguments: list[ArgumentDto] = field(default_factory=list)
    dependencies: list[DependencyDto] = field(default_factory=list)
    activities: list[ActivityDto] = field(default_factory=list)
    edges: list[EdgeDto] = field(default_factory=list)
    invocations: list[InvocationDto] = field(default_factory=list)

    # Issues
    issues: list[IssueDto] = field(default_factory=list)


@dataclass
class EntryPointInfo:
    """Entry point workflow information.

    Attributes:
        workflow_id: Stable workflow ID (wf:sha256:...)
        file_path: Relative file path
        unique_id: Original UUID from project.json
    """

    workflow_id: str
    file_path: str
    unique_id: str | None = None


@dataclass
class ProjectInfo:
    """Project-level information from project.json.

    Attributes:
        name: Project name
        path: Project directory path
        project_id: UUID from project.json
        description: Project description
        project_version: Semantic version (e.g., "1.0.0")
        schema_version: Project schema version (e.g., "4.0")
        studio_version: UiPath Studio version (e.g., "25.0.167.0")
        expression_language: Expression language (VisualBasic or CSharp)
        target_framework: Target framework (Windows or Cross-platform)
        main_workflow_id: Stable main workflow ID (wf:sha256:...)
        entry_points: List of entry point workflows
        dependencies: Package dependencies (package → version)
    """

    name: str
    path: str
    project_id: str | None = None
    description: str | None = None
    project_version: str | None = None
    schema_version: str | None = None
    studio_version: str | None = None
    expression_language: str = "VisualBasic"
    target_framework: str | None = None
    main_workflow_id: str | None = None
    entry_points: list[EntryPointInfo] = field(default_factory=list)
    dependencies: dict[str, str] = field(default_factory=dict)


@dataclass
class WorkflowCollectionDto:
    """Collection of workflows (project-level output).

    Attributes:
        schema_id: JSON Schema URL for collection
        schema_version: Schema version
        collected_at: Collection timestamp (ISO 8601 UTC)
        project_info: Project information (from project.json)
        workflows: List of workflows
        issues: Collection-level issues
    """

    schema_id: str = "https://rpax.io/schemas/xaml-workflow-collection.json"
    schema_version: str = "1.1.0"
    collected_at: str = ""
    project_info: ProjectInfo | None = None
    workflows: list[WorkflowDto] = field(default_factory=list)
    issues: list[IssueDto] = field(default_factory=list)
