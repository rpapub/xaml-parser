"""Smoke test for record export."""

import json
from pathlib import Path

import pytest

from cpmf_uips_xaml import load


@pytest.fixture
def test_corpus():
    """Test corpus path."""
    corpus_path = Path("/mnt/d/github.com/rpapub/rpax-corpuses/c25v001_CORE_00000011/")
    if not corpus_path.exists():
        # Try alternative corpus locations
        alt_paths = [
            Path("D:/github.com/rpapub/rpax-corpuses/c25v001_CORE_00000011/"),
            Path("../rpax-corpuses/c25v001_CORE_00000011/"),
        ]
        for alt_path in alt_paths:
            if alt_path.exists():
                return alt_path
    return corpus_path


def test_record_export_smoke(test_corpus):
    """Smoke test: record export works end-to-end."""
    if not test_corpus.exists():
        pytest.skip("Test corpus not available")

    session = load(test_corpus)

    # Test record conversion (workflows only)
    from cpmf_uips_xaml.stages.emit.records import workflows_to_records

    workflows = session.workflows()
    if not workflows:
        pytest.skip("No workflows found in test corpus")

    records = workflows_to_records(workflows[:1])  # Test first workflow only
    assert len(records) > 0

    # Validate first record structure
    record = records[0]
    assert record.kind == "workflow"
    assert record.schema_id == "cpmf-uips-xaml://v2/workflow-record"
    assert record.schema_version == "2.0.0"
    assert record.payload is not None

    # Validate payload has required fields
    payload = record.payload
    assert "id" in payload
    assert "name" in payload
    assert "path" in payload
    assert "annotation_tags" in payload
    assert "arguments" in payload
    assert "activity_ids" in payload
    assert "activity_count" in payload
    assert "edges" in payload

    print(f"✓ Record envelope structure valid for workflow: {payload['name']}")


def test_record_serialization(test_corpus):
    """Test record can be serialized to JSON."""
    if not test_corpus.exists():
        pytest.skip("Test corpus not available")

    session = load(test_corpus)

    from dataclasses import asdict

    from cpmf_uips_xaml.stages.emit.records import workflows_to_records

    workflows = session.workflows()
    if not workflows:
        pytest.skip("No workflows found in test corpus")

    records = workflows_to_records(workflows[:1])
    record = records[0]

    # Serialize to JSON
    record_dict = asdict(record)
    json_str = json.dumps(record_dict)

    # Deserialize and validate
    deserialized = json.loads(json_str)
    assert deserialized["kind"] == "workflow"
    assert deserialized["schema_id"] == "cpmf-uips-xaml://v2/workflow-record"
    assert deserialized["schema_version"] == "2.0.0"

    print(f"✓ Record serialization successful")
