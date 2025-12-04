# XAML Parser - Python Implementation

Python implementation of the XAML workflow parser for automation projects.

## Installation

### From PyPI (when published)

```bash
pip install cpmf-cpmf-xaml-parser
```

### For Development

```bash
# Clone the repository
git clone https://github.com/rpapub/cpmf-xaml-parser.git
cd cpmf-xaml-parser/python

# Install with uv (recommended)
uv sync

# Or with pip in editable mode
pip install -e .
```

## Quick Start

### Python API

```python
from pathlib import Path
from cpmf_xaml_parser import XamlParser

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
            print(f"{activity.activity_type}: {activity.annotation}")
else:
    print("Parsing failed:", result.errors)
```

### Command Line Interface

**Project Parsing (Primary Mode):**

```bash
# Parse entire project from project.json
cpmf-xaml-parser project.json
cpmf-xaml-parser /path/to/project.json
cpmf-xaml-parser /path/to/project        # Directory containing project.json

# Show workflow dependency graph
cpmf-xaml-parser project.json --graph

# Parse only entry points (no recursive discovery)
cpmf-xaml-parser project.json --entry-points-only

# Save to file
cpmf-xaml-parser project.json --json -o output.json
```

**Individual Workflow Files:**

```bash
# Parse single workflow
cpmf-xaml-parser Main.xaml

# JSON output
cpmf-xaml-parser Main.xaml --json

# List only arguments
cpmf-xaml-parser Main.xaml --arguments

# Show activity tree
cpmf-xaml-parser Main.xaml --tree

# Process multiple files
cpmf-xaml-parser *.xaml --summary

# Recursive search
cpmf-xaml-parser **/*.xaml --summary
```

**Using with uv (development):**
```bash
uv run cpmf-xaml-parser project.json
uv run cpmf-xaml-parser workflow.xaml
```

**CLI Options:**

*All modes:*
- `--json` - Output as JSON
- `-o FILE` - Write output to file
- `--no-expressions` - Skip expression extraction (faster)
- `--strict` - Fail on any error
- `--help` - Show all options

*Project mode:*
- `--graph` - Show workflow dependency graph
- `--entry-points-only` - Parse only entry points (no recursive discovery)

*File mode:*
- `--arguments` - Show only arguments
- `--activities` - Show only activities
- `--tree` - Show activity tree with nesting
- `--summary` - Summary for multiple files

**Python API for Projects:**

```python
from pathlib import Path
from cpmf_xaml_parser import ProjectParser

# Parse entire project
parser = ProjectParser()
result = parser.parse_project(Path("path/to/project"))

if result.success:
    print(f"Project: {result.project_config.name}")
    print(f"Workflows: {result.total_workflows}")

    # Access entry points
    for workflow in result.get_entry_points():
        print(f"Entry: {workflow.relative_path}")

    # Access dependency graph
    for workflow_path, dependencies in result.dependency_graph.items():
        print(f"{workflow_path} invokes:")
        for dep in dependencies:
            print(f"  -> {dep}")
else:
    print("Project parsing failed:", result.errors)
```

**How it works:**
1. Reads `project.json` to find entry points
2. Parses entry point workflows
3. Recursively discovers workflows via `InvokeWorkflowFile` activities
4. Builds complete dependency graph
5. Returns all workflows with parse results

## Features

- **Minimal Dependencies**: Single required dependency (defusedxml for secure XML parsing)
- **Complete Extraction**: Arguments, variables, activities, expressions, annotations
- **Project Parsing**: Auto-discover and parse entire UiPath projects with dependency analysis
- **Type Safety**: Full type hints for all APIs
- **Error Handling**: Graceful degradation with detailed error reporting
- **Schema Validation**: Output validates against JSON schemas
- **Performance**: Fast parsing even for large workflows
- **CLI Tool**: Full-featured command-line interface for batch processing

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

Main workflow parser class:

```python
parser = XamlParser(config=None)
result = parser.parse_file(Path("workflow.xaml"))
result = parser.parse_content(xaml_string)
```

### ProjectParser

Project-level parser class:

```python
parser = ProjectParser(config=None)
result = parser.parse_project(
    project_dir=Path("path/to/project"),
    recursive=True,              # Follow InvokeWorkflowFile references
    entry_points_only=False      # Only parse entry points
)
```

### Models

Data models for parsed content:

**Workflow Models:**
- `ParseResult`: Top-level result with success/error info
- `WorkflowContent`: Complete workflow metadata
- `WorkflowArgument`: Argument definition
- `WorkflowVariable`: Variable definition
- `Activity`: Activity with full metadata
- `Expression`: Expression with language detection

**Project Models:**
- `ProjectResult`: Complete project parsing result
- `ProjectConfig`: Parsed project.json configuration
- `WorkflowResult`: Individual workflow result in project context

### Validation

Schema-based validation:

```python
from cpmf_xaml_parser.validation import validate_output

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
│   ├── parser.py         # Main workflow parser
│   ├── project.py        # Project parser (NEW)
│   ├── cli.py            # Command-line interface
│   ├── models.py         # Data models
│   ├── extractors.py     # Extraction logic
│   ├── utils.py          # Utilities
│   ├── validation.py     # Schema validation
│   ├── visibility.py     # ViewState handling
│   └── constants.py      # Configuration
├── tests/                # Test suite
│   ├── conftest.py       # Pytest fixtures
│   ├── test_parser.py    # Parser tests
│   ├── test_project.py   # Project parser tests (NEW)
│   ├── test_corpus.py    # Corpus tests
│   └── test_validation.py
├── pyproject.toml        # Package configuration
├── uv.lock               # Dependency lock
└── README.md             # This file
```

## Requirements

- Python 3.11+
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

This project is dual-licensed:

- **Code**: Apache License 2.0 (see [LICENSE-APACHE](LICENSE-APACHE))
- **Documentation & Output**: Creative Commons Attribution 4.0 (see [LICENSE-CC-BY](LICENSE-CC-BY))

You may choose which license applies to your use case.

## Links

- **Repository**: https://github.com/rpapub/cpmf-xaml-parser
- **Issues**: https://github.com/rpapub/cpmf-xaml-parser/issues
- **PyPI**: https://pypi.org/project/cpmf-xaml-parser/ (coming soon)
