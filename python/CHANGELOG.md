# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- **BREAKING**: Renamed `stages.build` module to `stages.assemble` to avoid gitignore conflicts
  - Import path changed: `from cpmf_uips_xaml.stages.build` → `from cpmf_uips_xaml.stages.assemble`
  - All functionality preserved, only module name changed
  - Fixes issue where source code directory was being ignored by git due to Python build/ artifact pattern

## [0.1.0] - 2025-02-06

### Changed
- **BREAKING**: Package renamed from `cpmf-xaml-parser` to `cpmf-uips-xaml`
- **BREAKING**: Python import changed from `cpmf_xaml_parser` to `cpmf_uips_xaml`
- **BREAKING**: CLI command changed from `cpmf-xaml-parser` to `cpmf-uips-xaml`

### Migration Guide

**Old installation:**
```bash
pip install cpmf-xaml-parser
from cpmf_xaml_parser import XamlParser
cpmf-xaml-parser project.json
```

**New installation:**
```bash
pip install cpmf-uips-xaml
from cpmf_uips_xaml import XamlParser
cpmf-uips-xaml project.json
```

### Notes
This is the initial release under the new CPRIMA UIPS (UiPath Integration & Parsing Suite) branding. All functionality from cpmf-xaml-parser 0.3.0 is preserved.

## [0.3.0] - 2025-02-06

### Added
- Modular API structure with focused submodules (`api.parsing`, `api.analysis`, `api.views`, `api.emit`, `api.config`)
- Platform injection system with UiPath dialect abstraction (`platforms/uipath/`)
- Event-based progress reporting with `ProgressReporter` protocol
- Multiple progress reporter implementations (`RichReporter`, `TqdmReporter`, `JsonReporter`, `SimpleReporter`)
- Layered architecture with clear boundaries (`shared/`, `stages/`, `platforms/`, `api/`, `cli/`)
- `NULL_REPORTER` constant for disabling progress reporting

### Changed
- **BREAKING**: Progress reporting API - `show_progress: bool` parameter replaced with `reporter: ProgressReporter`
- **BREAKING**: CLI `--progress` flag now accepts choices (`rich`, `tqdm`, `json`, `simple`) instead of boolean
- API `__init__.py` refactored from 402 to 127 lines (backward compatible via re-exports)
- CLI reorganized into package structure (`cli/cli.py`, `cli/reporters.py`)
- File organization follows stages-based architecture (parsing → normalize → build → emit → analysis)
- Utility functions consolidated under `shared.utils` (data, debug, text, validation, xml)

### Fixed
- CLI layer boundary violations - imports now strictly through API facade
- Layer coupling - proper dependency injection through dialect pattern

### Documentation
- Comprehensive CLI reference with all flags organized by category
- API module organization guide with usage examples
- Architecture documentation (5-stage pipeline)
- Breaking changes migration guide for v0.3.0
- "When to use XamlParser vs API facade" guidance

### Developer
- Clean architectural boundaries enforced (CLI → API → Stages)
- Platform-specific code isolated and injected via dialect
- 100% backward compatible API despite internal refactoring

## [0.2.0] - 2025-12-03

### Added
- Expression language detection (VisualBasic vs CSharp) via `MetadataExtractor.extract_expression_language()`
- `expression_language` field to `WorkflowContent` model
- Encoding detection and fallback support (UTF-8, UTF-8-sig, UTF-16, ISO-8859-1, cp1252)
- Comprehensive unit tests for metadata extraction (19 new tests):
  - x:Class attribute extraction (4 tests)
  - .NET namespace imports extraction (2 tests)
  - Assembly references extraction (4 tests - modern and legacy formats)
  - Expression language detection (4 tests - VB.NET, C#, none)
  - Case-insensitive default value extraction (1 test)

### Fixed
- **Bug**: Case-insensitive default value extraction - Arguments with capitalized `Default` attribute now correctly extracted
- Parser now checks both `default` and `Default` attributes in `_extract_arguments()`

### Changed
- File reading now uses encoding detection with automatic fallback
- `encoding_detected` field in `ParseDiagnostics` now reflects actual encoding used

### Developer
- Added 6 detailed implementation plans (v0.2.1 through v0.2.6)
- Plan tracking with markdown checklists in docs/plans/
- All plans tracked with completion status

## [0.1.0] - 2025-10-11

### Added
- Initial release of xaml-parser Python package
- Complete XAML workflow parser for UiPath automation projects
- Project-level parsing with auto-discovery from project.json
- Recursive workflow traversal following InvokeWorkflowFile references
- Dependency graph construction
- Full-featured CLI with auto-detection (project.json vs .xaml files)
- Support for arguments, variables, activities, expressions, annotations extraction
- Schema-based validation
- Comprehensive test suite (63 tests passing)
- Zero external dependencies (except defusedxml for security)

### CLI Features
- Project parsing: `xaml-parser project.json`
- Individual file parsing: `xaml-parser workflow.xaml`
- Dependency graph: `xaml-parser project.json --graph`
- Multiple output formats: `--json`, `--arguments`, `--activities`, `--tree`, `--summary`
- Entry points only mode: `--entry-points-only`

### Python API
- `XamlParser` class for individual workflow parsing
- `ProjectParser` class for entire project parsing
- Complete type hints for all APIs
- Graceful error handling with detailed diagnostics

### Documentation
- Complete README with examples
- API reference documentation
- Contributing guidelines
- Shared test corpus for cross-language validation

## [0.0.1] - 2025-10-11

### Added
- Project structure and initial migration from rpax monorepo
- Core parsing functionality
- Test infrastructure
- Basic documentation

[Unreleased]: https://github.com/rpapub/xaml-parser/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/rpapub/xaml-parser/releases/tag/v0.1.0
[0.0.1]: https://github.com/rpapub/xaml-parser/releases/tag/v0.0.1
