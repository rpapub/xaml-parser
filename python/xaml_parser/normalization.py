"""Normalization layer for transforming parsing models to DTOs.

This module transforms internal parsing models (ParseResult, WorkflowContent, Activity)
into self-describing DTOs (WorkflowDto, ActivityDto, etc.) with stable IDs, control
flow edges, and deterministic ordering.

Design: ADR-DTO-DESIGN.md (Normalization Layer)
"""

from datetime import UTC, datetime
from pathlib import Path

from .control_flow import ControlFlowExtractor
from .dto import (
    ActivityDto,
    ArgumentDto,
    DependencyDto,
    InvocationDto,
    IssueDto,
    LocationInfo,
    SourceInfo,
    VariableDto,
    WorkflowDto,
    WorkflowMetadata,
)
from .id_generation import IdGenerator, generate_stable_id
from .models import Activity, ParseResult, WorkflowArgument, WorkflowVariable
from .ordering import sort_by_id, sort_by_name


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
    ) -> WorkflowDto:
        """Transform ParseResult to WorkflowDto.

        Args:
            parse_result: Parsing result from XamlParser
            workflow_name: Workflow name (derived from file if None)
            collected_at: Collection timestamp (ISO 8601 UTC, uses current time if None)
            workflow_id_map: Optional mapping of workflow paths to stable IDs for invocations
            sort_output: If True, sort all collections deterministically. If False (default),
                        preserve source file order for activities and other collections.

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

        # Generate workflow ID from XML content
        # Note: This assumes the parser stored the raw XML content somewhere
        # For now, we'll generate a placeholder ID based on name
        # TODO: Store raw XML content in ParseResult for proper workflow ID generation
        workflow_id = f"wf:sha256:{hash(workflow_name) & 0xFFFFFFFFFFFFFFFF:016x}"

        # Transform activities
        activities = [self._transform_activity(act) for act in content.activities]

        # Extract control flow edges
        edges = self.flow_extractor.extract_edges(content.activities)

        # Transform arguments
        arguments = [self._transform_argument(arg) for arg in content.arguments]

        # Transform variables
        variables = [self._transform_variable(var) for var in content.variables]

        # Transform dependencies
        # NOTE: Assembly references are NOT package dependencies - they are .NET framework
        # assemblies required by the VB expression engine. Real package dependencies should
        # come from project.json (not yet implemented). For now, return empty list.
        # See: docs/INSTRUCTIONS-assembly-refs.md
        dependencies: list[DependencyDto] = []

        # Sort all collections deterministically (only if explicitly requested)
        if sort_output:
            activities = sort_by_id(activities)
            edges = sort_by_id(edges)
            arguments = sort_by_name(arguments)
            variables = sort_by_name(variables)
            dependencies = sorted(dependencies, key=lambda d: (d.package, d.version))

        # Create source info
        source = SourceInfo(
            path=parse_result.file_path or "",
            path_aliases=[],
            hash="",  # TODO: Store full hash in ParseResult
            size_bytes=parse_result.diagnostics.file_size_bytes if parse_result.diagnostics else 0,
            encoding="utf-8",
        )

        # Create metadata
        metadata = WorkflowMetadata(
            project_name=None,  # TODO: Pass from project context
            namespace=None,
            expression_language=content.expression_language,
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

        # Create workflow DTO
        return WorkflowDto(
            schema_id="https://rpax.io/schemas/xaml-workflow.json",
            schema_version="1.0.0",
            collected_at=collected_at or self._current_timestamp(),
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
        )

    def _transform_activity(self, activity: Activity) -> ActivityDto:
        """Transform Activity to ActivityDto.

        Args:
            activity: Internal Activity model

        Returns:
            ActivityDto with all fields mapped
        """
        # Extract short type name (last component after '.')
        type_short = activity.activity_type.split(".")[-1]

        # Create location info
        location = None
        if activity.source_line is not None or activity.xpath_location:
            location = LocationInfo(
                line=activity.source_line,
                column=None,  # Column info not currently extracted
                xpath=activity.xpath_location,
            )

        # Extract input/output arguments from arguments dict
        in_args: dict[str, str] = {}
        out_args: dict[str, str] = {}

        # Parse arguments dict to separate In/Out
        for key, value in activity.arguments.items():
            # Simplified: treat all as input arguments for now
            # TODO: Properly detect direction from XAML metadata
            if isinstance(value, str):
                in_args[key] = value
            else:
                in_args[key] = str(value)

        return ActivityDto(
            id=activity.activity_id,
            type=activity.activity_type,
            type_short=type_short,
            display_name=activity.display_name,
            location=location,
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
