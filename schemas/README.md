# XAML Parser JSON Schemas

This directory contains JSON schemas that define the structure and validation rules for XAML parser output. These schemas serve as the contract between different language implementations (Python, Go, etc.) and ensure consistent output format.

## Schemas

### `parse_result.schema.json`

Top-level parse result structure containing:
- **content**: Parsed workflow content (or null on failure)
- **success**: Boolean indicating parse success
- **errors**: Array of error messages
- **warnings**: Array of warning messages
- **parse_time_ms**: Parsing duration in milliseconds
- **file_path**: Source file path
- **diagnostics**: Detailed diagnostic information
- **config_used**: Parser configuration

### `workflow_content.schema.json`

Complete parsed workflow content structure:
- **arguments**: Workflow argument definitions
- **variables**: Workflow variable definitions
- **activities**: Complete activity tree with metadata
- **root_annotation**: Main workflow description
- **namespaces**: XML namespace mappings
- **assembly_references**: External assembly references
- **expression_language**: VB.NET or C#
- **metadata**: Additional metadata
- **total_***: Summary counts

## Nested Definitions

### WorkflowArgument
- name, type, direction (in/out/inout)
- annotation, default_value

### WorkflowVariable
- name, type, scope
- default_value

### ActivityContent
- tag, activity_id, display_name, annotation
- visible_attributes, invisible_attributes
- configuration, variables, expressions
- parent_activity_id, child_activities
- depth_level, xpath_location, source_line

### Expression
- content, expression_type, language
- context, contains_variables, contains_methods

## Versioning

Schemas follow [Semantic Versioning](https://semver.org/) principles:

- **Major version**: Breaking changes to required fields or data types
- **Minor version**: Backward-compatible additions (new optional fields)
- **Patch version**: Clarifications, documentation, non-breaking fixes

Current schema version is embedded in the `$id` field of each schema.

## Usage

### Python

```python
from xaml_parser.validation import validate_output, get_validator

# Validate parser output
result = parser.parse_file(Path("workflow.xaml"))
errors = validate_output(result)

if errors:
    print("Validation failed:", errors)
```

### Go (Future)

```go
import "github.com/rpapub/xaml-parser/go/validation"

result, err := parser.ParseFile("workflow.xaml")
if err != nil {
    log.Fatal(err)
}

if err := validation.Validate(result); err != nil {
    log.Printf("Validation failed: %v", err)
}
```

## Schema Evolution

When modifying schemas:

1. **Never remove required fields** - this breaks existing implementations
2. **Add new fields as optional** - set `"required": false` or omit from required array
3. **Document changes** - update this README and CHANGELOG
4. **Update tests** - ensure golden freeze tests validate against new schema
5. **Bump version** - update `$id` field according to semver rules

## Validation Tools

Schemas can be validated using standard JSON Schema validators:

```bash
# Using ajv-cli
npm install -g ajv-cli
ajv validate -s parse_result.schema.json -d ../testdata/golden/*.json

# Using python jsonschema
pip install jsonschema
python -m jsonschema -i ../testdata/golden/simple_sequence.json parse_result.schema.json
```

## Cross-Language Testing

These schemas enable cross-language validation:
- Python implementation outputs JSON
- JSON validates against schemas
- Go implementation reads same test data
- Both produce schema-compliant output
- Outputs can be compared for consistency

## References

- [JSON Schema Specification](https://json-schema.org/specification.html)
- [Understanding JSON Schema](https://json-schema.org/understanding-json-schema/)
- [JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12/schema)
