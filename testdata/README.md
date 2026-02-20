# Test Data Corpus for XAML Parser

This directory contains a comprehensive test corpus shared across all language implementations (Python, Go, etc.) of the XAML parser. The test data is organized to support both golden freeze testing and realistic project structure testing.

## Directory Structure

```
testdata/
├── README.md                    # This file
├── golden/                      # Golden freeze test pairs
│   ├── simple_sequence.xaml
│   ├── simple_sequence.json
│   ├── complex_workflow.xaml
│   ├── complex_workflow.json
│   ├── invoke_workflows.xaml
│   ├── invoke_workflows.json
│   ├── ui_automation.xaml
│   └── ui_automation.json
└── corpus/                      # Structured test projects
    ├── README.md
    ├── simple_project/          # Basic project with minimal workflows
    │   ├── project.json         # UiPath project configuration
    │   ├── Main.xaml            # Simple main workflow
    │   └── workflows/           # Additional workflows
    │       └── GetConfig.xaml
    └── edge_cases/              # Edge cases and error conditions
        ├── malformed.xaml       # Malformed XML for error testing
        └── empty.xaml           # Empty workflow
```

## Golden Freeze Tests

Golden freeze tests provide reference implementations with known-good output. Each test consists of:
- **Input**: A XAML workflow file (`.xaml`)
- **Expected Output**: The corresponding JSON output (`.json`)

### Test Files

#### `simple_sequence.xaml` / `simple_sequence.json`
- **Purpose**: Basic sequence with variables, assignments, logging, and conditional logic
- **Key Activities**: Sequence, Assign, LogMessage, If
- **Business Logic**: Variable manipulation, conditional execution
- **Expected Activity Count**: 5 activities
- **Variables**: testMessage (String), counter (Int32)

#### `complex_workflow.xaml` / `complex_workflow.json`
- **Purpose**: Complex nested structures with loops, error handling, and branching logic
- **Key Activities**: TryCatch, ForEach, Switch, nested Sequences
- **Business Logic**: List processing with type-specific handling
- **Expected Activity Count**: 15+ activities
- **Variables**: itemList (List), currentItem (String), itemCount (Int32), processComplete (Boolean)

#### `invoke_workflows.xaml` / `invoke_workflows.json`
- **Purpose**: Workflow invocations with argument passing
- **Key Activities**: InvokeWorkflowFile with various argument patterns
- **Business Logic**: Framework/Process separation pattern
- **Expected Activity Count**: 8 activities
- **Invoked Workflows**: Framework\ValidateInput.xaml, Process\ProcessData.xaml, Framework\HandleError.xaml
- **Variables**: result1 (String), result2 (Int32), success (Boolean)

#### `ui_automation.xaml` / `ui_automation.json`
- **Purpose**: UI automation activities with selectors and target elements
- **Key Activities**: Click, TypeInto, ElementExists
- **Business Logic**: Web form interaction with selectors
- **Expected Activity Count**: 6 activities
- **Selectors**: Button, Input field, Submit button
- **Variables**: inputText (String), elementExists (Boolean)

## Corpus Tests

Corpus tests provide realistic project structures for comprehensive testing beyond individual workflow files.

### `simple_project/`

A basic UiPath project with minimal workflows demonstrating:
- **Arguments**: Input/output parameters with annotations
- **Variables**: Workflow and activity-scoped variables
- **Basic Activities**: Sequence, LogMessage, Assign, If/Else
- **Annotations**: Root and activity-level documentation

### `edge_cases/`

Edge cases and error conditions for robust parser testing:
- **Malformed XML**: Testing graceful degradation
- **Empty workflows**: Minimal workflow content
- **Encoding variations**: UTF-8, UTF-16, BOM handling

## Usage Across Languages

### Python

```python
from pathlib import Path
from xaml_parser import XamlParser

# Get test data directory (relative from python/tests/)
testdata_dir = Path(__file__).parent.parent / "testdata"
golden_dir = testdata_dir / "golden"
corpus_dir = testdata_dir / "corpus"

# Test with golden freeze data
parser = XamlParser()
result = parser.parse_file(golden_dir / "simple_sequence.xaml")

# Validate against golden output
import json
with open(golden_dir / "simple_sequence.json") as f:
    expected = json.load(f)
```

### Go (Future)

```go
import (
    "path/filepath"
    "testing"
)

func TestGoldenFreeze(t *testing.T) {
    testdataDir := filepath.Join("..", "testdata", "golden")
    xamlPath := filepath.Join(testdataDir, "simple_sequence.xaml")
    goldenPath := filepath.Join(testdataDir, "simple_sequence.json")

    // Parse and validate
    result, err := parser.ParseFile(xamlPath)
    if err != nil {
        t.Fatal(err)
    }

    // Compare with golden output
    expected := readGoldenJSON(goldenPath)
    assertEqual(t, expected, result)
}
```

## Test Coverage

This corpus provides coverage for:

- ✅ Basic activity types (Assign, LogMessage, If)
- ✅ UI automation activities (Click, TypeInto, ElementExists)
- ✅ Control flow (ForEach, Switch, TryCatch)
- ✅ Workflow invocations (InvokeWorkflowFile)
- ✅ Variable definitions and references
- ✅ Expression extraction (VB.NET and C#)
- ✅ Selector parsing
- ✅ Nested structures and complex hierarchies
- ✅ Error handling patterns
- ✅ Annotation extraction
- ✅ Arguments with directions and annotations
- ✅ Assembly references
- ✅ Namespace mappings

## Golden Freeze Philosophy

Golden freeze tests serve as:

1. **Regression Prevention**: Detect unintended changes to parser output
2. **Cross-Language Validation**: Ensure Python and Go implementations produce identical output
3. **Schema Compliance**: Validate output against JSON schemas
4. **Performance Benchmarks**: Track parsing performance over time
5. **Documentation**: Demonstrate expected parser behavior

## Updating Golden Data

When parser improvements require updating golden output:

1. **Parse new output**: Run parser on test XAML files
2. **Manual review**: Verify changes are correct and intentional
3. **Update JSON files**: Replace golden JSON with new output
4. **Document changes**: Note breaking changes in CHANGELOG
5. **Run full test suite**: Ensure all tests pass with new golden data

## Adding New Test Cases

When adding new test files:

1. **Create XAML file**: Add to `golden/` with descriptive name
2. **Generate golden output**: Parse and save JSON output
3. **Validate schema**: Ensure JSON conforms to schemas
4. **Update this README**: Document test purpose and expected counts
5. **Add test cases**: Create tests in each language implementation
6. **Commit both files**: XAML and JSON must be committed together

## Maintenance

- **Keep tests focused**: Each test should validate specific parser features
- **Minimize test data**: Use smallest XAML needed to demonstrate feature
- **Document expectations**: Clearly state what each test validates
- **Version test data**: Track changes to test corpus in git history

## License

Test data in this directory is licensed under CC-BY 4.0, same as the project.
