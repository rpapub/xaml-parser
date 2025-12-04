"""Expression parser for VB.NET and C# expressions in XAML workflows.

This module provides tokenization and parsing capabilities for UiPath expressions,
enabling extraction of variables, method calls, and operators from expression strings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Expression


# Token types for lexical analysis
class TokenType(str, Enum):
    """Token types for expression tokenization."""

    IDENTIFIER = "IDENTIFIER"  # Variable or method name
    BRACKET_VAR = "BRACKET_VAR"  # VB.NET [variable]
    STRING_LITERAL = "STRING_LITERAL"  # "text" or 'text'
    NUMBER = "NUMBER"  # 123, 45.67
    OPERATOR = "OPERATOR"  # +, -, AndAlso, ==, etc.
    LPAREN = "LPAREN"  # (
    RPAREN = "RPAREN"  # )
    DOT = "DOT"  # .
    COMMA = "COMMA"  # ,
    KEYWORD = "KEYWORD"  # New, If, Nothing, null, etc.
    WHITESPACE = "WHITESPACE"  # Spaces, tabs
    UNKNOWN = "UNKNOWN"  # Unrecognized


@dataclass
class Token:
    """A lexical token from expression parsing."""

    type: TokenType
    value: str
    position: int


@dataclass
class VariableAccess:
    """Records a variable access in an expression."""

    name: str  # Variable name
    access_type: str  # 'read' | 'write' | 'readwrite'
    context: str  # Where in expression (LHS, RHS, argument)
    member_chain: list[str] = field(default_factory=list)  # ['ToString', 'ToUpper']


@dataclass
class MethodCall:
    """Records a method call in an expression."""

    method_name: str  # Method name
    qualifier: str | None = None  # Qualifier (String, DateTime, variable name)
    is_static: bool = False  # True for String.Format, False for var.ToString()
    arguments: list[str] = field(default_factory=list)  # Argument expressions


@dataclass
class ParsedExpression:
    """Result of expression parsing."""

    raw: str  # Original expression
    language: str  # 'VisualBasic' | 'CSharp'
    is_valid: bool = True  # Parsing succeeded
    variables: list[VariableAccess] = field(default_factory=list)
    methods: list[MethodCall] = field(default_factory=list)
    operators: list[str] = field(default_factory=list)
    parse_errors: list[str] = field(default_factory=list)

    def to_expression(self, expression_type: str, context: str | None = None) -> Expression:
        """Convert to Expression model with populated fields.

        Args:
            expression_type: Type of expression (assignment, condition, etc.)
            context: Context where expression found (property name)

        Returns:
            Expression object with populated contains_variables and contains_methods
        """
        from .models import Expression as _Expression

        return _Expression(
            content=self.raw,
            expression_type=expression_type,
            language=self.language,
            context=context,
            contains_variables=[v.name for v in self.variables],
            contains_methods=[
                f"{m.qualifier}.{m.method_name}" if m.qualifier else m.method_name
                for m in self.methods
            ],
        )


class ExpressionTokenizer:
    """Tokenizes VB.NET and C# expressions into token streams."""

    # VB.NET patterns
    VB_OPERATORS = [
        "AndAlso",
        "OrElse",
        "Mod",
        "And",
        "Or",
        "Xor",
        "Not",
        "<>",
        "<=",
        ">=",
        "=",
        "<",
        ">",
        "+",
        "-",
        "*",
        "/",
        "&",
    ]

    VB_KEYWORDS = [
        "New",
        "If",
        "Then",
        "Else",
        "Nothing",
        "True",
        "False",
        "CType",
        "DirectCast",
        "Of",
    ]

    # C# patterns
    CS_OPERATORS = [
        "&&",
        "||",
        "==",
        "!=",
        "<=",
        ">=",
        "<<",
        ">>",
        "++",
        "--",
        "=>",
        "<",
        ">",
        "+",
        "-",
        "*",
        "/",
        "%",
        "!",
        "&",
        "|",
    ]

    CS_KEYWORDS = [
        "new",
        "if",
        "else",
        "null",
        "true",
        "false",
        "var",
        "return",
        "typeof",
        "as",
        "is",
    ]

    def __init__(self, language: str = "VisualBasic") -> None:
        """Initialize tokenizer for specific language.

        Args:
            language: 'VisualBasic' or 'CSharp'
        """
        self.language = language
        self.operators = self.VB_OPERATORS if language == "VisualBasic" else self.CS_OPERATORS
        self.keywords = self.VB_KEYWORDS if language == "VisualBasic" else self.CS_KEYWORDS

        # Sort operators by length (longest first) for greedy matching
        self.operators_sorted = sorted(self.operators, key=len, reverse=True)

    def tokenize(self, expression: str) -> list[Token]:
        """Tokenize expression into token stream.

        Args:
            expression: Expression text to tokenize

        Returns:
            List of tokens
        """
        tokens = []
        position = 0
        length = len(expression)

        while position < length:
            # Skip whitespace
            if expression[position].isspace():
                start = position
                while position < length and expression[position].isspace():
                    position += 1
                tokens.append(Token(TokenType.WHITESPACE, expression[start:position], start))
                continue

            # VB.NET bracket variables [var]
            if self.language == "VisualBasic" and expression[position] == "[":
                start = position
                position += 1
                var_name = ""
                while position < length and expression[position] != "]":
                    var_name += expression[position]
                    position += 1
                if position < length:
                    position += 1  # Skip closing ]
                tokens.append(Token(TokenType.BRACKET_VAR, var_name, start))
                continue

            # String literals
            if expression[position] in ('"', "'"):
                quote = expression[position]
                start = position
                position += 1
                string_content = quote
                while position < length:
                    if expression[position] == quote:
                        string_content += quote
                        position += 1
                        break
                    elif expression[position] == "\\" and position + 1 < length:
                        # Escape sequence
                        string_content += expression[position : position + 2]
                        position += 2
                    else:
                        string_content += expression[position]
                        position += 1
                tokens.append(Token(TokenType.STRING_LITERAL, string_content, start))
                continue

            # Numbers
            if expression[position].isdigit():
                start = position
                while position < length and (
                    expression[position].isdigit() or expression[position] == "."
                ):
                    position += 1
                tokens.append(Token(TokenType.NUMBER, expression[start:position], start))
                continue

            # Operators (multi-character, greedy matching)
            operator_matched = False
            for op in self.operators_sorted:
                if expression[position : position + len(op)] == op:
                    tokens.append(Token(TokenType.OPERATOR, op, position))
                    position += len(op)
                    operator_matched = True
                    break

            if operator_matched:
                continue

            # Single-character tokens
            char = expression[position]
            if char == "(":
                tokens.append(Token(TokenType.LPAREN, char, position))
                position += 1
            elif char == ")":
                tokens.append(Token(TokenType.RPAREN, char, position))
                position += 1
            elif char == ".":
                tokens.append(Token(TokenType.DOT, char, position))
                position += 1
            elif char == ",":
                tokens.append(Token(TokenType.COMMA, char, position))
                position += 1
            # Identifiers and keywords
            elif char.isalpha() or char == "_":
                start = position
                while position < length and (
                    expression[position].isalnum() or expression[position] == "_"
                ):
                    position += 1
                identifier = expression[start:position]

                # Check if it's a keyword
                if identifier in self.keywords:
                    tokens.append(Token(TokenType.KEYWORD, identifier, start))
                else:
                    tokens.append(Token(TokenType.IDENTIFIER, identifier, start))
            else:
                # Unknown token
                tokens.append(Token(TokenType.UNKNOWN, char, position))
                position += 1

        return tokens


class ExpressionParser:
    """Parses tokenized expressions to extract semantic information."""

    # Common .NET type names to exclude from variable extraction
    COMMON_TYPES = {
        "String",
        "Int32",
        "Int64",
        "Double",
        "Boolean",
        "DateTime",
        "TimeSpan",
        "Object",
        "Array",
        "List",
        "Dictionary",
        "Convert",
        "Math",
        "Path",
        "File",
        "Directory",
        "Console",
        "Enumerable",
        "Regex",
    }

    def __init__(self, language: str = "VisualBasic") -> None:
        """Initialize parser for specific language.

        Args:
            language: 'VisualBasic' or 'CSharp'
        """
        self.language = language
        self.tokenizer = ExpressionTokenizer(language)

    @lru_cache(maxsize=256)
    def parse(self, expression: str) -> ParsedExpression:
        """Parse expression and extract variables, methods, operators.

        Args:
            expression: Expression text to parse

        Returns:
            ParsedExpression with analysis results
        """
        if not expression or not expression.strip():
            return ParsedExpression(raw=expression, language=self.language, is_valid=False)

        try:
            tokens = self.tokenizer.tokenize(expression)

            # Filter out whitespace tokens for analysis
            tokens = [t for t in tokens if t.type != TokenType.WHITESPACE]

            # Extract components
            variables = self._extract_variables(tokens, expression)
            methods = self._extract_methods(tokens)
            operators = self._extract_operators(tokens)

            return ParsedExpression(
                raw=expression,
                language=self.language,
                is_valid=True,
                variables=variables,
                methods=methods,
                operators=operators,
            )
        except Exception as e:
            # Graceful degradation
            return ParsedExpression(
                raw=expression,
                language=self.language,
                is_valid=False,
                parse_errors=[str(e)],
            )

    def _extract_variables(self, tokens: list[Token], raw_expr: str) -> list[VariableAccess]:
        """Extract variable accesses with read/write classification.

        Args:
            tokens: Token stream
            raw_expr: Original expression for context

        Returns:
            List of variable accesses
        """
        variables = []

        # Find assignment operator to determine LHS vs RHS
        assignment_index = -1
        for i, token in enumerate(tokens):
            if token.type == TokenType.OPERATOR:
                # VB uses '=' for assignment, C# uses '=' but not '=='
                if self.language == "VisualBasic" and token.value == "=":
                    assignment_index = i
                    break
                elif (
                    self.language == "CSharp"
                    and token.value == "="
                    and (i + 1 >= len(tokens) or tokens[i + 1].value != "=")
                ):
                    assignment_index = i
                    break

        for i, token in enumerate(tokens):
            var_name = None
            member_chain = []

            # VB.NET bracket variables
            if token.type == TokenType.BRACKET_VAR:
                var_name = token.value

            # Regular identifiers (could be variables)
            elif token.type == TokenType.IDENTIFIER:
                # Skip common type names
                if token.value in self.COMMON_TYPES:
                    continue

                # Skip if followed by ( - it's a method call, not a variable
                if i + 1 < len(tokens) and tokens[i + 1].type == TokenType.LPAREN:
                    continue

                # Skip if preceded by DOT - it's a member access
                if i > 0 and tokens[i - 1].type == TokenType.DOT:
                    continue

                var_name = token.value

            if var_name:
                # Determine access type
                if assignment_index >= 0 and i < assignment_index:
                    access_type = "write"
                    context = "LHS"
                else:
                    access_type = "read"
                    context = "RHS"

                # Extract member chain (e.g., var.Method1().Property)
                j = i + 1
                while j < len(tokens):
                    if tokens[j].type == TokenType.DOT and j + 1 < len(tokens):
                        j += 1
                        if tokens[j].type == TokenType.IDENTIFIER:
                            member_chain.append(tokens[j].value)
                            j += 1
                            # Skip method parentheses
                            if j < len(tokens) and tokens[j].type == TokenType.LPAREN:
                                paren_depth = 1
                                j += 1
                                while j < len(tokens) and paren_depth > 0:
                                    if tokens[j].type == TokenType.LPAREN:
                                        paren_depth += 1
                                    elif tokens[j].type == TokenType.RPAREN:
                                        paren_depth -= 1
                                    j += 1
                        else:
                            break
                    else:
                        break

                variables.append(
                    VariableAccess(
                        name=var_name,
                        access_type=access_type,
                        context=context,
                        member_chain=member_chain,
                    )
                )

        return variables

    def _extract_methods(self, tokens: list[Token]) -> list[MethodCall]:
        """Extract method calls with qualifiers.

        Args:
            tokens: Token stream

        Returns:
            List of method calls
        """
        methods = []

        for i, token in enumerate(tokens):
            # Method call pattern: IDENTIFIER followed by LPAREN
            if (
                token.type == TokenType.IDENTIFIER
                and i + 1 < len(tokens)
                and tokens[i + 1].type == TokenType.LPAREN
            ):
                method_name = token.value
                qualifier = None
                is_static = False

                # Look back for qualifier (e.g., String.Format, var.ToString)
                if i > 1 and tokens[i - 1].type == TokenType.DOT:
                    if tokens[i - 2].type == TokenType.IDENTIFIER:
                        qualifier = tokens[i - 2].value
                        # Check if it's a static call (common type name)
                        is_static = qualifier in self.COMMON_TYPES
                    elif tokens[i - 2].type == TokenType.BRACKET_VAR:
                        qualifier = tokens[i - 2].value
                        is_static = False

                # Extract arguments (basic - just count them)
                arguments = []
                if i + 1 < len(tokens) and tokens[i + 1].type == TokenType.LPAREN:
                    paren_depth = 1
                    j = i + 2
                    arg_start = j
                    while j < len(tokens) and paren_depth > 0:
                        if tokens[j].type == TokenType.LPAREN:
                            paren_depth += 1
                        elif tokens[j].type == TokenType.RPAREN:
                            paren_depth -= 1
                            if paren_depth == 0:
                                # End of method call
                                if j > arg_start:
                                    # Has arguments (simplified - just note presence)
                                    arguments.append("arg")
                        elif tokens[j].type == TokenType.COMMA and paren_depth == 1:
                            # Argument separator
                            arguments.append("arg")
                            arg_start = j + 1
                        j += 1

                methods.append(
                    MethodCall(
                        method_name=method_name,
                        qualifier=qualifier,
                        is_static=is_static,
                        arguments=arguments,
                    )
                )

        return methods

    def _extract_operators(self, tokens: list[Token]) -> list[str]:
        """Extract operators from token stream.

        Args:
            tokens: Token stream

        Returns:
            List of operator strings
        """
        return [t.value for t in tokens if t.type == TokenType.OPERATOR]
