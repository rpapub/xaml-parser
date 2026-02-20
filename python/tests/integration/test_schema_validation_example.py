"""Example: validate record against v2 schema."""

import json
from pathlib import Path

import pytest

from cpmf_uips_xaml import load


def test_workflow_record_validates():
    """Example: workflow record validates against v2 schema."""
    corpus = Path("/mnt/d/github.com/rpapub/rpax-corpuses/c25v001_CORE_00000011/")
    if not corpus.exists():
        # Try alternative corpus locations
        alt_paths = [
            Path("D:/github.com/rpapub/rpax-corpuses/c25v001_CORE_00000011/"),
            Path("../rpax-corpuses/c25v001_CORE_00000011/"),
        ]
        for alt_path in alt_paths:
            if alt_path.exists():
                corpus = alt_path
                break

    if not corpus.exists():
        pytest.skip("Test corpus not available")

    # Load v2 schema
    schema_path = Path(__file__).parent.parent.parent.parent / "schemas/v2/workflow-record.schema.json"
    if not schema_path.exists():
        pytest.skip(f"Schema not found at {schema_path}")

    schema = json.loads(schema_path.read_text())

    # Load and convert workflows
    session = load(corpus)
    workflows = session.workflows()
    if not workflows:
        pytest.skip("No workflows found in test corpus")

    from dataclasses import asdict

    from cpmf_uips_xaml.stages.emit.records import workflows_to_records

    records = workflows_to_records(workflows[:1])  # Test first workflow only
    record = records[0]

    # Validate payload against schema (manual validation for now)
    payload = record.payload

    # Check required fields from schema
    required_fields = [
        "id",
        "name",
        "path",
        "annotation_tags",
        "arguments",
        "activity_ids",
        "activity_count",
        "edges",
    ]

    for field in required_fields:
        assert field in payload, f"Missing required field: {field}"

    # Validate field types
    assert isinstance(payload["id"], str), "id must be string"
    assert isinstance(payload["name"], str), "name must be string"
    assert isinstance(payload["path"], str), "path must be string"
    assert isinstance(payload["annotation_tags"], list), "annotation_tags must be array"
    assert isinstance(payload["arguments"], list), "arguments must be array"
    assert isinstance(payload["activity_ids"], list), "activity_ids must be array"
    assert isinstance(payload["activity_count"], int), "activity_count must be integer"
    assert isinstance(payload["edges"], list), "edges must be array"

    # Validate ID pattern (wf:sha256:...)
    assert payload["id"].startswith("wf:sha256:"), "id must match pattern wf:sha256:..."

    print(f"✓ Workflow record payload validates against v2 schema")

    # Optional: Use jsonschema library if available
    try:
        from jsonschema import validate

        validate(instance=payload, schema=schema)
        print(f"✓ JSON Schema validation passed")
    except ImportError:
        print("⚠ jsonschema library not available - skipping strict validation")
    except Exception as e:
        pytest.fail(f"Schema validation failed: {e}")
