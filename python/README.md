# XAML Parser - Python Implementation

Python implementation of the XAML workflow parser for automation projects.

## Installation

### From PyPI (when published)

```bash
pip install cpmf-uips-xaml
```

### For Development

```bash
# Clone the repository
git clone https://github.com/rpapub/cpmf-uips-xaml.git
cd cpmf-uips-xaml/python

# Install with uv (recommended)
uv sync

# Or with pip in editable mode
pip install -e .
```

## Quick Start

### Python API

```python
from pathlib import Path
from cpmf_uips_xaml import XamlParser

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
cpmf-uips-xaml project.json
cpmf-uips-xaml /path/to/project.json
cpmf-uips-xaml /path/to/project        # Directory containing project.json

# Show workflow dependency graph
cpmf-uips-xaml project.json --graph

# Parse only entry points (no recursive discovery)
cpmf-uips-xaml project.json --entry-points-only

# Save to file
cpmf-uips-xaml project.json --json -o output.json
```

**Individual Workflow Files:**

```bash
# Parse single workflow
cpmf-uips-xaml Main.xaml

# JSON output
cpmf-uips-xaml Main.xaml --json

# List only arguments
cpmf-uips-xaml Main.xaml --arguments

# Show activity tree
cpmf-uips-xaml Main.xaml --tree

# Process multiple files
cpmf-uips-xaml *.xaml --summary

# Recursive search
cpmf-uips-xaml **/*.xaml --summary
```

**Using with uv (development):**
```bash
uv run cpmf-uips-xaml project.json
uv run cpmf-uips-xaml workflow.xaml
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
from cpmf_uips_xaml import ProjectParser

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
from cpmf_uips_xaml.validation import validate_output

errors = validate_output(result)
if errors:
    print("Validation failed:", errors)
```

## Library API (v0.3.0+)

Starting in v0.3.0, the package provides a stable orchestration API that coordinates parsing, analysis, and output generation. This API is the recommended way to integrate XAML parsing into libraries and tools.

### Architecture

The package follows a layered architecture:

```
Your Application
      ↓
API Layer (orchestration) ← You are here
      ↓
Core, UiPS, Emitters, Views (internal implementation)
```

The API layer provides stable entry points while internal implementation details may change between versions.

### Core API Functions

#### parse_and_analyze_project()

Parse a project and build queryable index in one step:

```python
from pathlib import Path
from cpmf_uips_xaml.api import parse_and_analyze_project

# Parse project and build complete analysis
project_result, analyzer, index = parse_and_analyze_project(
    Path("./MyProject"),
    recursive=True,              # Follow InvokeWorkflowFile references
    entry_points_only=False,     # Parse all workflows, not just entry points
    show_progress=False          # Show progress bars
)

# Access project info
if project_result.project_config:
    print(f"Project: {project_result.project_config.name}")
    print(f"Main workflow: {project_result.project_config.main}")

# Query workflows
workflow_ids = index.list_workflows()
print(f"Total workflows: {len(workflow_ids)}")

# Traverse call graph
for workflow_id in index.list_workflows():
    callees = index.get_callees(workflow_id)
    if callees:
        print(f"{workflow_id} calls: {callees}")
```

#### render_project_view()

Transform analysis results into different view formats:

```python
from cpmf_uips_xaml.api import parse_and_analyze_project, render_project_view

# Parse and analyze
project_result, analyzer, index = parse_and_analyze_project(Path("./MyProject"))

# Render nested view (hierarchical structure)
nested = render_project_view(
    analyzer, index,
    view_type="nested"
)

# Render execution view (call graph traversal from entry point)
execution = render_project_view(
    analyzer, index,
    view_type="execution",
    entry_point="Main.xaml",
    max_depth=10
)

# Render slice view (context window around focal activity)
slice_view = render_project_view(
    analyzer, index,
    view_type="slice",
    focus="LogMessage_abc123",
    radius=2
)
```

#### emit_workflows()

Output workflows in different formats:

```python
from pathlib import Path
from cpmf_uips_xaml.api import parse_and_analyze_project, emit_workflows

# Parse project
project_result, analyzer, index = parse_and_analyze_project(Path("./MyProject"))

# Get workflow DTOs from analyzer
workflows = list(analyzer.workflows.values())

# Emit as JSON
result = emit_workflows(
    workflows,
    format="json",
    output_path=Path("output.json"),
    pretty=True,
    exclude_none=True
)

if result.success:
    print(f"Written {len(result.files_written)} files")
else:
    print(f"Errors: {result.errors}")

# Emit as Mermaid diagram
emit_workflows(
    workflows,
    format="mermaid",
    output_path=Path("output.mmd")
)

# Emit as Markdown documentation
emit_workflows(
    workflows,
    format="doc",
    output_path=Path("output.md")
)
```

Available formats: `json`, `mermaid`, `doc`

#### normalize_parse_results()

Convert raw ParseResult objects to structured WorkflowDto objects:

```python
from pathlib import Path
from cpmf_uips_xaml import XamlParser
from cpmf_uips_xaml.api import normalize_parse_results

# Parse files
parser = XamlParser()
parse_results = [
    parser.parse_file(Path("Main.xaml")),
    parser.parse_file(Path("GetConfig.xaml"))
]

# Normalize to DTOs
workflows = normalize_parse_results(
    parse_results,
    project_dir=Path("./MyProject"),
    sort_output=True,
    calculate_metrics=True,
    detect_anti_patterns=True
)

# Now you have structured DTOs ready for emission or analysis
for workflow in workflows:
    print(f"Workflow: {workflow.name}")
    print(f"  Activities: {len(workflow.activities)}")
    print(f"  Arguments: {len(workflow.arguments)}")
```

#### parse_file_to_dto()

Single-file parsing with DTO normalization:

```python
from pathlib import Path
from cpmf_uips_xaml.api import parse_file_to_dto

# Parse and normalize in one call
workflow = parse_file_to_dto(
    Path("Main.xaml"),
    project_dir=Path("./MyProject")
)

print(f"Workflow: {workflow.name}")
print(f"Activities: {len(workflow.activities)}")
```

#### Configuration Helpers

```python
from cpmf_uips_xaml.api import load_default_config, create_emitter_config

# Load default parser config
config = load_default_config()
print(config)  # Shows default settings

# Create emitter config with overrides
emitter_config = create_emitter_config(
    pretty=True,
    exclude_none=True,
    field_profile="minimal"
)
```

### Complete Example: Project Analysis Pipeline

```python
from pathlib import Path
from cpmf_uips_xaml.api import (
    parse_and_analyze_project,
    render_project_view,
    emit_workflows
)

# 1. Parse and analyze entire project
project_result, analyzer, index = parse_and_analyze_project(
    Path("./MyProject"),
    recursive=True,
    show_progress=True
)

# 2. Generate execution view from main entry point
execution_view = render_project_view(
    analyzer, index,
    view_type="execution",
    entry_point="Main.xaml",
    max_depth=15
)

# 3. Export workflows as JSON
workflows = list(analyzer.workflows.values())
emit_result = emit_workflows(
    workflows,
    format="json",
    output_path=Path("output.json"),
    pretty=True
)

print(f"Analyzed {len(workflows)} workflows")
print(f"Exported to {emit_result.files_written}")
```

### Migration from v0.2.x

If you were using internal APIs that are no longer exported, use direct imports:

```python
# ❌ v0.2.x - No longer works
from cpmf_uips_xaml import XmlUtils, ActivityExtractor

# ✅ v0.3.0+ - Use direct imports if needed
from cpmf_uips_xaml.core.utils import XmlUtils
from cpmf_uips_xaml.core.extractors import ActivityExtractor

# ✅ v0.3.0+ - Or better, use the API layer
from cpmf_uips_xaml.api import parse_and_analyze_project
```

**Recommended approach**: Use the API layer functions instead of reaching into internal modules. The API provides stable contracts while internals may change.

### Data Models (DTOs)

The API works with strongly-typed DTO models for all data exchange:

**Workflow DTOs:**
- `WorkflowDto` - Complete workflow with metadata, activities, edges
- `WorkflowCollectionDto` - Multiple workflows with project context
- `ActivityDto` - Activity with arguments and properties
- `ArgumentDto` - Workflow or activity argument
- `VariableDto` - Workflow variable
- `EdgeDto` - Control flow edge between activities

**Project DTOs:**
- `ProjectInfo` - Project metadata (name, version, dependencies)
- `EntryPointInfo` - Entry point definition
- `ProvenanceInfo` - Parser version and author tracking

**Analysis DTOs:**
- `QualityMetrics` - Workflow quality scores
- `AntiPattern` - Detected anti-patterns
- `IssueDto` - Parse errors or warnings

All DTOs are immutable dataclasses with full type hints.

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

- **Repository**: https://github.com/rpapub/cpmf-uips-xaml
- **Issues**: https://github.com/rpapub/cpmf-uips-xaml/issues
- **PyPI**: https://pypi.org/project/cpmf-uips-xaml/ (coming soon)
