# PLAN v0.2.5: Verify Assembly Reference Extraction

## Todo List

- [x] **Verify**: Confirm MetadataExtractor.extract_assembly_references() works correctly
- [x] **Test modern format**: TextExpression.ReferencesForImplementation
- [x] **Test legacy format**: AssemblyReference elements
- [x] **Test deduplication**: Verify no duplicates when both formats present
- [x] **Add unit tests**: Cover all extraction paths
- [x] **Test corpus**: Verify extraction on real UiPath projects

---

## Status
**Completed** - Unit Tests Added, Feature Verified

## Priority
**MEDIUM**

## Version
0.2.5

---

## Current State Analysis

### Feature Already Implemented with Legacy Support!

The `extract_assembly_references()` feature **already exists** and handles BOTH modern and legacy formats:

**MetadataExtractor** (`extractors.py:889-914`):
```python
@staticmethod
def extract_assembly_references(root: ET.Element) -> list[str]:
    """Extract assembly references from TextExpression.ReferencesForImplementation.

    Returns:
        List of assembly names (e.g., "UiPath.System.Activities", "System.Core")
    """
    references = []

    for elem in root.iter():
        # Look for TextExpression.ReferencesForImplementation element
        if "ReferencesForImplementation" in elem.tag:
            # Find Collection child
            for collection in elem:
                # Find all AssemblyReference children
                for ref_elem in collection:
                    if ref_elem.text and ref_elem.text.strip():
                        references.append(ref_elem.text.strip())

    # Also check for old-style AssemblyReference elements (legacy)
    for elem in root.iter():
        if elem.tag.endswith("AssemblyReference"):
            ref = elem.text or elem.get("Assembly")
            if ref and ref.strip() and ref.strip() not in references:
                references.append(ref.strip())

    return references
```

**Key Features:**
- ✅ Modern: `TextExpression.ReferencesForImplementation`
- ✅ Legacy: `AssemblyReference` elements
- ✅ Deduplication: `ref.strip() not in references`
- ✅ Attribute fallback: `elem.get("Assembly")`

**Model Field** (`models.py:36`):
```python
assembly_references: list[str] = field(default_factory=list)
```

**Parser Integration** (`parser.py:275-276`):
```python
if self.config["extract_assembly_references"]:
    content.assembly_references = self._extract_assembly_references(root)
```

---

## Problem Statement

While the implementation exists and appears complete, we need to:
1. **Verify correctness** against real UiPath XAML files
2. **Add comprehensive tests** for both modern and legacy formats
3. **Confirm deduplication** works correctly
4. **Document extraction behavior**

---

## XAML Structure Reference

### Modern Format (UiPath 20.x+)

```xml
<Activity x:Class="Main" ...>
  <TextExpression.ReferencesForImplementation>
    <scg:List x:TypeArguments="AssemblyReference">
      <AssemblyReference>UiPath.System.Activities</AssemblyReference>
      <AssemblyReference>UiPath.Excel.Activities</AssemblyReference>
      <AssemblyReference>System.Core</AssemblyReference>
    </scg:List>
  </TextExpression.ReferencesForImplementation>
</Activity>
```

### Legacy Format (Older UiPath Versions)

```xml
<Activity x:Class="Main" ...>
  <AssemblyReference Assembly="UiPath.System.Activities" />
  <AssemblyReference>UiPath.Excel.Activities</AssemblyReference>
</Activity>
```

---

## Verification Tasks

### Task 1: Test with Corpus Projects

```bash
# Run developer tests
uv run python developer-tests/test_corpus_output.py

# Check assembly_references
cat developer-tests/output/CORE_00000001/nested_view.json | jq '.workflows[0].assembly_references'
```

### Task 2: Add Unit Tests

```python
# File: python/tests/unit/test_extractors.py

class TestMetadataExtractor:
    def test_extract_assembly_references_modern(self):
        """Test modern ReferencesForImplementation format."""
        xaml = '''<Activity xmlns:scg="clr-namespace:System.Collections.Generic;assembly=mscorlib">
            <TextExpression.ReferencesForImplementation>
                <scg:List>
                    <AssemblyReference>UiPath.System.Activities</AssemblyReference>
                    <AssemblyReference>System.Core</AssemblyReference>
                </scg:List>
            </TextExpression.ReferencesForImplementation>
        </Activity>'''
        root = parse_xaml_string(xaml)

        result = MetadataExtractor.extract_assembly_references(root)

        assert len(result) == 2
        assert "UiPath.System.Activities" in result
        assert "System.Core" in result

    def test_extract_assembly_references_legacy(self):
        """Test legacy AssemblyReference elements."""
        xaml = '''<Activity>
            <AssemblyReference Assembly="UiPath.System.Activities" />
            <AssemblyReference>System.Core</AssemblyReference>
        </Activity>'''
        root = parse_xaml_string(xaml)

        result = MetadataExtractor.extract_assembly_references(root)

        assert len(result) == 2
        assert "UiPath.System.Activities" in result
        assert "System.Core" in result

    def test_extract_assembly_references_no_duplicates(self):
        """Test deduplication when both formats present."""
        xaml = '''<Activity xmlns:scg="clr-namespace:System.Collections.Generic;assembly=mscorlib">
            <TextExpression.ReferencesForImplementation>
                <scg:List>
                    <AssemblyReference>System.Core</AssemblyReference>
                </scg:List>
            </TextExpression.ReferencesForImplementation>
            <AssemblyReference>System.Core</AssemblyReference>
        </Activity>'''
        root = parse_xaml_string(xaml)

        result = MetadataExtractor.extract_assembly_references(root)

        assert result.count("System.Core") == 1  # No duplicates

    def test_extract_assembly_references_empty(self):
        """Test when no references present."""
        xaml = '''<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities">
        </Activity>'''
        root = parse_xaml_string(xaml)

        result = MetadataExtractor.extract_assembly_references(root)
        assert result == []
```

---

## Expected Assemblies (Common UiPath)

| Assembly | Purpose |
|----------|---------|
| `UiPath.System.Activities` | Core UiPath activities |
| `UiPath.Excel.Activities` | Excel automation |
| `UiPath.UIAutomation.Activities` | UI automation |
| `UiPath.Mail.Activities` | Email handling |
| `System.Core` | .NET Core extensions |
| `System.Data` | DataTable support |
| `mscorlib` | Core .NET runtime |

---

## Edge Cases to Test

| Scenario | Expected Result |
|----------|-----------------|
| Modern format only | All references extracted |
| Legacy format only | All references extracted |
| Both formats with overlap | Deduplicated |
| Whitespace in names | Trimmed |
| Empty Assembly attribute | Skipped |
| No references | Returns [] |

---

## Files to Review

| File | Line | Purpose |
|------|------|---------|
| `python/xaml_parser/extractors.py` | 889-914 | MetadataExtractor.extract_assembly_references |
| `python/xaml_parser/models.py` | 36 | WorkflowContent.assembly_references field |
| `python/xaml_parser/parser.py` | 275-276 | Conditional integration |

---

## Validation Criteria

- [ ] Unit tests pass for modern format
- [ ] Unit tests pass for legacy format
- [ ] Deduplication works correctly
- [ ] Corpus projects show expected assemblies
- [ ] No regressions in existing tests

---

## Estimated Effort

| Task | Effort |
|------|--------|
| Verify existing implementation | 30 minutes |
| Add unit tests | 1.5 hours |
| Test corpus projects | 30 minutes |
| **Total** | **~2.5 hours** |

---

## Notes

This plan is a **verification task**, not an implementation task. The feature already exists with both modern and legacy support. Focus on test coverage and validation of edge cases.
