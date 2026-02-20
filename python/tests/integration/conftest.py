"""Pytest configuration for integration tests.

Integration tests:
- Use real XAML files from testdata/
- Test end-to-end scenarios
- May be slower (file I/O)
- Test component interactions
"""

from pathlib import Path

import pytest

from cpmf_uips_xaml import XamlParser


@pytest.fixture
def parser():
    """Basic parser fixture."""
    return XamlParser()


@pytest.fixture
def strict_parser():
    """Parser with strict mode enabled."""
    return XamlParser({"strict_mode": True})


@pytest.fixture
def testdata_dir():
    """Path to shared testdata directory."""
    # testdata is at monorepo root, not in python/
    return Path(__file__).parent.parent.parent.parent / "testdata"


@pytest.fixture
def corpus_dir(testdata_dir):
    """Path to small embedded test corpus (testdata/corpus/)."""
    return testdata_dir / "corpus"


@pytest.fixture
def simple_project(corpus_dir):
    """Path to simple test project in testdata."""
    return corpus_dir / "simple_project"


@pytest.fixture
def main_workflow(simple_project):
    """Path to Main.xaml in simple project."""
    return simple_project / "Main.xaml"


@pytest.fixture
def corpus_available(corpus_dir):
    """Check if embedded corpus data is available."""
    return corpus_dir.exists() and (corpus_dir / "simple_project" / "Main.xaml").exists()
