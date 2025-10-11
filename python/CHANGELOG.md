# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Production-ready packaging with quality gates
- Ruff linting and formatting
- Mypy strict type checking
- Pre-commit hooks
- Test coverage requirements (≥90%)

### Changed
- Bumped minimum Python version to 3.11
- Switched build backend to hatchling

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
