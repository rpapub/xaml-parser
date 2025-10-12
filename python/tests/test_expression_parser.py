"""Tests for expression parser module."""

from xaml_parser.expression_parser import ExpressionParser


class TestSimpleExpressions:
    """Test parsing of simple variable references."""

    def setup_method(self):
        """Setup parser for each test."""
        self.parser = ExpressionParser()

    def test_parse_bracketed_variable(self):
        """Test parsing [varName]"""
        result = self.parser.analyze("[myVar]")
        assert len(result.source_variables) == 1
        assert result.source_variables[0] == "myVar"
        assert len(result.transformations) == 0
        assert result.confidence == "definite"

    def test_parse_simple_variable(self):
        """Test parsing varName without brackets"""
        result = self.parser.analyze("myVar")
        assert len(result.source_variables) == 1
        assert result.source_variables[0] == "myVar"
        assert len(result.transformations) == 0

    def test_parse_empty_expression(self):
        """Test parsing empty expression"""
        result = self.parser.analyze("")
        assert len(result.source_variables) == 0
        assert result.confidence == "unknown"

    def test_parse_null_expression(self):
        """Test parsing {x:Null}"""
        result = self.parser.analyze("{x:Null}")
        assert len(result.source_variables) == 0
        assert result.confidence == "unknown"


class TestDictionaryAccess:
    """Test parsing of dictionary/collection access."""

    def setup_method(self):
        """Setup parser for each test."""
        self.parser = ExpressionParser()

    def test_parse_dict_access_static_key(self):
        """Test parsing Config("Key")"""
        result = self.parser.analyze('[Config("ConnectionString")]')
        assert len(result.source_variables) == 1
        assert result.source_variables[0] == "Config"
        assert len(result.transformations) == 1
        assert result.transformations[0].operation == "dictionary_access"
        assert result.transformations[0].details["key"] == "ConnectionString"
        assert result.transformations[0].details["key_is_static"] is True
        assert result.confidence == "definite"

    def test_parse_dict_access_dynamic_key(self):
        """Test parsing Config(keyVar)"""
        result = self.parser.analyze("[Config(keyVar)]")
        assert len(result.source_variables) == 1
        assert result.source_variables[0] == "Config"
        assert len(result.transformations) == 1
        assert result.transformations[0].operation == "dictionary_access"
        assert result.transformations[0].details["key_is_static"] is False
        assert result.confidence == "possible"

    def test_parse_dict_access_with_method(self):
        """Test parsing Config("Key").ToString()"""
        result = self.parser.analyze('[Config("Key").ToString()]')
        assert len(result.source_variables) == 1
        assert result.source_variables[0] == "Config"
        assert len(result.transformations) == 2
        assert result.transformations[0].operation == "dictionary_access"
        assert result.transformations[0].details["key"] == "Key"
        assert result.transformations[1].operation == "method_call"
        assert result.transformations[1].details["method"] == "ToString"


class TestMethodCalls:
    """Test parsing of method call chains."""

    def setup_method(self):
        """Setup parser for each test."""
        self.parser = ExpressionParser()

    def test_parse_single_method(self):
        """Test parsing someVar.ToString()"""
        result = self.parser.analyze("[someVar.ToString()]")
        assert len(result.source_variables) == 1
        assert result.source_variables[0] == "someVar"
        assert len(result.transformations) == 1
        assert result.transformations[0].operation == "method_call"
        assert result.transformations[0].details["method"] == "ToString"

    def test_parse_method_chain(self):
        """Test parsing text.ToUpper().Trim()"""
        result = self.parser.analyze("[text.ToUpper().Trim()]")
        assert len(result.source_variables) == 1
        assert result.source_variables[0] == "text"
        assert len(result.transformations) == 2
        assert result.transformations[0].operation == "method_call"
        assert result.transformations[0].details["method"] == "ToUpper"
        assert result.transformations[1].operation == "method_call"
        assert result.transformations[1].details["method"] == "Trim"

    def test_parse_property_access(self):
        """Test parsing obj.Property"""
        result = self.parser.analyze("[obj.Name]")
        assert len(result.source_variables) == 1
        assert result.source_variables[0] == "obj"
        assert len(result.transformations) == 1
        assert result.transformations[0].operation == "property_access"
        assert result.transformations[0].details["property"] == "Name"


class TestComplexExpressions:
    """Test parsing of complex expressions with multiple variables."""

    def setup_method(self):
        """Setup parser for each test."""
        self.parser = ExpressionParser()

    def test_parse_string_concatenation(self):
        """Test parsing var1 + var2"""
        result = self.parser.analyze("[var1 + var2]")
        assert len(result.source_variables) == 2
        assert "var1" in result.source_variables
        assert "var2" in result.source_variables
        assert len(result.transformations) == 1
        assert result.transformations[0].operation == "aggregate"
        assert result.confidence == "possible"

    def test_parse_vb_concatenation(self):
        """Test parsing firstName & " " & lastName"""
        result = self.parser.analyze('[firstName & " " & lastName]')
        assert len(result.source_variables) == 2
        assert "firstName" in result.source_variables
        assert "lastName" in result.source_variables
        assert result.transformations[0].operation == "aggregate"


class TestCastExpressions:
    """Test parsing of type cast expressions."""

    def setup_method(self):
        """Setup parser for each test."""
        self.parser = ExpressionParser()

    def test_parse_cint(self):
        """Test parsing CInt(value)"""
        result = self.parser.analyze("[CInt(numericString)]")
        assert len(result.source_variables) == 1
        assert result.source_variables[0] == "numericString"
        # Should have cast transformation (possibly with inner transform for simple var)
        cast_trans = [t for t in result.transformations if t.operation == "cast"]
        assert len(cast_trans) == 1
        assert cast_trans[0].details["cast_function"] == "CInt"

    def test_parse_cstr(self):
        """Test parsing CStr(value)"""
        result = self.parser.analyze("[CStr(numericValue)]")
        assert len(result.source_variables) == 1
        assert result.source_variables[0] == "numericValue"
        # Should have cast transformation
        cast_trans = [t for t in result.transformations if t.operation == "cast"]
        assert len(cast_trans) == 1
        assert cast_trans[0].details["cast_function"] == "CStr"


class TestKeywordFiltering:
    """Test that VB keywords are excluded from variable detection."""

    def setup_method(self):
        """Setup parser for each test."""
        self.parser = ExpressionParser()

    def test_exclude_new_keyword(self):
        """Test that 'New' is not treated as variable"""
        result = self.parser.analyze("[New String()]")
        assert "New" not in result.source_variables
        assert "String" not in result.source_variables

    def test_exclude_method_names(self):
        """Test that common method names are excluded"""
        result = self.parser.analyze("[someVar.ToString()]")
        assert "ToString" not in result.source_variables
        assert len(result.source_variables) == 1
        assert result.source_variables[0] == "someVar"
