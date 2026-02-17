"""UiPath activity-specific utilities for business logic extraction.

This module provides helper functions for UiPath activity processing,
including activity ID generation, expression extraction, selector extraction,
and activity classification.
"""

import hashlib
import re
from typing import Any


class ActivityUtils:
    """Activity-specific utilities for business logic extraction."""

    @staticmethod
    def generate_activity_id(
        project_id: str, workflow_path: str, node_id: str, activity_content: str
    ) -> str:
        """Generate stable activity identifier with content hash.

        Args:
            project_id: Project identifier or slug
            workflow_path: Path to workflow file
            node_id: Hierarchical node identifier
            activity_content: Serialized activity content for hashing

        Returns:
            Stable activity ID in format: {projectId}#{workflowId}#{nodeId}#{contentHash}

        Examples:
            f4aa3834#Process/Calculator/ClickListOfCharacters#Activity/Sequence/ForEach/Sequence/NApplicationCard/Sequence/If/Sequence/NClick#abc123ef
            frozenchlorine-1082950b#StandardCalculator#Activity/Sequence/InvokeWorkflowFile_5#def456ab
        """
        # Generate content hash
        content_hash = hashlib.sha256(activity_content.encode()).hexdigest()[:8]

        # Normalize workflow ID (POSIX paths, remove .xaml extension)
        workflow_id = workflow_path.replace("\\", "/").replace(".xaml", "")

        # Construct stable activity ID
        return f"{project_id}#{workflow_id}#{node_id}#{content_hash}"

    @staticmethod
    def extract_expressions_from_text(text: str) -> list[str]:
        """Extract UiPath expressions from text content.

        Args:
            text: Text content that may contain expressions

        Returns:
            List of extracted expressions
        """
        if not text:
            return []

        expressions = []

        # Pattern for VB.NET expressions in brackets [...]
        vb_expressions = re.findall(r"\[([^\]]+)\]", text)
        expressions.extend(vb_expressions)

        # Pattern for method calls
        method_calls = re.findall(r"\w+\.\w+\([^)]*\)", text)
        expressions.extend(method_calls)

        # Pattern for string.Format calls
        format_calls = re.findall(r"string\.Format\([^)]+\)", text, re.IGNORECASE)
        expressions.extend(format_calls)

        return list(set(expressions))  # Remove duplicates

    @staticmethod
    def extract_variable_references(text: str) -> list[str]:
        """Extract variable references from expressions.

        Args:
            text: Expression or text content

        Returns:
            List of variable names referenced
        """
        if not text:
            return []

        variables = []

        # Common variable patterns in UiPath expressions
        # Variables in brackets: [variableName]
        bracket_vars = re.findall(r"\[([a-zA-Z_]\w*)\]", text)
        variables.extend(bracket_vars)

        # Variables in expressions: variableName.Method or variableName(...).property
        # Handle both direct property access and method call property access
        var_refs = re.findall(r"([a-zA-Z_]\w*)(?:\([^)]*\))?\.", text)
        variables.extend(var_refs)

        # Variables in assignments (not comparisons)
        assignment_vars = re.findall(r"([a-zA-Z_]\w*)\s*=(?!=)", text)  # = but not ==
        variables.extend(assignment_vars)

        # Variables as standalone identifiers (function parameters, etc.)
        # Look for variables that appear after commas or parentheses but aren't method calls
        standalone_vars = re.findall(r"[,(]\s*([a-zA-Z_]\w*)(?![.(])", text)
        variables.extend(standalone_vars)

        # Filter out common method names and keywords
        filtered_vars = []
        excluded_names = {
            "string",
            "String",
            "DateTime",
            "Convert",
            "Path",
            "File",
            "Directory",
            "System",
            "Microsoft",
            "UiPath",
            "New",
            "True",
            "False",
            "Nothing",
            "If",
            "Then",
            "Else",
            "End",
            "For",
            "Each",
            "While",
            "Do",
            "Loop",
        }

        for var in variables:
            if var not in excluded_names and len(var) > 1:
                filtered_vars.append(var)

        return list(set(filtered_vars))  # Remove duplicates

    @staticmethod
    def extract_selectors_from_config(configuration: dict[str, Any]) -> dict[str, str]:
        """Extract UI selectors from activity configuration.

        Args:
            configuration: Activity configuration dictionary

        Returns:
            Dictionary mapping selector types to selector strings
        """
        selectors = {}

        # Common selector fields in UiPath activities
        selector_fields = [
            "FullSelector",
            "FuzzySelector",
            "Selector",
            "TargetSelector",
            "FullSelectorArgument",
            "FuzzySelectorArgument",
            "TargetAnchorable",
        ]

        def _extract_from_dict(data: Any, path: str = "") -> None:
            if isinstance(data, dict):
                for key, value in data.items():
                    current_path = f"{path}.{key}" if path else key

                    if key in selector_fields and isinstance(value, str):
                        selectors[current_path] = value
                    else:
                        _extract_from_dict(value, current_path)
            elif isinstance(data, list):
                for i, item in enumerate(data):
                    _extract_from_dict(item, f"{path}[{i}]")

        _extract_from_dict(configuration)
        return selectors

    @staticmethod
    def classify_activity_type(activity_type: str) -> str:
        """Classify activity type into categories.

        Args:
            activity_type: Activity type name

        Returns:
            Activity category
        """
        activity_type_lower = activity_type.lower()

        # UI Automation activities - use more specific patterns to avoid false matches
        ui_patterns = [
            "click",
            "typetext",
            "typeinto",
            "gettext",
            "getfulltext",
            "getvalue",
            "find",
            "wait",
            "hover",
            "drag",
            "select",
            "image",
            "application",
        ]
        if any(ui_pattern in activity_type_lower for ui_pattern in ui_patterns):
            return "ui_automation"

        # Flow control activities
        if any(
            flow_term in activity_type_lower
            for flow_term in [
                "sequence",
                "if",
                "switch",
                "while",
                "foreach",
                "parallel",
                "flowchart",
            ]
        ):
            return "flow_control"

        # Data activities
        if any(
            data_term in activity_type_lower
            for data_term in ["assign", "invoke", "data", "read", "write", "build", "filter"]
        ):
            return "data_processing"

        # System activities
        if any(
            sys_term in activity_type_lower
            for sys_term in ["log", "message", "delay", "kill", "start", "environment"]
        ):
            return "system"

        # Exception handling
        if any(
            exc_term in activity_type_lower
            for exc_term in ["try", "catch", "throw", "rethrow", "finally"]
        ):
            return "exception_handling"

        return "other"

    @staticmethod
    def parse_expression(expression: str, language: str = "VisualBasic") -> Any:
        """Parse expression using tokenizer-based expression parser.

        Args:
            expression: Expression text to parse
            language: Expression language ('VisualBasic' or 'CSharp')

        Returns:
            ParsedExpression with extracted variables, methods, operators
        """
        from ...stages.parsing.expression_parser import ExpressionParser

        parser = ExpressionParser(language=language)
        return parser.parse(expression)
