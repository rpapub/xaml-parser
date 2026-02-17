# PLAN v0.2.3: Verify Imported .NET Namespaces Extraction

## Todo List

- [x] **Verify**: Confirm MetadataExtractor.extract_imported_namespaces() works correctly
- [x] **Test corpus**: Test extraction against test-corpus projects
- [x] **Add unit tests**: Add comprehensive tests for namespace extraction
- [x] **Test edge cases**: Empty lists, multiple collections, malformed XAML
- [x] **Verify DTO**: Confirm imported_namespaces propagates to output
- [x] **Documentation**: Update docstrings if needed

---

## Status
**Completed** - Unit Tests Added, Feature Verified

## Priority
**MEDIUM**

## Version
0.2.3

---

## Current State Analysis

### Feature Already Implemented!

The `extract_imported_namespaces()` feature **already exists** in the standalone xaml-parser:

**MetadataExtractor** (`extractors.py:868-886`):
```python
@staticmethod
def extract_imported_namespaces(root: ET.Element) -> list[str]:
    """Extract .NET namespaces from TextExpression.NamespacesForImplementation.

    Returns:
        List of .NET namespace strings (e.g., "System.Activities", "UiPath.Core")
    """
    namespaces = []

    for elem in root.iter():
        # Look for TextExpression.NamespacesForImplementation element
        if "NamespacesForImplementation" in elem.tag:
            # Find Collection child
            for collection in elem:
                # Find all x:String children containing namespace names
                for ns_elem in collection:
                    if ns_elem.text and ns_elem.text.strip():
                        namespaces.append(ns_elem.text.strip())

    return namespaces
```

**Model Field** (`models.py:34`):
```python
imported_namespaces: list[str] = field(default_factory=list)
```

**Parser Integration** (`parser.py:271`):
```python
content.imported_namespaces = self._extract_imported_namespaces(root)
```

---

## Problem Statement

While the implementation exists, we need to:
1. **Verify correctness** against real UiPath XAML files
2. **Add comprehensive tests** for edge cases
3. **Confirm output** in developer tests
4. **Document expected namespaces** for UiPath projects

---

## XAML Structure Reference

UiPath workflows store imported .NET namespaces in:

```xml
<Activity x:Class="Main" ...>
  <TextExpression.NamespacesForImplementation>
    <scg:List x:TypeArguments="x:String" Capacity="32">
      <x:String>System</x:String>
      <x:String>System.Collections.Generic</x:String>
      <x:String>System.Data</x:String>
      <x:String>System.Linq</x:String>
      <x:String>UiPath.Core</x:String>
      <x:String>UiPath.Core.Activities</x:String>
    </scg:List>
  </TextExpression.NamespacesForImplementation>
  ...
</Activity>
```

---

## Verification Tasks

### Task 1: Test with Corpus Projects

```bash
# Run developer tests
uv run python developer-tests/test_corpus_output.py

# Check imported_namespaces count
cat developer-tests/output/CORE_00000001/nested_view.json | jq '.workflows[0].imported_namespaces | length'
```

### Task 2: Add Unit Tests

```python
# File: python/tests/unit/test_extractors.py

class TestMetadataExtractor:
    def test_extract_imported_namespaces(self):
        """Test extraction of .NET namespaces."""
        xaml = '''<Activity xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
            xmlns:scg="clr-namespace:System.Collections.Generic;assembly=mscorlib">
            <TextExpression.NamespacesForImplementation>
                <scg:List x:TypeArguments="x:String">
                    <x:String>System</x:String>
                    <x:String>System.Linq</x:String>
                    <x:String>UiPath.Core</x:String>
                </scg:List>
            </TextExpression.NamespacesForImplementation>
        </Activity>'''
        root = parse_xaml_string(xaml)

        result = MetadataExtractor.extract_imported_namespaces(root)

        assert len(result) == 3
        assert "System" in result
        assert "System.Linq" in result
        assert "UiPath.Core" in result

    def test_extract_imported_namespaces_empty(self):
        """Test when no namespaces are imported."""
        xaml = '''<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities">
        </Activity>'''
        root = parse_xaml_string(xaml)

        result = MetadataExtractor.extract_imported_namespaces(root)
        assert result == []

    def test_extract_imported_namespaces_whitespace(self):
        """Test handling of whitespace in namespace names."""
        xaml = '''<Activity xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
            xmlns:scg="clr-namespace:System.Collections.Generic;assembly=mscorlib">
            <TextExpression.NamespacesForImplementation>
                <scg:List x:TypeArguments="x:String">
                    <x:String>  System  </x:String>
                </scg:List>
            </TextExpression.NamespacesForImplementation>
        </Activity>'''
        root = parse_xaml_string(xaml)

        result = MetadataExtractor.extract_imported_namespaces(root)
        assert result == ["System"]  # Trimmed
```

---

## Expected Namespaces (Common UiPath)

Typical UiPath workflows import these .NET namespaces:

| Namespace | Purpose |
|-----------|---------|
| `System` | Core .NET types |
| `System.Collections.Generic` | Collections |
| `System.Data` | DataTable support |
| `System.Linq` | LINQ queries |
| `System.Activities` | WF4 activities |
| `System.Activities.Statements` | Built-in activities |
| `UiPath.Core` | UiPath core types |
| `UiPath.Core.Activities` | UiPath activities |

---

## Edge Cases to Test

| Scenario | Expected Result |
|----------|-----------------|
| Standard list | All namespaces extracted |
| Empty list | Returns [] |
| No NamespacesForImplementation | Returns [] |
| Whitespace in names | Trimmed |
| Duplicate namespaces | All included (dedupe optional) |

---

## Files to Review

| File | Line | Purpose |
|------|------|---------|
| `python/xaml_parser/extractors.py` | 868-886 | MetadataExtractor.extract_imported_namespaces |
| `python/xaml_parser/models.py` | 34 | WorkflowContent.imported_namespaces field |
| `python/xaml_parser/parser.py` | 271 | Integration in parse flow |

---

## Validation Criteria

- [ ] Unit tests pass for all edge cases
- [ ] Corpus projects return expected namespace lists
- [ ] Developer test output shows imported_namespaces
- [ ] Common UiPath namespaces are correctly extracted

---

## Estimated Effort

| Task | Effort |
|------|--------|
| Verify existing implementation | 30 minutes |
| Add unit tests | 1 hour |
| Test corpus projects | 30 minutes |
| **Total** | **~2 hours** |

---

## Notes

This plan is a **verification task**, not an implementation task. The feature already exists and appears complete. Focus on test coverage and validation.
