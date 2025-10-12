"""Expression parsing for VB.NET and C# expressions in XAML.

This module provides regex-based parsing of UiPath expressions to extract
variable references and transformation operations.
"""

import re
from dataclasses import dataclass, field


@dataclass
class Transformation:
    """Single transformation step in an expression.

    Attributes:
        operation: Type of operation
        details: Operation-specific details
        is_static: Whether operation is deterministic (static key, known method)
    """

    operation: (
        str  # 'dictionary_access' | 'method_call' | 'property_access' | 'array_index' | 'cast'
    )
    details: dict[str, str | bool | int] = field(default_factory=dict)
    is_static: bool = True


@dataclass
class ExpressionAnalysis:
    """Result of analyzing an expression.

    Attributes:
        source_variables: Variable names referenced in expression
        transformations: Transformation chain applied
        confidence: Analysis confidence level
        raw_expression: Original expression text
    """

    source_variables: list[str] = field(default_factory=list)
    transformations: list[Transformation] = field(default_factory=list)
    confidence: str = "definite"  # 'definite' | 'possible' | 'unknown'
    raw_expression: str = ""


class ExpressionParser:
    """Parser for VB.NET and C# expressions in XAML workflows."""

    # VB.NET keywords to exclude from variable matching
    VB_KEYWORDS = {
        "New",
        "String",
        "Integer",
        "Boolean",
        "Object",
        "True",
        "False",
        "Nothing",
        "If",
        "Then",
        "Else",
        "ElseIf",
        "And",
        "Or",
        "Not",
        "AndAlso",
        "OrElse",
        "Xor",
        "For",
        "Each",
        "Next",
        "While",
        "Do",
        "Loop",
        "Select",
        "Case",
        "Function",
        "Sub",
        "Return",
        "Dim",
        "As",
        "Get",
        "Set",
        "Property",
        "Const",
        "ReadOnly",
        "Imports",
        "Namespace",
        "Class",
        "Module",
        "Structure",
        "Enum",
        "Interface",
        "Inherits",
        "Implements",
        "Public",
        "Private",
        "Protected",
        "Friend",
        "Shared",
        "Overridable",
        "Overrides",
        "MustOverride",
        "NotOverridable",
        "MustInherit",
        "NotInheritable",
        "Shadows",
        "Partial",
        "Try",
        "Catch",
        "Finally",
        "Throw",
        "Exit",
        "Continue",
        "GoTo",
        "With",
        "End",
        "Me",
        "MyBase",
        "MyClass",
        "AddHandler",
        "RemoveHandler",
        "RaiseEvent",
        "CType",
        "DirectCast",
        "TryCast",
        "GetType",
        "TypeOf",
        "Is",
        "IsNot",
        "Like",
        "Mod",
        # Cast functions
        "CInt",
        "CStr",
        "CDbl",
        "CBool",
        "CDate",
        "CLng",
        "CShort",
        "CByte",
        # Common method names
        "ToString",
        "ToUpper",
        "ToLower",
        "Trim",
        "Split",
        "Replace",
        "Substring",
        "Contains",
        "StartsWith",
        "EndsWith",
        "IndexOf",
        "Count",
        "Length",
        "Add",
        "Remove",
        "Clear",
        "First",
        "Last",
        "Where",
        "OrderBy",
        "GroupBy",
        "Join",
        "Sum",
        "Average",
        "Min",
        "Max",
        "Any",
        "All",
        "Take",
        "Skip",
        "Distinct",
        "Concat",
        "Union",
        "Intersect",
        "Except",
    }

    def analyze(self, expression: str) -> ExpressionAnalysis:
        """Analyze expression to extract variables and transformations.

        Args:
            expression: VB.NET or C# expression string

        Returns:
            ExpressionAnalysis with parsed components

        Examples:
            >>> parser = ExpressionParser()
            >>> parser.analyze("[myVar]")
            ExpressionAnalysis(source_variables=["myVar"], transformations=[])

            >>> parser.analyze('[Config("Key").ToString()]')
            ExpressionAnalysis(
                source_variables=["Config"],
                transformations=[
                    Transformation(op='dictionary_access', details={'key': 'Key'}),
                    Transformation(op='method_call', details={'method': 'ToString'})
                ]
            )
        """
        result = ExpressionAnalysis(raw_expression=expression)

        # Remove outer brackets if present: [expr] → expr
        expr = expression.strip()
        if expr.startswith("[") and expr.endswith("]"):
            expr = expr[1:-1].strip()

        # Handle empty expression
        if not expr or expr == "{x:Null}":
            result.confidence = "unknown"
            return result

        # Try to parse as simple variable reference first
        simple_var = self._parse_simple_variable(expr)
        if simple_var:
            result.source_variables = [simple_var]
            result.confidence = "definite"
            return result

        # Try complex expression parsing
        variables, transformations, confidence = self._parse_complex_expression(expr)
        result.source_variables = variables
        result.transformations = transformations
        result.confidence = confidence

        return result

    def _parse_simple_variable(self, expr: str) -> str | None:
        """Parse simple variable reference: just a variable name.

        Args:
            expr: Expression without brackets

        Returns:
            Variable name if simple reference, None otherwise
        """
        # Must be valid identifier with no operators or special chars
        if re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", expr):
            # Exclude keywords
            if expr not in self.VB_KEYWORDS:
                return expr
        return None

    def _parse_complex_expression(self, expr: str) -> tuple[list[str], list[Transformation], str]:
        """Parse complex expression with transformations.

        Args:
            expr: Expression without brackets

        Returns:
            Tuple of (variables, transformations, confidence)
        """
        variables: list[str] = []
        transformations: list[Transformation] = []
        confidence = "definite"

        # Pattern 0: Cast/conversion functions (CHECK FIRST before dictionary access)
        #   CInt(someVar)
        #   CStr(value)
        cast_match = re.match(
            r"^(CInt|CStr|CDbl|CBool|CDate|CLng|CShort|CByte|CType|DirectCast|TryCast)\s*\((.+)\)$",
            expr,
            re.IGNORECASE,
        )
        if cast_match:
            cast_func = cast_match.group(1)
            inner_expr = cast_match.group(2)

            # Recursively parse inner expression
            inner_vars, inner_transforms, inner_conf = self._parse_complex_expression(inner_expr)

            transformations.extend(inner_transforms)
            transformations.append(
                Transformation(
                    operation="cast",
                    details={"cast_function": cast_func},
                    is_static=True,
                )
            )

            return (inner_vars, transformations, inner_conf)

        # Pattern 1: Dictionary/Collection access with chaining
        #   Config("Key").ToString()
        #   arr(index).Property
        dict_chain_match = re.match(r"^([a-zA-Z_][a-zA-Z0-9_]*)\s*\(([^)]+)\)(.*)$", expr)
        if dict_chain_match:
            var_name = dict_chain_match.group(1)
            access_expr = dict_chain_match.group(2)
            remainder = dict_chain_match.group(3)

            if var_name not in self.VB_KEYWORDS:
                variables.append(var_name)

            # Determine if key is static (string literal) or dynamic (variable)
            is_static_key = bool(re.match(r'^["\'].*["\']$', access_expr.strip()))
            key_value = access_expr.strip().strip('"').strip("'")

            if is_static_key:
                transformations.append(
                    Transformation(
                        operation="dictionary_access",
                        details={"key": key_value, "key_is_static": True},
                        is_static=True,
                    )
                )
            else:
                # Dynamic key - could be variable or expression
                transformations.append(
                    Transformation(
                        operation="dictionary_access",
                        details={"key": access_expr.strip(), "key_is_static": False},
                        is_static=False,
                    )
                )
                confidence = "possible"

            # Parse remainder for method calls, property access
            if remainder:
                remainder_vars, remainder_transforms, remainder_conf = self._parse_method_chain(
                    remainder
                )
                variables.extend(remainder_vars)
                transformations.extend(remainder_transforms)
                if remainder_conf != "definite":
                    confidence = remainder_conf

            return (variables, transformations, confidence)

        # Pattern 2: Method/property chain without dictionary access
        #   someVar.ToString()
        #   obj.Property.Method()
        if "." in expr:
            return self._parse_method_chain(expr)

        # Pattern 3: Multiple variables (aggregation)
        #   var1 + var2
        #   firstName & " " & lastName
        if any(op in expr for op in ["+", "&", "-", "*", "/", "&&", "||"]):
            all_vars = self._extract_all_variables(expr)
            if len(all_vars) > 1:
                return (
                    all_vars,
                    [
                        Transformation(
                            operation="aggregate",
                            details={"expression": expr},
                            is_static=False,
                        )
                    ],
                    "possible",
                )
            elif len(all_vars) == 1:
                return (
                    all_vars,
                    [
                        Transformation(
                            operation="transform",
                            details={"expression": expr},
                            is_static=False,
                        )
                    ],
                    "possible",
                )

        # Fallback: extract all variables and mark as unknown
        all_vars = self._extract_all_variables(expr)
        return (
            all_vars,
            [
                Transformation(
                    operation="transform",
                    details={"expression": expr},
                    is_static=False,
                )
            ],
            "unknown" if len(all_vars) > 1 or not all_vars else "possible",
        )

    def _parse_method_chain(self, expr: str) -> tuple[list[str], list[Transformation], str]:
        """Parse method/property chain: obj.Method().Property.Method2()

        Args:
            expr: Expression potentially starting with . or containing method chains

        Returns:
            Tuple of (variables, transformations, confidence)
        """
        variables: list[str] = []
        transformations: list[Transformation] = []
        confidence = "definite"

        # Split on dots, being careful with method parentheses
        parts = []
        current_part = ""
        paren_depth = 0

        for char in expr:
            if char == "(":
                paren_depth += 1
                current_part += char
            elif char == ")":
                paren_depth -= 1
                current_part += char
            elif char == "." and paren_depth == 0:
                if current_part:
                    parts.append(current_part)
                current_part = ""
            else:
                current_part += char

        if current_part:
            parts.append(current_part)

        # First part should be the base variable (if not starting with .)
        if parts and not expr.startswith("."):
            first_part = parts[0].strip()
            # Check if it's a simple variable
            simple_var = self._parse_simple_variable(first_part)
            if simple_var:
                variables.append(simple_var)
                parts = parts[1:]

        # Process remaining parts as methods/properties
        for part in parts:
            part = part.strip()
            if not part:
                continue

            # Method call: Name(args)
            if "(" in part:
                method_match = re.match(r"^([a-zA-Z_][a-zA-Z0-9_]*)\s*\(([^)]*)\)$", part)
                if method_match:
                    method_name = method_match.group(1)
                    args = method_match.group(2).strip()

                    transformations.append(
                        Transformation(
                            operation="method_call",
                            details={"method": method_name, "arguments": args},
                            is_static=True,
                        )
                    )
            else:
                # Property access: Name
                if re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", part):
                    transformations.append(
                        Transformation(
                            operation="property_access",
                            details={"property": part},
                            is_static=True,
                        )
                    )

        return (variables, transformations, confidence)

    def _extract_all_variables(self, expr: str) -> list[str]:
        """Extract all variable references from expression.

        Uses pattern matching to find all identifiers that look like variables,
        excluding keywords and known method names.

        Args:
            expr: Expression to scan

        Returns:
            List of variable names found
        """
        # Find all identifier-like tokens
        pattern = r"\b([a-zA-Z_][a-zA-Z0-9_]*)\b"
        candidates = re.findall(pattern, expr)

        # Filter out keywords and common methods
        variables = []
        for candidate in candidates:
            if candidate not in self.VB_KEYWORDS and candidate not in variables:
                variables.append(candidate)

        return variables
