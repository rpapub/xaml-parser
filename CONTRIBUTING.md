# Contributing to XAML Parser

Thank you for your interest in contributing! This guide covers everything you need to know to develop, test, and contribute to the XAML Parser project.

## Code of Conduct

- Be respectful and constructive
- Welcome newcomers and help them get started
- Focus on what is best for the community
- Show empathy towards other contributors

## How to Contribute

### Reporting Issues

Include:
1. **Clear description** - What were you trying to do?
2. **Steps to reproduce** - How can we reproduce it?
3. **Expected vs actual behavior**
4. **Environment** - OS, Python/Go version
5. **Sample XAML** - Minimal example demonstrating the issue

### Suggesting Features

Before suggesting:
1. Check existing issues for duplicates
2. Describe the use case clearly
3. Explain how it benefits users
4. Consider fit with project goals (zero-dependency, multi-language)

### Submitting Pull Requests

1. Fork and create branch from `main`
2. Follow coding guidelines below
3. Add tests for new functionality
4. Update documentation
5. Ensure all tests pass
6. Submit PR with clear description

## Repository Structure

```
xaml-parser/                  # Monorepo root
├── python/                   # Python implementation
│   ├── xaml_parser/          # Source package
│   │   ├── __init__.py       # Public API
│   │   ├── parser.py         # Main parser
│   │   ├── models.py         # Data models
│   │   ├── extractors.py     # Extraction logic
│   │   ├── utils.py          # Utilities
│   │   ├── validation.py     # Schema validation
│   │   └── constants.py      # Configuration
│   ├── tests/                # Python tests
│   │   ├── conftest.py       # Pytest fixtures
│   │   ├── test_parser.py    # Parser tests
│   │   └── test_corpus.py    # Corpus tests
│   ├── pyproject.toml        # Package config
│   └── README.md             # Python docs
├── go/                       # Go implementation (planned)
│   ├── parser/               # Go package
│   │   ├── models.go         # Data structures
│   │   ├── parser.go         # Parser implementation
│   │   └── parser_test.go    # Tests
│   ├── go.mod                # Go module
│   └── README.md             # Go docs
├── testdata/                 # Shared test corpus
│   ├── golden/               # Golden freeze tests
│   │   ├── *.xaml            # Input XAML files
│   │   └── *.json            # Expected JSON output
│   └── corpus/               # Realistic projects
│       ├── simple_project/   # Basic UiPath project
│       └── edge_cases/       # Error conditions
├── schemas/                  # JSON schemas
│   ├── parse_result.schema.json
│   └── workflow_content.schema.json
├── docs/                     # Documentation
│   ├── MIGRATION.md          # Migration history
│   └── architecture.md       # Design docs
├── LICENSE                   # CC-BY 4.0
├── README.md                 # User documentation
└── CONTRIBUTING.md           # This file
```

## Development Setup

### Python

```bash
# Clone repository
git clone https://github.com/rpapub/xaml-parser.git
cd xaml-parser/python

# Install with uv (recommended)
uv sync

# Or with pip
pip install -e ".[dev]"

# Run tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ --cov=xaml_parser --cov-report=html

# Format code
uv run black xaml_parser/ tests/
uv run isort xaml_parser/ tests/

# Lint
uv run ruff check xaml_parser/ tests/

# Type check
uv run mypy xaml_parser/
```

### Go

```bash
cd go

# Download dependencies
go mod download

# Run tests
go test ./...

# Run with verbose output
go test -v ./...

# Format code
go fmt ./...

# Lint (requires golangci-lint)
golangci-lint run

# Vet code
go vet ./...
```

## Test Data Organization

### Golden Freeze Tests (`testdata/golden/`)

Reference test pairs with known-good output:
- `simple_sequence.xaml` + `simple_sequence.json`
- `complex_workflow.xaml` + `complex_workflow.json`
- `invoke_workflows.xaml` + `invoke_workflows.json`
- `ui_automation.xaml` + `ui_automation.json`

**Purpose:**
- Regression testing - detect unintended changes
- Cross-language validation - ensure Python and Go match
- Schema compliance - validate against JSON schemas
- Performance benchmarks - track parsing speed

**Adding golden tests:**
1. Create XAML file in `testdata/golden/`
2. Run parser to generate JSON output
3. **Manually review** output for correctness
4. Save as `<name>.json` in `testdata/golden/`
5. Add test case in both Python and Go
6. Commit XAML and JSON together

### Corpus Tests (`testdata/corpus/`)

Complete project structures for realistic testing:

**`simple_project/`** - Basic UiPath project
- Main.xaml with arguments and variables
- Invoked workflows in `workflows/`
- project.json configuration

**`edge_cases/`** - Error conditions
- `malformed.xaml` - Invalid XML
- `empty.xaml` - Minimal workflow

**Adding corpus tests:**
1. Create directory in `testdata/corpus/`
2. Add complete project structure
3. Include project.json if applicable
4. Update `testdata/README.md`
5. Add test cases using the corpus

### Test Data Access

**Python:**
```python
# In conftest.py
testdata_dir = Path(__file__).parent.parent / "testdata"
golden_dir = testdata_dir / "golden"
corpus_dir = testdata_dir / "corpus"

# In tests
def test_golden(golden_dir):
    xaml = golden_dir / "simple_sequence.xaml"
    golden = golden_dir / "simple_sequence.json"
    # ...
```

**Go:**
```go
testdataDir := filepath.Join("..", "..", "testdata", "golden")
xamlPath := filepath.Join(testdataDir, "simple_sequence.xaml")
goldenPath := filepath.Join(testdataDir, "simple_sequence.json")
```

## Coding Guidelines

### Python

**Style:**
- Follow PEP 8
- Use Black (88 char line length)
- Organize imports with isort (stdlib, third-party, local)
- Type hints for all functions

**Example:**
```python
from typing import Optional
from pathlib import Path

def parse_workflow(
    file_path: Path,
    config: Optional[dict] = None
) -> ParseResult:
    """Parse a XAML workflow file.

    Args:
        file_path: Path to XAML file
        config: Optional parser configuration

    Returns:
        ParseResult with workflow content

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If XAML is invalid
    """
    # Implementation
```

### Go

**Style:**
- Follow Go conventions
- Use gofmt for formatting
- Comment all exported functions
- Return errors, don't panic

**Example:**
```go
// ParseFile parses a XAML workflow file.
// Returns an error if the file cannot be read or parsed.
func (p *Parser) ParseFile(filePath string) (*ParseResult, error) {
    data, err := os.ReadFile(filePath)
    if err != nil {
        return nil, fmt.Errorf("failed to read file: %w", err)
    }
    // Implementation
}
```

## Testing Guidelines

### Unit Tests

- Test all new functionality
- Aim for >80% code coverage
- Use descriptive test names
- Test success and failure cases

**Python example:**
```python
def test_parse_valid_workflow(parser):
    """Test parsing a valid XAML workflow."""
    result = parser.parse_content(VALID_XAML)

    assert result.success
    assert len(result.content.arguments) == 2
    assert result.content.arguments[0].name == "in_Config"
```

**Go example:**
```go
func TestParseValidWorkflow(t *testing.T) {
    parser := New(nil)
    result, err := parser.ParseContent(validXAML, nil)

    if err != nil {
        t.Fatalf("unexpected error: %v", err)
    }

    if !result.Success {
        t.Error("expected success to be true")
    }
}
```

### Integration Tests

Use golden freeze tests for integration:

```python
def test_simple_sequence_golden(golden_dir):
    """Test against golden freeze data."""
    xaml_path = golden_dir / "simple_sequence.xaml"
    golden_path = golden_dir / "simple_sequence.json"

    parser = XamlParser()
    result = parser.parse_file(xaml_path)

    with open(golden_path) as f:
        expected = json.load(f)

    assert result.content.to_dict() == expected['content']
```

### Test Markers

Python tests use pytest markers:
- `@pytest.mark.slow` - Long-running tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.corpus` - Tests requiring corpus data

Run specific markers:
```bash
pytest -m "not slow"  # Skip slow tests
pytest -m corpus      # Run only corpus tests
```

## Schema Changes

JSON schemas in `schemas/` define the API contract.

### Adding Optional Fields

Safe - doesn't break existing code:

```json
{
  "properties": {
    "new_field": {
      "type": "string",
      "description": "New optional field"
    }
  }
}
```

Do NOT add to `required` array.

### Breaking Changes

Require careful handling:
1. **Major version bump** (0.1.0 → 1.0.0)
2. **Update all golden tests** with new format
3. **Update both implementations** (Python and Go)
4. **Document migration** in `docs/MIGRATION.md`
5. **Deprecation notice** if removing fields

**Process:**
1. Discuss in issue first
2. Update schema with new version
3. Update implementations
4. Update all test data
5. Update documentation
6. Create PR with full context

## Pull Request Process

### 1. Branch Naming

```bash
feature/add-expression-analysis    # New feature
fix/annotation-extraction-bug      # Bug fix
docs/update-api-examples           # Documentation
refactor/simplify-parser-logic     # Refactoring
```

### 2. Commit Messages

```
Add expression analysis for VB.NET LINQ queries

- Implement LINQ pattern detection
- Add tests for complex query expressions
- Update documentation with examples

Closes #123
```

### 3. Before Submitting

```bash
# Python
cd python
uv run pytest tests/ -v
uv run black xaml_parser/ tests/
uv run ruff check xaml_parser/
uv run mypy xaml_parser/

# Go
cd go
go test ./...
go fmt ./...
go vet ./...
```

### 4. PR Description

Include:
- What changed and why
- How to test the changes
- Any breaking changes
- Related issues

### 5. Review Process

- Maintainers will review
- Address feedback promptly
- Update tests if requested
- Squash commits if asked

## Release Process

For maintainers:

### 1. Version Bump

Update version in:
- `python/pyproject.toml`
- `python/xaml_parser/__version__.py`
- `go/go.mod` (future)

### 2. Update CHANGELOG

```markdown
## [0.2.0] - 2024-01-15

### Added
- Expression analysis for VB.NET LINQ
- Support for nested workflow invocations

### Fixed
- Annotation extraction for deeply nested activities

### Changed
- Improved error messages for malformed XAML
```

### 3. Create Tag

```bash
git tag -a v0.2.0 -m "Release version 0.2.0"
git push origin v0.2.0
```

### 4. Build and Publish

**Python:**
```bash
cd python
uv build
twine upload dist/*
```

**Go:**
Automatic via pkg.go.dev when tagged.

### 5. GitHub Release

Create release on GitHub with:
- Tag version
- Release notes from CHANGELOG
- Links to documentation

## Questions?

- **Issues**: https://github.com/rpapub/xaml-parser/issues
- **Discussions**: https://github.com/rpapub/xaml-parser/discussions

## License

By contributing, you agree your contributions will be licensed under CC-BY 4.0.

---

Thank you for contributing to XAML Parser!
