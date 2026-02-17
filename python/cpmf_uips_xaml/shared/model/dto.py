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
class ProvenanceInfo:
    """Provenance metadata for generated outputs.

    Captures authorship and generation information for CC-BY attribution.

    Attributes:
        generated_by: Tool name and version (e.g., "xaml-parser/0.5.0")
        generated_at: ISO 8601 timestamp (UTC)
        generator_url: Tool URL
        authors: List of authors (primary author + co-authors)
        license: License identifier (SPDX format, e.g., "CC-BY-4.0")
        license_url: License URL
    """

    generated_by: str
    generated_at: str  # ISO 8601
    generator_url: str = "https://github.com/rpapub/xaml-parser"
    authors: list[str] = field(default_factory=list)
    license: str = "CC-BY-4.0"
    license_url: str = "https://creativecommons.org/licenses/by/4.0/"


@dataclass
class AnnotationTag:
    """Single parsed annotation tag.

    Represents a single @tag from an annotation block, e.g., @author John Doe.

    Attributes:
        tag: Tag name without @ prefix (e.g., "author", "module", "custom:priority")
        value: Tag value/content (None for boolean flags like @public)
        raw: Original line(s) with @ prefix for debugging
        line_number: Line number in annotation block (1-indexed)

    Examples:
        @author John Doe → AnnotationTag(tag="author", value="John Doe")
        @ignore → AnnotationTag(tag="ignore", value=None)
        @module: ProcessInvoice → AnnotationTag(tag="module", value="ProcessInvoice")
    """

    tag: str  # Tag name without @ prefix
    value: str | None = None  # Tag value/content
    raw: str | None = None  # Original line(s) with @ prefix
    line_number: int = 0  # Line number in annotation block (1-indexed)


@dataclass
class AnnotationBlock:
    """Structured annotation with parsed tags.

    Maintains both raw text (backward compatibility) and parsed tags
    (structured analysis). Provides helper methods for common queries.

    Attributes:
        raw: Full annotation text (HTML decoded)
        tags: List of parsed annotation tags

    Example:
        text = "@module ProcessInvoice\\n@author John Doe"
        block = AnnotationBlock(
            raw=text,
            tags=[
                AnnotationTag(tag="module", value="ProcessInvoice", line_number=1),
                AnnotationTag(tag="author", value="John Doe", line_number=2),
            ]
        )
    """

    raw: str  # Full annotation text (HTML decoded)
    tags: list[AnnotationTag] = field(default_factory=list)  # Parsed tags

    def get_tag(self, tag_name: str) -> AnnotationTag | None:
        """Get first tag by name.

        Args:
            tag_name: Tag name to search for (without @ prefix)

        Returns:
            First matching AnnotationTag, or None if not found

        Example:
            >>> module = block.get_tag("module")
            >>> if module:
            ...     print(f"Module: {module.value}")
        """
        for tag in self.tags:
            if tag.tag == tag_name:
                return tag
        return None

    def get_tags(self, tag_name: str) -> list[AnnotationTag]:
        """Get all tags by name (for repeated tags like multiple @author).

        Args:
            tag_name: Tag name to search for (without @ prefix)

        Returns:
            List of matching AnnotationTag objects (may be empty)

        Example:
            >>> authors = block.get_tags("author")
            >>> for author in authors:
            ...     print(f"Author: {author.value}")
        """
        return [tag for tag in self.tags if tag.tag == tag_name]

    def has_tag(self, tag_name: str) -> bool:
        """Check if tag exists.

        Args:
            tag_name: Tag name to check for (without @ prefix)

        Returns:
            True if tag exists, False otherwise

        Example:
            >>> if block.has_tag("public"):
            ...     print("This is a public API")
        """
        return any(tag.tag == tag_name for tag in self.tags)

    @property
    def is_ignored(self) -> bool:
        """Check if @ignore or @ignore-all is present.

        Returns:
            True if workflow/activity should be ignored in analysis
        """
        return self.has_tag("ignore") or self.has_tag("ignore-all")

    @property
    def is_public_api(self) -> bool:
        """Check if marked as public API with @public tag.

        Returns:
            True if this is part of the public API
        """
        return self.has_tag("public")

    @property
    def is_test(self) -> bool:
        """Check if marked as test workflow with @test tag.

        Returns:
            True if this is a test workflow
        """
        return self.has_tag("test")

    @property
    def is_unit(self) -> bool:
        """Check if marked as unit workflow with @unit tag.

        Returns:
            True if this is an atomic unit of work
        """
        return self.has_tag("unit")

    @property
    def is_module(self) -> bool:
        """Check if marked as reusable module with @module tag.

        Returns:
            True if this is a reusable library workflow
        """
        return self.has_tag("module")

    @property
    def is_pathkeeper(self) -> bool:
        """Check if marked as pathkeeper with @pathkeeper tag.

        Returns:
            True if this workflow traverses Object Repository selectors read-only
        """
        return self.has_tag("pathkeeper")


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
        annotation: Root workflow annotation (raw text, backward compatibility)
        annotation_block: Structured annotation with parsed tags
        display_name: User-visible workflow name
        description: Workflow description
    """

    xaml_class: str | None = None
    xmlns_declarations: dict[str, str] = field(default_factory=dict)
    imported_namespaces: list[str] = field(default_factory=list)
    assembly_references: list[str] = field(default_factory=list)
    annotation: str | None = None  # Backward compatibility
    annotation_block: AnnotationBlock | None = None  # Structured tags
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
        annotation: Annotation text (raw text, backward compatibility)
        annotation_block: Structured annotation with parsed tags
        default_value: Default value expression
    """

    id: str
    name: str
    type: str
    direction: str  # In, Out, InOut
    annotation: str | None = None  # Backward compatibility
    annotation_block: AnnotationBlock | None = None  # Structured tags
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
class VariableFlowDto:
    """Variable data flow analysis.

    Tracks read/write patterns for a variable across activities.

    Attributes:
        variable_name: Variable name
        first_read: Activity ID where variable is first read
        first_write: Activity ID where variable is first written
        read_locations: List of activity IDs where variable is read
        write_locations: List of activity IDs where variable is written
        read_count: Total number of read operations
        write_count: Total number of write operations
        is_uninitialized: True if variable read before write (potential bug)
        is_unused: True if variable defined but never read
    """

    variable_name: str
    first_read: str | None = None
    first_write: str | None = None
    read_locations: list[str] = field(default_factory=list)
    write_locations: list[str] = field(default_factory=list)
    read_count: int = 0
    write_count: int = 0
    is_uninitialized: bool = False
    is_unused: bool = False


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
    annotation: str | None = None  # Backward compatibility
    annotation_block: AnnotationBlock | None = None  # Structured tags
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
    schema_version: str = "0.4.0"
    collected_at: str = ""  # ISO 8601

    # Provenance (authorship/generation)
    provenance: ProvenanceInfo | None = None

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

    # Quality Metrics (v0.2.10) - Optional, enabled by config
    quality_metrics: "QualityMetrics | None" = None
    anti_patterns: list["AntiPattern"] | None = None


@dataclass
class QualityMetrics:
    """Quality and complexity metrics for a workflow."""

    # Complexity metrics
    cyclomatic_complexity: int = 0
    cognitive_complexity: int = 0
    max_nesting_depth: int = 0

    # Size metrics
    total_activities: int = 0
    control_flow_activities: int = 0
    ui_automation_activities: int = 0
    data_activities: int = 0
    total_variables: int = 0
    total_expressions: int = 0
    complex_expressions: int = 0

    # Quality indicators
    has_error_handling: bool = False
    empty_catch_blocks: int = 0
    hardcoded_strings: int = 0
    unreachable_activities: int = 0
    unused_variables: int = 0

    # Overall score (0-100)
    quality_score: float = 0.0


@dataclass
class AntiPattern:
    """Detected anti-pattern or code smell in workflow."""

    pattern_type: str
    severity: str
    activity_id: str | None = None
    message: str = ""
    suggestion: str | None = None
    location: str | None = None


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
    schema_version: str = "0.4.0"
    collected_at: str = ""
    provenance: ProvenanceInfo | None = None
    project_info: ProjectInfo | None = None
    workflows: list[WorkflowDto] = field(default_factory=list)
    issues: list[IssueDto] = field(default_factory=list)
