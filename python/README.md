# XAML Parser - Python Implementation

Python implementation of the XAML workflow parser for automation projects.

## Installation

### From PyPI (when published)

```bash
pip install xaml-parser
```

### For Development

```bash
# Clone the monorepo
git clone https://github.com/rpapub/xaml-parser.git
cd xaml-parser/python

# Install with uv (recommended)
uv sync

# Or with pip in editable mode
pip install -e .
```

## Quick Start

```python
from pathlib import Path
from xaml_parser import XamlParser

# Parse a workflow file
parser = XamlParser()
result = parser.parse_file(Path("workflow.xaml"))

if result.success:
    content = result.content
    print(f"Workflow: {content.root_annotation}")
    print(f"Arguments: {len(content.arguments)}")
    print(f"Activities: {len(content.activities)}")

    # Access arguments
    for arg in content.arguments:
        print(f"  {arg.direction} {arg.name}: {arg.type}")
        if arg.annotation:
            print(f"    -> {arg.annotation}")

    # Access activities with annotations
    for activity in content.activities:
        if activity.annotation:
            print(f"{activity.tag}: {activity.annotation}")
else:
    print("Parsing failed:", result.errors)
```

## Features

- **Zero Dependencies**: Uses only Python standard library (except defusedxml for security)
- **Complete Extraction**: Arguments, variables, activities, expressions, annotations
- **Type Safety**: Full type hints for all APIs
- **Error Handling**: Graceful degradation with detailed error reporting
- **Schema Validation**: Output validates against JSON schemas
- **Performance**: Fast parsing even for large workflows

## Configuration

```python
config = {
    'extract_expressions': True,
    'extract_viewstate': False,
    'strict_mode': False,
    'max_depth': 50
}

parser = XamlParser(config)
result = parser.parse_file(file_path)
```

## API Reference

### XamlParser

Main parser class:

```python
parser = XamlParser(config=None)
result = parser.parse_file(Path("workflow.xaml"))
result = parser.parse_content(xaml_string)
```

### Models

Data models for parsed content:

- `ParseResult`: Top-level result with success/error info
- `WorkflowContent`: Complete workflow metadata
- `WorkflowArgument`: Argument definition
- `WorkflowVariable`: Variable definition
- `Activity`: Activity with full metadata
- `Expression`: Expression with language detection

### Validation

Schema-based validation:

```python
from xaml_parser.validation import validate_output

errors = validate_output(result)
if errors:
    print("Validation failed:", errors)
```

## Development

### Running Tests

```bash
# Run all tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ --cov=xaml_parser --cov-report=html

# Run specific test file
uv run pytest tests/test_parser.py -v

# Run corpus tests only
uv run pytest tests/test_corpus.py -v -m corpus
```

### Code Quality

```bash
# Format code
uv run black xaml_parser/ tests/

# Sort imports
uv run isort xaml_parser/ tests/

# Lint
uv run ruff check xaml_parser/ tests/

# Type check
uv run mypy xaml_parser/
```

### Building

```bash
# Build distribution
uv build

# Check package
twine check dist/*
```

## Project Structure

```
python/
├── xaml_parser/          # Source package
│   ├── __init__.py       # Public API
│   ├── __version__.py    # Version info
│   ├── parser.py         # Main parser
│   ├── models.py         # Data models
│   ├── extractors.py     # Extraction logic
│   ├── utils.py          # Utilities
│   ├── validation.py     # Schema validation
│   ├── visibility.py     # ViewState handling
│   └── constants.py      # Configuration
├── tests/                # Test suite
│   ├── conftest.py       # Pytest fixtures
│   ├── test_parser.py    # Parser tests
│   ├── test_corpus.py    # Corpus tests
│   └── test_validation.py
├── pyproject.toml        # Package configuration
├── uv.lock               # Dependency lock
└── README.md             # This file
```

## Requirements

- Python 3.9+
- defusedxml (for secure XML parsing)
- pytest (for development)

## Testing Philosophy

Tests reference shared test data in `../testdata/`:

- `../testdata/golden/`: Golden freeze test pairs (XAML + JSON)
- `../testdata/corpus/`: Structured test projects

This ensures consistency across language implementations.

## Contributing

See the main repository [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.

## License

Licensed under CC-BY 4.0. See [LICENSE](../LICENSE) for details.

## Links

- **Monorepo**: https://github.com/rpapub/xaml-parser
- **Issues**: https://github.com/rpapub/xaml-parser/issues
- **PyPI**: https://pypi.org/project/xaml-parser/ (planned)
