"""Test ProjectSession.emit() with record format."""

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


def test_session_emit_record_string_output(test_corpus):
    """Test session.emit('record') returns JSONL string."""
    if not test_corpus.exists():
        pytest.skip("Test corpus not available")

    session = load(test_corpus)

    # Test string output (no output_path)
    result = session.emit("record", kinds=["workflow"])

    # Should return JSONL string
    assert isinstance(result, str)
    assert len(result) > 0

    # Parse JSONL
    lines = result.strip().split("\n")
    assert len(lines) > 0

    # Validate first record
    record = json.loads(lines[0])
    assert record["kind"] == "workflow"
    assert record["schema_id"] == "cpmf-uips-xaml://v2/workflow-record"
    assert record["schema_version"] == "2.0.0"
    assert "payload" in record

    print(f"✓ session.emit('record') string output works: {len(lines)} records")


def test_session_emit_record_with_project(test_corpus):
    """Test session.emit('record') includes project record."""
    if not test_corpus.exists():
        pytest.skip("Test corpus not available")

    session = load(test_corpus)

    # Test with project kind
    result = session.emit("record", kinds=["project", "workflow"])

    # Parse JSONL
    lines = result.strip().split("\n")
    records = [json.loads(line) for line in lines]

    # Should have project and workflow records
    kinds = {rec["kind"] for rec in records}
    assert "workflow" in kinds

    # Check if project record exists
    project_records = [rec for rec in records if rec["kind"] == "project"]
    if project_records:
        project_rec = project_records[0]
        assert project_rec["schema_id"] == "cpmf-uips-xaml://v2/project-record"
        payload = project_rec["payload"]
        assert "name" in payload
        assert "type" in payload
        assert payload["type"] in ("Process", "Library")
        print(f"✓ Project record included: {payload['name']} ({payload['type']})")
    else:
        print("⚠ No project record (project_config may be None)")


def test_session_emit_record_multi_kind(test_corpus):
    """Test session.emit('record') with multiple kinds."""
    if not test_corpus.exists():
        pytest.skip("Test corpus not available")

    session = load(test_corpus)

    # Test multi-kind export
    result = session.emit("record", kinds=["workflow", "activity", "argument"])

    # Parse JSONL
    lines = result.strip().split("\n")
    records = [json.loads(line) for line in lines]

    # Should have multiple kinds
    kinds = {rec["kind"] for rec in records}
    assert "workflow" in kinds

    # May have activity/argument if workflow has them
    if "activity" in kinds:
        activity_recs = [rec for rec in records if rec["kind"] == "activity"]
        assert len(activity_recs) > 0
        print(f"✓ Multi-kind export: {len(records)} total records, {len(kinds)} kinds")
    else:
        print(f"✓ Multi-kind export: {len(records)} total records")


def test_session_emit_record_no_filters(test_corpus):
    """Test that field filters are bypassed for record format."""
    if not test_corpus.exists():
        pytest.skip("Test corpus not available")

    session = load(test_corpus)

    # Emit with minimal field profile (filters would normally apply)
    result = session.emit(
        "record",
        kinds=["workflow"],
        field_profile="minimal",  # Should be ignored for record format
        exclude_none=True,  # Should be ignored for record format
    )

    # Parse first record
    lines = result.strip().split("\n")
    record = json.loads(lines[0])
    payload = record["payload"]

    # Required fields should still be present (not filtered out)
    assert "id" in payload
    assert "name" in payload
    assert "path" in payload
    assert "annotation_tags" in payload
    assert "arguments" in payload
    assert "activity_ids" in payload
    assert "activity_count" in payload
    assert "edges" in payload

    print("✓ Field filters bypassed for record format (schema compliance preserved)")
