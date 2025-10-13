# XAML Parser Monorepo Migration Plan

## Overview

This document outlines the migration strategy for transforming the `xaml_parser` Python package from a subpackage in the rpax repository into a standalone monorepo supporting both Python and Go implementations with shared test data.

## Source Location

**Original Package**: `D:\github.com\rpapub\rpax\src\xaml_parser\`

## Target Monorepo Structure

```
xaml-parser/                      # Monorepo root
├── LICENSE                       # CC-BY 4.0
├── README.md                     # Monorepo overview
├── CONTRIBUTING.md               # Contribution guidelines
├── .gitignore                    # Combined Python + Go
├── schemas/                      # Shared JSON schemas
│   ├── README.md
│   ├── parse_result.schema.json
│   └── workflow_content.schema.json
├── testdata/                     # Shared test corpus (Go convention)
│   ├── README.md
│   ├── golden/                   # Golden freeze test pairs
│   │   ├── simple_sequence.xaml
│   │   ├── simple_sequence.json
│   │   ├── complex_workflow.xaml
│   │   ├── complex_workflow.json
│   │   ├── invoke_workflows.xaml
│   │   ├── invoke_workflows.json
│   │   ├── ui_automation.xaml
│   │   └── ui_automation.json
│   └── corpus/                   # Structured test projects
│       ├── README.md
│       ├── simple_project/
│       │   ├── project.json
│       │   ├── Main.xaml
│       │   └── workflows/
│       └── edge_cases/
│           ├── malformed.xaml
│           ├── empty.xaml
│           └── ...
├── python/                       # Python implementation
│   ├── README.md                 # Python-specific documentation
│   ├── pyproject.toml            # Python package configuration
│   ├── uv.lock                   # Python dependency lock
│   ├── xaml_parser/              # Source package
│   │   ├── __init__.py
│   │   ├── __version__.py
│   │   ├── parser.py
│   │   ├── models.py
│   │   ├── extractors.py
│   │   ├── utils.py
│   │   ├── validation.py
│   │   ├── visibility.py
│   │   └── constants.py
│   ├── tests/                    # Python tests (references ../testdata)
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── test_parser.py
│   │   ├── test_parser_pytest.py
│   │   ├── test_corpus.py
│   │   └── test_validation.py
│   └── examples/                 # Python usage examples
├── go/                           # Go implementation (prepared structure)
│   ├── README.md                 # Go implementation roadmap
│   ├── go.mod                    # Go module definition
│   ├── go.sum                    # Go dependency checksums
│   ├── parser/                   # Go package
│   │   ├── parser.go
│   │   ├── models.go
│   │   ├── extractors.go
│   │   └── utils.go
│   ├── parser_test.go            # Go tests (references ../testdata)
│   └── examples/                 # Go usage examples
└── docs/                         # Shared documentation
    ├── MIGRATION.md              # This file
    ├── architecture.md           # Design decisions
    ├── api-compatibility.md      # Cross-language API contract
    └── schemas.md                # Schema documentation
```

## Migration Phases

### Phase 1: Foundation Setup

**Objective**: Establish monorepo infrastructure and shared resources

1. **License & Root Documentation**
   - Copy LICENSE from source (CC-BY 4.0)
   - Create comprehensive root README.md:
     - Project overview
     - Multi-language implementation status
     - Getting started for both Python and Go
     - Repository structure explanation
   - Update repository URLs from rpax to xaml-parser

2. **Version Control Configuration**
   - Create combined `.gitignore`:
     ```
     # Python
     __pycache__/
     *.py[cod]
     .pytest_cache/
     *.egg-info/
     dist/
     build/
     .venv/
     venv/

     # Go
     *.exe
     *.test
     *.out
     vendor/

     # IDE
     .vscode/
     .idea/
     *.swp

     # OS
     .DS_Store
     Thumbs.db
     ```

3. **Schemas Directory**
   - Create `schemas/` at root
   - Copy `parse_result.schema.json` from source
   - Copy `workflow_content.schema.json` from source
   - Create `schemas/README.md` documenting schema versioning strategy

4. **Test Data Migration**
   - Create `testdata/` structure
   - Migrate all test files (see detailed mapping below)
   - Normalize filenames and organization
   - Update README files for new structure

### Phase 2: Python Implementation Migration

**Objective**: Relocate Python package while maintaining full functionality

1. **Directory Structure**
   - Create `python/` directory
   - Create `python/xaml_parser/` for source code
   - Create `python/tests/` for test suite

2. **Source Code Migration**
   - Copy all `.py` files from source to `python/xaml_parser/`:
     - `__init__.py`
     - `__version__.py`
     - `parser.py`
     - `models.py`
     - `extractors.py`
     - `utils.py`
     - `validation.py`
     - `visibility.py`
     - `constants.py`

3. **Package Configuration**
   - Copy `pyproject.toml` to `python/`
   - Update paths in `pyproject.toml`:
     ```toml
     [tool.setuptools]
     package-dir = {"" = "."}

     [tool.setuptools.packages.find]
     where = ["."]
     include = ["xaml_parser*"]
     ```
   - Update URLs to point to monorepo
   - Copy `uv.lock` to `python/`

4. **Test Suite Migration**
   - Copy all test files to `python/tests/`:
     - `__init__.py`
     - `conftest.py`
     - `test_parser.py`
     - `test_parser_pytest.py`
     - `test_corpus.py`
     - `test_validation.py`

5. **Test Path Updates**
   - Update `conftest.py` to reference `../testdata`:
     ```python
     from pathlib import Path

     TESTDATA_DIR = Path(__file__).parent.parent / "testdata"
     GOLDEN_DIR = TESTDATA_DIR / "golden"
     CORPUS_DIR = TESTDATA_DIR / "corpus"
     ```
   - Update all test files:
     - Replace `test_data/` with `../testdata/golden/`
     - Replace `corpus/` with `../testdata/corpus/`
     - Update Path references to use relative paths from python/tests/

6. **Python Documentation**
   - Create `python/README.md` with:
     - Python-specific installation instructions
     - Development setup with uv
     - Running tests
     - Publishing workflow

### Phase 3: Test Data Normalization

**Objective**: Create unified, language-agnostic test corpus

1. **Golden Freeze Tests**
   - Move to `testdata/golden/`:
     - `simple_sequence.xaml` (from `test_data/simple_sequence.xaml`)
     - `simple_sequence.json` (from `test_data/simple_sequence_golden.json`)
     - `complex_workflow.xaml` (from `test_data/complex_workflow.xaml`)
     - `complex_workflow.json` (from `test_data/complex_workflow_golden.json`)
     - `invoke_workflows.xaml` (from `test_data/invoke_workflows_sample.xaml`)
     - `invoke_workflows.json` (from `test_data/invoke_workflows_sample_golden.json`)
     - `ui_automation.xaml` (from `test_data/ui_automation_sample.xaml`)
     - `ui_automation.json` (from `test_data/ui_automation_sample_golden.json`)

2. **Corpus Migration**
   - Move to `testdata/corpus/`:
     - Copy entire `tests/corpus/` directory structure
     - Preserve project structures:
       - `simple_project/`
       - `edge_cases/`
   - Copy and update `tests/corpus/README.md` to `testdata/corpus/README.md`

3. **Test Data Documentation**
   - Create `testdata/README.md`:
     - Explain golden freeze testing approach
     - Document corpus organization
     - Provide usage examples for both Python and Go
     - Define test data versioning strategy

### Phase 4: Go Implementation Preparation

**Objective**: Set up Go implementation structure for future development

1. **Go Module Initialization**
   - Create `go/` directory
   - Initialize Go module:
     ```bash
     cd go
     go mod init github.com/rpapub/xaml-parser/go
     ```

2. **Package Structure**
   - Create `go/parser/` directory
   - Create stub implementations:
     - `models.go`: Go structs matching Python dataclasses
     - `parser.go`: Parser interface and skeleton
     - `extractors.go`: Extractor function signatures
     - `utils.go`: Utility function signatures

3. **Test Structure**
   - Create `go/parser_test.go` with:
     - Test helpers for loading `../testdata`
     - Placeholder tests for golden freeze validation
     - Corpus discovery tests

4. **Go Documentation**
   - Create `go/README.md`:
     - Implementation status and roadmap
     - API compatibility goals with Python
     - Development setup
     - Testing approach

### Phase 5: Documentation & Tooling

**Objective**: Complete monorepo with comprehensive documentation and CI/CD

1. **Contribution Guidelines**
   - Create `CONTRIBUTING.md`:
     - How to contribute to Python implementation
     - How to contribute to Go implementation
     - Test data contribution guidelines
     - Schema update process
     - PR review process

2. **Architecture Documentation**
   - Create `docs/architecture.md`:
     - Parser design philosophy
     - Extractor pattern explanation
     - Model structure rationale
     - Zero-dependency constraint reasoning

3. **API Compatibility Guide**
   - Create `docs/api-compatibility.md`:
     - Define API surface contract
     - Document expected behavior for edge cases
     - Schema as source of truth
     - Cross-language validation strategy

4. **Schema Documentation**
   - Create `docs/schemas.md`:
     - Schema versioning policy
     - Breaking vs non-breaking changes
     - Schema extension guidelines

5. **CI/CD Setup** (Optional for initial migration)
   - Create `.github/workflows/python-tests.yml`
   - Create `.github/workflows/go-tests.yml` (future)
   - Create `.github/workflows/schema-validation.yml`

## Detailed Path Mapping

### Source → Destination Mapping

| Source Path | Destination Path | Notes |
|------------|------------------|-------|
| `LICENSE` | `LICENSE` | Root level |
| `README.md` | `python/README.md` | Python-specific, create new root README |
| `pyproject.toml` | `python/pyproject.toml` | Update paths |
| `uv.lock` | `python/uv.lock` | Direct copy |
| `__init__.py` | `python/xaml_parser/__init__.py` | No changes needed |
| `__version__.py` | `python/xaml_parser/__version__.py` | No changes needed |
| `parser.py` | `python/xaml_parser/parser.py` | No changes needed |
| `models.py` | `python/xaml_parser/models.py` | No changes needed |
| `extractors.py` | `python/xaml_parser/extractors.py` | No changes needed |
| `utils.py` | `python/xaml_parser/utils.py` | No changes needed |
| `validation.py` | `python/xaml_parser/validation.py` | No changes needed |
| `visibility.py` | `python/xaml_parser/visibility.py` | No changes needed |
| `constants.py` | `python/xaml_parser/constants.py` | No changes needed |
| `conftest.py` | `python/tests/conftest.py` | Update paths to `../testdata` |
| `tests/*.py` | `python/tests/*.py` | Update import paths |
| `schemas/*.json` | `schemas/*.json` | Root level shared resource |
| `test_data/*.xaml` | `testdata/golden/*.xaml` | Rename files (remove `_sample` suffix) |
| `test_data/*_golden.json` | `testdata/golden/*.json` | Rename (remove `_golden` suffix) |
| `tests/corpus/` | `testdata/corpus/` | Entire directory structure |

### File Renaming Reference

| Original | New | Location |
|----------|-----|----------|
| `simple_sequence.xaml` | `simple_sequence.xaml` | `testdata/golden/` |
| `simple_sequence_golden.json` | `simple_sequence.json` | `testdata/golden/` |
| `complex_workflow.xaml` | `complex_workflow.xaml` | `testdata/golden/` |
| `complex_workflow_golden.json` | `complex_workflow.json` | `testdata/golden/` |
| `invoke_workflows_sample.xaml` | `invoke_workflows.xaml` | `testdata/golden/` |
| `invoke_workflows_sample_golden.json` | `invoke_workflows.json` | `testdata/golden/` |
| `ui_automation_sample.xaml` | `ui_automation.xaml` | `testdata/golden/` |
| `ui_automation_sample_golden.json` | `ui_automation.json` | `testdata/golden/` |

## Test Path Updates

### Python Test Updates

**conftest.py**:
```python
# Before
TESTDATA_DIR = Path(__file__).parent / "test_data"

# After
TESTDATA_DIR = Path(__file__).parent.parent / "testdata" / "golden"
CORPUS_DIR = Path(__file__).parent.parent / "testdata" / "corpus"
```

**test_*.py files**:
```python
# Before
test_file = Path(__file__).parent / "test_data" / "simple_sequence.xaml"
golden_file = Path(__file__).parent / "test_data" / "simple_sequence_golden.json"

# After
test_file = Path(__file__).parent.parent / "testdata" / "golden" / "simple_sequence.xaml"
golden_file = Path(__file__).parent.parent / "testdata" / "golden" / "simple_sequence.json"
```

### Go Test Pattern (Future)

```go
// Test data loading
testdataDir := filepath.Join("..", "testdata", "golden")
xamlPath := filepath.Join(testdataDir, "simple_sequence.xaml")
goldenPath := filepath.Join(testdataDir, "simple_sequence.json")
```

## Implementation Checklist

### Phase 1: Foundation
- [ ] Create monorepo directory structure
- [ ] Copy LICENSE with proper attribution
- [ ] Create comprehensive root README.md
- [ ] Create `.gitignore` for Python + Go
- [ ] Create `schemas/` directory
- [ ] Copy JSON schemas
- [ ] Create `schemas/README.md`
- [ ] Create `testdata/` structure
- [ ] Create `testdata/README.md`
- [ ] Create `docs/` directory

### Phase 2: Python Migration
- [ ] Create `python/` directory structure
- [ ] Copy all Python source files to `python/xaml_parser/`
- [ ] Copy `pyproject.toml` and update paths
- [ ] Copy `uv.lock`
- [ ] Copy test files to `python/tests/`
- [ ] Update `conftest.py` paths
- [ ] Update all test file paths
- [ ] Create `python/README.md`
- [ ] Run tests to verify migration
- [ ] Fix any broken import paths

### Phase 3: Test Data
- [ ] Create `testdata/golden/` directory
- [ ] Copy and rename XAML files
- [ ] Copy and rename golden JSON files
- [ ] Create `testdata/corpus/` directory
- [ ] Copy entire corpus structure
- [ ] Copy and update corpus README
- [ ] Verify Python tests still pass

### Phase 4: Go Preparation
- [ ] Create `go/` directory
- [ ] Initialize Go module
- [ ] Create `go/parser/` package
- [ ] Create stub `models.go`
- [ ] Create stub `parser.go`
- [ ] Create basic `parser_test.go`
- [ ] Create `go/README.md` with roadmap

### Phase 5: Documentation
- [ ] Create `CONTRIBUTING.md`
- [ ] Create `docs/architecture.md`
- [ ] Create `docs/api-compatibility.md`
- [ ] Create `docs/schemas.md`
- [ ] Review and update all documentation
- [ ] Add examples directory structure

## Validation Steps

After migration, verify:

1. **Python Package Integrity**
   ```bash
   cd python
   uv run pytest tests/ -v
   uv build
   ```

2. **Import Paths**
   ```python
   from xaml_parser import XamlParser
   from xaml_parser.models import WorkflowContent
   ```

3. **Test Data Access**
   - Python tests can load `../testdata/golden/*.xaml`
   - Python tests can load `../testdata/corpus/**/*`

4. **Schema Validation**
   - All golden JSON files validate against schemas
   - Schema references are accessible from both Python and Go

5. **Documentation Completeness**
   - All README files are comprehensive
   - Links between docs are valid
   - Examples are runnable

## Rollback Plan

If migration issues occur:

1. **Python Package Issues**: Original source remains in rpax repository
2. **Test Data Issues**: Keep original test_data/ as reference until validation complete
3. **Git Strategy**: Use feature branch for migration, don't delete source until validated

## Post-Migration Tasks

1. **Update rpax Repository**
   - Update rpax to reference new monorepo as dependency
   - Archive or redirect xaml_parser subpackage

2. **PyPI Publishing** (Optional)
   - Register `xaml-parser` package name
   - Configure publishing workflow
   - Update package metadata

3. **Go Implementation**
   - Schedule Go implementation sprints
   - Define API compatibility test suite
   - Create cross-language validation tests

4. **Community**
   - Announce monorepo structure
   - Update issue templates
   - Create discussion forums

## Notes & Considerations

### Design Decisions

1. **`testdata` vs `test_data`**: Following Go convention for test data directory naming
2. **`golden/` subdirectory**: Clearly separates golden freeze tests from corpus tests
3. **Flat golden structure**: Simple XAML/JSON pairs without subdirectories
4. **Language directories at root**: Clear separation of implementations
5. **Shared schemas**: Single source of truth for output format

### Future Considerations

1. **Additional Languages**: Structure supports adding Rust, JavaScript, etc.
2. **Performance Benchmarks**: Can add `benchmarks/` directory
3. **Docker Support**: Add `docker/` for containerized testing
4. **Web Examples**: Add `web/` for WASM or API examples

### Migration Timing

- **Estimated Duration**: 4-6 hours for careful migration
- **Testing Buffer**: Additional 2-3 hours for validation
- **Recommended**: Execute in single session to maintain consistency

## References

- Original Package: `D:\github.com\rpapub\rpax\src\xaml_parser\`
- Target Repository: `D:\github.com\rpapub\xaml-parser\`
- License: CC-BY 4.0 (https://creativecommons.org/licenses/by/4.0/)
