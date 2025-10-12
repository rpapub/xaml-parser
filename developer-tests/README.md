# Developer Tests

This directory contains **manual developer test scripts** for inspecting and validating DTO outputs. These are **NOT part of the pytest suite**.

## Purpose

Generate human-readable DTO outputs from test-corpus projects to:
- Validate DTO structure and content
- Inspect graph-based analysis results
- Compare different view outputs (flat, execution, slice)
- Debug parsing and analysis issues

## Scripts

### `test_corpus_output.py`

Generates comprehensive DTO outputs for test-corpus projects.

**Usage**:
```bash
cd xaml-parser
uv run python developer-tests/test_corpus_output.py
```

**Output Location**: `developer-tests/output/`

**Generated Files**:
```
output/
├── CORE_00000001/
│   ├── flat_view.json              # FlatView output (collection)
│   ├── execution_view.json         # ExecutionView output (call graph)
│   ├── slice_view_1.json           # SliceView output (activity 1)
│   ├── slice_view_2.json           # SliceView output (activity 2)
│   ├── slice_view_3.json           # SliceView output (activity 3)
│   ├── workflows/                  # Individual workflow summaries
│   │   ├── Main.json
│   │   ├── InitAllSettings.json
│   │   └── ...
│   └── activities/                 # Sample activity DTOs
│       ├── abc123def456.json
│       └── ...
└── CORE_00000010/
    └── ... (same structure)
```

## Test Corpus Projects

The script processes these test-corpus projects:

1. **CORE_00000001** (`c25v001_CORE_00000001`)
   - Multi-entry point project
   - Framework components
   - Data processing workflows

2. **CORE_00000010** (`c25v001_CORE_00000010`)
   - Simple Main.xaml project
   - Framework components
   - Basic structure

## Output Files Explained

### View Outputs

- **`flat_view.json`**: Traditional flat list of workflows (backward compatible)
  - Schema: `xaml-workflow-collection.json` v1.0.0
  - All workflows in linear array
  - No nesting or call graph traversal

- **`execution_view.json`**: Call graph traversal from entry point
  - Schema: `xaml-workflow-execution.json` v2.0.0
  - Nested activity tree (callee activities under InvokeWorkflowFile)
  - Shows "what actually runs" from entry to leaves
  - Includes `call_depth` per workflow

- **`slice_view_N.json`**: Context extraction around specific activity
  - Schema: `xaml-activity-slice.json` v2.1.0
  - Focal activity with metadata
  - Parent chain (root → focal)
  - Siblings (same parent)
  - Context window (configurable radius)
  - Optimized for LLM consumption

### Individual Object Outputs

- **`workflows/*.json`**: Workflow summaries
  - Metadata, source info, counts
  - Not full DTO (summary only)

- **`activities/*.json`**: Sample activity DTOs
  - First 5 activities from each project
  - Complete activity metadata
  - Properties, expressions, children

## Usage Workflow

1. **Run the script**:
   ```bash
   uv run python developer-tests/test_corpus_output.py
   ```

2. **Inspect outputs**:
   ```bash
   # View flat output
   cat developer-tests/output/CORE_00000001/flat_view.json | jq

   # View execution output
   cat developer-tests/output/CORE_00000001/execution_view.json | jq

   # View specific workflow
   cat developer-tests/output/CORE_00000001/workflows/Main.json | jq

   # View specific activity
   cat developer-tests/output/CORE_00000001/activities/*.json | jq
   ```

3. **Validate against schemas**:
   ```bash
   # Validate flat view
   ajv validate -s schemas/xaml-workflow-collection.schema.json \
       -d developer-tests/output/CORE_00000001/flat_view.json

   # Validate execution view
   ajv validate -s schemas/xaml-workflow-execution.schema.json \
       -d developer-tests/output/CORE_00000001/execution_view.json

   # Validate slice view
   ajv validate -s schemas/xaml-activity-slice.schema.json \
       -d developer-tests/output/CORE_00000001/slice_view_1.json
   ```

## Adding New Tests

To add new developer test scripts:

1. Create script in `developer-tests/`
2. Make it executable: `chmod +x developer-tests/your_script.py`
3. Add shebang: `#!/usr/bin/env python3`
4. Document usage in this README
5. Output to `developer-tests/output/`

## Notes

- **Not for CI**: These tests are for manual inspection only
- **Git ignored**: Output directory is in `.gitignore`
- **No assertions**: Scripts generate output for human review
- **Update as needed**: Modify scripts to test specific features

## Cleanup

```bash
# Remove all output files
rm -rf developer-tests/output/

# Regenerate
uv run python developer-tests/test_corpus_output.py
```

---

**Last Updated**: 2025-10-12
**Maintainer**: xaml-parser core team
