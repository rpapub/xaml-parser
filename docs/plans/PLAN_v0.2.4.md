# PLAN v0.2.4: Implement Expression Language Detection

## Todo List

- [x] **Implement**: Add MetadataExtractor.extract_expression_language() method
- [x] **Add model field**: Add expression_language to WorkflowContent
- [x] **Integrate parser**: Call extractor from parser.py
- [x] **Add unit tests**: Test VB.NET, C#, and missing detection
- [x] **Test corpus**: Verify detection on real UiPath projects
- [x] **Update DTO**: Propagate to WorkflowDto if needed

---

## Status
**Completed** - Feature Implemented and Tested

## Priority
**LOW**

## Version
0.2.4

---

## Problem Statement

### Missing Feature

The standalone xaml-parser does **NOT** currently detect the expression language (VB.NET vs C#) used in a workflow. This information is important for:

1. **Expression parsing**: VB.NET uses `[variable]`, C# uses different syntax
2. **Tooling integration**: IDE features need to know the language
3. **Migration analysis**: Detecting legacy VB.NET vs modern C# workflows

### Evidence

**constants.py** has a default but no detection:
```python
DEFAULT_CONFIG = {
    ...
    'expression_language': 'VisualBasic'  # Hardcoded default!
}
```

**No extraction method exists** in MetadataExtractor.

---

## UiPath Expression Language Detection

### Method 1: TextExpression Settings (Primary)

UiPath stores expression language settings in XAML:

```xml
<Activity x:Class="Main" ...>
  <TextExpression.ReferencesForImplementation>
    ...
  </TextExpression.ReferencesForImplementation>
  <!-- For VB.NET: -->
  <VisualBasic.Settings>
    <x:Null />
  </VisualBasic.Settings>
</Activity>
```

Or for C#:
```xml
<Activity x:Class="Main" ...>
  <!-- C# workflows have CSharpValue elements -->
  <sco:Collection x:TypeArguments="InArgument" ...>
    <CSharpValue x:TypeArguments="x:String" ...>
```

### Method 2: Expression Type Detection (Secondary)

- **VB.NET**: Uses `VisualBasicValue`, `VisualBasicReference` elements
- **C#**: Uses `CSharpValue`, `CSharpReference` elements

### Method 3: Project.json (Best Source)

```json
{
  "expressionLanguage": "VisualBasic"  // or "CSharp"
}
```

This is already parsed by ProjectParser!

---

## Implementation Plan

### Step 1: Add MetadataExtractor Method

```python
# File: python/xaml_parser/extractors.py
# Add to MetadataExtractor class:

@staticmethod
def extract_expression_language(root: ET.Element) -> str | None:
    """Detect expression language (VB.NET or C#) from workflow XAML.

    Detection strategies:
    1. Look for VisualBasic.Settings element → "VisualBasic"
    2. Look for CSharpValue/CSharpReference elements → "CSharp"
    3. Look for VisualBasicValue/VisualBasicReference elements → "VisualBasic"

    Returns:
        "VisualBasic", "CSharp", or None if not detected
    """
    # Strategy 1: Check for VisualBasic.Settings element
    for elem in root.iter():
        tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag

        if 'VisualBasic.Settings' in elem.tag or tag == 'Settings':
            # Check if it's in VisualBasic namespace
            if 'VisualBasic' in elem.tag:
                return "VisualBasic"

    # Strategy 2: Check for expression type elements
    for elem in root.iter():
        tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag

        if tag in ('CSharpValue', 'CSharpReference'):
            return "CSharp"
        if tag in ('VisualBasicValue', 'VisualBasicReference'):
            return "VisualBasic"

    # Strategy 3: Check for namespace declarations
    for key, value in root.attrib.items():
        if 'CSharpExpressions' in value:
            return "CSharp"
        if 'VisualBasic' in value:
            return "VisualBasic"

    return None  # Unable to detect
```

### Step 2: Add Model Field

```python
# File: python/xaml_parser/models.py
# In WorkflowContent class:

@dataclass
class WorkflowContent:
    ...
    # Expression settings
    expression_language: str | None = None  # "VisualBasic" or "CSharp"
```

### Step 3: Integrate in Parser

```python
# File: python/xaml_parser/parser.py
# In _parse_workflow_content():

# After line 276 (assembly_references):
content.expression_language = self._extract_expression_language(root)

# Add delegate method:
def _extract_expression_language(self, root: ET.Element) -> str | None:
    """Delegate to MetadataExtractor."""
    return MetadataExtractor.extract_expression_language(root)
```

### Step 4: Update ProjectParser Integration

The project.json already contains `expressionLanguage`. Ensure it's used:

```python
# File: python/xaml_parser/project.py
# Verify project-level expression_language is accessible
```

---

## Test Plan

### Unit Tests

```python
# File: python/tests/unit/test_extractors.py

class TestMetadataExtractor:
    def test_extract_expression_language_vb(self):
        """Test VB.NET detection via VisualBasic.Settings."""
        xaml = '''<Activity xmlns:vb="Microsoft.VisualBasic.Activities">
            <vb:VisualBasic.Settings>
                <x:Null />
            </vb:VisualBasic.Settings>
        </Activity>'''
        root = parse_xaml_string(xaml)

        result = MetadataExtractor.extract_expression_language(root)
        assert result == "VisualBasic"

    def test_extract_expression_language_csharp(self):
        """Test C# detection via CSharpValue element."""
        xaml = '''<Activity xmlns:cs="CSharpExpressions">
            <cs:CSharpValue x:TypeArguments="x:String">
                "test"
            </cs:CSharpValue>
        </Activity>'''
        root = parse_xaml_string(xaml)

        result = MetadataExtractor.extract_expression_language(root)
        assert result == "CSharp"

    def test_extract_expression_language_none(self):
        """Test when language cannot be detected."""
        xaml = '''<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities">
            <Sequence DisplayName="Main">
            </Sequence>
        </Activity>'''
        root = parse_xaml_string(xaml)

        result = MetadataExtractor.extract_expression_language(root)
        assert result is None
```

### Corpus Tests

```bash
# CORE_00000001 should be VisualBasic (from project_info)
cat developer-tests/output/CORE_00000001/nested_view.json | jq '.project_info.expression_language'
```

---

## Edge Cases

| Scenario | Detection | Expected |
|----------|-----------|----------|
| VisualBasic.Settings present | Strategy 1 | "VisualBasic" |
| CSharpValue elements | Strategy 2 | "CSharp" |
| VisualBasicValue elements | Strategy 2 | "VisualBasic" |
| Namespace declaration hint | Strategy 3 | Detected |
| No indicators | All fail | None |
| Mixed (edge case) | First match | Whichever found first |

---

## Files to Modify

| File | Change |
|------|--------|
| `python/xaml_parser/extractors.py` | Add extract_expression_language() |
| `python/xaml_parser/models.py` | Add expression_language field |
| `python/xaml_parser/parser.py` | Integrate extraction call |
| `python/tests/unit/test_extractors.py` | Add unit tests |

---

## Validation Criteria

- [ ] MetadataExtractor.extract_expression_language() implemented
- [ ] VB.NET workflows correctly detected
- [ ] C# workflows correctly detected
- [ ] None returned when detection fails
- [ ] Field propagates to parse output
- [ ] Unit tests pass

---

## Estimated Effort

| Task | Effort |
|------|--------|
| Implement extractor method | 1 hour |
| Add model field | 15 minutes |
| Integrate in parser | 15 minutes |
| Write unit tests | 1 hour |
| Test corpus | 30 minutes |
| **Total** | **~3 hours** |

---

## References

- UiPath expression languages: https://docs.uipath.com/activities/
- WF4 TextExpression: https://docs.microsoft.com/en-us/dotnet/framework/windows-workflow-foundation/
- project.json schema: expressionLanguage field
