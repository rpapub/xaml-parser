# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**xaml-parser** is a standalone XAML workflow parser for UiPath automation projects. It parses UiPath .xaml files and extracts structured metadata (arguments, variables, activities, control flow, expressions) into stable, self-describing JSON output suitable for data lake pipelines, MCP servers, and LLM consumption.

**Key principles:**
- Zero external dependencies (only Python stdlib + defusedxml for security)
- Stable content-hash based IDs that survive file renames (`wf:sha256:abc123...`)
- Project-first architecture with call graph traversal
- Deterministic, reproducible output using binary collation

## Commands

### Python Development (use `uv` for all Python tasks)

```bash
# Setup
cd python/
uv sync                           # Install dependencies

# Testing
uv run pytest tests/ -v           # All tests
uv run pytest tests/ -m "not corpus"  # Fast tests only (default)
uv run pytest tests/ -m corpus    # Slow corpus tests
uv run pytest tests/test_parser.py::test_specific -v  # Single test
uv run pytest tests/ --cov=cpmf_xaml_parser --cov-report=html  # Coverage

# Code Quality
uv run ruff check cpmf_xaml_parser/ tests/       # Lint
uv run ruff format cpmf_xaml_parser/ tests/      # Format
uv run mypy cpmf_xaml_parser/                     # Type check

# CLI Usage
uv run xaml-parser project.json             # Parse project
uv run xaml-parser Main.xaml                # Parse single workflow
uv run xaml-parser Main.xaml --json         # JSON output
uv run xaml-parser project.json --dto --profile mcp  # DTO output
```

### Build & Package

```bash
cd python/
uv build                          # Build distribution
twine check dist/*                # Verify package
```

## Architecture

### Data Flow Pipeline

```
XAML Files → XamlParser → ParseResult (internal models)
                ↓
         Normalizer (transforms to DTOs)
                ↓
    WorkflowDto (stable IDs, edges, sorted)
                ↓
         Emitters (JSON, Mermaid, Docs)
```

### Key Components

1. **Parsing Layer** (`parser.py`, `project.py`, `extractors.py`)
   - `XamlParser`: Parses individual XAML files using defusedxml
   - `ProjectParser`: Parses entire projects, follows `InvokeWorkflowFile` references
   - `ActivityExtractor`, `ArgumentExtractor`, `VariableExtractor`: Specialized extractors

2. **Internal Models** (`models.py`)
   - `ParseResult`, `WorkflowContent`, `Activity` - Parsing output (internal use)
   - These are NOT stable - use DTOs for external APIs

3. **Normalization Layer** (`normalization.py`, `id_generation.py`, `control_flow.py`)
   - `Normalizer`: Transforms internal models → DTOs
   - `IdGenerator`: Generates stable content-hash IDs using W3C XML C14N
   - `ControlFlowExtractor`: Extracts explicit edges (Then/Else/Next/Catch/etc.)

4. **DTO Layer** (`dto.py`)
   - `WorkflowDto`, `ActivityDto`, `EdgeDto` - Self-describing, stable output
   - Includes schema metadata (`schema_id`, `schema_version`, `collected_at`)
   - **These are the stable API** - use for all external output

5. **Emitters** (`emitters/`)
   - `JsonEmitter`: JSON output with field profiles (full/minimal/mcp/datalake)
   - `MermaidEmitter`: Workflow diagram generation
   - `DocEmitter`: Documentation generation with Jinja2

### Stable ID System

All workflow entities get content-hash based IDs:

- **Workflows**: `wf:sha256:abc123def456` (16 hex chars)
- **Activities**: `act:sha256:abc123def456` (16 hex chars)
- **Edges**: `edge:sha256:abc123def456` (16 hex chars)

**Implementation:**
1. Normalize XML using W3C C14N (sort attributes, normalize whitespace)
2. SHA-256 hash the normalized content
3. Truncate to 16 hex chars (64 bits) for readability
4. Store full hash in `SourceInfo.hash` for audit trails

**Why:** IDs are stable across file renames, minor formatting changes, and git operations.

### Control Flow Modeling

Control flow is explicitly modeled as edges separate from the activity tree:

**Edge kinds**: `Then`, `Else`, `Next`, `True`, `False`, `Case`, `Default`, `Catch`, `Finally`, `Link`, `Transition`, `Branch`, `Retry`, `Timeout`, `Done`, `Trigger`

**Why:** Enables static analysis, diagram generation, and path finding without inferring from tree structure.

### Deterministic Output

All output is deterministically sorted for reproducibility:

- Activities: by ID (UTF-8 binary collation)
- Arguments/Variables: by name (case-sensitive)
- Properties: by key name
- Edges: by (from_id, to_id, kind)

**No locale-sensitive sorting** - uses binary byte comparison for cross-platform consistency.

## Testing Philosophy

### Test Categories

1. **Unit tests** (fast, always run)
   - Test individual functions and classes
   - Mock external dependencies
   - `pytest tests/ -m "not corpus"`

2. **Corpus tests** (slow, skipped by default)
   - Test against real UiPath projects in `test-corpus/`
   - Mark with `@pytest.mark.corpus`
   - Run explicitly: `pytest tests/ -m corpus`

3. **Golden baseline tests** (`python/tests/corpus/golden/`)
   - Committed reference outputs for regression detection
   - XAML input + expected JSON output pairs
   - Detect unintended changes in parser behavior

### Test Corpus Structure

- `test-corpus/`: Git submodule with UiPath projects
- `.test-artifacts/python/`: Ephemeral test outputs (gitignored)
- `python/tests/corpus/golden/`: Committed golden baselines
- **CORE category projects**: "Guaranteed-to-work" reference implementations

## Logging and Output Standards

- **DO NOT use Unicode characters** in logging output (✓, ✗, →, etc.)
- **USE simple ASCII** like `[OK]`, `[FAIL]`, `[INFO]`, `[WARN]`, `[ERROR]`
- **Professional, consistent formatting** for all console output

### Good Examples
```
[OK] Parsed 10 workflows in 234ms
[FAIL] File not found: project.json
[INFO] Generating Mermaid diagrams...
```

### Bad Examples
```
✓ Parsed 10 workflows
✗ File not found
🚀 Starting...
```

## Code Style

### Python Conventions

- Type hints on all functions (mypy strict mode)
- Dataclasses for data structures
- `pathlib.Path` for file operations
- Use `uv` for all package management
- Follow ruff defaults (line length 100)

## Common Patterns

### Parsing a Project

```python
from pathlib import Path
from cpmf_xaml_parser import ProjectParser

parser = ProjectParser()
result = parser.parse_project(
    Path("path/to/project"),
    recursive=True,              # Follow InvokeWorkflowFile
    entry_points_only=False      # Parse all workflows
)

# Access workflows
for wf in result.workflows:
    print(f"{wf.relative_path}: {len(wf.parse_result.content.activities)} activities")

# Check dependency graph
for path, deps in result.dependency_graph.items():
    print(f"{path} invokes: {deps}")
```

### Converting to DTOs

```python
from cpmf_xaml_parser.normalization import Normalizer
from cpmf_xaml_parser.id_generation import IdGenerator
from cpmf_xaml_parser.control_flow import ControlFlowExtractor

# Create normalizer pipeline
id_gen = IdGenerator()
flow_extractor = ControlFlowExtractor(id_gen)
normalizer = Normalizer(id_gen, flow_extractor)

# Transform ParseResult → WorkflowDto
workflow_dto = normalizer.normalize(
    parse_result,
    workflow_name="Main",
    workflow_id_map={}  # For linking InvokeWorkflowFile
)

# Now workflow_dto has stable IDs and explicit edges
```

### Emitting Output

```python
from cpmf_xaml_parser.emitters import JsonEmitter, EmitterConfig

emitter = JsonEmitter()
config = EmitterConfig(
    field_profile="mcp",     # full/minimal/mcp/datalake
    combine=True,            # Single file or per-workflow
    pretty=True,
    exclude_none=True
)

result = emitter.emit([workflow_dto], output_path, config)
```

## Important Files

- `docs/ADR-DTO-DESIGN.md`: DTO architecture decisions
- `python/xaml_parser/dto.py`: DTO definitions (stable API)
- `python/xaml_parser/models.py`: Internal models (not stable)
- `CONTRIBUTING.md`: Development process and PR guidelines

## Links

- Repository: https://github.com/rpapub/xaml-parser
- Issues: https://github.com/rpapub/xaml-parser/issues
- Original project: https://github.com/rpapub/rpax
