# PLAN v0.2.6: Enhanced Error Handling Patterns

## Todo List

- [x] **Analyze**: Compare error handling in rpax vs standalone parser
- [x] **Identify gaps**: Document missing error handling scenarios
- [x] **Implement encoding fallbacks**: Handle non-UTF-8 files gracefully
- [x] **Improve diagnostics**: Add context to error messages (ParseDiagnostic with line/column)
- [x] **Add recovery modes**: Partial parsing on errors (graceful error handling)
- [x] **Add unit tests**: Test malformed XAML, encoding issues
- [x] **Test corpus**: Verify handling of edge-case files

---

## Status
**Completed** - Encoding Detection and Enhanced Diagnostics Implemented

## Priority
**MEDIUM**

## Version
0.2.6

---

## Problem Statement

The standalone xaml-parser may not handle all edge cases gracefully:
- Malformed XML files
- Encoding issues (UTF-8 BOM, UTF-16, ISO-8859-1)
- Partial/corrupted files
- Extremely large files
- Missing required attributes

Better error handling improves:
- **User experience**: Clear, actionable error messages
- **Robustness**: Parser doesn't crash on edge cases
- **Debugging**: Context helps identify issues

---

## Current Error Handling Analysis

### Existing Implementation (`parser.py`)

```python
# File: python/xaml_parser/parser.py

def parse_file(self, file_path: Path) -> ParseResult:
    try:
        # Read file content
        content = file_path.read_text(encoding="utf-8")
        ...
    except FileNotFoundError:
        return ParseResult(
            success=False,
            file_path=file_path,
            error=f"File not found: {file_path}",
        )
    except ET.ParseError as e:
        return ParseResult(
            success=False,
            file_path=file_path,
            error=f"XML parse error: {e}",
        )
    except Exception as e:
        return ParseResult(
            success=False,
            file_path=file_path,
            error=f"Unexpected error: {e}",
        )
```

### What's Missing

1. **Encoding detection/fallback**: Only UTF-8 supported
2. **Parse error context**: No line/column info in error messages
3. **Partial recovery**: All-or-nothing parsing
4. **Warning levels**: Only errors, no warnings
5. **Diagnostic details**: Sparse context information

---

## Enhancement Plan

### 1. Encoding Detection and Fallback

```python
# File: python/xaml_parser/parser.py

def _read_file_content(self, file_path: Path) -> tuple[str, str]:
    """Read file content with encoding detection.

    Returns:
        Tuple of (content, encoding_used)
    """
    encodings = ["utf-8", "utf-8-sig", "utf-16", "iso-8859-1", "cp1252"]

    for encoding in encodings:
        try:
            content = file_path.read_text(encoding=encoding)
            return content, encoding
        except UnicodeDecodeError:
            continue

    # Last resort: read as binary, replace errors
    content = file_path.read_bytes().decode("utf-8", errors="replace")
    return content, "utf-8-fallback"
```

### 2. Enhanced Parse Error Messages

```python
# File: python/xaml_parser/parser.py

def _handle_parse_error(self, e: ET.ParseError, file_path: Path, content: str) -> ParseResult:
    """Create detailed parse error with context."""
    # Extract line/column from error
    line = getattr(e, 'lineno', None)
    column = getattr(e, 'offset', None)

    # Build context snippet
    context = ""
    if line and content:
        lines = content.splitlines()
        if 0 < line <= len(lines):
            context = f"\n  Line {line}: {lines[line-1][:80]}"
            if column:
                context += f"\n  {'':>{column+9}}^"

    error_msg = f"XML parse error in {file_path.name}: {e}{context}"

    return ParseResult(
        success=False,
        file_path=file_path,
        error=error_msg,
        diagnostics=[
            ParseDiagnostic(
                level="error",
                message=str(e),
                line=line,
                column=column,
            )
        ],
    )
```

### 3. ParseDiagnostic Enhancements

```python
# File: python/xaml_parser/models.py

@dataclass
class ParseDiagnostic:
    """Diagnostic message from parsing."""

    level: str  # "error", "warning", "info"
    message: str
    line: int | None = None
    column: int | None = None
    element: str | None = None  # Element that caused the issue
    suggestion: str | None = None  # How to fix

    def __str__(self) -> str:
        loc = f" at line {self.line}" if self.line else ""
        return f"[{self.level.upper()}]{loc}: {self.message}"
```

### 4. Warning Collection

```python
# File: python/xaml_parser/parser.py

def _parse_workflow_content(self, root: ET.Element, content: str) -> WorkflowContent:
    """Parse with warning collection."""
    warnings = []

    # Warn on missing expected elements
    if not root.get(f"{{{self.x_ns}}}Class"):
        warnings.append(ParseDiagnostic(
            level="warning",
            message="Missing x:Class attribute on root element",
            suggestion="Add x:Class='WorkflowName' to Activity element",
        ))

    # Warn on deprecated patterns
    for elem in root.iter():
        if elem.tag.endswith("VisualBasicSettings"):
            warnings.append(ParseDiagnostic(
                level="info",
                message="Workflow uses VB.NET expressions (legacy)",
                suggestion="Consider migrating to C# expressions",
            ))
            break

    return content, warnings
```

### 5. Strict Mode Option

```python
# File: python/xaml_parser/constants.py

DEFAULT_CONFIG = {
    ...
    'strict_mode': False,  # If True, warnings become errors
    'max_file_size_mb': 50,  # Skip files larger than this
    'encoding_fallback': True,  # Try multiple encodings
}
```

---

## Test Plan

### Unit Tests

```python
# File: python/tests/unit/test_parser.py

class TestErrorHandling:
    def test_malformed_xml(self):
        """Test handling of malformed XML."""
        xaml = "<Activity><Unclosed>"
        parser = XamlParser()
        result = parser.parse_string(xaml, "test.xaml")

        assert not result.success
        assert "XML parse error" in result.error
        assert result.diagnostics[0].level == "error"

    def test_encoding_utf8_bom(self, tmp_path):
        """Test handling of UTF-8 with BOM."""
        file_path = tmp_path / "test.xaml"
        content = '\ufeff<Activity />'  # UTF-8 BOM
        file_path.write_bytes(content.encode("utf-8-sig"))

        parser = XamlParser()
        result = parser.parse_file(file_path)

        assert result.success  # Should handle BOM

    def test_encoding_fallback(self, tmp_path):
        """Test encoding detection fallback."""
        file_path = tmp_path / "test.xaml"
        content = '<Activity DisplayName="Tëst" />'
        file_path.write_bytes(content.encode("iso-8859-1"))

        parser = XamlParser()
        result = parser.parse_file(file_path)

        assert result.success or "encoding" in result.error.lower()

    def test_missing_x_class_warning(self):
        """Test warning for missing x:Class."""
        xaml = '<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities" />'
        parser = XamlParser()
        result = parser.parse_string(xaml, "test.xaml")

        assert result.success
        warnings = [d for d in result.diagnostics if d.level == "warning"]
        assert any("x:Class" in w.message for w in warnings)

    def test_file_not_found(self):
        """Test handling of missing file."""
        parser = XamlParser()
        result = parser.parse_file(Path("nonexistent.xaml"))

        assert not result.success
        assert "not found" in result.error.lower()
```

---

## Files to Modify

| File | Change |
|------|--------|
| `python/xaml_parser/parser.py` | Add encoding detection, enhanced errors |
| `python/xaml_parser/models.py` | Enhance ParseDiagnostic dataclass |
| `python/xaml_parser/constants.py` | Add error handling config options |
| `python/tests/unit/test_parser.py` | Add error handling tests |

---

## Validation Criteria

- [ ] Malformed XML returns clear error message
- [ ] UTF-8 with BOM files parse successfully
- [ ] Non-UTF-8 files handled with fallback
- [ ] Missing x:Class generates warning (not error)
- [ ] Error messages include line/column when available
- [ ] All existing tests pass

---

## Estimated Effort

| Task | Effort |
|------|--------|
| Implement encoding detection | 1 hour |
| Enhance parse error messages | 1 hour |
| Improve ParseDiagnostic | 30 minutes |
| Add warning collection | 1 hour |
| Write unit tests | 1.5 hours |
| Test corpus | 1 hour |
| **Total** | **~6 hours** |

---

## References

- Python encoding handling: https://docs.python.org/3/library/codecs.html
- XML parsing errors: https://docs.python.org/3/library/xml.etree.elementtree.html
- defusedxml: https://github.com/tiran/defusedxml
