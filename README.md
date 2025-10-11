# XAML Parser

Parse UiPath XAML workflow files and extract complete metadata - arguments, variables, activities, expressions, and annotations.

[![License: CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)

## What is this?

A zero-dependency parser for UiPath XAML workflow files. Extract all metadata from automation projects:
- Workflow arguments (inputs/outputs)
- Variables and their scopes
- Activities and their configurations
- Business logic annotations
- VB.NET and C# expressions

**Available in**: Python (stable) | Go (planned)

## Installation

### Python

```bash
pip install xaml-parser
```

Or for development:
```bash
git clone https://github.com/rpapub/xaml-parser.git
cd xaml-parser/python
uv sync
```

## Quick Examples by Use Case

### 1. Extract Workflow Arguments

```python
from pathlib import Path
from xaml_parser import XamlParser

parser = XamlParser()
result = parser.parse_file(Path("Main.xaml"))

if result.success:
    for arg in result.content.arguments:
        print(f"{arg.direction.upper()}: {arg.name} ({arg.type})")
        if arg.annotation:
            print(f"  → {arg.annotation}")
```

**Output:**
```
IN: Config (System.Collections.Generic.Dictionary<String, Object>)
  → Configuration dictionary from orchestrator
OUT: TransactionData (System.Data.DataRow)
  → Current transaction item
```

### 2. List All Activities

```python
result = parser.parse_file(Path("Process.xaml"))

for activity in result.content.activities:
    indent = "  " * activity.depth_level
    print(f"{indent}{activity.tag}: {activity.display_name or '(unnamed)'}")
```

**Output:**
```
Sequence: Process Transaction
  TryCatch: Try Process
    Assign: Set Transaction Data
    InvokeWorkflowFile: Update System
  LogMessage: Transaction Complete
```

### 3. Extract Business Logic Annotations

```python
result = parser.parse_file(Path("workflow.xaml"))

# Root workflow annotation
if result.content.root_annotation:
    print(f"Workflow Purpose: {result.content.root_annotation}")

# Activity annotations
for activity in result.content.activities:
    if activity.annotation:
        print(f"\n{activity.display_name}:")
        print(f"  {activity.annotation}")
```

### 4. Find All Expressions

```python
config = {'extract_expressions': True}
parser = XamlParser(config)
result = parser.parse_file(Path("workflow.xaml"))

for activity in result.content.activities:
    for expr in activity.expressions:
        print(f"{activity.display_name}: {expr.content}")
        print(f"  Language: {expr.language}")
        print(f"  Type: {expr.expression_type}")
```

### 5. Generate Workflow Documentation

```python
import json

result = parser.parse_file(Path("Main.xaml"))

doc = {
    'workflow': result.content.display_name or 'Main',
    'description': result.content.root_annotation,
    'arguments': [
        {
            'name': arg.name,
            'type': arg.type,
            'direction': arg.direction,
            'description': arg.annotation
        }
        for arg in result.content.arguments
    ],
    'activity_count': len(result.content.activities),
    'variable_count': len(result.content.variables)
}

print(json.dumps(doc, indent=2))
```

### 6. Validate Workflow Structure in CI/CD

```python
import sys

result = parser.parse_file(Path("workflow.xaml"))

if not result.success:
    print(f"❌ Parsing failed: {', '.join(result.errors)}")
    sys.exit(1)

# Check for required arguments
required = ['in_Config', 'out_Result']
actual = {arg.name for arg in result.content.arguments}

if not all(req in actual for req in required):
    print(f"❌ Missing required arguments")
    sys.exit(1)

print(f"✅ Workflow valid: {len(result.content.activities)} activities")
```

### 7. Analyze Workflow Dependencies

```python
invocations = []

for activity in result.content.activities:
    if activity.tag == 'InvokeWorkflowFile':
        workflow_path = activity.visible_attributes.get('WorkflowFileName', '')
        invocations.append(workflow_path)

print("Invoked workflows:")
for path in invocations:
    print(f"  - {path}")
```

## What Can You Extract?

### Workflow Arguments
- Name, type, direction (in/out/inout)
- Default values
- Documentation annotations

### Variables
- Name, type, scope
- Default values
- Scoped to workflow or activity

### Activities
- Activity type (Sequence, Assign, If, etc.)
- Display name and annotations
- All properties (visible and ViewState)
- Nested configuration
- Parent-child relationships
- Depth level in tree

### Expressions
- VB.NET and C# expressions
- Expression type (assignment, condition, etc.)
- Variable and method references
- LINQ query detection

### Metadata
- XML namespaces
- Assembly references
- Expression language (VB/C#)
- Parse diagnostics and performance

## Configuration Options

```python
config = {
    'extract_arguments': True,      # Extract workflow arguments
    'extract_variables': True,      # Extract variables
    'extract_activities': True,     # Extract activities
    'extract_expressions': True,    # Parse expressions (slower)
    'extract_viewstate': False,     # Include ViewState data
    'strict_mode': False,           # Fail on any error
    'max_depth': 50,                # Max activity nesting depth
}

parser = XamlParser(config)
```

## Error Handling

The parser handles errors gracefully:

```python
result = parser.parse_file(Path("malformed.xaml"))

if not result.success:
    print("Errors:")
    for error in result.errors:
        print(f"  - {error}")

    print("\nWarnings:")
    for warning in result.warnings:
        print(f"  - {warning}")

# Partial results may still be available
if result.content:
    print(f"\nPartially parsed: {len(result.content.activities)} activities")
```

## Language Support

| Language | Status | Package |
|----------|--------|---------|
| **Python** | ✅ Stable (3.9+) | `xaml-parser` |
| **Go** | 🚧 Planned | `github.com/rpapub/xaml-parser/go` |

## Documentation

- **[Python API Documentation](python/README.md)** - Detailed Python usage
- **[Contributing Guide](CONTRIBUTING.md)** - For developers
- **[Architecture](docs/architecture.md)** - Design decisions
- **[Schemas](schemas/)** - JSON output schemas

## Use Cases

- **Static Analysis** - Extract metadata for code quality tools
- **Documentation** - Auto-generate workflow documentation
- **Migration** - Parse workflows for platform migration
- **CI/CD Validation** - Validate structure in pipelines
- **Code Review** - Extract business logic for review
- **Dependency Analysis** - Map workflow dependencies

## License

[CC-BY 4.0](LICENSE) - Christian Prior-Mamulyan and contributors

**Attribution:**
```
XAML Parser by Christian Prior-Mamulyan, licensed under CC-BY 4.0
Source: https://github.com/rpapub/xaml-parser
```

## Links

- **GitHub**: https://github.com/rpapub/xaml-parser
- **Issues**: https://github.com/rpapub/xaml-parser/issues
- **PyPI**: https://pypi.org/project/xaml-parser/ (planned)

## History

Originally developed as part of the [rpax](https://github.com/rpapub/rpax) automation analysis project.
