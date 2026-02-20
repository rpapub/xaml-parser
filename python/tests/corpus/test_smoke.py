"""Smoke tests for corpus projects.

These tests verify basic robustness:
- Projects parse without fatal errors
- Workflows have valid structure
- No crashes on real-world data
"""

import pytest

from cpmf_uips_xaml.stages.assemble.project import ProjectParser


@pytest.mark.corpus
@pytest.mark.smoke
def test_all_corpus_projects_parse_without_crash(corpus_projects):
    """All corpus projects should parse without fatal crashes."""
    failures = []

    for project_path in corpus_projects:
        try:
            parser = ProjectParser()
            result = parser.parse_project(project_path)

            if not result:
                failures.append(f"{project_path.name}: No result returned")
            elif result.errors and not result.workflows:
                failures.append(f"{project_path.name}: {result.errors[0]}")

        except Exception as e:
            failures.append(f"{project_path.name}: Crashed with {type(e).__name__}: {e}")

    assert not failures, f"Failed to parse {len(failures)} projects:\n" + "\n".join(failures[:10])


@pytest.mark.corpus
@pytest.mark.smoke
def test_core_projects_parse_successfully(core_projects):
    """CORE projects should parse successfully (guaranteed-to-work)."""
    failures = []

    for project_path in core_projects:
        parser = ProjectParser()
        result = parser.parse_project(project_path)

        if not result.success:
            failures.append(f"{project_path.name}: Parse failed with {len(result.errors)} errors")

    assert not failures, "CORE projects failed:\n" + "\n".join(failures)


@pytest.mark.corpus
@pytest.mark.smoke
def test_workflows_have_valid_structure(core_projects):
    """Parsed workflows should have expected structure."""
    for project_path in core_projects:
        parser = ProjectParser()
        result = parser.parse_project(project_path)

        for wf in result.workflows:
            # File path should exist
            assert wf.file_path.exists(), f"File doesn't exist: {wf.file_path}"

            # Should have relative path
            assert wf.relative_path, f"Missing relative path for {wf.file_path}"

            # Should have parse result
            assert wf.parse_result is not None, f"Missing parse result for {wf.file_path}"

            # If successful, should have content
            if wf.parse_result.success:
                assert (
                    wf.parse_result.content is not None
                ), f"Successful parse has no content: {wf.file_path}"


@pytest.mark.corpus
@pytest.mark.smoke
def test_entry_points_discovered(core_projects):
    """Entry points from project.json should be discovered."""
    for project_path in core_projects:
        parser = ProjectParser()
        result = parser.parse_project(project_path)

        # Should have at least one entry point
        entry_points = result.get_entry_points()
        assert len(entry_points) > 0, f"{project_path.name}: No entry points discovered"

        # All entry points should parse successfully
        for ep in entry_points:
            assert (
                ep.parse_result.success
            ), f"{project_path.name}: Entry point {ep.relative_path} failed to parse"
