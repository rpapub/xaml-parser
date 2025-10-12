"""Pytest fixtures for corpus tests."""

from pathlib import Path

import pytest

# Path constants
CORPUS_ROOT = Path(__file__).parent.parent.parent.parent / "test-corpus"
GOLDEN_DIR = Path(__file__).parent / "golden"
ARTIFACTS_DIR = Path(__file__).parent.parent.parent.parent / ".test-artifacts" / "python"


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--update-golden",
        action="store_true",
        default=False,
        help="Update golden baseline files instead of comparing",
    )


@pytest.fixture(scope="session")
def corpus_root():
    """Root directory of test corpus (git submodule)."""
    if not CORPUS_ROOT.exists():
        pytest.skip("Test corpus not available (run: git submodule update --init)")
    return CORPUS_ROOT


@pytest.fixture(scope="session")
def golden_dir():
    """Directory containing golden baseline files."""
    return GOLDEN_DIR


@pytest.fixture(scope="session")
def artifacts_dir():
    """Directory for ephemeral test artifacts."""
    artifacts_dir = ARTIFACTS_DIR
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    return artifacts_dir


@pytest.fixture(scope="session")
def corpus_projects(corpus_root):
    """Discover all corpus projects (c25v001_*)."""
    projects = []
    for project_json in sorted(corpus_root.glob("c25*/project.json")):
        projects.append(project_json.parent)

    if not projects:
        pytest.skip("No corpus projects found in test-corpus/")

    return projects


@pytest.fixture(scope="session")
def core_projects(corpus_projects):
    """Filter to only CORE category projects."""
    return [p for p in corpus_projects if "CORE" in p.name]


@pytest.fixture
def update_golden(request):
    """Check if --update-golden flag was passed."""
    return request.config.getoption("--update-golden")
