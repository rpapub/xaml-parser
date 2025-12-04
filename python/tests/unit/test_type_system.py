"""Tests for type system module."""

from cpmf_xaml_parser.type_system import TypeInfo


class TestTypeInfoParsing:
    """Test TypeInfo.parse() with various .NET type signatures."""

    def test_parse_simple_type(self):
        """Test parsing simple type: System.String"""
        t = TypeInfo.parse("System.String")
        assert t.name == "String"
        assert t.namespace == "System"
        assert t.full_name == "System.String"
        assert t.generic_args is None
        assert not t.is_array

    def test_parse_short_type(self):
        """Test parsing type without namespace: String"""
        t = TypeInfo.parse("String")
        assert t.name == "String"
        assert t.namespace == ""
        assert not t.is_array

    def test_parse_generic_type_simple(self):
        """Test parsing simple generic: List`1[String]"""
        t = TypeInfo.parse("List`1[String]")
        assert t.name == "List"
        assert t.generic_args is not None
        assert len(t.generic_args) == 1
        assert t.generic_args[0].name == "String"

    def test_parse_dictionary(self):
        """Test parsing Dictionary`2[String,Object]"""
        t = TypeInfo.parse("Dictionary`2[System.String,System.Object]")
        assert t.name == "Dictionary"
        assert t.generic_args is not None
        assert len(t.generic_args) == 2
        assert t.generic_args[0].name == "String"
        assert t.generic_args[1].name == "Object"

    def test_parse_array_single_dimension(self):
        """Test parsing array: String[]"""
        t = TypeInfo.parse("String[]")
        assert t.name == "String"
        assert t.is_array
        assert t.array_rank == 1

    def test_parse_array_multi_dimension(self):
        """Test parsing multi-dimensional array: Int32[,]"""
        t = TypeInfo.parse("Int32[,]")
        assert t.name == "Int32"
        assert t.is_array
        assert t.array_rank == 2

    def test_parse_nested_generic(self):
        """Test parsing nested generic: List`1[Dictionary`2[String,Object]]"""
        t = TypeInfo.parse("List`1[Dictionary`2[String,Object]]")
        assert t.name == "List"
        assert t.generic_args is not None
        assert len(t.generic_args) == 1

        inner = t.generic_args[0]
        assert inner.name == "Dictionary"
        assert inner.generic_args is not None
        assert len(inner.generic_args) == 2


class TestTypeInfoElementType:
    """Test TypeInfo.get_element_type() for collections."""

    def test_get_element_type_array(self):
        """Test element type for array: String[] → String"""
        t = TypeInfo.parse("String[]")
        elem = t.get_element_type()
        assert elem is not None
        assert elem.name == "String"
        assert not elem.is_array

    def test_get_element_type_dictionary(self):
        """Test element type for dictionary: Dict<K,V> → V"""
        t = TypeInfo.parse("Dictionary`2[String,Object]")
        elem = t.get_element_type()
        assert elem is not None
        assert elem.name == "Object"

    def test_get_element_type_list(self):
        """Test element type for list: List<T> → T"""
        t = TypeInfo.parse("List`1[Int32]")
        elem = t.get_element_type()
        assert elem is not None
        assert elem.name == "Int32"

    def test_get_element_type_non_collection(self):
        """Test element type for non-collection returns None"""
        t = TypeInfo.parse("System.String")
        elem = t.get_element_type()
        assert elem is None


class TestTypeInfoMethodInference:
    """Test TypeInfo.infer_method_return_type()."""

    def test_infer_tostring(self):
        """Test ToString() returns String"""
        t = TypeInfo.parse("System.Object")
        ret = t.infer_method_return_type("ToString")
        assert ret is not None
        assert ret.name == "String"

    def test_infer_string_methods(self):
        """Test String method return types"""
        t = TypeInfo.parse("System.String")

        ret = t.infer_method_return_type("ToUpper")
        assert ret is not None
        assert ret.name == "String"

        ret = t.infer_method_return_type("Contains")
        assert ret is not None
        assert ret.name == "Boolean"

        ret = t.infer_method_return_type("IndexOf")
        assert ret is not None
        assert ret.name == "Int32"

    def test_infer_collection_count(self):
        """Test Count() on collection returns Int32"""
        t = TypeInfo.parse("List`1[String]")
        ret = t.infer_method_return_type("Count")
        assert ret is not None
        assert ret.name == "Int32"

    def test_infer_collection_first(self):
        """Test First() on collection returns element type"""
        t = TypeInfo.parse("List`1[String]")
        ret = t.infer_method_return_type("First")
        assert ret is not None
        assert ret.name == "String"

    def test_infer_unknown_method(self):
        """Test unknown method returns None"""
        t = TypeInfo.parse("System.String")
        ret = t.infer_method_return_type("UnknownMethod")
        assert ret is None


class TestTypeInfoPropertyInference:
    """Test TypeInfo.infer_property_type()."""

    def test_infer_string_length(self):
        """Test String.Length returns Int32"""
        t = TypeInfo.parse("System.String")
        ret = t.infer_property_type("Length")
        assert ret is not None
        assert ret.name == "Int32"

    def test_infer_collection_count_property(self):
        """Test collection.Count property returns Int32"""
        t = TypeInfo.parse("List`1[Object]")
        ret = t.infer_property_type("Count")
        assert ret is not None
        assert ret.name == "Int32"


class TestTypeInfoStringRepresentation:
    """Test TypeInfo string representations."""

    def test_str_simple_type(self):
        """Test string representation of simple type"""
        t = TypeInfo.parse("System.String")
        assert str(t) == "String"

    def test_str_generic_type(self):
        """Test string representation of generic type"""
        t = TypeInfo.parse("List`1[String]")
        assert str(t) == "List<String>"

    def test_str_dictionary(self):
        """Test string representation of dictionary"""
        t = TypeInfo.parse("Dictionary`2[String,Object]")
        assert str(t) == "Dictionary<String, Object>"

    def test_str_array(self):
        """Test string representation of array"""
        t = TypeInfo.parse("String[]")
        assert str(t) == "String[]"

    def test_repr(self):
        """Test debug representation"""
        t = TypeInfo.parse("System.String")
        assert repr(t) == "TypeInfo(System.String)"
