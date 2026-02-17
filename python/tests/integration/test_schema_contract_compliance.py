"""Test schema contract compliance for all record kinds."""

import json
from pathlib import Path

import pytest


def test_all_schemas_exist():
    """Verify all 8 v2 schemas exist."""
    schema_dir = Path(__file__).parent.parent.parent.parent / "schemas/v2"
    required_schemas = [
        "record-envelope.schema.json",
        "workflow-record.schema.json",
        "activity-record.schema.json",
        "argument-record.schema.json",
        "invocation-record.schema.json",
        "issue-record.schema.json",
        "dependency-record.schema.json",
        "project-record.schema.json",
    ]

    for schema_file in required_schemas:
        schema_path = schema_dir / schema_file
        assert schema_path.exists(), f"Missing schema: {schema_file}"

        # Validate it's valid JSON
        schema = json.loads(schema_path.read_text())
        assert "$schema" in schema, f"Invalid schema: {schema_file}"
        assert "title" in schema, f"Schema missing title: {schema_file}"

    print(f"✓ All {len(required_schemas)} v2 schemas exist and are valid JSON")


def test_dependency_record_contract():
    """Verify dependency record matches schema contract."""
    from cpmf_uips_xaml.stages.emit.records import dependency_to_record

    # Test with DependencyDto field names
    record = dependency_to_record({
        "package": "UiPath.System.Activities",  # DTO field
        "version": "23.10.0",
    })

    assert record.kind == "dependency"
    assert record.schema_id == "cpmf-uips-xaml://v2/dependency-record"
    assert record.schema_version == "2.0.0"

    payload = record.payload
    assert payload["package_id"] == "UiPath.System.Activities"  # Schema field
    assert payload["version"] == "23.10.0"
    assert payload["source"] is None  # Not in DependencyDto
    assert payload["dependency_type"] == "direct"  # Default

    # Verify dependency_type enum is valid
    assert payload["dependency_type"] in ["direct", "transitive"]

    # Test with another package
    record = dependency_to_record({
        "package": "UiPath.Excel.Activities",  # DTO field
        "version": "2.20.0",
    })
    assert record.payload["package_id"] == "UiPath.Excel.Activities"
    assert record.payload["dependency_type"] == "direct"  # Default

    print("✓ Dependency record contract validated")


def test_invocation_record_contract():
    """Verify invocation record matches schema contract."""
    from cpmf_uips_xaml.stages.emit.records import invocation_to_record

    # Test with InvocationDto field names + caller_workflow_id from parent
    record = invocation_to_record({
        "caller_workflow_id": "wf:sha256:abc123",  # From parent workflow
        "via_activity_id": "act:sha256:def456",  # DTO field
        "callee_id": "wf:sha256:ghi789",  # DTO field
        "callee_path": "Workflows/Process.xaml",  # DTO field
    })

    assert record.kind == "invocation"
    assert record.schema_id == "cpmf-uips-xaml://v2/invocation-record"

    payload = record.payload
    assert payload["caller_workflow_id"] == "wf:sha256:abc123"
    assert payload["caller_activity_id"] == "act:sha256:def456"  # Mapped from via_activity_id
    assert payload["callee_workflow_id"] == "wf:sha256:ghi789"  # Mapped from callee_id
    assert payload["callee_workflow_path"] == "Workflows/Process.xaml"  # Mapped from callee_path
    assert payload["invocation_type"] == "InvokeWorkflowFile"  # Inferred

    # Verify invocation_type enum is valid
    assert payload["invocation_type"] in ["InvokeWorkflow", "InvokeWorkflowFile", "DynamicInvoke"]

    # Test with minimal DTO fields
    record = invocation_to_record({
        "caller_workflow_id": "wf:sha256:test",
        "via_activity_id": "act:sha256:minimal",
        "callee_id": "wf:sha256:target",
        "callee_path": "Sub.xaml",
    })
    assert record.payload["caller_activity_id"] == "act:sha256:minimal"
    assert record.payload["invocation_type"] == "InvokeWorkflowFile"

    print("✓ Invocation record contract validated")


def test_issue_record_contract():
    """Verify issue record matches schema contract."""
    from cpmf_uips_xaml.stages.emit.records import issue_to_record

    # Test with IssueDto field names + workflow_id from parent
    record = issue_to_record({
        "level": "error",  # DTO field
        "code": "PARSE_ERROR",  # DTO field
        "message": "Failed to parse XAML",  # DTO field
        "path": "Workflows/Main.xaml:42",  # DTO field
        "workflow_id": "wf:sha256:abc123",  # From parent workflow
    })

    assert record.kind == "issue"
    assert record.schema_id == "cpmf-uips-xaml://v2/issue-record"

    payload = record.payload
    assert payload["severity"] == "error"  # Mapped from level
    assert payload["code"] == "PARSE_ERROR"
    assert payload["message"] == "Failed to parse XAML"
    assert payload["workflow_id"] == "wf:sha256:abc123"
    assert payload["activity_id"] is None  # Not in IssueDto
    assert payload["location"] == "Workflows/Main.xaml:42"  # Mapped from path

    # Verify severity enum is valid
    assert payload["severity"] in ["error", "warning", "info"]

    # Test required code field has default when None
    record = issue_to_record({
        "level": "warning",
        "message": "Unknown error",
        "code": None,  # DTO can have None
    })
    assert record.payload["code"] == "UNKNOWN"  # Safe default
    assert record.payload["code"] != ""  # Not empty
    assert record.payload["severity"] == "warning"  # Mapped from level

    print("✓ Issue record contract validated")


def test_project_record_contract():
    """Verify project record matches schema contract."""
    from cpmf_uips_xaml.stages.emit.records import project_to_record

    # Test with complete info
    record = project_to_record({
        "name": "MyUiPathProject",
        "type": "Process",
        "path": "/path/to/project",
        "version": "1.0.0",
        "description": "Sample project",
    })

    assert record.kind == "project"
    assert record.schema_id == "cpmf-uips-xaml://v2/project-record"

    payload = record.payload
    assert payload["name"] == "MyUiPathProject"
    assert payload["type"] == "Process"
    assert payload["path"] == "/path/to/project"
    assert payload["version"] == "1.0.0"
    assert payload["description"] == "Sample project"

    # Verify type enum is valid
    assert payload["type"] in ["Process", "Library"]

    # Test with minimal required fields
    record = project_to_record({
        "name": "MinimalProject",
        "type": "Library",
        "path": "/minimal",
    })
    assert record.payload["name"] == "MinimalProject"
    assert record.payload["type"] == "Library"
    assert record.payload["path"] == "/minimal"
    assert record.payload["version"] is None  # Nullable
    assert record.payload["description"] is None  # Nullable

    print("✓ Project record contract validated")


def test_filter_bypass_for_record_format():
    """Verify field filters are bypassed for record format."""
    from dataclasses import dataclass, field

    from cpmf_uips_xaml.api.emit import create_pipeline

    # Create pipeline with record format and minimal profile
    pipeline = create_pipeline(
        format="record",
        field_profile="minimal",  # Would normally filter fields
        exclude_none=True,  # Would normally remove None values
    )

    # Verify filters were bypassed (None)
    assert pipeline.filters is None or len(pipeline.filters) == 0, \
        "Field filters should be bypassed for record format to prevent schema breaks"

    # Compare with JSON format (should have filters)
    json_pipeline = create_pipeline(
        format="json",
        field_profile="minimal",
        exclude_none=True,
    )

    assert json_pipeline.filters is not None and len(json_pipeline.filters) > 0, \
        "JSON format should apply field filters"

    print("✓ Filter bypass for record format verified")
