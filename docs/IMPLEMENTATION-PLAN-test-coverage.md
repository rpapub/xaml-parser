# Test Coverage Improvement Plan

## Executive Summary
**Goal**: Increase test coverage from 75% to 90%+ for critical modules
**Target Modules**: parser.py, extractors.py, validation.py, normalization.py, utils.py
**Approach**: Systematic gap analysis and targeted test creation
**Timeline**: 2-3 weeks

## Current Coverage Status

### Critical Modules (Target: 80-90%)
| Module | Current | Target | Gap | Priority |
|--------|---------|--------|-----|----------|
| parser.py | 88% | 90% | 2% | Medium |
| extractors.py | 91% | 95% | 4% | Low |
| normalization.py | 87% | 90% | 3% | Medium |
| validation.py | 86% | 90% | 4% | Medium |
| utils.py | 39% | 85% | 46% | **HIGH** |

### Secondary Modules
| Module | Current | Target | Gap | Priority |
|--------|---------|--------|-----|----------|
| field_profiles.py | 48% | 80% | 32% | Medium |
| visibility.py | 52% | 80% | 28% | Medium |
| emitters/registry.py | 71% | 85% | 14% | Low |
| provenance.py | 81% | 85% | 4% | Low |
| type_system.py | 84% | 90% | 6% | Medium |

### Excluded Modules (Not Production Critical)
- ancestry_graph.py (0%) - Phase 7 feature, not yet used
- interprocedural_analysis.py (0%) - Future feature
- emitters/ancestry_emitter.py (0%) - Phase 7 feature

## Gap Analysis by Module

### 1. utils.py (39% → 85%) - HIGHEST PRIORITY

**Missing Coverage**: 150 lines out of 247

#### Untested Areas:
1. **XmlUtils class** (lines 28-37, 50-71, 83-86)
   - `safe_parse()` error recovery branch
   - `get_element_text()` edge cases
   - `find_elements_by_attribute()` with filters
   - `get_namespace_prefix()` edge cases

2. **TextUtils class** (lines 114-127, 139-155, 167-184)
   - `clean_annotation()` HTML entity handling
   - `extract_type_name()` complex type parsing
   - `normalize_path()` Windows vs POSIX
   - `truncate_text()` edge cases

3. **ValidationUtils class** (lines 200-218, 223-243, 248-265, 277-292)
   - `validate_workflow_content()` full paths
   - `_validate_arguments()` duplicate detection
   - `_validate_activities()` validation rules
   - `is_valid_expression()` pattern matching

4. **DataUtils class** (lines 309-317, 331-343, 356-363, 376-382)
   - `merge_dictionaries()` deep merging
   - `flatten_nested_dict()` recursion
   - `extract_unique_values()` list handling
   - `group_by_field()` grouping logic

5. **DebugUtils class** (lines 398-445)
   - `element_info()` diagnostics
   - `summarize_parsing_stats()` statistics

6. **ActivityUtils class** (lines 471-477, 489-506, 518-574, 586-613, 625-682)
   - `generate_activity_id()` hashing
   - `extract_expressions_from_text()` patterns
   - `extract_variable_references()` filtering
   - `extract_selectors_from_config()` recursion
   - `classify_activity_type()` categorization

#### Test Files to Create:
1. **test_utils_xml.py** - XmlUtils coverage
2. **test_utils_text.py** - TextUtils coverage
3. **test_utils_validation.py** - ValidationUtils coverage
4. **test_utils_data.py** - DataUtils coverage
5. **test_utils_debug.py** - DebugUtils coverage
6. **test_utils_activity.py** - ActivityUtils coverage

### 2. parser.py (88% → 90%)

**Missing Coverage**: 41 lines out of 343

#### Untested Areas:
1. **Import fallback** (lines 17-19)
   - `defusedxml` import failure → stdlib fallback

2. **Strict mode validation** (lines 118-125, 190-193)
   - Validation errors in strict mode
   - Validation failure exception handling

3. **Error handling edge cases** (lines 304-305, 307, 321, 334)
   - Specific extraction errors
   - Nested extraction failures

4. **Configuration extraction** (lines 447-449)
   - Configuration edge cases

5. **Expression classification** (lines 512, 519)
   - Expression type classification edge cases

6. **Error boundaries** (lines 575-576, 582-584, 618, 627, 640, 669, 688-694, 713, 717)
   - Various error handling paths
   - Edge case processing

#### Test Files to Enhance:
1. **tests/integration/test_parser.py** - Add strict mode tests
2. **tests/unit/test_parser_errors.py** (NEW) - Error handling tests

### 3. validation.py (86% → 90%)

**Missing Coverage**: 23 lines out of 162

#### Untested Areas:
1. **Error path validation** (lines 62, 67, 69)
   - Invalid data type checks
   - Boundary conditions

2. **Workflow content validation** (lines 104, 111, 118)
   - Complex validation rules
   - Nested validation errors

3. **Diagnostics validation** (lines 127, 135, 143, 145)
   - Performance metrics validation
   - Processing steps validation

4. **Config validation** (lines 184, 188, 192)
   - Configuration type checks
   - Invalid config values

5. **Activity validation** (lines 250, 262, 265, 272)
   - Activity structure validation
   - Reference validation

6. **Exception handling** (lines 288, 302, 308, 335-337)
   - Validation exceptions
   - Error aggregation

#### Test Files to Enhance:
1. **tests/unit/test_validation.py** - Add edge case tests

### 4. normalization.py (87% → 90%)

**Missing Coverage**: 18 lines out of 141

#### Untested Areas:
1. **Error handling** (lines 229, 234-242)
   - Normalization failures
   - Invalid input handling

2. **Edge cases** (lines 280, 282)
   - Empty content normalization
   - Missing fields handling

3. **Source info creation** (lines 459)
   - Source info edge cases

4. **Project info** (lines 508-512)
   - Project metadata normalization
   - Missing project info

#### Test Files to Enhance:
1. **tests/unit/test_normalization.py** - Add error path tests

### 5. field_profiles.py (48% → 80%)

**Missing Coverage**: 32 lines out of 61

#### Untested Areas:
1. **Profile configuration** (lines 89, 97, 101)
   - Profile selection logic
   - Profile merging

2. **Field filtering** (lines 123, 137, 152, 165-184)
   - Field inclusion/exclusion rules
   - Profile-specific filtering

3. **Export logic** (lines 216, 232-247)
   - Export format handling
   - Field transformation

#### Test Files to Create:
1. **tests/unit/test_field_profiles.py** - Field profile tests

### 6. visibility.py (52% → 80%)

**Missing Coverage**: 24 lines out of 50

#### Untested Areas:
1. **Visibility rules** (lines 79, 92)
   - Visibility determination logic
   - Inheritance rules

2. **Attribute categorization** (lines 130-143)
   - Visible/invisible attribute classification
   - Namespace handling

3. **ViewState handling** (lines 157-178, 190-196)
   - ViewState extraction
   - ViewState transformation

#### Test Files to Create:
1. **tests/unit/test_visibility.py** - Visibility logic tests

## Implementation Strategy

### Phase 1: Foundation (Week 1)
**Focus**: High-impact, low-complexity tests

#### Day 1-2: Utils Module Foundation
- Create test_utils_xml.py
- Create test_utils_text.py
- Target: +20% coverage on utils.py

#### Day 3-4: Utils Module Completion
- Create test_utils_validation.py
- Create test_utils_data.py
- Target: +25% more coverage on utils.py (total: 85%)

#### Day 5: Utils Module Edge Cases
- Create test_utils_debug.py
- Create test_utils_activity.py
- Target: Reach 85%+ on utils.py

### Phase 2: Core Modules (Week 2)
**Focus**: Parser, validation, normalization

#### Day 1-2: Parser Error Handling
- Create test_parser_errors.py
- Test defusedxml fallback
- Test strict mode validation
- Target: parser.py → 92%

#### Day 3: Validation Edge Cases
- Enhance test_validation.py
- Add boundary condition tests
- Add complex validation scenarios
- Target: validation.py → 92%

#### Day 4: Normalization Error Paths
- Enhance test_normalization.py
- Add error path tests
- Add edge case scenarios
- Target: normalization.py → 92%

#### Day 5: Integration Tests
- Add cross-module integration tests
- Test error propagation
- Test validation chains

### Phase 3: Secondary Modules (Week 3)
**Focus**: Field profiles, visibility, type system

#### Day 1-2: Field Profiles
- Create test_field_profiles.py
- Test all profile types
- Test field filtering logic
- Target: field_profiles.py → 85%

#### Day 3-4: Visibility Logic
- Create test_visibility.py
- Test visibility rules
- Test ViewState handling
- Target: visibility.py → 85%

#### Day 5: Final Cleanup
- Address remaining gaps
- Review coverage reports
- Optimize tests for maintainability

## Test Writing Guidelines

### 1. Test Structure Pattern
```python
"""Tests for [Module] [Class/Function] functionality."""

import pytest
from unittest.mock import Mock, patch
from xaml_parser.[module] import [Class/Function]


class Test[ClassName]:
    """Test cases for [ClassName]."""

    def setup_method(self):
        """Set up test fixtures."""
        # Common setup

    def test_[function_name]_success(self):
        """Test [function_name] with valid input."""
        # Arrange
        input_data = ...

        # Act
        result = function(input_data)

        # Assert
        assert result == expected

    def test_[function_name]_edge_case(self):
        """Test [function_name] with edge case input."""
        # Test edge cases

    def test_[function_name]_error_handling(self):
        """Test [function_name] error handling."""
        # Test error paths
```

### 2. Coverage Targets per Test File

#### Minimum Requirements:
- **Happy path**: Basic functionality with valid input
- **Edge cases**: Boundary conditions, empty input, null values
- **Error paths**: Exception handling, invalid input
- **Integration**: Interaction with other modules

#### Test Categories:
1. **Unit tests**: Isolated function/method testing
2. **Integration tests**: Multi-module interactions
3. **Edge case tests**: Boundary conditions
4. **Error tests**: Exception handling and recovery

### 3. Mock Usage Guidelines

```python
# Mock external dependencies
@patch('xaml_parser.parser.defused_fromstring')
def test_parser_with_mock_xml(mock_fromstring):
    mock_fromstring.return_value = Mock()
    # Test logic

# Mock file I/O
@patch('pathlib.Path.read_text')
def test_parse_file_with_mock(mock_read):
    mock_read.return_value = "<xml>...</xml>"
    # Test logic

# Mock complex objects
def test_with_mock_workflow_content():
    mock_content = Mock(spec=WorkflowContent)
    mock_content.arguments = []
    # Test logic
```

### 4. Parametrized Tests

```python
@pytest.mark.parametrize("input_value,expected", [
    ("simple", "simple"),
    ("with spaces", "with spaces"),
    ("", ""),
    (None, ""),
])
def test_clean_annotation_variations(input_value, expected):
    """Test clean_annotation with various inputs."""
    result = TextUtils.clean_annotation(input_value)
    assert result == expected
```

### 5. Fixture Usage

```python
@pytest.fixture
def sample_xml_root():
    """Sample XML root element for testing."""
    xml_content = """
    <Activity xmlns="http://...">
        <Sequence DisplayName="Test" />
    </Activity>
    """
    return ET.fromstring(xml_content)

@pytest.fixture
def mock_parser():
    """Configured parser instance for testing."""
    config = {"extract_arguments": True}
    return XamlParser(config)
```

## Specific Test Plans

### Test Plan 1: utils.py - XmlUtils

**File**: tests/unit/test_utils_xml.py

```python
class TestXmlUtilsSafeParse:
    """Tests for XmlUtils.safe_parse()."""

    def test_safe_parse_valid_xml(self):
        """Test parsing valid XML."""
        xml = '<?xml version="1.0"?><root><child /></root>'
        result = XmlUtils.safe_parse(xml)
        assert result is not None
        assert result.tag == "root"

    def test_safe_parse_invalid_xml(self):
        """Test parsing invalid XML returns None."""
        xml = '<root><unclosed>'
        result = XmlUtils.safe_parse(xml)
        assert result is None

    def test_safe_parse_with_encoding_declaration(self):
        """Test parsing XML with encoding declaration."""
        xml = '<?xml version="1.0" encoding="utf-8"?><root />'
        result = XmlUtils.safe_parse(xml)
        assert result is not None

    def test_safe_parse_removes_bad_encoding_declaration(self):
        """Test recovery by removing encoding declaration."""
        xml = '<?xml version="1.0" encoding="invalid"?><root />'
        result = XmlUtils.safe_parse(xml)
        # Should either parse successfully or return None
        assert result is None or result.tag == "root"


class TestXmlUtilsElementText:
    """Tests for XmlUtils.get_element_text()."""

    def test_get_element_text_with_text(self):
        """Test getting text from element with content."""
        elem = ET.fromstring("<root>Hello</root>")
        result = XmlUtils.get_element_text(elem)
        assert result == "Hello"

    def test_get_element_text_empty(self):
        """Test getting text from empty element."""
        elem = ET.fromstring("<root></root>")
        result = XmlUtils.get_element_text(elem)
        assert result == ""

    def test_get_element_text_with_default(self):
        """Test getting text with custom default."""
        elem = ET.fromstring("<root></root>")
        result = XmlUtils.get_element_text(elem, default="N/A")
        assert result == "N/A"

    def test_get_element_text_strips_whitespace(self):
        """Test that whitespace is stripped."""
        elem = ET.fromstring("<root>  text  </root>")
        result = XmlUtils.get_element_text(elem)
        assert result == "text"


class TestXmlUtilsFindElements:
    """Tests for XmlUtils.find_elements_by_attribute()."""

    @pytest.fixture
    def sample_tree(self):
        """Sample XML tree for testing."""
        xml = """
        <root>
            <child id="1" type="A" />
            <child id="2" type="B" />
            <child id="3" type="A" />
        </root>
        """
        return ET.fromstring(xml)

    def test_find_by_attribute_any_value(self, sample_tree):
        """Test finding all elements with attribute."""
        results = XmlUtils.find_elements_by_attribute(sample_tree, "id")
        assert len(results) == 3

    def test_find_by_attribute_specific_value(self, sample_tree):
        """Test finding elements with specific attribute value."""
        results = XmlUtils.find_elements_by_attribute(sample_tree, "type", "A")
        assert len(results) == 2

    def test_find_by_attribute_no_matches(self, sample_tree):
        """Test finding with no matches."""
        results = XmlUtils.find_elements_by_attribute(sample_tree, "nonexistent")
        assert len(results) == 0


class TestXmlUtilsNamespace:
    """Tests for namespace extraction."""

    def test_get_namespace_prefix_with_namespace(self):
        """Test extracting namespace from qualified tag."""
        tag = "{http://schemas.microsoft.com/netfx/2009/xaml/activities}Sequence"
        result = XmlUtils.get_namespace_prefix(tag)
        assert result == "http://schemas.microsoft.com/netfx/2009/xaml/activities"

    def test_get_namespace_prefix_no_namespace(self):
        """Test extracting from unqualified tag."""
        tag = "Sequence"
        result = XmlUtils.get_namespace_prefix(tag)
        assert result is None

    def test_get_local_name_with_namespace(self):
        """Test extracting local name from qualified tag."""
        tag = "{http://...}Sequence"
        result = XmlUtils.get_local_name(tag)
        assert result == "Sequence"

    def test_get_local_name_without_namespace(self):
        """Test extracting local name from unqualified tag."""
        tag = "Sequence"
        result = XmlUtils.get_local_name(tag)
        assert result == "Sequence"
```

**Lines Covered**: 28-37, 50-71, 83-86, 98
**Estimated Coverage Gain**: +15%

### Test Plan 2: utils.py - TextUtils

**File**: tests/unit/test_utils_text.py

```python
class TestTextUtilsCleanAnnotation:
    """Tests for TextUtils.clean_annotation()."""

    def test_clean_annotation_empty_string(self):
        """Test cleaning empty string."""
        result = TextUtils.clean_annotation("")
        assert result == ""

    def test_clean_annotation_none(self):
        """Test cleaning None value."""
        result = TextUtils.clean_annotation(None)
        assert result == ""

    def test_clean_annotation_html_entities(self):
        """Test decoding HTML entities."""
        text = "Test &amp; Demo &lt;value&gt;"
        result = TextUtils.clean_annotation(text)
        assert result == "Test & Demo <value>"

    def test_clean_annotation_whitespace_normalization(self):
        """Test normalizing multiple whitespace."""
        text = "Test   with    spaces"
        result = TextUtils.clean_annotation(text)
        assert result == "Test with spaces"

    def test_clean_annotation_line_breaks(self):
        """Test converting HTML line breaks."""
        text = "Line 1&#xA;Line 2"
        result = TextUtils.clean_annotation(text)
        assert "Line 1\nLine 2" in result

    def test_clean_annotation_br_tags(self):
        """Test converting <br> tags."""
        text = "Line 1<br>Line 2<br/>Line 3"
        result = TextUtils.clean_annotation(text)
        assert result.count("\n") == 2


class TestTextUtilsExtractTypeName:
    """Tests for TextUtils.extract_type_name()."""

    @pytest.mark.parametrize("type_signature,expected", [
        ("InArgument(x:String)", "String"),
        ("OutArgument(x:Int32)", "Int32"),
        ("InOutArgument(x:Boolean)", "Boolean"),
        ("x:String", "String"),
        ("String", "String"),
        ("", "Object"),
        (None, "Object"),
    ])
    def test_extract_type_name_variations(self, type_signature, expected):
        """Test extracting type names from various signatures."""
        result = TextUtils.extract_type_name(type_signature)
        assert result == expected

    def test_extract_type_name_complex_generic(self):
        """Test extracting from complex generic type."""
        type_sig = "InArgument(scg:List(x:String))"
        result = TextUtils.extract_type_name(type_sig)
        assert "List" in result or "String" in result


class TestTextUtilsNormalizePath:
    """Tests for TextUtils.normalize_path()."""

    def test_normalize_path_windows(self):
        """Test normalizing Windows path."""
        path = "C:\\Users\\test\\file.xaml"
        result = TextUtils.normalize_path(path)
        assert result == "C:/Users/test/file.xaml"

    def test_normalize_path_posix(self):
        """Test normalizing POSIX path."""
        path = "/home/user/file.xaml"
        result = TextUtils.normalize_path(path)
        assert result == "/home/user/file.xaml"

    def test_normalize_path_empty(self):
        """Test normalizing empty path."""
        result = TextUtils.normalize_path("")
        assert result == ""

    def test_normalize_path_none(self):
        """Test normalizing None."""
        result = TextUtils.normalize_path(None)
        assert result == ""


class TestTextUtilsTruncate:
    """Tests for TextUtils.truncate_text()."""

    def test_truncate_text_within_limit(self):
        """Test text within limit is unchanged."""
        text = "Short text"
        result = TextUtils.truncate_text(text, max_length=100)
        assert result == text

    def test_truncate_text_exceeds_limit(self):
        """Test text exceeding limit is truncated."""
        text = "A" * 150
        result = TextUtils.truncate_text(text, max_length=100)
        assert len(result) == 100
        assert result.endswith("...")

    def test_truncate_text_custom_suffix(self):
        """Test truncation with custom suffix."""
        text = "A" * 150
        result = TextUtils.truncate_text(text, max_length=100, suffix="[...]")
        assert result.endswith("[...]")

    def test_truncate_text_empty(self):
        """Test truncating empty text."""
        result = TextUtils.truncate_text("", max_length=100)
        assert result == ""
```

**Lines Covered**: 114-127, 139-155, 167-184
**Estimated Coverage Gain**: +20%

### Test Plan 3: utils.py - ValidationUtils

**File**: tests/unit/test_utils_validation.py

```python
class TestValidationUtilsWorkflowContent:
    """Tests for ValidationUtils.validate_workflow_content()."""

    def test_validate_workflow_content_valid(self):
        """Test validating valid workflow content."""
        content = {
            "arguments": [],
            "variables": [],
            "activities": []
        }
        errors = ValidationUtils.validate_workflow_content(content)
        assert len(errors) == 0

    def test_validate_workflow_content_missing_fields(self):
        """Test validating content with missing fields."""
        content = {"arguments": []}
        errors = ValidationUtils.validate_workflow_content(content)
        assert len(errors) >= 2  # Missing variables and activities
        assert any("variables" in err for err in errors)
        assert any("activities" in err for err in errors)

    def test_validate_workflow_content_invalid_arguments(self):
        """Test validating content with invalid arguments."""
        content = {
            "arguments": [{"name": ""}],  # Empty name
            "variables": [],
            "activities": []
        }
        errors = ValidationUtils.validate_workflow_content(content)
        assert len(errors) > 0
        assert any("name" in err.lower() for err in errors)


class TestValidationUtilsArguments:
    """Tests for ValidationUtils._validate_arguments()."""

    def test_validate_arguments_valid(self):
        """Test validating valid arguments."""
        arguments = [
            {"name": "arg1", "direction": "in"},
            {"name": "arg2", "direction": "out"}
        ]
        errors = ValidationUtils._validate_arguments(arguments)
        assert len(errors) == 0

    def test_validate_arguments_missing_name(self):
        """Test validating arguments with missing name."""
        arguments = [{"direction": "in"}]
        errors = ValidationUtils._validate_arguments(arguments)
        assert len(errors) > 0
        assert any("name" in err.lower() for err in errors)

    def test_validate_arguments_duplicate_names(self):
        """Test detecting duplicate argument names."""
        arguments = [
            {"name": "arg1", "direction": "in"},
            {"name": "arg1", "direction": "out"}
        ]
        errors = ValidationUtils._validate_arguments(arguments)
        assert len(errors) > 0
        assert any("duplicate" in err.lower() for err in errors)

    def test_validate_arguments_invalid_direction(self):
        """Test validating invalid direction."""
        arguments = [{"name": "arg1", "direction": "invalid"}]
        errors = ValidationUtils._validate_arguments(arguments)
        assert len(errors) > 0
        assert any("direction" in err.lower() for err in errors)


class TestValidationUtilsActivities:
    """Tests for ValidationUtils._validate_activities()."""

    def test_validate_activities_valid(self):
        """Test validating valid activities."""
        activities = [
            {"activity_id": "act1", "tag": "Sequence"},
            {"activity_id": "act2", "tag": "Assign"}
        ]
        errors = ValidationUtils._validate_activities(activities)
        assert len(errors) == 0

    def test_validate_activities_missing_id(self):
        """Test validating activities with missing ID."""
        activities = [{"tag": "Sequence"}]
        errors = ValidationUtils._validate_activities(activities)
        assert len(errors) > 0
        assert any("activity_id" in err.lower() for err in errors)

    def test_validate_activities_duplicate_ids(self):
        """Test detecting duplicate activity IDs."""
        activities = [
            {"activity_id": "act1", "tag": "Sequence"},
            {"activity_id": "act1", "tag": "Assign"}
        ]
        errors = ValidationUtils._validate_activities(activities)
        assert len(errors) > 0
        assert any("duplicate" in err.lower() for err in errors)

    def test_validate_activities_missing_tag(self):
        """Test validating activities with missing tag."""
        activities = [{"activity_id": "act1"}]
        errors = ValidationUtils._validate_activities(activities)
        assert len(errors) > 0
        assert any("tag" in err.lower() for err in errors)


class TestValidationUtilsExpression:
    """Tests for ValidationUtils.is_valid_expression()."""

    @pytest.mark.parametrize("expression,expected", [
        # Valid expressions
        ("[variableName]", True),
        ("New System.Data.DataTable", True),
        ("string.Format(\"test\")", True),
        ("value1 + value2", True),
        ("If(condition, true, false)", True),
        ("variable.ToString()", True),
        # Invalid expressions
        ("", False),
        ("  ", False),
        ("a", False),
        (None, False),
    ])
    def test_is_valid_expression_variations(self, expression, expected):
        """Test expression validation with various inputs."""
        result = ValidationUtils.is_valid_expression(expression)
        assert result == expected
```

**Lines Covered**: 200-218, 223-243, 248-265, 277-292
**Estimated Coverage Gain**: +25%

## Success Metrics

### Quantitative Metrics
1. **Overall Coverage**: 75% → 90% (Target: +15%)
2. **Critical Modules**: All above 85%
3. **Test Count**: ~355 → ~500 tests (Target: +145 tests)
4. **Test Execution Time**: Keep under 20 seconds

### Qualitative Metrics
1. **Test Maintainability**: Clear, well-documented tests
2. **Test Independence**: No test interdependencies
3. **Edge Case Coverage**: Comprehensive boundary testing
4. **Error Path Coverage**: All error handlers tested

### Coverage Targets by Module
- ✅ **parser.py**: 88% → 92%
- ✅ **extractors.py**: 91% → 95%
- ✅ **normalization.py**: 87% → 92%
- ✅ **validation.py**: 86% → 92%
- ✅ **utils.py**: 39% → 85% (PRIORITY)
- ✅ **field_profiles.py**: 48% → 85%
- ✅ **visibility.py**: 52% → 85%
- ✅ **Overall**: 75% → 90%

## Execution Checklist

### Week 1: Utils Module
- [ ] Day 1: Create test_utils_xml.py (XmlUtils)
- [ ] Day 2: Create test_utils_text.py (TextUtils)
- [ ] Day 3: Create test_utils_validation.py (ValidationUtils)
- [ ] Day 4: Create test_utils_data.py (DataUtils)
- [ ] Day 5: Create test_utils_debug.py + test_utils_activity.py
- [ ] Verify utils.py coverage reaches 85%+

### Week 2: Core Modules
- [ ] Day 1: Create test_parser_errors.py
- [ ] Day 2: Enhance parser tests for edge cases
- [ ] Day 3: Enhance test_validation.py for edge cases
- [ ] Day 4: Enhance test_normalization.py for error paths
- [ ] Day 5: Integration tests across modules
- [ ] Verify all core modules reach 90%+

### Week 3: Secondary Modules + Cleanup
- [ ] Day 1: Create test_field_profiles.py
- [ ] Day 2: Enhance field_profiles tests
- [ ] Day 3: Create test_visibility.py
- [ ] Day 4: Enhance visibility tests
- [ ] Day 5: Final review and cleanup
- [ ] Verify overall coverage reaches 90%+

### Daily Review Points
- Run coverage report: `uv run pytest --cov=xaml_parser --cov-report=term-missing`
- Check for test failures
- Review test execution time
- Update this plan with actual coverage numbers

## Maintenance Guidelines

### 1. Adding New Code
- **Rule**: New code must have 90%+ coverage
- **Process**: Write tests alongside implementation
- **Review**: Coverage check in pre-commit hook

### 2. Modifying Existing Code
- **Rule**: Maintain or improve existing coverage
- **Process**: Update tests before modifying code
- **Review**: Coverage diff in PR reviews

### 3. Test Quality Standards
- **Clarity**: Tests should be self-documenting
- **Independence**: No shared state between tests
- **Speed**: Tests should execute quickly
- **Relevance**: Test actual behavior, not implementation details

### 4. Coverage Exceptions
Acceptable reasons for excluding lines from coverage:
- Defensive programming (should-never-happen cases)
- Platform-specific code paths
- Debug/development-only code
- Abstract methods meant to be overridden

Use `# pragma: no cover` sparingly and document why.

## Notes

### Testing Philosophy
- **Favor integration tests** for end-to-end workflows
- **Use unit tests** for utility functions and edge cases
- **Mock sparingly** - prefer real objects when possible
- **Test behavior** not implementation details

### Common Pitfalls to Avoid
1. **Over-mocking**: Don't mock everything, test real behavior
2. **Brittle tests**: Don't test private methods or internal state
3. **Slow tests**: Keep tests fast with minimal I/O
4. **Unclear tests**: Make test names and intent obvious
5. **Test interdependencies**: Each test should be independent

### Tools and Commands
```bash
# Run all tests with coverage
uv run pytest --cov=xaml_parser --cov-report=term-missing --cov-report=html

# Run specific test file
uv run pytest tests/unit/test_utils.py -v

# Run tests matching pattern
uv run pytest -k "test_xml" -v

# Run with coverage for specific module
uv run pytest --cov=xaml_parser.utils --cov-report=term-missing

# Generate HTML coverage report
uv run pytest --cov=xaml_parser --cov-report=html
# Open htmlcov/index.html in browser
```

## Appendix: Test Template Library

### Template 1: Simple Function Test
```python
def test_function_name_success():
    """Test function_name with valid input."""
    # Arrange
    input_value = "test"

    # Act
    result = function_name(input_value)

    # Assert
    assert result == expected_value
```

### Template 2: Class Method Test
```python
class TestClassName:
    """Test cases for ClassName."""

    def setup_method(self):
        """Set up test fixtures."""
        self.instance = ClassName()

    def test_method_success(self):
        """Test method with valid input."""
        result = self.instance.method("input")
        assert result is not None
```

### Template 3: Exception Test
```python
def test_function_raises_exception():
    """Test function raises appropriate exception."""
    with pytest.raises(ValueError) as exc_info:
        function_with_error("invalid")

    assert "expected error message" in str(exc_info.value)
```

### Template 4: Parametrized Test
```python
@pytest.mark.parametrize("input_val,expected", [
    ("case1", "result1"),
    ("case2", "result2"),
    ("case3", "result3"),
])
def test_function_variations(input_val, expected):
    """Test function with various inputs."""
    result = function(input_val)
    assert result == expected
```

### Template 5: Mock Test
```python
@patch('module.external_dependency')
def test_function_with_mock(mock_dependency):
    """Test function with mocked dependency."""
    mock_dependency.return_value = "mocked_value"

    result = function_using_dependency()

    mock_dependency.assert_called_once()
    assert result == "expected"
```
