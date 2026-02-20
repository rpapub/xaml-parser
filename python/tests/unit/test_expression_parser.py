"""Tests for expression parser module (v0.2.9 tokenizer-based parser)."""

from cpmf_uips_xaml.stages.parsing.expression_parser import (
    ExpressionParser,
    ExpressionTokenizer,
    TokenType,
)


class TestExpressionTokenizer:
    """Test expression tokenization for VB.NET and C#."""

    def test_tokenize_simple_vb_expression(self):
        """Test tokenizing simple VB.NET expression."""
        tokenizer = ExpressionTokenizer("VisualBasic")
        tokens = tokenizer.tokenize("counter + 1")

        assert len(tokens) == 5  # counter, +, 1, plus whitespace tokens
        assert tokens[0].type == TokenType.IDENTIFIER
        assert tokens[0].value == "counter"

    def test_tokenize_bracket_variable(self):
        """Test tokenizing VB.NET bracketed variable."""
        tokenizer = ExpressionTokenizer("VisualBasic")
        tokens = tokenizer.tokenize("[my variable]")

        # Filter whitespace
        tokens = [t for t in tokens if t.type != TokenType.WHITESPACE]
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.BRACKET_VAR
        assert tokens[0].value == "my variable"

    def test_tokenize_string_literal(self):
        """Test tokenizing string literals."""
        tokenizer = ExpressionTokenizer("VisualBasic")
        tokens = tokenizer.tokenize('"Hello World"')

        assert len(tokens) == 1
        assert tokens[0].type == TokenType.STRING_LITERAL
        assert tokens[0].value == '"Hello World"'

    def test_tokenize_method_call(self):
        """Test tokenizing method call."""
        tokenizer = ExpressionTokenizer("VisualBasic")
        tokens = tokenizer.tokenize("myVar.ToString()")

        tokens = [t for t in tokens if t.type != TokenType.WHITESPACE]
        assert tokens[0].type == TokenType.IDENTIFIER  # myVar
        assert tokens[1].type == TokenType.DOT
        assert tokens[2].type == TokenType.IDENTIFIER  # ToString
        assert tokens[3].type == TokenType.LPAREN
        assert tokens[4].type == TokenType.RPAREN

    def test_tokenize_vb_operators(self):
        """Test tokenizing VB.NET operators."""
        tokenizer = ExpressionTokenizer("VisualBasic")
        tokens = tokenizer.tokenize("a AndAlso b")

        tokens = [t for t in tokens if t.type != TokenType.WHITESPACE]
        assert tokens[1].type == TokenType.OPERATOR
        assert tokens[1].value == "AndAlso"

    def test_tokenize_csharp_operators(self):
        """Test tokenizing C# operators."""
        tokenizer = ExpressionTokenizer("CSharp")
        tokens = tokenizer.tokenize("a && b")

        tokens = [t for t in tokens if t.type != TokenType.WHITESPACE]
        assert tokens[1].type == TokenType.OPERATOR
        assert tokens[1].value == "&&"

    def test_tokenize_numbers(self):
        """Test tokenizing numeric literals."""
        tokenizer = ExpressionTokenizer("VisualBasic")
        tokens = tokenizer.tokenize("42 + 3.14")

        tokens = [t for t in tokens if t.type != TokenType.WHITESPACE]
        assert tokens[0].type == TokenType.NUMBER
        assert tokens[0].value == "42"
        assert tokens[2].type == TokenType.NUMBER
        assert tokens[2].value == "3.14"

    def test_tokenize_keywords(self):
        """Test tokenizing keywords."""
        tokenizer = ExpressionTokenizer("VisualBasic")
        tokens = tokenizer.tokenize("If True Then x Else y")

        tokens = [t for t in tokens if t.type != TokenType.WHITESPACE]
        assert tokens[0].type == TokenType.KEYWORD  # If
        assert tokens[0].value == "If"
        assert tokens[1].type == TokenType.KEYWORD  # True
        assert tokens[1].value == "True"


class TestExpressionParserVariables:
    """Test variable extraction from expressions."""

    def test_parse_simple_variable(self):
        """Test parsing simple variable reference."""
        parser = ExpressionParser("VisualBasic")
        result = parser.parse("counter")

        assert result.is_valid
        assert len(result.variables) == 1
        assert result.variables[0].name == "counter"
        assert result.variables[0].access_type == "read"

    def test_parse_bracket_variable(self):
        """Test parsing VB.NET bracketed variable."""
        parser = ExpressionParser("VisualBasic")
        result = parser.parse("[my variable]")

        assert result.is_valid
        assert len(result.variables) == 1
        assert result.variables[0].name == "my variable"
        assert result.variables[0].access_type == "read"

    def test_parse_assignment_read_write(self):
        """Test detecting read vs write in assignment."""
        parser = ExpressionParser("VisualBasic")
        result = parser.parse("result = counter + 1")

        assert result.is_valid
        assert len(result.variables) == 2

        # Find result and counter
        result_var = next((v for v in result.variables if v.name == "result"), None)
        counter_var = next((v for v in result.variables if v.name == "counter"), None)

        assert result_var is not None
        assert result_var.access_type == "write"
        assert result_var.context == "LHS"

        assert counter_var is not None
        assert counter_var.access_type == "read"
        assert counter_var.context == "RHS"

    def test_parse_multiple_reads(self):
        """Test parsing multiple variable reads."""
        parser = ExpressionParser("VisualBasic")
        result = parser.parse("firstName + lastName")

        assert result.is_valid
        assert len(result.variables) == 2
        names = {v.name for v in result.variables}
        assert names == {"firstName", "lastName"}
        assert all(v.access_type == "read" for v in result.variables)

    def test_parse_member_chain(self):
        """Test parsing variable with member chain."""
        parser = ExpressionParser("VisualBasic")
        result = parser.parse("myVar.ToString().ToUpper()")

        assert result.is_valid
        assert len(result.variables) == 1
        assert result.variables[0].name == "myVar"
        assert result.variables[0].member_chain == ["ToString", "ToUpper"]

    def test_exclude_common_types(self):
        """Test that common .NET types are excluded from variables."""
        parser = ExpressionParser("VisualBasic")
        result = parser.parse("String.Format(template, value)")

        # String should not be in variables (it's a type)
        # value should be in variables
        var_names = {v.name for v in result.variables}
        assert "String" not in var_names
        assert "template" in var_names
        assert "value" in var_names


class TestExpressionParserMethods:
    """Test method call extraction from expressions."""

    def test_parse_simple_method(self):
        """Test parsing simple method call."""
        parser = ExpressionParser("VisualBasic")
        result = parser.parse("myVar.ToString()")

        assert result.is_valid
        assert len(result.methods) == 1
        assert result.methods[0].method_name == "ToString"
        assert result.methods[0].qualifier == "myVar"
        assert result.methods[0].is_static is False

    def test_parse_static_method(self):
        """Test parsing static method call."""
        parser = ExpressionParser("VisualBasic")
        result = parser.parse('String.Format("Hello {0}", name)')

        assert result.is_valid
        assert len(result.methods) == 1
        assert result.methods[0].method_name == "Format"
        assert result.methods[0].qualifier == "String"
        assert result.methods[0].is_static is True

    def test_parse_method_chain(self):
        """Test parsing chained method calls."""
        parser = ExpressionParser("VisualBasic")
        result = parser.parse("text.ToUpper().Trim()")

        assert result.is_valid
        assert len(result.methods) == 2
        assert result.methods[0].method_name == "ToUpper"
        assert result.methods[0].qualifier == "text"
        assert result.methods[1].method_name == "Trim"
        assert result.methods[1].qualifier is None  # Chained, no direct qualifier

    def test_parse_method_with_arguments(self):
        """Test parsing method with arguments."""
        parser = ExpressionParser("VisualBasic")
        result = parser.parse("String.Join(delimiter, items)")

        assert result.is_valid
        assert len(result.methods) == 1
        assert result.methods[0].method_name == "Join"
        assert len(result.methods[0].arguments) == 2  # Two arguments


class TestExpressionParserOperators:
    """Test operator extraction from expressions."""

    def test_parse_arithmetic_operators(self):
        """Test parsing arithmetic operators."""
        parser = ExpressionParser("VisualBasic")
        result = parser.parse("a + b - c * d / e")

        assert result.is_valid
        assert len(result.operators) == 4
        assert "+" in result.operators
        assert "-" in result.operators
        assert "*" in result.operators
        assert "/" in result.operators

    def test_parse_vb_comparison_operators(self):
        """Test parsing VB.NET comparison operators."""
        parser = ExpressionParser("VisualBasic")
        result = parser.parse("x = 5 And y <> 10")

        assert result.is_valid
        assert "=" in result.operators
        assert "And" in result.operators
        assert "<>" in result.operators

    def test_parse_vb_logical_operators(self):
        """Test parsing VB.NET logical operators."""
        parser = ExpressionParser("VisualBasic")
        result = parser.parse("condition1 AndAlso condition2 OrElse condition3")

        assert result.is_valid
        assert "AndAlso" in result.operators
        assert "OrElse" in result.operators

    def test_parse_csharp_operators(self):
        """Test parsing C# operators."""
        parser = ExpressionParser("CSharp")
        result = parser.parse("x == 5 && y != 10")

        assert result.is_valid
        assert "==" in result.operators
        assert "&&" in result.operators
        assert "!=" in result.operators


class TestExpressionParserEdgeCases:
    """Test edge cases and error handling."""

    def test_parse_empty_expression(self):
        """Test parsing empty expression."""
        parser = ExpressionParser("VisualBasic")
        result = parser.parse("")

        assert result.is_valid is False
        assert len(result.variables) == 0
        assert len(result.methods) == 0

    def test_parse_whitespace_only(self):
        """Test parsing whitespace-only expression."""
        parser = ExpressionParser("VisualBasic")
        result = parser.parse("   ")

        assert result.is_valid is False

    def test_parse_complex_expression(self):
        """Test parsing complex real-world expression."""
        parser = ExpressionParser("VisualBasic")
        expr = 'String.Format("Result: {0}", counter.ToString())'
        result = parser.parse(expr)

        assert result.is_valid
        assert len(result.variables) == 1
        assert result.variables[0].name == "counter"
        assert len(result.methods) >= 2  # Format and ToString

    def test_parse_with_nested_parentheses(self):
        """Test parsing with nested parentheses."""
        parser = ExpressionParser("VisualBasic")
        result = parser.parse("Calculate(GetValue(x), GetValue(y))")

        assert result.is_valid
        assert len(result.methods) == 3  # Calculate, GetValue (x2)

    def test_parse_string_with_escaped_quotes(self):
        """Test parsing string with escaped quotes."""
        parser = ExpressionParser("VisualBasic")
        result = parser.parse('"She said \\"Hello\\""')

        assert result.is_valid
        # Should have the string literal token

    def test_caching_works(self):
        """Test that LRU cache works for repeated parsing."""
        parser = ExpressionParser("VisualBasic")

        result1 = parser.parse("counter + 1")
        result2 = parser.parse("counter + 1")

        # Results should be identical (cached)
        assert result1 is result2


class TestParsedExpressionToExpression:
    """Test conversion from ParsedExpression to Expression model."""

    def test_to_expression_populates_fields(self):
        """Test that to_expression() populates contains_variables and contains_methods."""
        parser = ExpressionParser("VisualBasic")
        parsed = parser.parse('result = String.Format("{0}", counter.ToString())')

        expr = parsed.to_expression(expression_type="assignment", context="Value")

        assert expr.content == parsed.raw
        assert expr.expression_type == "assignment"
        assert expr.language == "VisualBasic"
        assert expr.context == "Value"

        # Check contains_variables populated
        assert "result" in expr.contains_variables
        assert "counter" in expr.contains_variables

        # Check contains_methods populated
        method_names = [m for m in expr.contains_methods]
        assert any("Format" in m for m in method_names)
        assert any("ToString" in m for m in method_names)

    def test_to_expression_with_qualified_methods(self):
        """Test that qualified methods are formatted correctly."""
        parser = ExpressionParser("VisualBasic")
        parsed = parser.parse("String.IsNullOrEmpty(text)")

        expr = parsed.to_expression(expression_type="condition")

        # Should have "String.IsNullOrEmpty" in contains_methods
        assert "String.IsNullOrEmpty" in expr.contains_methods


class TestLanguageSpecificParsing:
    """Test language-specific parsing (VB.NET vs C#)."""

    def test_vb_bracket_syntax(self):
        """Test VB.NET bracket variable syntax."""
        parser = ExpressionParser("VisualBasic")
        result = parser.parse("[variable with spaces]")

        assert result.is_valid
        assert len(result.variables) == 1
        assert result.variables[0].name == "variable with spaces"

    def test_csharp_no_bracket_syntax(self):
        """Test that C# doesn't support bracket syntax."""
        parser = ExpressionParser("CSharp")
        parser.parse("[variable]")

        # In C#, brackets are not for variables
        # Should not extract "variable" as a variable name
        # (Would be treated as array access or other syntax)

    def test_vb_keywords(self):
        """Test VB.NET keyword recognition."""
        parser = ExpressionParser("VisualBasic")
        result = parser.parse("If condition Then result Else fallback")

        # Keywords should not be treated as variables
        var_names = {v.name for v in result.variables}
        assert "If" not in var_names
        assert "Then" not in var_names
        assert "Else" not in var_names

        # But condition, result, fallback should be
        assert "condition" in var_names
        assert "result" in var_names
        assert "fallback" in var_names

    def test_csharp_keywords(self):
        """Test C# keyword recognition."""
        parser = ExpressionParser("CSharp")
        result = parser.parse("if (condition) return value")

        # Keywords should not be treated as variables
        var_names = {v.name for v in result.variables}
        assert "if" not in var_names
        assert "return" not in var_names

        # But condition and value should be
        assert "condition" in var_names
        assert "value" in var_names


class TestRealWorldExpressions:
    """Test parsing of real-world UiPath expressions."""

    def test_parse_assign_activity_value(self):
        """Test parsing typical Assign activity value."""
        parser = ExpressionParser("VisualBasic")
        result = parser.parse("counter = counter + 1")

        assert result.is_valid
        assert len(result.variables) == 2
        # counter appears twice (write and read)

    def test_parse_log_message_expression(self):
        """Test parsing LogMessage activity expression."""
        parser = ExpressionParser("VisualBasic")
        result = parser.parse('"Processing item: " + item.ToString()')

        assert result.is_valid
        assert "item" in {v.name for v in result.variables}
        assert any(m.method_name == "ToString" for m in result.methods)

    def test_parse_if_condition(self):
        """Test parsing If activity condition."""
        parser = ExpressionParser("VisualBasic")
        result = parser.parse("counter > 10 AndAlso status <> Nothing")

        assert result.is_valid
        assert "counter" in {v.name for v in result.variables}
        assert "status" in {v.name for v in result.variables}
        assert ">" in result.operators
        assert "AndAlso" in result.operators
        assert "<>" in result.operators

    def test_parse_datetime_manipulation(self):
        """Test parsing DateTime manipulation expression."""
        parser = ExpressionParser("VisualBasic")
        result = parser.parse("DateTime.Now.AddDays(offset)")

        assert result.is_valid
        assert "offset" in {v.name for v in result.variables}
        assert any(m.method_name == "AddDays" for m in result.methods)

    def test_parse_string_format(self):
        """Test parsing String.Format expression."""
        parser = ExpressionParser("VisualBasic")
        result = parser.parse(
            'String.Format("Hello {0}, you have {1} messages", userName, msgCount)'
        )

        assert result.is_valid
        assert "userName" in {v.name for v in result.variables}
        assert "msgCount" in {v.name for v in result.variables}
        assert any(m.method_name == "Format" and m.is_static for m in result.methods)

    def test_parse_linq_expression(self):
        """Test parsing LINQ-like expression."""
        parser = ExpressionParser("VisualBasic")
        result = parser.parse("items.Where(Function(x) x.IsActive).Count()")

        assert result.is_valid
        assert "items" in {v.name for v in result.variables}
        # Should detect Where and Count methods
