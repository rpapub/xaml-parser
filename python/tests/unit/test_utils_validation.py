"""Tests for ValidationUtils utility functions."""

from xaml_parser.utils import ValidationUtils


class TestValidateWorkflowContent:
    """Tests for ValidationUtils.validate_workflow_content()."""

    def test_validate_valid_workflow(self):
        """Test validation of valid workflow content."""
        content = {
            "arguments": [{"name": "arg1", "direction": "in", "type": "String"}],
            "variables": [{"name": "var1", "type": "String"}],
            "activities": [{"activity_id": "act1", "tag": "Sequence"}],
        }
        errors = ValidationUtils.validate_workflow_content(content)
        assert errors == []

    def test_validate_missing_arguments(self):
        """Test validation with missing arguments field."""
        content = {"variables": [], "activities": []}
        errors = ValidationUtils.validate_workflow_content(content)
        assert "Missing required field: arguments" in errors

    def test_validate_missing_variables(self):
        """Test validation with missing variables field."""
        content = {"arguments": [], "activities": []}
        errors = ValidationUtils.validate_workflow_content(content)
        assert "Missing required field: variables" in errors

    def test_validate_missing_activities(self):
        """Test validation with missing activities field."""
        content = {"arguments": [], "variables": []}
        errors = ValidationUtils.validate_workflow_content(content)
        assert "Missing required field: activities" in errors

    def test_validate_all_fields_missing(self):
        """Test validation with all required fields missing."""
        content = {}
        errors = ValidationUtils.validate_workflow_content(content)
        assert len(errors) == 3
        assert any("arguments" in e for e in errors)
        assert any("variables" in e for e in errors)
        assert any("activities" in e for e in errors)

    def test_validate_empty_lists(self):
        """Test validation with empty but present lists."""
        content = {"arguments": [], "variables": [], "activities": []}
        errors = ValidationUtils.validate_workflow_content(content)
        assert errors == []

    def test_validate_invalid_arguments(self):
        """Test validation with invalid arguments."""
        content = {
            "arguments": [{"name": ""}],  # Empty name
            "variables": [],
            "activities": [],
        }
        errors = ValidationUtils.validate_workflow_content(content)
        assert any("Argument 0" in e and "name" in e for e in errors)

    def test_validate_invalid_activities(self):
        """Test validation with invalid activities."""
        content = {
            "arguments": [],
            "variables": [],
            "activities": [{"tag": "Sequence"}],  # Missing activity_id
        }
        errors = ValidationUtils.validate_workflow_content(content)
        assert any("Activity 0" in e and "activity_id" in e for e in errors)


class TestValidateArguments:
    """Tests for ValidationUtils._validate_arguments()."""

    def test_validate_arguments_valid(self):
        """Test validation of valid arguments."""
        arguments = [
            {"name": "arg1", "direction": "in", "type": "String"},
            {"name": "arg2", "direction": "out", "type": "Int32"},
        ]
        errors = ValidationUtils._validate_arguments(arguments)
        assert errors == []

    def test_validate_arguments_missing_name(self):
        """Test validation with missing argument name."""
        arguments = [{"direction": "in", "type": "String"}]
        errors = ValidationUtils._validate_arguments(arguments)
        assert len(errors) == 1
        assert "Argument 0" in errors[0]
        assert "name" in errors[0]

    def test_validate_arguments_empty_name(self):
        """Test validation with empty argument name."""
        arguments = [{"name": "", "direction": "in"}]
        errors = ValidationUtils._validate_arguments(arguments)
        assert len(errors) == 1
        assert "Argument 0" in errors[0]
        assert "empty name" in errors[0]

    def test_validate_arguments_duplicate_names(self):
        """Test validation with duplicate argument names."""
        arguments = [
            {"name": "duplicate", "direction": "in"},
            {"name": "duplicate", "direction": "out"},
        ]
        errors = ValidationUtils._validate_arguments(arguments)
        assert len(errors) == 1
        assert "Duplicate name" in errors[0]
        assert "duplicate" in errors[0]

    def test_validate_arguments_invalid_direction(self):
        """Test validation with invalid direction."""
        arguments = [{"name": "arg1", "direction": "invalid"}]
        errors = ValidationUtils._validate_arguments(arguments)
        assert len(errors) == 1
        assert "Invalid direction" in errors[0]
        assert "invalid" in errors[0]

    def test_validate_arguments_valid_directions(self):
        """Test all valid direction values."""
        arguments = [
            {"name": "arg1", "direction": "in"},
            {"name": "arg2", "direction": "out"},
            {"name": "arg3", "direction": "inout"},
        ]
        errors = ValidationUtils._validate_arguments(arguments)
        assert errors == []

    def test_validate_arguments_no_direction(self):
        """Test validation without direction field (optional)."""
        arguments = [{"name": "arg1", "type": "String"}]
        errors = ValidationUtils._validate_arguments(arguments)
        assert errors == []

    def test_validate_arguments_multiple_errors(self):
        """Test validation with multiple errors."""
        arguments = [
            {"name": ""},  # Empty name
            {"name": "dup"},  # First duplicate
            {"name": "dup"},  # Second duplicate
            {"name": "bad", "direction": "wrong"},  # Invalid direction
        ]
        errors = ValidationUtils._validate_arguments(arguments)
        # Should have: empty name, duplicate, invalid direction
        assert len(errors) >= 3


class TestValidateActivities:
    """Tests for ValidationUtils._validate_activities()."""

    def test_validate_activities_valid(self):
        """Test validation of valid activities."""
        activities = [
            {"activity_id": "act1", "tag": "Sequence"},
            {"activity_id": "act2", "tag": "Assign"},
        ]
        errors = ValidationUtils._validate_activities(activities)
        assert errors == []

    def test_validate_activities_missing_id(self):
        """Test validation with missing activity_id."""
        activities = [{"tag": "Sequence"}]
        errors = ValidationUtils._validate_activities(activities)
        assert len(errors) == 1
        assert "Activity 0" in errors[0]
        assert "activity_id" in errors[0]

    def test_validate_activities_empty_id(self):
        """Test validation with empty activity_id."""
        activities = [{"activity_id": "", "tag": "Sequence"}]
        errors = ValidationUtils._validate_activities(activities)
        assert len(errors) >= 1
        assert any("activity_id" in e for e in errors)

    def test_validate_activities_duplicate_ids(self):
        """Test validation with duplicate activity IDs."""
        activities = [
            {"activity_id": "duplicate", "tag": "Sequence"},
            {"activity_id": "duplicate", "tag": "Assign"},
        ]
        errors = ValidationUtils._validate_activities(activities)
        assert len(errors) == 1
        assert "Duplicate activity_id" in errors[0]
        assert "duplicate" in errors[0]

    def test_validate_activities_missing_tag(self):
        """Test validation with missing tag."""
        activities = [{"activity_id": "act1"}]
        errors = ValidationUtils._validate_activities(activities)
        assert len(errors) == 1
        assert "Activity 0" in errors[0]
        assert "tag" in errors[0]

    def test_validate_activities_empty_tag(self):
        """Test validation with empty tag."""
        activities = [{"activity_id": "act1", "tag": ""}]
        errors = ValidationUtils._validate_activities(activities)
        assert len(errors) == 1
        assert "tag" in errors[0]

    def test_validate_activities_multiple_errors(self):
        """Test validation with multiple errors."""
        activities = [
            {"tag": "Sequence"},  # Missing ID
            {"activity_id": "dup", "tag": "Assign"},
            {"activity_id": "dup", "tag": "Sequence"},  # Duplicate ID
            {"activity_id": "act3"},  # Missing tag
        ]
        errors = ValidationUtils._validate_activities(activities)
        # Should have: missing ID, duplicate ID, missing tag
        assert len(errors) >= 3


class TestIsValidExpression:
    """Tests for ValidationUtils.is_valid_expression()."""

    def test_is_valid_expression_empty_string(self):
        """Test that empty string is not valid."""
        assert ValidationUtils.is_valid_expression("") is False

    def test_is_valid_expression_whitespace_only(self):
        """Test that whitespace-only is not valid."""
        assert ValidationUtils.is_valid_expression("   ") is False

    def test_is_valid_expression_too_short(self):
        """Test that single character is not valid."""
        assert ValidationUtils.is_valid_expression("a") is False

    def test_is_valid_expression_vb_bracket_syntax(self):
        """Test VB.NET bracket expression."""
        assert ValidationUtils.is_valid_expression("[variableName]") is True
        assert ValidationUtils.is_valid_expression("[DateTime.Now]") is True

    def test_is_valid_expression_new_keyword(self):
        """Test object creation with New keyword."""
        assert ValidationUtils.is_valid_expression("New String()") is True
        assert ValidationUtils.is_valid_expression("New DataTable") is True

    def test_is_valid_expression_method_access(self):
        """Test method/property access with dots."""
        assert ValidationUtils.is_valid_expression("variable.Property") is True
        assert ValidationUtils.is_valid_expression("obj.Method()") is True

    def test_is_valid_expression_arithmetic(self):
        """Test arithmetic expressions."""
        assert ValidationUtils.is_valid_expression("value + 1") is True
        assert ValidationUtils.is_valid_expression("a - b") is True
        assert ValidationUtils.is_valid_expression("x * y") is True
        assert ValidationUtils.is_valid_expression("num / 2") is True

    def test_is_valid_expression_if_function(self):
        """Test VB.NET If function."""
        assert ValidationUtils.is_valid_expression("If(condition, true, false)") is True

    def test_is_valid_expression_assignment_like(self):
        """Test assignment-like expressions."""
        assert ValidationUtils.is_valid_expression("variable = value") is True

    def test_is_valid_expression_tostring(self):
        """Test ToString method call."""
        assert ValidationUtils.is_valid_expression("value.ToString()") is True

    def test_is_valid_expression_plain_text(self):
        """Test that plain text without expression indicators is invalid."""
        assert ValidationUtils.is_valid_expression("just plain text") is False
        assert ValidationUtils.is_valid_expression("hello world") is False

    def test_is_valid_expression_complex_valid(self):
        """Test complex valid expressions."""
        assert (
            ValidationUtils.is_valid_expression('If(value > 10, value.ToString(), "default")')
            is True
        )
        assert (
            ValidationUtils.is_valid_expression("New List(Of String) From {item1, item2}") is True
        )

    def test_is_valid_expression_whitespace_around(self):
        """Test expressions with surrounding whitespace."""
        assert ValidationUtils.is_valid_expression("  [variable]  ") is True
        assert ValidationUtils.is_valid_expression("  value.Property  ") is True
