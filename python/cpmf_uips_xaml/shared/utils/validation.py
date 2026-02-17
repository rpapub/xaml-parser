"""Validation utilities for XAML parsing operations.

This module provides helper functions for data validation,
workflow content validation, and expression validation.
"""

import re
from typing import Any


class ValidationUtils:
    """Validation and data quality utilities."""

    @staticmethod
    def validate_workflow_content(content: dict[str, Any]) -> list[str]:
        """Validate workflow content structure and data quality.

        Args:
            content: Workflow content dictionary

        Returns:
            List of validation errors
        """
        errors = []

        # Check required fields
        required_fields = ["arguments", "variables", "activities"]
        for field in required_fields:
            if field not in content:
                errors.append(f"Missing required field: {field}")

        # Validate arguments
        if "arguments" in content:
            arg_errors = ValidationUtils._validate_arguments(content["arguments"])
            errors.extend(arg_errors)

        # Validate activities
        if "activities" in content:
            activity_errors = ValidationUtils._validate_activities(content["activities"])
            errors.extend(activity_errors)

        return errors

    @staticmethod
    def _validate_arguments(arguments: list[dict[str, Any]]) -> list[str]:
        """Validate argument definitions."""
        errors = []
        names = set()

        for i, arg in enumerate(arguments):
            # Check required fields
            if "name" not in arg or not arg["name"]:
                errors.append(f"Argument {i}: Missing or empty name")
            else:
                # Check for duplicates
                name = arg["name"]
                if name in names:
                    errors.append(f"Argument {i}: Duplicate name '{name}'")
                names.add(name)

            # Validate direction
            if "direction" in arg:
                valid_directions = {"in", "out", "inout"}
                if arg["direction"] not in valid_directions:
                    errors.append(f"Argument {i}: Invalid direction '{arg['direction']}'")

        return errors

    @staticmethod
    def _validate_activities(activities: list[dict[str, Any]]) -> list[str]:
        """Validate activity definitions."""
        errors = []
        activity_ids = set()

        for i, activity in enumerate(activities):
            # Check required fields
            if "activity_id" not in activity or not activity["activity_id"]:
                errors.append(f"Activity {i}: Missing activity_id")
            else:
                # Check for duplicate IDs
                activity_id = activity["activity_id"]
                if activity_id in activity_ids:
                    errors.append(f"Activity {i}: Duplicate activity_id '{activity_id}'")
                activity_ids.add(activity_id)

            if "tag" not in activity or not activity["tag"]:
                errors.append(f"Activity {i}: Missing tag")

        return errors

    @staticmethod
    def is_valid_expression(text: str) -> bool:
        """Check if text appears to be a valid expression.

        Args:
            text: Text to validate

        Returns:
            True if text looks like a valid expression
        """
        if not text or len(text.strip()) < 2:
            return False

        # Common expression patterns
        expression_indicators = [
            r"\[.*\]",  # VB.NET expressions in brackets
            r"New\s+\w+",  # Object creation
            r"\w+\.\w+",  # Method/property access
            r"\w+\s*[+\-*/]\s*\w+",  # Arithmetic
            r"If\s*\(",  # VB.NET If function
            r"\w+\s*=\s*",  # Assignment-like
            r"\.ToString\(\)",  # Common method call
        ]

        text_clean = text.strip()
        return any(re.search(pattern, text_clean) for pattern in expression_indicators)
