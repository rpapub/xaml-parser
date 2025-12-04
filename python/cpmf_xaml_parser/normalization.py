"""Normalization layer for transforming parsing models to DTOs.

This module transforms internal parsing models (ParseResult, WorkflowContent, Activity)
into self-describing DTOs (WorkflowDto, ActivityDto, etc.) with stable IDs, control
flow edges, and deterministic ordering.

Design: ADR-DTO-DESIGN.md (Normalization Layer)
"""

from datetime import UTC, datetime
from pathlib import Path

from .anti_patterns import AntiPatternDetector
from .control_flow import ControlFlowExtractor
from .dto import (
    ActivityDto,
    AntiPattern,
    ArgumentDto,
    DependencyDto,
    InvocationDto,
    IssueDto,
    QualityMetrics,
    SourceInfo,
    VariableDto,
    WorkflowDto,
    WorkflowMetadata,
)
from .id_generation import IdGenerator, generate_stable_id
from .models import Activity, ParseResult, WorkflowArgument, WorkflowVariable
from .ordering import sort_by_id, sort_by_name
from .provenance import create_provenance
from .quality_metrics import QualityMetricsCalculator


class Normalizer:
    """Transform parsing models to self-describing DTOs.

    This class orchestrates the normalization pipeline:
    1. Generate stable IDs for all entities
    2. Extract control flow edges
    3. Transform models to DTOs
    4. Optionally sort deterministically (explicit request only)
    5. Add self-describing metadata
    """

    def __init__(
        self,
        id_generator: IdGenerator | None = None,
        flow_extractor: ControlFlowExtractor | None = None,
    ) -> None:
        """Initialize normalizer.

        Args:
            id_generator: ID generator for stable IDs (creates new if None)
            flow_extractor: Control flow extractor (creates new if None)
        """
        self.id_generator = id_generator or IdGenerator()
        self.flow_extractor = flow_extractor or ControlFlowExtractor(self.id_generator)

    def normalize(
        self,
        parse_result: ParseResult,
        workflow_name: str | None = None,
        collected_at: str | None = None,
        workflow_id_map: dict[str, str] | None = None,
        sort_output: bool = False,
        project_dependencies: dict[str, str] | None = None,
        author: str | None = None,
        calculate_metrics: bool = False,
        detect_anti_patterns: bool = False,
    ) -> WorkflowDto:
        """Transform ParseResult to WorkflowDto.

        Args:
            parse_result: Parsing result from XamlParser
            workflow_name: Workflow name (derived from file if None)
            collected_at: Collection timestamp (ISO 8601 UTC, uses current time if None)
            workflow_id_map: Optional mapping of workflow paths to stable IDs for invocations
            sort_output: If True, sort all collections deterministically. If False (default),
                        preserve source file order for activities and other collections.
            project_dependencies: Optional dict of package dependencies from project.json.
                                Format: {"PackageName": "[version_constraint]", ...}
                                Example: {"UiPath.Excel.Activities": "[3.0.1]"}
            author: Author name for provenance metadata (will load from config if None)
            calculate_metrics: If True, calculate quality metrics (v0.2.10)
            detect_anti_patterns: If True, detect anti-patterns and code smells (v0.2.10)

        Returns:
            WorkflowDto with stable IDs, edges, and metadata
        """
        # Handle empty/failed parse results
        if not parse_result.content:
            return WorkflowDto(
                collected_at=collected_at or self._current_timestamp(),
                issues=[
                    IssueDto(
                        level="error",
                        message="Parse failed: no content",
                        path=parse_result.file_path,
                        code="PARSE_FAILED",
                    )
                ],
            )

        content = parse_result.content

        # Derive workflow name from file path if not provided
        if not workflow_name and parse_result.file_path:
            workflow_name = Path(parse_result.file_path).stem
        elif not workflow_name:
            workflow_name = "Untitled"

        # Generate workflow ID from XML content hash
        if parse_result.content_hash:
            # Use the stored content hash for stable IDs
            # content_hash format is "sha256:abc..." so extract just the hash part
            hash_part = parse_result.content_hash.replace("sha256:", "")[:16]
            workflow_id = f"wf:sha256:{hash_part}"
        else:
            # Fallback: generate from workflow name (less stable)
            workflow_id = f"wf:sha256:{hash(workflow_name) & 0xFFFFFFFFFFFFFFFF:016x}"

        # Transform activities
        activities = [self._transform_activity(act) for act in content.activities]

        # Extract control flow edges
        edges = self.flow_extractor.extract_edges(content.activities)

        # Transform arguments
        arguments = [self._transform_argument(arg) for arg in content.arguments]

        # Transform variables
        variables = [self._transform_variable(var) for var in content.variables]

        # Transform dependencies from project.json (if provided)
        # NOTE: Assembly references are NOT package dependencies - they are .NET framework
        # assemblies required by the VB expression engine and are intentionally excluded.
        # Real package dependencies come from project.json.
        # See: docs/INSTRUCTIONS-assembly-refs.md
        if project_dependencies:
            dependencies = self._parse_project_dependencies(project_dependencies)
        else:
            dependencies = []

        # Sort all collections deterministically (only if explicitly requested)
        if sort_output:
            activities = sort_by_id(activities)
            edges = sort_by_id(edges)
            arguments = sort_by_name(arguments)
            variables = sort_by_name(variables)
            dependencies = sorted(dependencies, key=lambda d: (d.package, d.version))

        # Generate timestamp and provenance
        timestamp = collected_at or self._current_timestamp()
        provenance = create_provenance(author=author, timestamp=timestamp)

        # Create source info
        source = SourceInfo(
            path=parse_result.file_path or "",
            path_aliases=[],
            hash=parse_result.content_hash or "",  # Full SHA-256 hash from parser
            size_bytes=parse_result.diagnostics.file_size_bytes if parse_result.diagnostics else 0,
            encoding="utf-8",
        )

        # Create metadata with XAML-specific fields
        metadata = WorkflowMetadata(
            xaml_class=content.xaml_class,
            xmlns_declarations=content.xmlns_declarations,
            imported_namespaces=content.imported_namespaces,
            assembly_references=content.assembly_references,
            annotation=content.root_annotation,
            display_name=content.display_name,
            description=content.description,
        )

        # Collect issues from parse result
        issues = []
        for error in parse_result.errors:
            issues.append(
                IssueDto(
                    level="error",
                    message=error,
                    path=parse_result.file_path,
                    code="PARSE_ERROR",
                )
            )
        for warning in parse_result.warnings:
            issues.append(
                IssueDto(
                    level="warning",
                    message=warning,
                    path=parse_result.file_path,
                    code="PARSE_WARNING",
                )
            )

        # Calculate quality metrics (v0.2.10)
        quality_metrics: QualityMetrics | None = None
        if calculate_metrics:
            metrics_calculator = QualityMetricsCalculator()
            # Collect all expressions from activities
            expressions = []
            for activity in content.activities:
                expressions.extend(activity.expression_objects)
            # Calculate metrics
            raw_metrics = metrics_calculator.calculate(
                content.activities, content.variables, [str(e) for e in expressions]
            )
            # Convert to DTO format (copy fields)
            quality_metrics = QualityMetrics(
                cyclomatic_complexity=raw_metrics.cyclomatic_complexity,
                cognitive_complexity=raw_metrics.cognitive_complexity,
                max_nesting_depth=raw_metrics.max_nesting_depth,
                total_activities=raw_metrics.total_activities,
                control_flow_activities=raw_metrics.control_flow_activities,
                ui_automation_activities=raw_metrics.ui_automation_activities,
                data_activities=raw_metrics.data_activities,
                total_variables=raw_metrics.total_variables,
                total_expressions=raw_metrics.total_expressions,
                complex_expressions=raw_metrics.complex_expressions,
                has_error_handling=raw_metrics.has_error_handling,
                empty_catch_blocks=raw_metrics.empty_catch_blocks,
                hardcoded_strings=raw_metrics.hardcoded_strings,
                unreachable_activities=raw_metrics.unreachable_activities,
                unused_variables=raw_metrics.unused_variables,
                quality_score=raw_metrics.quality_score,
            )

        # Detect anti-patterns (v0.2.10)
        anti_patterns: list[AntiPattern] | None = None
        if detect_anti_patterns:
            detector = AntiPatternDetector()
            raw_patterns = detector.detect(content.activities, content.variables)
            # Convert to DTO format (copy fields)
            anti_patterns = [
                AntiPattern(
                    pattern_type=p.pattern_type,
                    severity=p.severity,
                    activity_id=p.activity_id,
                    message=p.message,
                    suggestion=p.suggestion,
                    location=p.location,
                )
                for p in raw_patterns
            ]

        # Create workflow DTO
        return WorkflowDto(
            schema_id="https://rpax.io/schemas/xaml-workflow.json",
            schema_version="0.4.0",
            collected_at=timestamp,
            provenance=provenance,
            id=workflow_id,
            name=workflow_name,
            source=source,
            metadata=metadata,
            variables=variables,
            arguments=arguments,
            dependencies=dependencies,
            activities=activities,
            edges=edges,
            invocations=self._extract_invocations(content.activities, workflow_id_map or {}),
            issues=issues,
            quality_metrics=quality_metrics,
            anti_patterns=anti_patterns,
        )

    def _detect_property_direction(self, property_name: str, activity: Activity) -> str | None:
        """Detect argument direction from XAML metadata.

        Args:
            property_name: Property/argument name
            activity: Activity containing the property

        Returns:
            'in', 'out', 'inout', or None if direction cannot be determined

        Note:
            In XAML, property directions are encoded in metadata attributes or
            can be inferred from common patterns:
            - Result properties are typically Out
            - Value, Target, Condition properties are typically In
        """
        prop_lower = property_name.lower()

        # Common output properties by convention
        if prop_lower in ["result", "output", "out"]:
            return "out"

        # Check metadata for explicit direction markers
        # Some UiPath activities annotate properties with [In], [Out], [InOut] attributes
        if property_name in activity.metadata:
            metadata_val = activity.metadata[property_name]
            if isinstance(metadata_val, str):
                metadata_lower = metadata_val.lower()
                if "outargument" in metadata_lower or "[out]" in metadata_lower:
                    return "out"
                elif "inargument" in metadata_lower or "[in]" in metadata_lower:
                    return "in"
                elif "inoutargument" in metadata_lower or "[inout]" in metadata_lower:
                    return "inout"

        # Default: cannot determine from metadata
        return None

    def _transform_activity(self, activity: Activity) -> ActivityDto:
        """Transform Activity to ActivityDto.

        Args:
            activity: Internal Activity model

        Returns:
            ActivityDto with all fields mapped
        """
        # Use already-extracted namespace information from Activity model
        # If not available, fallback to extracting short type
        type_full = activity.activity_type
        type_short = (
            activity.activity_type_short
            if activity.activity_type_short
            else activity.activity_type.split(".")[-1]
        )
        type_namespace = activity.activity_namespace
        type_prefix = activity.activity_prefix

        # Extract input/output arguments from arguments dict
        in_args: dict[str, str] = {}
        out_args: dict[str, str] = {}

        # Parse arguments dict to separate In/Out based on metadata
        for key, value in activity.arguments.items():
            str_value = str(value) if not isinstance(value, str) else value

            # Detect direction from metadata (if available)
            # Check metadata for property direction attributes
            direction = self._detect_property_direction(key, activity)

            if direction == "out" or direction == "inout":
                out_args[key] = str_value
            if direction == "in" or direction == "inout":
                in_args[key] = str_value
            if direction is None:
                # Default: treat as input argument for backward compatibility
                in_args[key] = str_value

        return ActivityDto(
            id=activity.activity_id,
            type=type_full,
            type_short=type_short,
            type_namespace=type_namespace,
            type_prefix=type_prefix,
            display_name=activity.display_name,
            parent_id=activity.parent_activity_id,
            children=activity.child_activities,
            depth=activity.depth,
            properties=activity.properties,
            in_args=in_args,
            out_args=out_args,
            annotation=activity.annotation,
            expressions=activity.expressions,
            variables_referenced=activity.variables_referenced,
            selectors=activity.selectors if activity.selectors else None,
        )

    def _transform_argument(self, argument: WorkflowArgument) -> ArgumentDto:
        """Transform WorkflowArgument to ArgumentDto.

        Args:
            argument: Internal WorkflowArgument model

        Returns:
            ArgumentDto with stable ID
        """
        # Generate stable ID for argument based on name and type
        arg_id = generate_stable_id("arg", f"{argument.name}:{argument.type}")

        # Normalize direction to title case (In, Out, InOut)
        direction = argument.direction.title()

        return ArgumentDto(
            id=arg_id,
            name=argument.name,
            type=argument.type,
            direction=direction,
            annotation=argument.annotation,
            default_value=argument.default_value,
        )

    def _transform_variable(self, variable: WorkflowVariable) -> VariableDto:
        """Transform WorkflowVariable to VariableDto.

        Args:
            variable: Internal WorkflowVariable model

        Returns:
            VariableDto with stable ID
        """
        # Generate stable ID for variable based on name and type
        var_id = generate_stable_id("var", f"{variable.name}:{variable.type}")

        return VariableDto(
            id=var_id,
            name=variable.name,
            type=variable.type,
            scope=variable.scope,
            default_value=variable.default_value,
        )

    def _transform_dependencies(self, assembly_refs: list[str]) -> list[DependencyDto]:
        """Transform assembly references to DependencyDto list.

        Args:
            assembly_refs: List of assembly reference strings

        Returns:
            List of DependencyDto objects
        """
        dependencies = []

        for ref in assembly_refs:
            # Parse assembly reference format: "PackageName, Version=X.Y.Z, ..."
            # For now, use simple parsing
            parts = ref.split(",")
            if len(parts) >= 1:
                package = parts[0].strip()
                version = "unknown"

                # Look for Version= in parts
                for part in parts[1:]:
                    part = part.strip()
                    if part.startswith("Version="):
                        version = part.replace("Version=", "").strip()
                        break

                dependencies.append(DependencyDto(package=package, version=version))

        return dependencies

    def _parse_project_dependencies(self, project_deps: dict[str, str]) -> list[DependencyDto]:
        """Parse project.json dependencies into DependencyDto list.

        Args:
            project_deps: Dictionary from project.json dependencies field.
                         Format: {"PackageName": "[version_constraint]", ...}
                         Example: {"UiPath.Excel.Activities": "[3.0.1]"}

        Returns:
            List of DependencyDto objects with parsed versions

        Examples:
            >>> deps = {"UiPath.Excel.Activities": "[3.0.1]"}
            >>> result = self._parse_project_dependencies(deps)
            >>> result[0]
            DependencyDto(package="UiPath.Excel.Activities", version="3.0.1")

            >>> deps = {"UiPath.System.Activities": "[25.4.4]"}
            >>> result = self._parse_project_dependencies(deps)
            >>> result[0]
            DependencyDto(package="UiPath.System.Activities", version="25.4.4")
        """
        dependencies = []

        for package_name, version_constraint in project_deps.items():
            # Parse version constraint format: "[3.0.1]" → "3.0.1"
            # Also handle: "(3.0.1,4.0.0)", "[3.0.1,)", "3.0.1", etc.
            version = version_constraint.strip()

            # Remove brackets/parentheses for exact versions
            if version.startswith("[") and version.endswith("]"):
                # Exact version: "[3.0.1]" → "3.0.1"
                version = version[1:-1].strip()
            elif version.startswith("(") or version.startswith("["):
                # Range: "(3.0,4.0)" or "[3.0,)" → keep first version
                version = version.lstrip("([").split(",")[0].strip()

            # Create DependencyDto
            dependencies.append(
                DependencyDto(package=package_name, version=version if version else "unknown")
            )

        return dependencies

    def _current_timestamp(self) -> str:
        """Get current timestamp in ISO 8601 format (UTC).

        Returns:
            ISO 8601 timestamp string (e.g., "2025-10-11T07:15:00Z")
        """
        return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    def _extract_invocations(
        self, activities: list[Activity], workflow_id_map: dict[str, str]
    ) -> list[InvocationDto]:
        """Extract workflow invocations from InvokeWorkflowFile activities.

        Args:
            activities: List of activities to scan
            workflow_id_map: Map of workflow paths to stable workflow IDs

        Returns:
            List of InvocationDto objects
        """
        invocations = []

        for activity in activities:
            # Check if this is an InvokeWorkflowFile activity
            if "InvokeWorkflowFile" not in activity.activity_type:
                continue

            # Extract WorkflowFileName from various sources
            callee_path = (
                activity.arguments.get("WorkflowFileName")
                or activity.properties.get("WorkflowFileName")
                or activity.visible_attributes.get("WorkflowFileName")
            )

            if not callee_path:
                continue

            # Clean up path (remove quotes, expression syntax)
            callee_path_str = str(callee_path).strip('"').strip("'")

            # Normalize path separators
            callee_path_str = callee_path_str.replace("\\", "/")

            # Lookup stable ID from map (or use placeholder)
            callee_id = workflow_id_map.get(callee_path_str, f"wf:unresolved:{callee_path_str}")

            # Extract argument mappings
            arguments_passed = self._extract_argument_mappings(activity)

            invocation = InvocationDto(
                callee_id=callee_id,
                callee_path=callee_path_str,
                via_activity_id=activity.activity_id,
                arguments_passed=arguments_passed,
            )
            invocations.append(invocation)

        return invocations

    def _extract_argument_mappings(self, activity: Activity) -> dict[str, str]:
        """Extract argument mappings from InvokeWorkflowFile activity.

        Args:
            activity: InvokeWorkflowFile activity

        Returns:
            Dictionary mapping argument names to expressions
        """
        mappings = {}

        # Look for argument bindings in arguments dict
        # Arguments are typically in format: argumentName: expression
        for key, value in activity.arguments.items():
            # Skip the WorkflowFileName itself
            if key == "WorkflowFileName":
                continue

            # Add argument mapping
            if value is not None:
                mappings[key] = str(value)

        # Also check properties for argument bindings
        # Some UiPath versions store them differently
        if "Arguments" in activity.properties:
            args_config = activity.properties["Arguments"]
            if isinstance(args_config, dict):
                for arg_name, arg_value in args_config.items():
                    if arg_value is not None:
                        mappings[arg_name] = str(arg_value)

        return mappings
