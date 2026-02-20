"""Integration test for record export through full pipeline."""

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


def test_record_renderer_through_pipeline(test_corpus):
    """Test RecordRenderer works through full emit pipeline."""
    if not test_corpus.exists():
        pytest.skip("Test corpus not available")

    from dataclasses import asdict

    from cpmf_uips_xaml.config.models import EmitterConfig
    from cpmf_uips_xaml.stages.emit.renderers.record_renderer import RecordRenderer

    # Load workflows
    session = load(test_corpus)
    workflows = session.workflows()
    if not workflows:
        pytest.skip("No workflows found in test corpus")

    # Create renderer config with kinds
    class SimpleConfig:
        kinds = ["workflow", "activity"]

    config = SimpleConfig()

    # Convert workflows to dicts (as pipeline does)
    workflow_dicts = [asdict(wf) for wf in workflows[:1]]

    # Test render_many through pipeline path
    renderer = RecordRenderer()
    result = renderer.render_many(workflow_dicts, config)

    assert result.success
    assert result.content
    assert "record_count" in result.metadata
    assert result.metadata["record_count"] > 0

    # Parse JSONL output
    lines = result.content.strip().split("\n")
    assert len(lines) > 0

    # Validate each record
    for line in lines:
        record = json.loads(line)
        assert "schema_id" in record
        assert "schema_version" in record
        assert "kind" in record
        assert "payload" in record
        assert record["schema_version"] == "2.0.0"
        assert record["kind"] in ["workflow", "activity"]

    # Parse all records
    all_records = [json.loads(line) for line in lines]

    # Validate workflow record
    workflow_records = [rec for rec in all_records if rec["kind"] == "workflow"]
    if workflow_records:
        wf_record = workflow_records[0]
        assert wf_record["schema_id"] == "cpmf-uips-xaml://v2/workflow-record"
        payload = wf_record["payload"]
        assert "id" in payload
        assert "name" in payload
        assert "path" in payload
        assert "annotation_tags" in payload
        assert "arguments" in payload
        assert "activity_ids" in payload
        assert "activity_count" in payload
        assert "edges" in payload

    # Validate activity records
    activity_records = [rec for rec in all_records if rec["kind"] == "activity"]
    if activity_records:
        act_record = activity_records[0]
        assert act_record["schema_id"] == "cpmf-uips-xaml://v2/activity-record"
        payload = act_record["payload"]
        assert "id" in payload
        assert "workflow_id" in payload
        assert "type" in payload
        assert "depth" in payload
        assert "children" in payload
        assert "annotation_tags" in payload
        assert "properties" in payload

        # Validate properties are strings (Issue #5 fix)
        for key, value in payload["properties"].items():
            assert isinstance(value, str), f"Property {key} must be string, got {type(value)}"

    print(f"✓ Record export through pipeline successful: {result.metadata['record_count']} records")


def test_record_kinds_parameter(test_corpus):
    """Test record export with different kinds combinations."""
    if not test_corpus.exists():
        pytest.skip("Test corpus not available")

    from dataclasses import asdict

    from cpmf_uips_xaml.stages.emit.renderers.record_renderer import RecordRenderer

    session = load(test_corpus)
    workflows = session.workflows()
    if not workflows:
        pytest.skip("No workflows found in test corpus")

    workflow_dicts = [asdict(wf) for wf in workflows[:1]]
    renderer = RecordRenderer()

    # Test workflow-only export
    class WorkflowOnlyConfig:
        kinds = ["workflow"]

    result = renderer.render_many(workflow_dicts, WorkflowOnlyConfig())
    lines = result.content.strip().split("\n")
    kinds = {json.loads(line)["kind"] for line in lines}
    assert kinds == {"workflow"}

    # Test multi-kind export
    class MultiKindConfig:
        kinds = ["workflow", "activity", "argument"]

    result = renderer.render_many(workflow_dicts, MultiKindConfig())
    lines = result.content.strip().split("\n")
    kinds = {json.loads(line)["kind"] for line in lines}
    assert "workflow" in kinds
    # May have activity/argument if workflow has them
    assert len(kinds) >= 1

    print(f"✓ Record kinds parameter works correctly")
