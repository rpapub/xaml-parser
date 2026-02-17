# XAML Parser JSON Schemas

This directory contains JSON schemas that define the structure and validation rules for XAML parser output. These schemas serve as the contract between different language implementations (Python, Go, etc.) and ensure consistent output format.

**Version**: 2.0 (Graph-Based Architecture)
**Last Updated**: 2025-10-12

---

## Schema Overview

### Public API Schemas (DTO Layer)

These schemas define the stable public API for xaml-parser output. Use these for validation and integration.

#### Core DTO Schemas

| Schema | Purpose | Version |
|--------|---------|---------|
| **[xaml-workflow-collection.schema.json](#xaml-workflow-collection)** | Workflow collection (FlatView output) | 1.0.0 |
| **[workflow.schema.json](#workflow)** | Single workflow DTO | 1.0.0 |
| **[activity.schema.json](#activity)** | Activity instance | 1.0.0 |
| **[argument.schema.json](#argument)** | Workflow argument | 1.0.0 |
| **[variable.schema.json](#variable)** | Variable definition | 1.0.0 |
| **[edge.schema.json](#edge)** | Control flow edge | 1.0.0 |
| **[invocation.schema.json](#invocation)** | Workflow invocation | 1.0.0 |

#### View Schemas (v2.0 Multi-View Output)

| Schema | Purpose | Version |
|--------|---------|---------|
| **[xaml-workflow-execution.schema.json](#execution-view)** | ExecutionView output (call graph traversal) | 2.0.0 |
| **[xaml-activity-slice.schema.json](#slice-view)** | SliceView output (LLM context extraction) | 2.1.0 |

### Internal Schemas (Reference Only)

Located in `internal/` - these document internal parsing models, not the public API.

| Schema | Purpose |
|--------|---------|
| `internal/parse_result.schema.json` | ParseResult (internal parsing output) |
| `internal/workflow_content.schema.json` | WorkflowContent (internal model) |

### Legacy Schemas (Archived)

Located in `legacy/` - older monolithic schema files with all definitions inline. These are preserved for reference but superseded by the modular schemas above.

| Schema | Purpose | Status |
|--------|---------|--------|
| `legacy/xaml-workflow-1.0.0.json` | Monolithic workflow schema (all DTOs inline) | Superseded |
| `legacy/xaml-workflow-collection-1.0.0.json` | Monolithic collection schema | Superseded |

**Note**: These legacy schemas were originally in `python/schemas/` and have been consolidated here as of 2025-10-12.

---

## Schema Details

### <a name="xaml-workflow-collection"></a>xaml-workflow-collection.schema.json

**Purpose**: Collection of workflows (default FlatView output)

**Schema ID**: `https://rpax.io/schemas/xaml-workflow-collection.json`

**Version**: 1.0.0

**Use Case**: Default output format for project parsing, 100% backward compatible with v1.x

**Structure**:
```json
{
  "schema_id": "https://rpax.io/schemas/xaml-workflow-collection.json",
  "schema_version": "1.0.0",
  "collected_at": "2025-10-12T18:30:00Z",
  "project": {
    "name": "MyRPAProject",
    "path": "D:/Projects/MyRPAProject",
    "main_workflow": "wf:sha256:abc123def456"
  },
  "workflows": [/* WorkflowDto array */],
  "issues": [/* IssueDto array */]
}
```

**Python Usage**:
```python
from cpmf_xaml_parser import ProjectParser, analyze_project
from cpmf_xaml_parser.views import FlatView

parser = ProjectParser()
result = parser.parse_project(Path("project"))
index = analyze_project(result)

view = FlatView()
output = view.render(index)  # Validates against this schema
```

---

### <a name="workflow"></a>workflow.schema.json

**Purpose**: Single workflow with complete metadata

**Schema ID**: `https://rpax.io/schemas/xaml-workflow.json`

**Version**: 1.0.0

**Structure**:
```json
{
  "id": "wf:sha256:abc123def456",
  "name": "Main",
  "source": {/* SourceInfo */},
  "metadata": {/* WorkflowMetadata */},
  "arguments": [/* ArgumentDto array */],
  "variables": [/* VariableDto array */],
  "activities": [/* ActivityDto array */],
  "edges": [/* EdgeDto array */],
  "invocations": [/* InvocationDto array */],
  "issues": [/* IssueDto array */]
}
```

**Key Features**:
- Content-hash based stable ID (`wf:sha256:...`)
- Source tracking with path aliases for rename stability
- Complete business logic (activities, edges, expressions)
- Workflow invocation graph

---

### <a name="activity"></a>activity.schema.json

**Purpose**: Activity instance with complete business logic

**Schema ID**: `https://github.com/rpapub/xaml-parser/schemas/activity.schema.json`

**Version**: 1.0.0

**Structure**:
```json
{
  "id": "act:sha256:abc123def456",
  "type": "System.Activities.Statements.Sequence",
  "type_short": "Sequence",
  "display_name": "Process Transaction",
  "location": {"line": 42, "column": 8, "xpath": "/Activity/Sequence[1]"},
  "parent_id": null,
  "children": ["act:sha256:child1", "act:sha256:child2"],
  "depth": 0,
  "properties": {/* Activity properties */},
  "in_args": {/* Input arguments */},
  "out_args": {/* Output arguments */},
  "annotation": "Main transaction processing sequence",
  "expressions": ["TransactionData IsNot Nothing"],
  "variables_referenced": ["TransactionData", "RetryCount"],
  "selectors": {/* UI selectors for UI automation */}
}
```

**Key Features**:
- Stable activity ID (content-hash based)
- Parent-child hierarchy
- Source location tracking
- Expression and variable reference extraction
- UI automation selector support

---

### <a name="argument"></a>argument.schema.json

**Purpose**: Workflow argument definition

**Version**: 1.0.0

**Structure**:
```json
{
  "id": "arg:sha256:abc123def456",
  "name": "in_Config",
  "direction": "in",
  "type": "System.Collections.Generic.Dictionary<String, Object>",
  "annotation": "Configuration dictionary from Orchestrator",
  "default_value": null
}
```

---

### <a name="variable"></a>variable.schema.json

**Purpose**: Variable definition with scope

**Version**: 1.0.0

**Structure**:
```json
{
  "id": "var:sha256:abc123def456",
  "name": "TransactionItem",
  "type": "System.Data.DataRow",
  "scope": "Sequence_Main",
  "default_value": null
}
```

---

### <a name="edge"></a>edge.schema.json

**Purpose**: Explicit control flow edge

**Version**: 1.0.0

**Structure**:
```json
{
  "id": "edge:sha256:abc123def456",
  "from_id": "act:sha256:aaa111bbb222",
  "to_id": "act:sha256:ccc333ddd444",
  "kind": "Then",
  "label": null
}
```

**Edge Kinds**: `Then`, `Else`, `Next`, `True`, `False`, `Case`, `Default`, `Catch`, `Finally`, `Link`, `Transition`, `Branch`, `Retry`, `Timeout`, `Done`, `Trigger`

---

### <a name="invocation"></a>invocation.schema.json

**Purpose**: Workflow invocation (call graph edge)

**Version**: 1.0.0

**Structure**:
```json
{
  "callee_id": "wf:sha256:abc123def456",
  "callee_path": "Framework/InitAllSettings.xaml",
  "via_activity_id": "act:sha256:def456abc123"
}
```

---

### <a name="execution-view"></a>xaml-workflow-execution.schema.json

**Purpose**: Execution view with call graph traversal and nested activities

**Schema ID**: `https://rpax.io/schemas/xaml-workflow-execution.json`

**Version**: 2.0.0

**Use Case**: "Show me what actually runs when I start from Main.xaml"

**Structure**:
```json
{
  "schema_id": "https://rpax.io/schemas/xaml-workflow-execution.json",
  "schema_version": "2.0.0",
  "collected_at": "2025-10-12T18:30:00Z",
  "entry_point": "wf:sha256:abc123def456",
  "max_depth": 10,
  "workflows": [
    {
      "id": "wf:sha256:abc123def456",
      "name": "Main",
      "call_depth": 0,
      "activities": [
        {
          "id": "act:sha256:seq1",
          "type": "System.Activities.Statements.Sequence",
          "children": [
            {
              "id": "act:sha256:invoke1",
              "type": "UiPath.Core.Activities.InvokeWorkflowFile",
              "expanded_from": "wf:sha256:helper123",
              "children": [/* Nested callee activities */]
            }
          ]
        }
      ]
    }
  ]
}
```

**Key Features**:
- DFS traversal from entry point
- `call_depth` per workflow (0 = entry point)
- Nested activity tree (no `parent_id`, children inline)
- `expanded_from` marks InvokeWorkflowFile expansions

**Python Usage**:
```python
from cpmf_xaml_parser.views import ExecutionView

entry_workflow_id = index.entry_points[0]
view = ExecutionView(entry_point=entry_workflow_id, max_depth=10)
output = view.render(index)
```

**CLI Usage**:
```bash
uv run xaml-parser project.json --dto --json \
  --view execution --entry "wf:sha256:abc123def456"
```

---

### <a name="slice-view"></a>xaml-activity-slice.schema.json

**Purpose**: Focused context extraction around a specific activity (LLM-optimized)

**Schema ID**: `https://rpax.io/schemas/xaml-activity-slice.json`

**Version**: 2.1.0

**Use Case**: Provide minimal relevant context to LLM without token overflow

**Structure**:
```json
{
  "schema_id": "https://rpax.io/schemas/xaml-activity-slice.json",
  "schema_version": "2.1.0",
  "collected_at": "2025-10-12T18:30:00Z",
  "focus": "act:sha256:focal123abc",
  "radius": 2,
  "workflow": {/* Minimal workflow context */},
  "focal_activity": {/* The target activity */},
  "parent_chain": [/* Root → Parent path */],
  "siblings": [/* Same-parent activities */],
  "context_activities": [/* Activities within radius */],
  "edges": [/* Control flow edges */]
}
```

**Key Features**:
- Focal activity with complete metadata
- Parent chain from root to focal
- Siblings (same parent)
- Context window (configurable radius)
- Relevant control flow edges

**Python Usage**:
```python
from cpmf_xaml_parser.views import SliceView

focal_activity_id = "act:sha256:abc123def456"
view = SliceView(focus=focal_activity_id, radius=2)
output = view.render(index)
```

**CLI Usage**:
```bash
uv run xaml-parser project.json --dto --json \
  --view slice --focus "act:sha256:abc123def456" --radius 3
```

---

## Versioning

Schemas follow [Semantic Versioning](https://semver.org/):

- **Major version**: Breaking changes to required fields or data types
- **Minor version**: Backward-compatible additions (new optional fields)
- **Patch version**: Clarifications, documentation, non-breaking fixes

Current versions are embedded in the `$id` and `version` fields.

---

## Schema Evolution

When modifying schemas:

1. **Never remove required fields** - this breaks existing implementations
2. **Add new fields as optional** - omit from `required` array
3. **Document changes** - update this README and CHANGELOG
4. **Update tests** - ensure outputs validate against new schema
5. **Bump version** - update `$id` and `version` according to semver

---

## Validation

### Python

```python
from cpmf_xaml_parser.validation import validate_output, get_validator

# Validate parser output
result = parser.parse_file(Path("workflow.xaml"))
errors = validate_output(result)

if errors:
    print("Validation failed:", errors)
```

### Command Line (ajv-cli)

```bash
# Install ajv-cli
npm install -g ajv-cli

# Validate JSON output
ajv validate -s xaml-workflow-collection.schema.json -d ../output.json

# Validate multiple files
ajv validate -s xaml-workflow-collection.schema.json -d "../.test-artifacts/*.json"
```

### Command Line (python jsonschema)

```bash
# Install jsonschema
pip install jsonschema

# Validate output
python -m jsonschema -i ../output.json xaml-workflow-collection.schema.json
```

---

## Cross-Language Testing

These schemas enable cross-language validation:

1. Python implementation outputs JSON
2. JSON validates against schemas
3. Go implementation reads same test data
4. Both produce schema-compliant output
5. Outputs can be compared for consistency

---

## Schema Relationships

```
xaml-workflow-collection.schema.json (FlatView)
├── workflow.schema.json
    ├── argument.schema.json
    ├── variable.schema.json
    ├── activity.schema.json
    ├── edge.schema.json
    └── invocation.schema.json

xaml-workflow-execution.schema.json (ExecutionView)
├── argument.schema.json
├── variable.schema.json
└── Nested activities (recursive structure)

xaml-activity-slice.schema.json (SliceView)
├── activity.schema.json
├── edge.schema.json
└── Workflow context (minimal)
```

---

## References

- **JSON Schema Specification**: https://json-schema.org/specification.html
- **Understanding JSON Schema**: https://json-schema.org/understanding-json-schema/
- **JSON Schema Draft 2020-12**: https://json-schema.org/draft/2020-12/schema
- **ADR: Graph Architecture**: ../docs/ADR-GRAPH-ARCHITECTURE.md
- **ADR: DTO Design**: ../docs/ADR-DTO-DESIGN.md

---

## Files in This Directory

```
schemas/
├── README.md                                   # This file
├── EVALUATION.md                               # Schema evaluation report
│
# Public API Schemas (DTO Layer)
├── xaml-workflow-collection.schema.json       # FlatView output (v1.0.0)
├── xaml-workflow-execution.schema.json        # ExecutionView output (v2.0.0)
├── xaml-activity-slice.schema.json            # SliceView output (v2.1.0)
│
# DTO Component Schemas
├── workflow.schema.json                        # WorkflowDto
├── activity.schema.json                        # ActivityDto
├── argument.schema.json                        # ArgumentDto
├── variable.schema.json                        # VariableDto
├── edge.schema.json                            # EdgeDto
├── invocation.schema.json                      # InvocationDto
│
# Internal Schemas (Reference)
├── internal/
│   ├── parse_result.schema.json                # ParseResult (internal)
│   └── workflow_content.schema.json            # WorkflowContent (internal)
│
# Legacy Schemas (Archived)
└── legacy/
    ├── xaml-workflow-1.0.0.json                # Old monolithic workflow schema
    └── xaml-workflow-collection-1.0.0.json     # Old monolithic collection schema
```

**Note**: All schemas are now consolidated in this directory. The previous `python/schemas/` directory has been merged here.

---

**Last Updated**: 2025-10-12
**Maintainer**: xaml-parser core team
**Repository**: https://github.com/rpapub/xaml-parser
