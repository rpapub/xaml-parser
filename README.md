# XAML Parser

Standalone XAML workflow parser for automation projects with multi-language implementations.

[![License: CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)

## Overview

XAML Parser is a robust, zero-dependency parser for UiPath XAML workflow files, providing complete metadata extraction from automation projects. This monorepo supports implementations in multiple languages with a shared test corpus ensuring consistency across implementations.

### Key Features

- **Complete metadata extraction** from XAML workflow files
- **Arguments** with types, directions, and annotations
- **Variables** from all workflow scopes
- **Activities** with full property analysis (visible and invisible)
- **Annotations** and documentation text
- **Expressions** with language detection (VB.NET, C#)
- **Zero dependencies** - uses only standard libraries
- **Graceful error handling** with detailed diagnostics

## Implementation Status

| Language | Status | Location | Package |
|----------|--------|----------|---------|
| **Python** | ✅ Stable | [`python/`](python/) | `xaml-parser` |
| **Go** | 🚧 Planned | [`go/`](go/) | `github.com/rpapub/xaml-parser/go` |

## Quick Start

### Python

```bash
# Install
pip install xaml-parser

# Or for development
cd python
uv sync
```

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
else:
    print("Parsing failed:", result.errors)
```

See [Python README](python/README.md) for detailed documentation.

### Go (Coming Soon)

```go
// Future API
import "github.com/rpapub/xaml-parser/go/parser"

p := parser.New()
result, err := p.ParseFile("workflow.xaml")
if err != nil {
    log.Fatal(err)
}

fmt.Printf("Arguments: %d\n", len(result.Content.Arguments))
```

## Repository Structure

```
xaml-parser/
├── python/              # Python implementation
│   ├── xaml_parser/     # Source package
│   └── tests/           # Python tests
├── go/                  # Go implementation (planned)
│   └── parser/          # Go package
├── testdata/            # Shared test corpus
│   ├── golden/          # Golden freeze test pairs
│   └── corpus/          # Structured test projects
├── schemas/             # JSON schemas for output validation
├── docs/                # Documentation
│   ├── MIGRATION.md     # Migration plan and history
│   └── ...
└── README.md            # This file
```

## Test Data

The monorepo includes a comprehensive test corpus shared across all language implementations:

- **Golden Freeze Tests**: XAML files with expected JSON output for validation
- **Corpus Tests**: Complete UiPath project structures for realistic testing
- **Edge Cases**: Malformed files, empty workflows, encoding variations

See [`testdata/README.md`](testdata/README.md) for details.

## Data Models

### WorkflowContent

Main result containing all extracted metadata:
- `arguments`: List of WorkflowArgument objects
- `variables`: List of WorkflowVariable objects
- `activities`: List of Activity objects
- `root_annotation`: Main workflow description
- `namespaces`: XML namespace mappings
- `expression_language`: VB.NET or C#

### WorkflowArgument

Workflow parameter definition:
- `name`: Argument name
- `type`: Full .NET type signature
- `direction`: 'in', 'out', or 'inout'
- `annotation`: Documentation text
- `default_value`: Default value expression

### Activity

Complete activity representation:
- `tag`: Activity type (Sequence, LogMessage, etc.)
- `display_name`: User-friendly name
- `annotation`: Business logic description
- `visible_attributes`: User-configured properties
- `invisible_attributes`: Technical ViewState data
- `configuration`: Nested element structure
- `expressions`: All expressions in activity

## Supported XAML Features

- **Arguments**: InArgument, OutArgument, InOutArgument with annotations
- **Variables**: All scoped variables with types and defaults
- **Activities**: Complete activity tree with properties
- **Annotations**: Business logic documentation on all elements
- **Expressions**: VB.NET and C# expressions with LINQ, lambdas, method calls
- **ViewState**: UI metadata for studio presentation
- **Assembly References**: External library dependencies

## Schema-Driven Validation

The parser output conforms to strict JSON schemas defined in [`schemas/`](schemas/):

- `parse_result.schema.json`: Top-level parse result structure
- `workflow_content.schema.json`: Workflow content and nested objects

These schemas serve as the contract between language implementations and guarantee consistent output.

## Architecture

The parser is designed for modularity and reusability:

- **Parser**: Main parsing orchestration
- **Models**: Data structures for workflow elements
- **Extractors**: Specialized extraction logic for different XAML elements
- **Validators**: Schema-based output validation
- **Utils**: Helper functions and common operations

See [Architecture Documentation](docs/architecture.md) for design details.

## Contributing

We welcome contributions in any supported language! See [CONTRIBUTING.md](CONTRIBUTING.md) for:

- Development setup for Python and Go
- Test data contribution guidelines
- Schema update process
- Pull request guidelines

## Development

### Prerequisites

**Python**:
- Python 3.9+
- [uv](https://github.com/astral-sh/uv) for dependency management

**Go** (future):
- Go 1.21+

### Running Tests

**Python**:
```bash
cd python
uv run pytest tests/ -v
```

**Go** (future):
```bash
cd go
go test ./...
```

### Building

**Python**:
```bash
cd python
uv build
```

## Use Cases

- **Static Analysis**: Extract workflow metadata for analysis tools
- **Documentation Generation**: Auto-generate documentation from workflows
- **Migration Tools**: Parse legacy workflows for migration to new platforms
- **CI/CD Validation**: Validate workflow structure in automated pipelines
- **Code Review**: Extract business logic for human review
- **Dependency Analysis**: Map workflow dependencies and invocations

## Project History

This parser was originally developed as part of the [rpax](https://github.com/rpapub/rpax) project and has been extracted into a standalone monorepo to support multi-language implementations and broader reusability.

## License

This project is licensed under the [Creative Commons Attribution 4.0 International License (CC-BY 4.0)](LICENSE).

When using this package, please include the following attribution:

```
XAML Parser by Christian Prior-Mamulyan and contributors, licensed under CC-BY 4.0
Source: https://github.com/rpapub/xaml-parser
```

## Author

Christian Prior-Mamulyan <cprior@gmail.com>

## Links

- **Repository**: https://github.com/rpapub/xaml-parser
- **Python Package**: https://pypi.org/project/xaml-parser/ (planned)
- **Issues**: https://github.com/rpapub/xaml-parser/issues
- **Documentation**: [docs/](docs/)

## Acknowledgments

Originally developed as part of the rpax automation analysis project.
