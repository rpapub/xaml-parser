# PLAN v0.2.7: Enhanced Namespace Handling

## Todo List

- [x] **Analyze**: Compare namespace handling in rpax vs standalone
- [x] **Identify edge cases**: Default namespace, aliased prefixes, missing declarations
- [x] **Improve XmlUtils**: Better namespace prefix resolution (3 methods added)
- [x] **Handle missing namespaces**: Graceful fallback behavior
- [x] **Add unit tests**: Cover all namespace edge cases
- [x] **Test corpus**: Verify with diverse UiPath projects

---

## Status
**Completed** - Namespace Utility Methods Implemented

## Priority
**MEDIUM**

## Version
0.2.7

---

## Problem Statement

XML namespace handling in XAML parsing can have edge cases:

1. **Default namespace** (no prefix): `xmlns="..."`
2. **Multiple prefixes** for same URI
3. **Missing declarations**: Element uses prefix not declared
4. **Namespace inheritance**: Child elements inherit parent namespaces
5. **Namespace aliasing**: Different prefixes in different files

Better namespace handling improves:
- **Robustness**: Handle non-standard XAML files
- **Activity classification**: Correctly identify activity types by namespace
- **Expression parsing**: Understand expression language context

---

## Current Implementation Analysis

### Existing Namespace Handling

**MetadataExtractor.extract_namespaces()** (`extractors.py:824-835`):
```python
@staticmethod
def extract_namespaces(root: ET.Element) -> dict[str, str]:
    """Extract all XML namespaces (xmlns declarations)."""
    namespaces = {}

    for key, value in root.attrib.items():
        if key.startswith("xmlns:"):
            prefix = key[6:]
            namespaces[prefix] = value
        elif key == "xmlns":
            namespaces[""] = value  # Default namespace

    return namespaces
```

**Parser.py** namespace usage:
```python
# Get namespace URIs from declarations
self.namespaces = self._extract_namespaces(root)
self.x_ns = self.namespaces.get("x", "")
self.sap2010_ns = self.namespaces.get("sap2010", "")
```

### What's Missing

1. **Namespace URI → prefix reverse lookup**: Need to find prefix for known URI
2. **Fallback for common namespaces**: If `x` not declared, try standard URI
3. **Namespace-aware element lookup**: Find elements regardless of prefix
4. **Validation of namespace declarations**: Warn on missing declarations

---

## Enhancement Plan

### 1. Add Reverse Namespace Lookup

```python
# File: python/xaml_parser/utils.py

class XmlUtils:
    @staticmethod
    def get_prefix_for_uri(namespaces: dict[str, str], uri: str) -> str | None:
        """Find prefix for a namespace URI.

        Args:
            namespaces: Prefix → URI mapping
            uri: Namespace URI to find

        Returns:
            Prefix string or None if not found
        """
        for prefix, ns_uri in namespaces.items():
            if ns_uri == uri:
                return prefix
        return None

    @staticmethod
    def get_prefixes_for_uri(namespaces: dict[str, str], uri: str) -> list[str]:
        """Find all prefixes for a namespace URI (handles aliasing)."""
        return [prefix for prefix, ns_uri in namespaces.items() if ns_uri == uri]
```

### 2. Namespace-Aware Element Lookup

```python
# File: python/xaml_parser/utils.py

class XmlUtils:
    @staticmethod
    def find_elements_by_local_name(
        root: ET.Element,
        local_name: str,
        namespace_uri: str | None = None
    ) -> list[ET.Element]:
        """Find elements by local name, optionally filtered by namespace.

        Handles case where elements might have different prefixes.
        """
        results = []
        for elem in root.iter():
            # Extract local name from tag
            if '}' in elem.tag:
                ns, name = elem.tag[1:].split('}', 1)
            else:
                ns, name = None, elem.tag

            if name == local_name:
                if namespace_uri is None or ns == namespace_uri:
                    results.append(elem)

        return results
```

### 3. Common Namespace Fallback

```python
# File: python/xaml_parser/constants.py

# Standard namespace URIs for fallback
STANDARD_NAMESPACE_URIS = {
    "x": "http://schemas.microsoft.com/winfx/2006/xaml",
    "activities": "http://schemas.microsoft.com/netfx/2009/xaml/activities",
    "sap2010": "http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation",
    "ui": "http://schemas.uipath.com/workflow/activities",
}
```

```python
# File: python/xaml_parser/parser.py

def _get_namespace_uri(self, prefix: str) -> str:
    """Get namespace URI for prefix with fallback."""
    # First try declared namespaces
    if prefix in self.namespaces:
        return self.namespaces[prefix]

    # Fallback to standard URIs
    if prefix in STANDARD_NAMESPACE_URIS:
        logger.debug(f"Using fallback namespace for '{prefix}'")
        return STANDARD_NAMESPACE_URIS[prefix]

    return ""
```

### 4. Namespace Validation Warnings

```python
# File: python/xaml_parser/parser.py

def _validate_namespaces(self, root: ET.Element) -> list[ParseDiagnostic]:
    """Validate namespace declarations and usage."""
    warnings = []
    declared = set(self.namespaces.keys())

    # Check for elements using undeclared prefixes
    for elem in root.iter():
        if ':' in elem.tag and '}' not in elem.tag:
            prefix = elem.tag.split(':')[0]
            if prefix not in declared:
                warnings.append(ParseDiagnostic(
                    level="warning",
                    message=f"Element uses undeclared namespace prefix '{prefix}'",
                    element=elem.tag,
                ))

        # Check attributes too
        for attr in elem.attrib:
            if ':' in attr and '}' not in attr:
                prefix = attr.split(':')[0]
                if prefix not in declared and prefix != 'xmlns':
                    warnings.append(ParseDiagnostic(
                        level="warning",
                        message=f"Attribute uses undeclared namespace prefix '{prefix}'",
                        element=f"{elem.tag}@{attr}",
                    ))

    return warnings
```

---

## Test Plan

### Unit Tests

```python
# File: python/tests/unit/test_utils_xml.py

class TestXmlUtilsNamespace:
    def test_get_prefix_for_uri(self):
        """Test reverse namespace lookup."""
        namespaces = {
            "x": "http://schemas.microsoft.com/winfx/2006/xaml",
            "ui": "http://schemas.uipath.com/workflow/activities",
        }

        assert XmlUtils.get_prefix_for_uri(
            namespaces,
            "http://schemas.microsoft.com/winfx/2006/xaml"
        ) == "x"

    def test_get_prefix_for_uri_not_found(self):
        """Test reverse lookup returns None when not found."""
        namespaces = {"x": "http://example.com"}

        assert XmlUtils.get_prefix_for_uri(namespaces, "http://other.com") is None

    def test_find_elements_by_local_name(self):
        """Test finding elements regardless of prefix."""
        xaml = '''<root xmlns:a="http://ns1" xmlns:b="http://ns1">
            <a:Element />
            <b:Element />
            <Element />
        </root>'''
        root = parse_xaml_string(xaml)

        elements = XmlUtils.find_elements_by_local_name(root, "Element")
        assert len(elements) == 3

    def test_find_elements_by_local_name_with_ns(self):
        """Test finding elements filtered by namespace."""
        xaml = '''<root xmlns:a="http://ns1" xmlns:b="http://ns2">
            <a:Element />
            <b:Element />
        </root>'''
        root = parse_xaml_string(xaml)

        elements = XmlUtils.find_elements_by_local_name(
            root, "Element", "http://ns1"
        )
        assert len(elements) == 1

    def test_default_namespace_handling(self):
        """Test extraction of default namespace."""
        xaml = '''<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities">
        </Activity>'''
        root = parse_xaml_string(xaml)
        namespaces = MetadataExtractor.extract_namespaces(root)

        assert "" in namespaces
        assert namespaces[""] == "http://schemas.microsoft.com/netfx/2009/xaml/activities"
```

---

## Edge Cases to Test

| Scenario | Expected Behavior |
|----------|-------------------|
| Default namespace (xmlns="...") | Stored with empty string key |
| Multiple prefixes for same URI | All prefixes returned |
| Missing namespace declaration | Warning generated, fallback used |
| Non-standard prefix (e.g., `xaml:` instead of `x:`) | Recognized by URI |
| Mixed prefixed/unprefixed elements | Both handled correctly |

---

## Files to Modify

| File | Change |
|------|--------|
| `python/xaml_parser/utils.py` | Add namespace utility methods |
| `python/xaml_parser/constants.py` | Add STANDARD_NAMESPACE_URIS |
| `python/xaml_parser/parser.py` | Add namespace fallback and validation |
| `python/tests/unit/test_utils_xml.py` | Add namespace tests |

---

## Validation Criteria

- [ ] Reverse namespace lookup works correctly
- [ ] Elements found regardless of prefix
- [ ] Default namespace handled
- [ ] Missing declarations generate warnings
- [ ] Fallback to standard URIs works
- [ ] All existing tests pass

---

## Estimated Effort

| Task | Effort |
|------|--------|
| Add XmlUtils namespace methods | 1 hour |
| Implement namespace fallback | 1 hour |
| Add validation warnings | 1 hour |
| Write unit tests | 1.5 hours |
| Test corpus | 30 minutes |
| **Total** | **~5 hours** |

---

## References

- XML Namespaces: https://www.w3.org/TR/xml-names/
- ElementTree namespace handling: https://docs.python.org/3/library/xml.etree.elementtree.html#parsing-xml-with-namespaces
- UiPath XAML namespaces: Standard UiPath namespace URIs
