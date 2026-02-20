# PLAN v0.2.2: Verify XAML Class Extraction

## Todo List

- [x] **Verify**: Confirm MetadataExtractor.extract_xaml_class() works correctly
- [x] **Test corpus**: Test extraction against test-corpus projects
- [x] **Add unit tests**: Add comprehensive tests for x:Class extraction
- [x] **Test edge cases**: Multiple namespaces, missing x:Class, aliased prefixes
- [x] **Verify DTO**: Confirm xaml_class propagates to WorkflowDto
- [x] **Documentation**: Update docstrings if needed

---

## Status
**Completed** - Unit Tests Added, Feature Verified

## Priority
**MEDIUM**

## Version
0.2.2

---

## Current State Analysis

### Feature Already Implemented!

The `extract_xaml_class()` feature **already exists** in the standalone xaml-parser:

**MetadataExtractor** (`extractors.py:838-865`):
```python
@staticmethod
def extract_xaml_class(root: ET.Element, namespaces: dict[str, str]) -> str | None:
    """Extract x:Class attribute from root Activity element."""
    # Try to find x:Class attribute with namespace
    x_ns = namespaces.get("x", "")
    if x_ns:
        class_attr = root.get(f"{{{x_ns}}}Class")
        if class_attr:
            return class_attr

    # Fallback: try common namespace URIs
    common_x_namespaces = [
        "http://schemas.microsoft.com/winfx/2006/xaml",
        "http://schemas.microsoft.com/winfx/2009/xaml",
    ]
    for ns_uri in common_x_namespaces:
        class_attr = root.get(f"{{{ns_uri}}}Class")
        if class_attr:
            return class_attr

    return None
```

**Model Field** (`models.py:30`):
```python
xaml_class: str | None = None  # x:Class attribute from root Activity element
```

**Parser Integration** (`parser.py:267`):
```python
content.xaml_class = self._extract_xaml_class(root, content.namespaces)
```

---

## Problem Statement

While the implementation exists, we need to:
1. **Verify correctness** against real UiPath XAML files
2. **Add comprehensive tests** for edge cases
3. **Confirm DTO propagation** to final output
4. **Document behavior** in developer tests

---

## Verification Tasks

### Task 1: Test with Corpus Projects

```bash
# Run developer tests and inspect output
uv run python developer-tests/test_corpus_output.py

# Check xaml_class in workflow outputs
cat developer-tests/output/CORE_00000001/workflows/*.json | jq '.xaml_class'
```

### Task 2: Add Unit Tests

```python
# File: python/tests/unit/test_extractors.py

class TestMetadataExtractor:
    def test_extract_xaml_class_standard(self):
        """Test x:Class extraction with standard namespace."""
        xaml = '''<Activity x:Class="Main"
            xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
        </Activity>'''
        root = parse_xaml_string(xaml)
        namespaces = MetadataExtractor.extract_namespaces(root)

        result = MetadataExtractor.extract_xaml_class(root, namespaces)
        assert result == "Main"

    def test_extract_xaml_class_with_namespace(self):
        """Test x:Class with fully qualified class name."""
        xaml = '''<Activity x:Class="MyProject.Workflows.Main"
            xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
        </Activity>'''
        root = parse_xaml_string(xaml)
        namespaces = MetadataExtractor.extract_namespaces(root)

        result = MetadataExtractor.extract_xaml_class(root, namespaces)
        assert result == "MyProject.Workflows.Main"

    def test_extract_xaml_class_missing(self):
        """Test when x:Class is not present."""
        xaml = '''<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities">
        </Activity>'''
        root = parse_xaml_string(xaml)
        namespaces = MetadataExtractor.extract_namespaces(root)

        result = MetadataExtractor.extract_xaml_class(root, namespaces)
        assert result is None

    def test_extract_xaml_class_2009_namespace(self):
        """Test x:Class with 2009 XAML namespace."""
        xaml = '''<Activity x:Class="Main"
            xmlns:x="http://schemas.microsoft.com/winfx/2009/xaml">
        </Activity>'''
        root = parse_xaml_string(xaml)
        namespaces = MetadataExtractor.extract_namespaces(root)

        result = MetadataExtractor.extract_xaml_class(root, namespaces)
        assert result == "Main"
```

### Task 3: Verify DTO Output

Confirm `xaml_class` appears in:
1. `WorkflowContent.xaml_class` (internal model)
2. `WorkflowDto.metadata.xaml_class` (if exposed in DTO)
3. JSON output via emitters

---

## Edge Cases to Test

| Scenario | Expected Result |
|----------|-----------------|
| Standard `x:Class="Main"` | Returns "Main" |
| Namespaced `x:Class="Project.Main"` | Returns "Project.Main" |
| Missing x:Class | Returns None |
| Different x namespace prefix | Fallback to common URIs |
| 2006 vs 2009 XAML namespace | Both work |

---

## Files to Review

| File | Line | Purpose |
|------|------|---------|
| `python/xaml_parser/extractors.py` | 838-865 | MetadataExtractor.extract_xaml_class |
| `python/xaml_parser/models.py` | 30 | WorkflowContent.xaml_class field |
| `python/xaml_parser/parser.py` | 267 | Integration in parse flow |
| `python/xaml_parser/parser.py` | 549-559 | Delegate method |

---

## Validation Criteria

- [ ] Unit tests pass for all edge cases
- [ ] Corpus projects return expected xaml_class values
- [ ] Developer test output shows xaml_class
- [ ] No regressions in existing tests

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

This plan is a **verification task**, not an implementation task. The feature already exists and appears to be complete. We need to ensure it works correctly and has adequate test coverage.
