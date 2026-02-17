"""Record envelope conversion with curated payloads for external contracts.

IMPORTANT: Record payloads are CURATED, not raw DTO dumps.
This decouples external contracts from internal DTO structure.
"""

from dataclasses import asdict, dataclass
from typing import Any, Literal

from ...shared.model.dto import ActivityDto, ArgumentDto, WorkflowDto

# Schema version for v2 contracts
SCHEMA_VERSION = "2.0.0"


@dataclass
class RecordEnvelope:
    """Versioned record envelope for stable external consumption."""

    schema_id: str  # e.g., "cpmf-uips-xaml://v2/workflow-record"
    schema_version: str  # e.g., "2.0.0"
    kind: Literal["project", "workflow", "activity", "argument", "invocation", "issue", "dependency"]
    payload: dict[str, Any]  # CURATED payload (not raw DTO)


def workflow_to_record(workflow: WorkflowDto) -> RecordEnvelope:
    """Convert WorkflowDto to curated record envelope.

    CURATES fields for stable external contract.
    """
    return RecordEnvelope(
        schema_id="cpmf-uips-xaml://v2/workflow-record",
        schema_version=SCHEMA_VERSION,
        kind="workflow",
        payload={
            # Core identity
            "id": workflow.id,
            "name": workflow.name,
            "path": workflow.source.path,
            # Metadata (curated subset)
            "display_name": workflow.metadata.display_name if workflow.metadata else None,
            "description": workflow.metadata.description if workflow.metadata else None,
            "xaml_class": workflow.metadata.xaml_class if workflow.metadata else None,
            # Annotations (first-class)
            "annotation": workflow.metadata.annotation if workflow.metadata else None,
            "annotation_tags": [
                {
                    "tag": tag.tag,
                    "value": tag.value,
                    "line_number": tag.line_number if tag.line_number > 0 else 1,  # Schema requires minimum 1
                }
                for tag in (
                    workflow.metadata.annotation_block.tags
                    if workflow.metadata and workflow.metadata.annotation_block
                    else []
                )
            ],
            # Arguments (curated)
            "arguments": [
                {
                    "name": arg.name,
                    "type": arg.type,
                    "direction": arg.direction,
                    "default_value": arg.default_value,
                }
                for arg in workflow.arguments
            ],
            # Activities (curated IDs only, not full objects)
            "activity_ids": [act.id for act in workflow.activities],
            "activity_count": len(workflow.activities),
            # Edges
            "edges": [
                {"from": edge.from_id, "to": edge.to_id, "label": edge.label}
                for edge in workflow.edges
            ],
        },
    )


def activity_to_record(activity: ActivityDto, workflow_id: str) -> RecordEnvelope:
    """Convert ActivityDto to curated record envelope.

    Includes workflow_id for traceability.
    """
    return RecordEnvelope(
        schema_id="cpmf-uips-xaml://v2/activity-record",
        schema_version=SCHEMA_VERSION,
        kind="activity",
        payload={
            # Identity and traceability
            "id": activity.id,
            "workflow_id": workflow_id,
            # Type information
            "type": activity.type,
            "type_short": activity.type_short,
            "display_name": activity.display_name,
            # Structure
            "depth": activity.depth,
            "children": activity.children,
            # Annotations (curated)
            "annotation": activity.annotation,
            "annotation_tags": [
                {
                    "tag": tag.tag,
                    "value": tag.value,
                }
                for tag in (activity.annotation_block.tags if activity.annotation_block else [])
            ],
            # Properties (curated key properties only)
            "properties": {
                k: str(v) if v is not None else ""  # Schema requires string values
                for k, v in (activity.properties or {}).items()
                if k in {"DisplayName", "Result", "Target", "Selector"}  # Curate specific keys
            },
        },
    )


def argument_to_record(argument: ArgumentDto, workflow_id: str) -> RecordEnvelope:
    """Convert ArgumentDto to curated record envelope."""
    return RecordEnvelope(
        schema_id="cpmf-uips-xaml://v2/argument-record",
        schema_version=SCHEMA_VERSION,
        kind="argument",
        payload={
            "workflow_id": workflow_id,
            "name": argument.name,
            "type": argument.type,
            "direction": argument.direction,
            "default_value": argument.default_value,
            "annotation": argument.annotation,
        },
    )


def workflows_to_records(workflows: list[WorkflowDto]) -> list[RecordEnvelope]:
    """Convert workflows to record envelopes."""
    return [workflow_to_record(wf) for wf in workflows]


def flatten_to_activity_records(workflows: list[WorkflowDto]) -> list[RecordEnvelope]:
    """Flatten workflows into activity records (for datalake/JSONL)."""
    records = []
    for wf in workflows:
        for activity in wf.activities:
            records.append(activity_to_record(activity, wf.id))
    return records


def flatten_to_argument_records(workflows: list[WorkflowDto]) -> list[RecordEnvelope]:
    """Flatten workflows into argument records."""
    records = []
    for wf in workflows:
        for argument in wf.arguments:
            records.append(argument_to_record(argument, wf.id))
    return records


def project_to_record(project_info: dict[str, Any]) -> RecordEnvelope:
    """Convert project metadata to curated record envelope.

    Args:
        project_info: Project metadata dict with name, type, path.
            Typically from ProjectConfig with type derived from project.json.

    Schema contract:
        - name: str (required) - Project name
        - type: "Process" | "Library" (required) - Project type
        - path: str (required) - Project root path
        - version: str | null - Project version
        - description: str | null - Project description
    """
    project_type = project_info.get("type", "Process")
    # Validate enum: must be Process or Library
    # (ProjectConfig normalizes other types like BusinessProcess → Process)
    if project_type not in ("Process", "Library"):
        project_type = "Process"  # Fallback for safety

    return RecordEnvelope(
        schema_id="cpmf-uips-xaml://v2/project-record",
        schema_version=SCHEMA_VERSION,
        kind="project",
        payload={
            "name": project_info.get("name", ""),
            "type": project_type,  # Derived from project.json projectType
            "path": project_info.get("path", ""),
            "version": project_info.get("version"),
            "description": project_info.get("description"),
        },
    )


def invocation_to_record(invocation_info: dict[str, Any]) -> RecordEnvelope:
    """Convert workflow invocation to curated record envelope.

    Args:
        invocation_info: Invocation data from InvocationDto + caller workflow ID.

    InvocationDto fields:
        - callee_id: str - Target workflow ID
        - callee_path: str - Original reference path
        - via_activity_id: str - InvokeWorkflowFile activity ID
        - arguments_passed: dict - Argument mappings

    Schema contract:
        - caller_workflow_id: str (required) - Calling workflow ID (from parent)
        - caller_activity_id: str (required) - Calling activity ID
        - callee_workflow_id: str | null - Called workflow ID
        - callee_workflow_path: str | null - Called workflow path
        - invocation_type: "InvokeWorkflow" | "InvokeWorkflowFile" | "DynamicInvoke" (required)
    """
    return RecordEnvelope(
        schema_id="cpmf-uips-xaml://v2/invocation-record",
        schema_version=SCHEMA_VERSION,
        kind="invocation",
        payload={
            "caller_workflow_id": invocation_info.get("caller_workflow_id", ""),
            "caller_activity_id": invocation_info.get("via_activity_id", ""),  # DTO field
            "callee_workflow_id": invocation_info.get("callee_id"),  # DTO field
            "callee_workflow_path": invocation_info.get("callee_path"),  # DTO field
            "invocation_type": "InvokeWorkflowFile",  # Inferred from DTO presence
        },
    )


def issue_to_record(issue_info: dict[str, Any]) -> RecordEnvelope:
    """Convert parse/validation issue to curated record envelope.

    Args:
        issue_info: Issue data from IssueDto + workflow_id from parent.

    IssueDto fields:
        - level: str - Issue severity (error, warning, info)
        - message: str - Human-readable message
        - path: str | None - Location path (workflow/activity path)
        - code: str | None - Issue code for programmatic handling

    Schema contract:
        - severity: "error" | "warning" | "info" (required)
        - code: str (required) - Error or validation code
        - message: str (required) - Human-readable message
        - workflow_id: str | null - Associated workflow ID (from parent)
        - activity_id: str | null - Associated activity ID (not in DTO)
        - location: str | null - File path or location
    """
    return RecordEnvelope(
        schema_id="cpmf-uips-xaml://v2/issue-record",
        schema_version=SCHEMA_VERSION,
        kind="issue",
        payload={
            "severity": issue_info.get("level", "error"),  # DTO field: level
            "code": issue_info.get("code") or "UNKNOWN",  # DTO field, ensure non-empty
            "message": issue_info.get("message", ""),
            "workflow_id": issue_info.get("workflow_id"),  # From parent workflow
            "activity_id": None,  # Not in IssueDto
            "location": issue_info.get("path"),  # DTO field: path
        },
    )


def dependency_to_record(dependency_info: dict[str, Any]) -> RecordEnvelope:
    """Convert package dependency to curated record envelope.

    Args:
        dependency_info: Dependency data from DependencyDto.

    DependencyDto fields:
        - package: str - Package name
        - version: str - Package version

    Schema contract:
        - package_id: str (required) - Package identifier
        - version: str (required) - Package version
        - source: str | null - Package source (not in DTO)
        - dependency_type: "direct" | "transitive" (required, not in DTO)
    """
    return RecordEnvelope(
        schema_id="cpmf-uips-xaml://v2/dependency-record",
        schema_version=SCHEMA_VERSION,
        kind="dependency",
        payload={
            "package_id": dependency_info.get("package", ""),  # DTO field: package
            "version": dependency_info.get("version", ""),
            "source": None,  # Not in DependencyDto
            "dependency_type": "direct",  # Not in DependencyDto, default
        },
    )


__all__ = [
    "RecordEnvelope",
    "SCHEMA_VERSION",
    "workflow_to_record",
    "activity_to_record",
    "argument_to_record",
    "project_to_record",
    "invocation_to_record",
    "issue_to_record",
    "dependency_to_record",
    "workflows_to_records",
    "flatten_to_activity_records",
    "flatten_to_argument_records",
]
