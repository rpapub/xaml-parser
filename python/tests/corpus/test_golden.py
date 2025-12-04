"""Golden baseline tests for corpus projects.

These tests compare current parser output against committed baselines
to detect regressions or unintended changes.
"""

import dataclasses
import gzip
import json

import pytest

from cpmf_xaml_parser.project import ProjectParser, project_result_to_dto


@pytest.mark.corpus
@pytest.mark.golden
@pytest.mark.parametrize("project_name", ["CORE_00000001", "CORE_00000010"])
def test_output_matches_golden_baseline(project_name, corpus_root, golden_dir, update_golden):
    """Parser output should match golden reference (or update it)."""
    # Find project
    project_path = corpus_root / f"c25v001_{project_name}"
    assert project_path.exists(), f"Project not found: {project_path}"

    # Parse project
    parser = ProjectParser()
    result = parser.parse_project(project_path)
    dto = project_result_to_dto(result)

    # Convert to comparable format
    actual = dataclasses.asdict(dto)

    # Golden file path
    golden_file = golden_dir / f"{project_name}.json.gz"

    if update_golden or not golden_file.exists():
        # Save new golden baseline
        with gzip.open(golden_file, "wt", encoding="utf-8") as f:
            json.dump(actual, f, indent=2)
        pytest.skip(f"Updated golden baseline for {project_name}")

    # Load golden baseline
    with gzip.open(golden_file, "rt", encoding="utf-8") as f:
        expected = json.load(f)

    # Compare (basic structure check for now)
    assert len(actual["workflows"]) == len(expected["workflows"]), (
        f"Workflow count mismatch: "
        f"got {len(actual['workflows'])}, "
        f"expected {len(expected['workflows'])}"
    )

    # Verify workflow names match
    actual_names = {w["name"] for w in actual["workflows"]}
    expected_names = {w["name"] for w in expected["workflows"]}
    assert actual_names == expected_names, (
        f"Workflow names mismatch: " f"got {actual_names}, " f"expected {expected_names}"
    )

    # Deep comparison using DeepDiff
    from deepdiff import DeepDiff

    # Exclude provenance fields (timestamps change each run)
    exclude_paths = [
        "root['collected_at']",
        "root['provenance']",
        "root['workflows'][*]['collected_at']",
        "root['workflows'][*]['provenance']",
    ]

    diff = DeepDiff(
        expected,
        actual,
        exclude_paths=exclude_paths,
        ignore_order=False,  # Preserve order for deterministic output
        verbose_level=2,
    )

    if diff:
        import pprint

        print("\n[FAIL] Golden baseline mismatch:")
        pprint.pprint(dict(diff), width=120)
        pytest.fail(f"Output differs from golden baseline:\n{diff}")


@pytest.mark.corpus
@pytest.mark.golden
def test_golden_manifest_valid(golden_dir):
    """Golden manifest should be valid and match files."""
    manifest_file = golden_dir / "manifest.json"
    assert manifest_file.exists(), "Golden manifest not found"

    with open(manifest_file) as f:
        manifest = json.load(f)

    assert "baselines" in manifest
    assert len(manifest["baselines"]) > 0

    # Verify all referenced files exist
    for baseline in manifest["baselines"]:
        golden_file = golden_dir / baseline["file"]
        assert golden_file.exists(), f"Golden file missing: {baseline['file']}"
