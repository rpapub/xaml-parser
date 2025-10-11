# XAML Parser Architecture

This document describes the design decisions, architecture patterns, and implementation philosophy of the XAML Parser project.

## Design Philosophy

### Zero Dependencies

The parser is designed to work with minimal external dependencies:

- **Python**: Only standard library (plus defusedxml for security)
- **Go**: Only standard library (planned)

This ensures:
- Easy installation and deployment
- Minimal security surface
- Long-term maintainability
- Fast startup time

### Multi-Language Support

The monorepo structure supports multiple language implementations with:
- **Shared test data**: Single source of truth for expected behavior
- **JSON schemas**: Contract between implementations
- **Consistent API**: Similar interfaces across languages

### Graceful Degradation

The parser handles malformed input gracefully:
- Continue parsing on non-critical errors
- Collect and report all errors
- Partial results when possible
- Detailed diagnostics for debugging

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    XAML Parser                          │
├─────────────────────────────────────────────────────────┤
│  Input Layer                                            │
│    - File reading                                       │
│    - Encoding detection                                 │
│    - XML parsing                                        │
├─────────────────────────────────────────────────────────┤
│  Extraction Layer                                       │
│    - Argument extraction                                │
│    - Variable extraction                                │
│    - Activity extraction                                │
│    - Annotation extraction                              │
│    - Expression extraction                              │
├─────────────────────────────────────────────────────────┤
│  Processing Layer                                       │
│    - Activity tree building                             │
│    - Expression analysis                                │
│    - Namespace resolution                               │
│    - ViewState handling                                 │
├─────────────────────────────────────────────────────────┤
│  Validation Layer                                       │
│    - Schema validation                                  │
│    - Data completeness checks                           │
│    - Type validation                                    │
├─────────────────────────────────────────────────────────┤
│  Output Layer                                           │
│    - Model construction                                 │
│    - JSON serialization                                 │
│    - Diagnostics reporting                              │
└─────────────────────────────────────────────────────────┘
```

## Component Design

### Parser (parser.py / parser.go)

Main orchestration component:

```python
class XamlParser:
    def __init__(self, config: Optional[Dict] = None)
    def parse_file(self, file_path: Path) -> ParseResult
    def parse_content(self, content: str) -> ParseResult
```

Responsibilities:
- Configuration management
- High-level parsing workflow
- Error collection and reporting
- Performance tracking

### Extractors (extractors.py)

Specialized components for extracting specific XAML elements:

- **ArgumentExtractor**: Extracts workflow arguments with types and directions
- **VariableExtractor**: Extracts variables from all scopes
- **ActivityExtractor**: Extracts activities with full metadata
- **AnnotationExtractor**: Extracts documentation annotations
- **MetadataExtractor**: Extracts assembly references and namespaces

Design pattern: **Strategy Pattern**
- Each extractor implements a focused extraction strategy
- Can be used independently or in combination
- Easy to test in isolation

### Models (models.py / models.go)

Data models using dataclasses (Python) or structs (Go):

```python
@dataclass
class WorkflowContent:
    arguments: List[WorkflowArgument]
    variables: List[WorkflowVariable]
    activities: List[Activity]
    # ...

@dataclass
class Activity:
    tag: str
    activity_id: str
    display_name: Optional[str]
    # ...
```

Design decisions:
- **Immutability**: Models are immutable where possible
- **Type Safety**: Strong typing enforced
- **JSON Serialization**: Direct mapping to JSON schemas
- **Optional Fields**: Use Optional/nullable types appropriately

### Utilities (utils.py)

Helper functions organized by domain:

- **XmlUtils**: XML parsing, namespace handling
- **TextUtils**: String cleaning, normalization
- **ValidationUtils**: Data validation helpers
- **DataUtils**: Data transformation utilities

Design pattern: **Static Utility Pattern**
- Pure functions with no side effects
- Easy to test
- Reusable across components

### Validation (validation.py)

Schema-based validation:

```python
def validate_output(result: ParseResult) -> List[str]:
    """Validate parse result against JSON schema."""
    # Returns list of validation errors
```

Uses JSON Schema Draft 2020-12 for validation.

## Data Flow

```
XAML File
    ↓
[Read & Parse XML]
    ↓
XML ElementTree
    ↓
[Extract Arguments] → WorkflowArgument[]
[Extract Variables] → WorkflowVariable[]
[Extract Activities] → Activity[]
[Extract Metadata] → Namespaces, Assembly Refs
    ↓
[Build Activity Tree]
    ↓
[Analyze Expressions]
    ↓
WorkflowContent
    ↓
[Validate Schema]
    ↓
ParseResult
    ↓
JSON Output
```

## Error Handling Strategy

### Error Levels

1. **Fatal Errors**: Stop parsing immediately
   - File not found
   - Invalid XML syntax
   - Critical configuration errors

2. **Errors**: Collected and reported, parsing continues
   - Missing required attributes
   - Unknown activity types
   - Invalid expression syntax

3. **Warnings**: Collected for informational purposes
   - Deprecated patterns
   - Unusual structures
   - Performance concerns

### Error Collection

```python
class ParseResult:
    success: bool
    errors: List[str]
    warnings: List[str]
    # ...
```

All errors are collected and reported together, enabling users to fix multiple issues in one iteration.

## Performance Considerations

### XML Parsing

- Use streaming parsers for large files (future enhancement)
- Limit recursion depth to prevent stack overflow
- Cache namespace mappings

### Memory Management

- Lazy evaluation where possible
- Avoid copying large data structures
- Clear intermediate structures when done

### Expression Analysis

- Parse expressions on demand (when extract_expressions=True)
- Cache compiled regex patterns
- Skip complex analysis in fast mode

## Testing Strategy

### Unit Tests

Test individual components in isolation:
- Extractors with minimal XML samples
- Utilities with edge cases
- Models with various inputs

### Integration Tests

Test complete parsing workflow:
- Golden freeze tests with known-good outputs
- Corpus tests with realistic project structures

### Cross-Language Tests

Ensure consistency between implementations:
- Both parse same XAML files
- Both produce identical JSON output
- Both validate against same schemas

### Test Data Organization

```
testdata/
├── golden/          # XAML + expected JSON pairs
│   ├── *.xaml
│   └── *.json
└── corpus/          # Complete project structures
    ├── simple_project/
    └── complex_project/
```

## Schema Design

### Versioning

Schemas use semantic versioning in the `$id` field:

```json
{
  "$id": "https://github.com/rpapub/xaml-parser/schemas/workflow_content.json",
  "version": "1.0.0"
}
```

### Extensibility

Schemas allow for future extensions:
- Optional fields for new features
- Additional properties in metadata objects
- Version-specific handling

### Validation

All parser output must validate against schemas:
- Enforces consistency
- Documents expected structure
- Enables cross-language testing

## Configuration System

### Default Configuration

Sensible defaults for common use cases:

```python
DEFAULT_CONFIG = {
    'extract_arguments': True,
    'extract_variables': True,
    'extract_activities': True,
    'extract_expressions': True,
    'extract_viewstate': False,  # Often not needed
    'strict_mode': False,         # Graceful degradation
    'max_depth': 50,              # Prevent deep recursion
}
```

### Custom Configuration

Users can override defaults:

```python
config = {
    'strict_mode': True,          # Fail on any error
    'extract_viewstate': True,    # Include UI metadata
    'max_depth': 100,             # Allow deeper nesting
}
parser = XamlParser(config)
```

## Future Enhancements

### Performance

- [ ] Streaming XML parser for very large files
- [ ] Parallel activity extraction
- [ ] Caching for repeated parses

### Features

- [ ] XAML generation (inverse operation)
- [ ] Workflow diff/compare functionality
- [ ] Query language for activities
- [ ] Visualization export

### Languages

- [ ] Rust implementation for maximum performance
- [ ] JavaScript/WASM for browser usage
- [ ] CLI tool for command-line usage

## Design Patterns Used

1. **Strategy Pattern**: Extractors implement different extraction strategies
2. **Builder Pattern**: ParseResult construction with diagnostics
3. **Factory Pattern**: Parser creation with configuration
4. **Singleton Pattern**: Schema validators (cached)
5. **Facade Pattern**: XamlParser provides simple interface to complex system

## Security Considerations

### XML Security

- Use defusedxml to prevent XML bombs, billion laughs, etc.
- Limit file size for parsing
- Limit recursion depth
- Validate encoding

### Expression Safety

- Do not execute expressions (parse only)
- Sanitize output for display
- Warn about potentially malicious patterns

## Monorepo Structure Benefits

1. **Single Source of Truth**: Test data shared across implementations
2. **Consistent Schemas**: All implementations validate against same schemas
3. **Coordinated Releases**: Version all implementations together
4. **Unified Documentation**: Architecture applies to all implementations
5. **Easy Comparison**: Side-by-side language examples

## References

- [JSON Schema Specification](https://json-schema.org/)
- [UiPath XAML Documentation](https://docs.uipath.com/)
- [Python Type Hints](https://peps.python.org/pep-0484/)
- [Go Project Layout](https://github.com/golang-standards/project-layout)
