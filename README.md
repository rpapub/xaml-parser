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
pip install cpmf-xaml-parser
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
from cpmf_xaml_parser import XamlParser

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

## Advanced: Graph-Based Analysis & Multi-View Output

**New in v2.0**: Transform parsed workflows into queryable graph structures with multiple output views.

### Project-Level Analysis

Parse entire UiPath projects and analyze call graphs, control flow, and activity relationships:

```python
from pathlib import Path
from cpmf_xaml_parser import ProjectParser, analyze_project

# Parse entire project
parser = ProjectParser()
project_result = parser.parse_project(Path("MyProject"), recursive=True)

# Build queryable graph structures
index = analyze_project(project_result)

# Query the project
print(f"Total workflows: {index.total_workflows}")
print(f"Total activities: {index.activities.node_count()}")
print(f"Entry points: {len(index.entry_points)}")

# Find circular dependencies
cycles = index.find_call_cycles()
if cycles:
    print(f"Warning: Found {len(cycles)} circular call chains")
```

### Multi-View Output

Generate different representations of the same project:

#### 1. Flat View (Default, Backward Compatible)

```python
from cpmf_xaml_parser.views import FlatView

view = FlatView()
output = view.render(index)
# Returns traditional flat list of workflows
```

#### 2. Execution View (Call Graph Traversal)

Follow the execution path from an entry point, showing nested invocations:

```python
from cpmf_xaml_parser.views import ExecutionView

# Start from entry point workflow
entry_workflow_id = index.entry_points[0]
view = ExecutionView(entry_point=entry_workflow_id, max_depth=10)
output = view.render(index)

# Output shows:
# - Call depth for each workflow
# - Nested activities (callee activities under InvokeWorkflowFile)
# - Execution order from entry to leaves
```

**Use case**: Understand what actually runs when you start from Main.xaml

#### 3. Slice View (Context Window for LLM)

Extract focused context around a specific activity:

```python
from cpmf_xaml_parser.views import SliceView

# Focus on a specific activity
focal_activity_id = "act:sha256:abc123def456"
view = SliceView(focus=focal_activity_id, radius=2)
output = view.render(index)

# Output includes:
# - The focal activity
# - Parent chain (root to focal)
# - Siblings (same parent)
# - Context activities within radius
```

**Use case**: Provide relevant context to LLMs without overwhelming token limits

### CLI Usage with Views

```bash
# Parse project with flat view (default)
uv run xaml-parser project.json --dto --json

# Execution view from entry point
uv run xaml-parser project.json --dto --json \
  --view execution \
  --entry "wf:sha256:abc123def456"

# Slice view around specific activity
uv run xaml-parser project.json --dto --json \
  --view slice \
  --focus "act:sha256:abc123def456" \
  --radius 3
```

### Graph Query Methods

The ProjectIndex provides powerful query methods:

```python
# Get workflow by ID or path
workflow = index.get_workflow("wf:sha256:abc123")
workflow = index.get_workflow_by_path("Workflows/Process.xaml")

# Get activity and its containing workflow
activity = index.get_activity("act:sha256:def456")
parent_workflow = index.get_workflow_for_activity("act:sha256:def456")

# Get all workflows reachable from entry point
reachable = index.workflows.reachable_from(entry_workflow_id)

# Topological sort of workflow call graph
execution_order = index.get_execution_order()

# Extract context around activity
context = index.slice_context("act:sha256:abc123", radius=2)
```

### Architecture

```
XAML Files → Parse → Normalize → Analyze → ProjectIndex (IR)
                                              ↓
                          Views (Flat, Execution, Slice)
                                              ↓
                              Emitters (JSON, Mermaid, Docs)
```

**ProjectIndex** is an Intermediate Representation (IR) with 4 graph layers:
- **Workflows Graph**: All workflows with metadata
- **Activities Graph**: All activities across all workflows
- **Call Graph**: Workflow invocation relationships
- **Control Flow Graph**: Activity execution edges

**Benefits**:
- Single parse, multiple output formats
- Queryable structure for analysis tools
- Optimized for LLM context extraction
- 100% backward compatible (FlatView produces same output as v1.x)

See [docs/ADR-GRAPH-ARCHITECTURE.md](docs/ADR-GRAPH-ARCHITECTURE.md) for design decisions.

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
