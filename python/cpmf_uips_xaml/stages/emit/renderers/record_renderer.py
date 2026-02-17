"""Record renderer for v2 envelope output.

Renders workflows as v2 record envelopes (PRIMARY export format).
"""

import json
from dataclasses import asdict
from typing import Any

from ..records import (
    RecordEnvelope,
    dependency_to_record,
    invocation_to_record,
    issue_to_record,
    project_to_record,
)
from .base import RenderResult


def _dict_to_workflow_record_payload(workflow_dict: dict[str, Any]) -> dict[str, Any]:
    """Convert workflow dict to curated record payload.

    Works directly with dicts (from asdict) without rehydrating DTOs.
    """
    metadata = workflow_dict.get("metadata") or {}
    source = workflow_dict.get("source") or {}
    annotation_block = metadata.get("annotation_block") or {}
    tags = annotation_block.get("tags") or []

    return {
        # Core identity
        "id": workflow_dict.get("id", ""),
        "name": workflow_dict.get("name", ""),
        "path": source.get("path", ""),
        # Metadata (curated subset)
        "display_name": metadata.get("display_name"),
        "description": metadata.get("description"),
        "xaml_class": metadata.get("xaml_class"),
        # Annotations (first-class)
        "annotation": metadata.get("annotation"),
        "annotation_tags": [
            {
                "tag": tag.get("tag", ""),
                "value": tag.get("value"),
                "line_number": tag.get("line_number", 1) if tag.get("line_number", 0) > 0 else 1,
            }
            for tag in tags
        ],
        # Arguments (curated)
        "arguments": [
            {
                "name": arg.get("name", ""),
                "type": arg.get("type"),
                "direction": arg.get("direction", "In"),
                "default_value": arg.get("default_value"),
            }
            for arg in workflow_dict.get("arguments", [])
        ],
        # Activities (curated IDs only, not full objects)
        "activity_ids": [act.get("id", "") for act in workflow_dict.get("activities", [])],
        "activity_count": len(workflow_dict.get("activities", [])),
        # Edges
        "edges": [
            {"from": edge.get("from_id", ""), "to": edge.get("to_id", ""), "label": edge.get("label")}
            for edge in workflow_dict.get("edges", [])
        ],
    }


def _dict_to_activity_record_payload(
    activity_dict: dict[str, Any], workflow_id: str
) -> dict[str, Any]:
    """Convert activity dict to curated record payload."""
    annotation_block = activity_dict.get("annotation_block") or {}
    tags = annotation_block.get("tags") or []

    return {
        # Identity and traceability
        "id": activity_dict.get("id", ""),
        "workflow_id": workflow_id,
        # Type information
        "type": activity_dict.get("type", ""),
        "type_short": activity_dict.get("type_short"),
        "display_name": activity_dict.get("display_name"),
        # Structure
        "depth": activity_dict.get("depth", 0),
        "children": activity_dict.get("children", []),
        # Annotations (curated)
        "annotation": activity_dict.get("annotation"),
        "annotation_tags": [
            {
                "tag": tag.get("tag", ""),
                "value": tag.get("value"),
            }
            for tag in tags
        ],
        # Properties (curated key properties only, coerced to strings)
        "properties": {
            k: str(v) if v is not None else ""
            for k, v in (activity_dict.get("properties") or {}).items()
            if k in {"DisplayName", "Result", "Target", "Selector"}
        },
    }


def _dict_to_argument_record_payload(
    argument_dict: dict[str, Any], workflow_id: str
) -> dict[str, Any]:
    """Convert argument dict to curated record payload."""
    return {
        "workflow_id": workflow_id,
        "name": argument_dict.get("name", ""),
        "type": argument_dict.get("type"),
        "direction": argument_dict.get("direction", "In"),
        "default_value": argument_dict.get("default_value"),
        "annotation": argument_dict.get("annotation"),
    }


class RecordRenderer:
    """Renders workflows as v2 record envelopes (PRIMARY export format)."""

    @property
    def name(self) -> str:
        """Unique renderer identifier."""
        return "record"

    @property
    def output_extension(self) -> str:
        """Suggested file extension."""
        return ".jsonl"  # Default to JSONL (datalake-friendly)

    def render_one(self, workflow_dict: dict[str, Any], config: Any) -> RenderResult:
        """Render single workflow as record envelope.

        Args:
            workflow_dict: Workflow data as dict (from asdict)
            config: Renderer configuration

        Returns:
            RenderResult with JSONL record (single line)
        """
        # Work directly with dict - pipeline feeds dicts, not DTOs
        record_payload = _dict_to_workflow_record_payload(workflow_dict)

        record = RecordEnvelope(
            schema_id="cpmf-uips-xaml://v2/workflow-record",
            schema_version="2.0.0",
            kind="workflow",
            payload=record_payload,
        )

        # Serialize to JSONL (single line)
        content = json.dumps(asdict(record)) + "\n"

        return RenderResult(
            success=True,
            content=content,
            metadata={"suggested_filename": f"{workflow_dict.get('name', 'workflow')}.record.jsonl"},
        )

    def render_many(
        self, workflow_dicts: list[dict[str, Any]], config: Any
    ) -> RenderResult:
        """Render multiple workflows as record envelopes.

        Args:
            workflow_dicts: List of workflow dicts (from asdict)
            config: Renderer configuration with:
                - kinds: list[str] - Record kinds to include (default: ["workflow"])
                - combine: bool - Whether to combine into single output
                - pretty: bool - Pretty-print JSON (not recommended for JSONL)

        Returns:
            RenderResult with JSONL content (one record per line)
        """
        # Get record kinds from config
        kinds = getattr(config, "kinds", ["workflow"])
        records: list[RecordEnvelope] = []

        # Work directly with dicts - pipeline feeds dicts, not DTOs
        for wf_dict in workflow_dicts:
            workflow_id = wf_dict.get("id", "")

            if "workflow" in kinds:
                payload = _dict_to_workflow_record_payload(wf_dict)
                records.append(
                    RecordEnvelope(
                        schema_id="cpmf-uips-xaml://v2/workflow-record",
                        schema_version="2.0.0",
                        kind="workflow",
                        payload=payload,
                    )
                )

            if "activity" in kinds:
                for activity_dict in wf_dict.get("activities", []):
                    payload = _dict_to_activity_record_payload(activity_dict, workflow_id)
                    records.append(
                        RecordEnvelope(
                            schema_id="cpmf-uips-xaml://v2/activity-record",
                            schema_version="2.0.0",
                            kind="activity",
                            payload=payload,
                        )
                    )

            if "argument" in kinds:
                for argument_dict in wf_dict.get("arguments", []):
                    payload = _dict_to_argument_record_payload(argument_dict, workflow_id)
                    records.append(
                        RecordEnvelope(
                            schema_id="cpmf-uips-xaml://v2/argument-record",
                            schema_version="2.0.0",
                            kind="argument",
                            payload=payload,
                        )
                    )

            # Support invocation records (from workflow metadata)
            if "invocation" in kinds:
                for invocation_dict in wf_dict.get("invocations", []):
                    # Add caller_workflow_id for context
                    invocation_dict["caller_workflow_id"] = workflow_id
                    # Use canonical converter from records.py
                    records.append(invocation_to_record(invocation_dict))

            # Support issue records (from workflow errors)
            if "issue" in kinds:
                for issue_dict in wf_dict.get("issues", []):
                    # Add workflow_id for context
                    issue_dict["workflow_id"] = workflow_id
                    # Use canonical converter from records.py
                    records.append(issue_to_record(issue_dict))

            # Support dependency records (from workflow dependencies)
            if "dependency" in kinds:
                for dependency_dict in wf_dict.get("dependencies", []):
                    # Use canonical converter from records.py
                    records.append(dependency_to_record(dependency_dict))

        # Support project records (passed separately in config)
        if "project" in kinds:
            project_info = getattr(config, "project_info", None)
            if project_info:
                # Use canonical converter from records.py
                records.append(project_to_record(project_info))

        # Serialize to JSONL (one record per line)
        lines = [json.dumps(asdict(rec)) for rec in records]
        content = "\n".join(lines) + "\n"

        return RenderResult(
            success=True,
            content=content,
            metadata={
                "suggested_filename": "workflows.records.jsonl",
                "record_count": len(records),
                "kinds": kinds,
            },
        )

    def render_json(
        self,
        workflow_dicts: list[dict[str, Any]],
        *,
        pretty: bool = True,
    ) -> str:
        """Render workflows as JSON array of record envelopes.

        Args:
            workflow_dicts: Workflow dicts to render (from asdict)
            pretty: Pretty-print JSON

        Returns:
            JSON string with record envelopes
        """
        records = []
        for wf_dict in workflow_dicts:
            payload = _dict_to_workflow_record_payload(wf_dict)
            records.append(
                RecordEnvelope(
                    schema_id="cpmf-uips-xaml://v2/workflow-record",
                    schema_version="2.0.0",
                    kind="workflow",
                    payload=payload,
                )
            )

        data = [asdict(rec) for rec in records]
        return json.dumps(data, indent=2 if pretty else None)

    def render_jsonl(
        self,
        workflow_dicts: list[dict[str, Any]],
        *,
        kinds: list[str] | None = None,
    ) -> str:
        """Render as JSONL (one record per line) with multiple kinds.

        Args:
            workflow_dicts: Workflow dicts to render (from asdict)
            kinds: Record kinds to include (default: ["workflow"])

        Returns:
            JSONL string (one record per line)
        """
        kinds = kinds or ["workflow"]
        records: list[RecordEnvelope] = []

        for wf_dict in workflow_dicts:
            workflow_id = wf_dict.get("id", "")

            if "workflow" in kinds:
                payload = _dict_to_workflow_record_payload(wf_dict)
                records.append(
                    RecordEnvelope(
                        schema_id="cpmf-uips-xaml://v2/workflow-record",
                        schema_version="2.0.0",
                        kind="workflow",
                        payload=payload,
                    )
                )

            if "activity" in kinds:
                for activity_dict in wf_dict.get("activities", []):
                    payload = _dict_to_activity_record_payload(activity_dict, workflow_id)
                    records.append(
                        RecordEnvelope(
                            schema_id="cpmf-uips-xaml://v2/activity-record",
                            schema_version="2.0.0",
                            kind="activity",
                            payload=payload,
                        )
                    )

            if "argument" in kinds:
                for argument_dict in wf_dict.get("arguments", []):
                    payload = _dict_to_argument_record_payload(argument_dict, workflow_id)
                    records.append(
                        RecordEnvelope(
                            schema_id="cpmf-uips-xaml://v2/argument-record",
                            schema_version="2.0.0",
                            kind="argument",
                            payload=payload,
                        )
                    )

            if "invocation" in kinds:
                for invocation_dict in wf_dict.get("invocations", []):
                    invocation_dict["caller_workflow_id"] = workflow_id
                    records.append(invocation_to_record(invocation_dict))

            if "issue" in kinds:
                for issue_dict in wf_dict.get("issues", []):
                    issue_dict["workflow_id"] = workflow_id
                    records.append(issue_to_record(issue_dict))

            if "dependency" in kinds:
                for dependency_dict in wf_dict.get("dependencies", []):
                    records.append(dependency_to_record(dependency_dict))

        lines = [json.dumps(asdict(rec)) for rec in records]
        return "\n".join(lines) + "\n"


__all__ = ["RecordRenderer"]
