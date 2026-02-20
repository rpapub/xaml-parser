# PLAN v0.2.1: Case-Insensitive Default Value Extraction

## Todo List

- [x] **Research**: Confirm which code paths use parser.py vs extractors.py
- [x] **Fix parser.py**: Update `_extract_arguments()` to check both `default` and `Default`
- [x] **Add test fixtures**: Create XAML with capitalized `Default` attribute for arguments
- [x] **Add unit tests**: Test both lowercase and uppercase default attribute extraction
- [x] **Add integration test**: End-to-end test with real corpus XAML
- [x] **Run full test suite**: Ensure no regressions
- [x] **Update CHANGELOG**: Document the bug fix

---

## Status
**Completed** - Bug Fixed

## Priority
**HIGH** - Bug Fix

## Version
0.2.1

---

## Problem Statement

### The Bug

The `parser.py._extract_arguments()` method only checks lowercase `default` attribute:

**File**: `python/xaml_parser/parser.py:371`
```python
# CURRENT (BUG):
default_value = prop.get("default") or prop.text
```

This misses default values stored in the capitalized `Default` attribute, which UiPath sometimes uses.

### Impact

- **Data Loss**: Arguments with `Default="value"` are parsed with `default_value=None`
- **Silent Failure**: No error is raised, the value is simply missing
- **Inconsistency**: `extractors.py` correctly handles both cases, but `parser.py` does not

### Evidence

**rpax/src/xaml_parser/extractors.py:74-76** (CORRECT):
```python
default_value = (
    prop.get("default") or
    prop.get("Default") or
    prop.text
)
```

**rpax/src/xaml_parser/parser.py:313** (BUG - same as standalone):
```python
default_value = prop.get("default") or prop.text
```

**standalone xaml-parser/python/xaml_parser/parser.py:371** (BUG):
```python
default_value = prop.get("default") or prop.text
```

**standalone xaml-parser/python/xaml_parser/extractors.py:73** (CORRECT):
```python
default_value = prop.get("default") or prop.get("Default") or prop.text
```

---

## Root Cause Analysis

### Two Code Paths

The xaml-parser has **two parallel implementations** for argument extraction:

1. **`parser.py._extract_arguments()`** (lines 340-382)
   - Older implementation embedded in XamlParser class
   - Used by direct `XamlParser.parse_file()` calls
   - **HAS THE BUG**

2. **`extractors.py.ArgumentExtractor.extract_arguments()`** (lines 31-85)
   - Newer modular extractor implementation
   - Used when explicitly calling `ArgumentExtractor`
   - **CORRECT IMPLEMENTATION**

### Why Both Exist?

The extractors were refactored into separate classes for modularity, but the parser.py still contains legacy methods that weren't fully deprecated.

---

## Solution

### Approach 1: Fix parser.py (Recommended)

Update `parser.py._extract_arguments()` to match extractors.py behavior:

**File**: `python/xaml_parser/parser.py:371`
```python
# BEFORE (BUG):
default_value = prop.get("default") or prop.text

# AFTER (FIX):
default_value = prop.get("default") or prop.get("Default") or prop.text
```

### Approach 2: Delegate to Extractors (Alternative)

Refactor parser.py to delegate to extractors.py instead of duplicating logic. This is a larger change but prevents future drift.

**Recommendation**: Approach 1 for this bug fix, Approach 2 as future refactoring work.

---

## Files to Modify

### Primary Changes

| File | Line | Change |
|------|------|--------|
| `python/xaml_parser/parser.py` | 371 | Add `prop.get("Default")` check |

### Verification (Already Correct)

| File | Line | Status |
|------|------|--------|
| `python/xaml_parser/extractors.py` | 73 | Already checks both cases |
| `python/xaml_parser/extractors.py` | 115 | VariableExtractor - only `Default` (correct for variables) |
| `python/xaml_parser/extractors.py` | 361 | Activity variables - only `Default` (correct) |

### Test Files to Add/Modify

| File | Change |
|------|--------|
| `python/tests/unit/conftest.py` | Add fixture with `Default="value"` attribute |
| `python/tests/unit/test_parser.py` | Add test for parser._extract_arguments with Default |

---

## Implementation Details

### Step 1: Fix parser.py

```python
# File: python/xaml_parser/parser.py
# Line: 371

# Change from:
default_value = prop.get("default") or prop.text

# To:
default_value = prop.get("default") or prop.get("Default") or prop.text
```

### Step 2: Add Test Fixture

```python
# File: python/tests/unit/conftest.py
# Add new fixture:

@pytest.fixture
def xaml_with_capitalized_default():
    """XAML with capitalized Default attribute on argument."""
    return '''<?xml version="1.0" encoding="utf-8"?>
<Activity x:Class="TestWorkflow"
    xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
    xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
    xmlns:sap2010="http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation">
    <x:Members>
        <x:Property Name="in_ConfigPath" Type="InArgument(x:String)" Default="Config.xlsx" />
        <x:Property Name="in_FilePath" Type="InArgument(x:String)" default="data.csv" />
    </x:Members>
    <Sequence DisplayName="Main">
    </Sequence>
</Activity>'''
```

### Step 3: Add Unit Tests

```python
# File: python/tests/unit/test_parser.py

def test_extract_arguments_with_capitalized_default(xaml_with_capitalized_default):
    """Test that both 'default' and 'Default' attributes are extracted."""
    parser = XamlParser()
    root = parse_xaml_string(xaml_with_capitalized_default)
    namespaces = {"x": "http://schemas.microsoft.com/winfx/2006/xaml"}

    arguments = parser._extract_arguments(root, namespaces)

    config_arg = next(a for a in arguments if a.name == "in_ConfigPath")
    file_arg = next(a for a in arguments if a.name == "in_FilePath")

    assert config_arg.default_value == "Config.xlsx"  # Capitalized Default
    assert file_arg.default_value == "data.csv"       # Lowercase default
```

### Step 4: Verify with Developer Tests

```bash
# Run developer test to verify output
cd D:\github.com\rpapub\xaml-parser
uv run python developer-tests/test_corpus_output.py

# Inspect argument default values in output
cat developer-tests/output/CORE_00000001/workflows/*.json | jq '.arguments'
```

---

## Test Plan

### Unit Tests

1. **test_argument_lowercase_default**: Verify `default="value"` is extracted
2. **test_argument_capitalized_default**: Verify `Default="value"` is extracted
3. **test_argument_both_defaults_in_same_file**: Verify both work together
4. **test_argument_default_from_text_content**: Verify fallback to `prop.text`
5. **test_argument_no_default**: Verify `None` when no default present

### Regression Tests

1. **test_existing_fixtures_unchanged**: Run all existing tests, ensure no regressions

---

## Validation Criteria

### Success Criteria

- [ ] All existing tests pass (no regressions)
- [ ] New tests for capitalized Default pass
- [ ] Developer test output shows correct default values
- [ ] Arguments with `Default="..."` are correctly extracted
- [ ] Arguments with `default="..."` are still correctly extracted

### Manual Verification

```bash
# Run all tests
uv run pytest tests/ -v

# Run specific test
uv run pytest tests/unit/test_parser.py -k "capitalized_default" -v

# Check developer output
uv run python developer-tests/test_corpus_output.py
```

---

## Risks and Mitigations

### Risk 1: Breaking Existing Behavior

**Mitigation**: The change is additive (adding a fallback), not modifying existing logic. All existing tests should pass unchanged.

### Risk 2: Order of Precedence

**Question**: If both `default` and `Default` are present, which wins?

**Answer**: The `or` chain short-circuits, so lowercase `default` takes precedence. This matches extractors.py behavior.

---

## Estimated Effort

| Task | Effort |
|------|--------|
| Fix parser.py | 5 minutes |
| Add test fixture | 10 minutes |
| Add unit tests | 30 minutes |
| Run full test suite | 10 minutes |
| **Total** | **~1 hour** |

---

## References

### ADR Alignment

- **ADR-DTO-DESIGN.md**: DTOs should contain complete, accurate data from parsing
- **ADR-GRAPH-ARCHITECTURE.md**: Parsing layer must extract all relevant data for downstream views

### Related Files

- `python/xaml_parser/parser.py` - XamlParser class with _extract_arguments
- `python/xaml_parser/extractors.py` - Modular extractors (already correct)
- `python/xaml_parser/models.py` - WorkflowArgument dataclass
- `developer-tests/test_corpus_output.py` - Developer validation script

### UiPath XAML Patterns

UiPath uses both attribute forms:
```xml
<!-- Lowercase (common) -->
<x:Property Name="arg1" Type="InArgument(x:String)" default="value" />

<!-- Capitalized (also valid) -->
<x:Property Name="arg2" Type="InArgument(x:String)" Default="value" />

<!-- Text content fallback -->
<x:Property Name="arg3" Type="InArgument(x:String)">default text</x:Property>
```

---

## Changelog Entry

```markdown
## [0.2.1] - 2025-XX-XX

### Fixed
- Case-insensitive default value extraction: Arguments with capitalized `Default`
  attribute are now correctly extracted. Previously, only lowercase `default` was
  checked in `parser.py._extract_arguments()`, causing default values to be lost.
```

---

## Approval

- [ ] Plan reviewed
- [ ] Implementation approved
- [ ] Ready for development
