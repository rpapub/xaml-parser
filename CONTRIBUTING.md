# Contributing to XAML Parser

Thank you for your interest in contributing to the XAML Parser project! This document provides guidelines and information for contributors.

## Code of Conduct

This project follows a respectful and collaborative approach. Please:
- Be respectful and constructive in all interactions
- Welcome newcomers and help them get started
- Focus on what is best for the community
- Show empathy towards other community members

## How to Contribute

### Reporting Issues

When reporting issues, please include:

1. **Clear description**: What were you trying to do?
2. **Steps to reproduce**: How can we reproduce the issue?
3. **Expected behavior**: What did you expect to happen?
4. **Actual behavior**: What actually happened?
5. **Environment**: OS, Python/Go version, etc.
6. **Sample XAML**: If applicable, provide a minimal XAML sample that demonstrates the issue

### Suggesting Features

Feature suggestions are welcome! Please:

1. Check existing issues to avoid duplicates
2. Clearly describe the feature and its use case
3. Explain how it would benefit users
4. Consider how it fits with the project's goals (zero-dependency, multi-language support)

### Submitting Pull Requests

1. **Fork the repository** and create your branch from `main`
2. **Make your changes** following the coding guidelines below
3. **Add tests** for new functionality
4. **Update documentation** as needed
5. **Ensure tests pass** for all affected implementations
6. **Submit a pull request** with a clear description

## Development Setup

### Python Implementation

```bash
# Clone the repository
git clone https://github.com/rpapub/xaml-parser.git
cd xaml-parser/python

# Install dependencies with uv (recommended)
uv sync

# Or with pip
pip install -e ".[dev]"

# Run tests
uv run pytest tests/ -v

# Format code
uv run black xaml_parser/ tests/
uv run isort xaml_parser/ tests/

# Lint
uv run ruff check xaml_parser/ tests/

# Type check
uv run mypy xaml_parser/
```

### Go Implementation

```bash
cd go

# Get dependencies
go mod download

# Run tests
go test ./...

# Format code
go fmt ./...

# Lint (requires golangci-lint)
golangci-lint run

# Vet
go vet ./...
```

## Coding Guidelines

### Python

- **Style**: Follow PEP 8, enforced by Black and Ruff
- **Type Hints**: Use type hints for all functions and methods
- **Docstrings**: Use Google-style docstrings
- **Imports**: Organized by isort (stdlib, third-party, local)
- **Line Length**: 88 characters (Black default)

```python
def parse_xaml_file(file_path: Path, config: Optional[Dict] = None) -> ParseResult:
    """Parse a XAML workflow file.

    Args:
        file_path: Path to the XAML file to parse
        config: Optional parser configuration dictionary

    Returns:
        ParseResult with workflow content and diagnostics

    Raises:
        FileNotFoundError: If the file does not exist
        ValueError: If the file is not valid XAML
    """
    # Implementation here
```

### Go

- **Style**: Follow Go conventions, enforced by gofmt
- **Comments**: Exported functions must have comments
- **Error Handling**: Return errors, don't panic
- **Testing**: Use table-driven tests where appropriate

```go
// ParseFile parses a XAML workflow file and returns the result.
// Returns an error if the file cannot be read or parsed.
func (p *Parser) ParseFile(filePath string) (*ParseResult, error) {
    // Implementation here
}
```

## Testing Guidelines

### Unit Tests

- Write tests for all new functionality
- Aim for high code coverage (>80%)
- Use descriptive test names
- Test both success and failure cases

### Golden Freeze Tests

When adding new golden freeze tests:

1. **Create XAML file** in `testdata/golden/`
2. **Generate expected output** by running the parser
3. **Manual review** to ensure correctness
4. **Add test cases** in both Python and Go

Example test structure:

```python
# Python
def test_my_feature(golden_dir):
    xaml_path = golden_dir / "my_feature.xaml"
    golden_path = golden_dir / "my_feature.json"

    parser = XamlParser()
    result = parser.parse_file(xaml_path)

    with open(golden_path) as f:
        expected = json.load(f)

    assert result.content == expected
```

```go
// Go
func TestMyFeature(t *testing.T) {
    xamlPath := filepath.Join("..", "..", "testdata", "golden", "my_feature.xaml")
    goldenPath := filepath.Join("..", "..", "testdata", "golden", "my_feature.json")

    parser := New(nil)
    result, err := parser.ParseFile(xamlPath)
    // Assertions here
}
```

### Corpus Tests

For complex scenarios, add complete project structures to `testdata/corpus/`.

## Schema Changes

When modifying JSON schemas in `schemas/`:

1. **Backward Compatibility**: Avoid breaking changes if possible
2. **Versioning**: Follow semantic versioning for schemas
3. **Documentation**: Update `schemas/README.md`
4. **Testing**: Update all golden freeze tests
5. **Cross-Language**: Ensure both Python and Go implementations support the change

### Adding Optional Fields

```json
{
  "properties": {
    "new_field": {
      "type": "string",
      "description": "Description of new field"
    }
  }
}
```

Note: Don't add `new_field` to the `required` array.

### Breaking Changes

Breaking changes require:
- Major version bump
- Update to all golden freeze tests
- Migration guide in documentation
- Deprecation notice (if applicable)

## Documentation

### Code Documentation

- **Python**: Use Google-style docstrings
- **Go**: Follow Go doc conventions
- **Examples**: Include usage examples in docstrings

### README Files

- Keep language-specific READMEs up to date
- Update main README.md for project-wide changes
- Include examples and getting started guides

### Migration Guide

When making breaking changes, document the migration path in `docs/MIGRATION.md`.

## Pull Request Process

1. **Create a branch** with a descriptive name:
   - `feature/add-expression-parser`
   - `fix/annotation-extraction-bug`
   - `docs/update-contributing-guide`

2. **Commit messages** should be clear and descriptive:
   ```
   Add expression parser for VB.NET LINQ queries

   - Implement LINQ detection in expressions
   - Add tests for complex LINQ patterns
   - Update documentation

   Closes #123
   ```

3. **Run all tests** before submitting:
   ```bash
   # Python
   cd python && uv run pytest tests/ -v

   # Go
   cd go && go test ./...
   ```

4. **Update CHANGELOG** (if applicable)

5. **Request review** from maintainers

6. **Address feedback** promptly and professionally

## Release Process

Releases are managed by maintainers:

1. Update version numbers in:
   - `python/pyproject.toml`
   - `python/xaml_parser/__version__.py`
   - `go/go.mod` (future)

2. Update CHANGELOG.md with release notes

3. Create a git tag: `v0.2.0`

4. Build and publish packages:
   - Python: PyPI
   - Go: pkg.go.dev (automatic)

5. Create GitHub release with notes

## Questions?

- **Issues**: https://github.com/rpapub/xaml-parser/issues
- **Discussions**: https://github.com/rpapub/xaml-parser/discussions (if enabled)

## License

By contributing, you agree that your contributions will be licensed under the CC-BY 4.0 License.

## Acknowledgments

Thank you for contributing to XAML Parser! Your contributions help make this project better for everyone.
