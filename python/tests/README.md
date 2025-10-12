# XAML Parser Test Suite

This document describes the testing strategy and organization for the XAML Parser project.

## Test Structure

The test suite is organized into three categories:

```
tests/
├── unit/                # Fast, isolated unit tests
├── integration/         # Integration tests with real XAML files
├── corpus/              # Large-scale corpus tests (test-corpus submodule)
└── conftest.py          # Shared test configuration
```

### Unit Tests (`tests/unit/`)

**Purpose**: Fast, isolated tests of individual functions and classes.

**Characteristics**:
- **Fast**: < 10ms per test
- **No I/O**: No file system access, no network
- **Isolated**: Test single functions/classes in isolation
- **Inline data**: Use inline XAML strings or mocks

**When to add unit tests**:
- Testing individual extractor classes
- Testing utility functions
- Testing data models and DTOs
- Testing validation logic
- Testing ID generation algorithms
- Testing sorting and ordering logic

**Example**:
```python
def test_id_generation_deterministic(simple_xaml):
    """ID generation should be deterministic for same input."""
    parser = XamlParser()
    result1 = parser.parse_string(simple_xaml)
    result2 = parser.parse_string(simple_xaml)
    assert result1.content.activities[0].activity_id == result2.content.activities[0].activity_id
```

**Fixtures**: See `unit/conftest.py` for inline XAML fixtures.

### Integration Tests (`tests/integration/`)

**Purpose**: Test component interactions and end-to-end scenarios.

**Characteristics**:
- **Medium speed**: Acceptable file I/O overhead
- **Real files**: Use actual XAML files from `testdata/`
- **Component interaction**: Test how components work together
- **Realistic scenarios**: Test real-world use cases

**When to add integration tests**:
- Testing parser with real XAML files
- Testing project-level parsing
- Testing emitters (JSON, Markdown, Mermaid)
- Testing control flow extraction from complete workflows
- Testing end-to-end scenarios

**Example**:
```python
def test_project_parsing_complete(simple_project, parser):
    """Complete project should parse successfully."""
    from xaml_parser.project import ProjectParser
    project_parser = ProjectParser()
    result = project_parser.parse_project(simple_project)
    assert result.success
    assert len(result.workflows) > 0
```

**Fixtures**: See `integration/conftest.py` for testdata file fixtures.

### Corpus Tests (`tests/corpus/`)

**Purpose**: Large-scale testing against real-world UiPath projects.

**Characteristics**:
- **Slow**: Can take several seconds
- **Real projects**: Uses `test-corpus/` git submodule
- **Regression testing**: Golden baseline comparisons
- **Robustness**: Smoke tests to ensure no crashes

**When to add corpus tests**:
- Testing against new corpus projects
- Adding golden baseline tests for output format stability
- Adding smoke tests for robustness

**Example**:
```python
@pytest.mark.corpus
@pytest.mark.smoke
def test_core_projects_parse_successfully(core_projects):
    """CORE projects should parse without errors."""
    failures = []
    for project_path in core_projects:
        parser = ProjectParser()
        result = parser.parse_project(project_path)
        if not result.success:
            failures.append(f"{project_path.name}: {result.errors}")
    assert not failures, f"Failed projects:\n" + "\n".join(failures)
```

**Fixtures**: See `corpus/conftest.py` for corpus-specific fixtures.

---

## Running Tests

### Quick Development Workflow

```bash
# Fast feedback during development (unit tests only)
pytest tests/unit/

# With coverage
pytest tests/unit/ --cov=xaml_parser --cov-report=term-missing
```

### Full Test Suite

```bash
# All tests except corpus (default)
pytest

# Specific test categories
pytest tests/unit/              # Unit tests only
pytest tests/integration/       # Integration tests only
pytest tests/corpus/            # Corpus tests only

# Run with specific markers
pytest -m unit                  # Only unit tests
pytest -m integration           # Only integration tests
pytest -m "not corpus"          # Exclude corpus tests (default)
```

### Corpus Tests

Corpus tests require the `test-corpus` git submodule:

```bash
# Initialize corpus submodule (one-time)
git submodule update --init

# Run corpus tests
pytest tests/corpus/ -m corpus

# Update golden baselines
pytest tests/corpus/ -m golden --update-golden
```

---

## Test Markers

Tests are automatically marked based on directory location:

| Marker | Description | Auto-applied to |
|--------|-------------|-----------------|
| `@pytest.mark.unit` | Fast, isolated unit tests | `tests/unit/` |
| `@pytest.mark.integration` | Integration tests with real files | `tests/integration/` |
| `@pytest.mark.corpus` | Corpus tests (slow) | `tests/corpus/` |
| `@pytest.mark.smoke` | Basic robustness tests | Manual |
| `@pytest.mark.golden` | Golden baseline tests | Manual |

### Running by Marker

```bash
pytest -m unit                   # Run only unit tests
pytest -m "unit or integration"  # Run unit and integration
pytest -m "not corpus"           # Exclude corpus tests (default)
pytest -m smoke                  # Run smoke tests only
```

---

## Test Data

### Inline XAML Strings (`unit/conftest.py`)

**When to use**: Unit tests that need minimal XAML snippets.

**Available fixtures**:
- `simple_xaml` - Minimal valid XAML
- `xaml_with_argument` - XAML with single argument
- `xaml_with_variable` - XAML with variable
- `xaml_with_activities` - XAML with multiple activities
- `malformed_xaml` - Invalid XAML for error testing
- `empty_xaml` - Minimal empty XAML

**Example**:
```python
def test_parse_simple_xaml(simple_xaml):
    parser = XamlParser()
    result = parser.parse_string(simple_xaml)
    assert result.success
```

### Test Data Files (`testdata/corpus/`)

**When to use**: Integration tests that need complete, realistic XAML files.

**Location**: `<repo-root>/testdata/corpus/`

**Available fixtures** (`integration/conftest.py`):
- `testdata_dir` - Root testdata directory
- `corpus_dir` - Path to testdata/corpus/
- `simple_project` - Small test project
- `main_workflow` - Path to Main.xaml

**Example**:
```python
def test_parse_real_workflow(main_workflow, parser):
    result = parser.parse_file(main_workflow)
    assert result.success
```

### Test Corpus Submodule (`test-corpus/`)

**When to use**: Corpus tests for regression and robustness.

**Location**: `<repo-root>/test-corpus/` (git submodule)

**Available fixtures** (`corpus/conftest.py`):
- `corpus_root` - Root of test-corpus/
- `corpus_projects` - All corpus projects
- `core_projects` - CORE category projects (guaranteed to work)
- `golden_dir` - Directory for golden baseline files
- `artifacts_dir` - Directory for test artifacts

**Example**:
```python
@pytest.mark.corpus
def test_all_projects_parse(corpus_projects):
    for project in corpus_projects:
        parser = ProjectParser()
        result = parser.parse_project(project)
        assert result is not None  # Should not crash
```

---

## Coverage Requirements

**Target**: 90% overall coverage

**Current Status**: See coverage report after running tests

**Priority modules** (should have >80% coverage):
- `parser.py` - Core parsing logic
- `extractors.py` - Content extraction
- `validation.py` - Output validation
- `normalization.py` - DTO normalization
- `id_generation.py` - Stable ID generation

**Viewing coverage**:
```bash
# Generate coverage report
pytest --cov=xaml_parser --cov-report=html

# Open in browser
start htmlcov/index.html  # Windows
open htmlcov/index.html   # macOS
```

---

## Writing New Tests

### Decision Tree

1. **Does your test need real XAML files?**
   - **No** → `tests/unit/` (use inline XAML fixtures)
   - **Yes** → Continue to 2

2. **Does your test use the test-corpus submodule?**
   - **Yes** → `tests/corpus/`
   - **No** → `tests/integration/` (use testdata fixtures)

3. **Is it a smoke/robustness test?**
   - **Yes** → Add `@pytest.mark.smoke`
   - **No** → Use auto-markers from directory

### Test Naming Conventions

```python
# Good names (descriptive, clear intent)
def test_parser_handles_missing_namespaces():
def test_id_generation_is_deterministic():
def test_emitter_creates_valid_json():

# Bad names (vague, unclear)
def test_parser():
def test_something():
def test_case1():
```

### Test Structure (AAA Pattern)

```python
def test_parser_extracts_arguments(xaml_with_argument):
    # Arrange
    parser = XamlParser()

    # Act
    result = parser.parse_string(xaml_with_argument)

    # Assert
    assert result.success
    assert len(result.content.arguments) == 1
    assert result.content.arguments[0].name == "in_TestArg"
```

---

## Common Tasks

### Adding a New Unit Test

1. Create test in `tests/unit/test_<module>.py`
2. Use inline XAML fixtures from `unit/conftest.py`
3. Test will be auto-marked with `@pytest.mark.unit`

### Adding a New Integration Test

1. Create test in `tests/integration/test_<feature>.py`
2. Use testdata fixtures from `integration/conftest.py`
3. Test will be auto-marked with `@pytest.mark.integration`

### Adding a New Corpus Test

1. Create test in `tests/corpus/test_<scenario>.py`
2. Use corpus fixtures from `corpus/conftest.py`
3. Add `@pytest.mark.corpus` decorator
4. Test will be skipped if corpus submodule not initialized

### Updating Golden Baselines

```bash
# Update all golden baselines
pytest tests/corpus/ -m golden --update-golden

# Review changes
git diff tests/corpus/golden/

# Commit if changes are expected
git add tests/corpus/golden/
git commit -m "Update golden baselines after X change"
```

---

## Continuous Integration

**Default CI behavior**:
- Runs all unit tests
- Runs all integration tests
- **Skips corpus tests** (too slow for every PR)

**Nightly/Weekly CI**:
- Runs full test suite including corpus
- Updates coverage reports
- Checks for regressions in golden baselines

---

## Troubleshooting

### "No corpus data available" error

```bash
# Initialize the corpus submodule
git submodule update --init

# If already initialized, update it
git submodule update --remote
```

### Tests fail after moving files

```bash
# Clear pytest cache
rm -rf .pytest_cache __pycache__

# Reinstall package in development mode
uv pip install -e .
```

### Coverage is too low

1. Check which modules have low coverage:
   ```bash
   pytest --cov=xaml_parser --cov-report=term-missing
   ```

2. Add unit tests for uncovered lines

3. Focus on critical modules first (parser, extractors, validation)

---

## Best Practices

1. **Keep unit tests fast** - If a test takes >100ms, consider moving to integration
2. **Use appropriate fixtures** - Don't use file fixtures in unit tests
3. **Test edge cases** - Empty inputs, None values, malformed data
4. **Test error paths** - Not just happy paths
5. **Use descriptive names** - Test name should describe what it tests
6. **One assertion per concept** - Multiple asserts OK if testing one concept
7. **Avoid test interdependence** - Each test should be independent
8. **Use parametrize** - For testing variations of same scenario
9. **Document complex tests** - Add docstrings explaining what's being tested
10. **Keep tests maintainable** - Refactor test code like production code

---

## References

- [Pytest Documentation](https://docs.pytest.org/)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [Test Pyramid](https://martinfowler.com/articles/practical-test-pyramid.html)
- [AAA Pattern](https://automationpanda.com/2020/07/07/arrange-act-assert-a-pattern-for-writing-good-tests/)

---

## Questions?

See the main project README or open an issue on GitHub.
