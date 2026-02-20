"""Pytest configuration for XAML parser tests.

This root conftest defines:
- Test markers
- Collection hooks
- Shared fixtures (if any)

Subdirectory-specific fixtures are in:
- unit/conftest.py - Inline XAML fixtures
- integration/conftest.py - testdata/ file fixtures
- corpus/conftest.py - test-corpus/ submodule fixtures
"""

import pytest


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: mark test as a unit test (fast, no I/O)")
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test (uses testdata)"
    )
    config.addinivalue_line(
        "markers", "corpus: mark test as a corpus test (uses test-corpus submodule)"
    )
    config.addinivalue_line("markers", "smoke: mark test as a smoke test (basic robustness)")
    config.addinivalue_line("markers", "requires_corpus: mark test as requiring corpus data")


def pytest_collection_modifyitems(config, items):
    """Automatically mark tests based on their location."""
    for item in items:
        # Auto-mark based on directory structure
        if "/unit/" in str(item.fspath) or "\\unit\\" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "/integration/" in str(item.fspath) or "\\integration\\" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "/corpus/" in str(item.fspath) or "\\corpus\\" in str(item.fspath):
            item.add_marker(pytest.mark.corpus)
            item.add_marker(pytest.mark.requires_corpus)
