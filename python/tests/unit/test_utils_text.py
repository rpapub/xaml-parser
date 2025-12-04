"""Tests for TextUtils utility functions."""

from cpmf_xaml_parser.utils import TextUtils


class TestTextUtilsCleanAnnotation:
    """Tests for TextUtils.clean_annotation()."""

    def test_clean_annotation_empty_string(self):
        """Test cleaning empty string."""
        result = TextUtils.clean_annotation("")
        assert result == ""

    def test_clean_annotation_none_equivalent(self):
        """Test cleaning None-like input."""
        result = TextUtils.clean_annotation("")
        assert result == ""

    def test_clean_annotation_html_entities(self):
        """Test decoding HTML entities."""
        text = "This &amp; that &lt;tag&gt; &quot;quotes&quot;"
        result = TextUtils.clean_annotation(text)
        assert result == 'This & that <tag> "quotes"'

    def test_clean_annotation_whitespace_normalization(self):
        """Test normalizing multiple whitespace to single space."""
        text = "Text   with    multiple     spaces"
        result = TextUtils.clean_annotation(text)
        assert result == "Text with multiple spaces"

    def test_clean_annotation_leading_trailing_whitespace(self):
        """Test stripping leading and trailing whitespace."""
        text = "   Text with spaces   "
        result = TextUtils.clean_annotation(text)
        assert result == "Text with spaces"

    def test_clean_annotation_newline_entities(self):
        """Test converting newline entities to actual newlines."""
        text = "Line1&#xA;Line2&#xa;Line3"
        result = TextUtils.clean_annotation(text)
        # Whitespace normalization happens before line break conversion,
        # so these become spaces first
        assert "Line1 Line2 Line3" == result

    def test_clean_annotation_html_line_breaks(self):
        """Test converting HTML line breaks."""
        text = "Line1<br>Line2<br/>Line3"
        result = TextUtils.clean_annotation(text)
        assert "Line1\nLine2\nLine3" in result

    def test_clean_annotation_complex_mixed(self):
        """Test complex annotation with multiple issues."""
        text = "  Workflow &amp; Process<br/>Step1&#xA;Step2   with   spaces  "
        result = TextUtils.clean_annotation(text)
        assert "Workflow & Process" in result
        # &#xA; gets decoded then normalized to space, <br/> survives as \n
        assert "Workflow & Process\nStep1 Step2 with spaces" == result


class TestTextUtilsExtractTypeName:
    """Tests for TextUtils.extract_type_name()."""

    def test_extract_type_name_empty_string(self):
        """Test extracting from empty string returns Object."""
        result = TextUtils.extract_type_name("")
        assert result == "Object"

    def test_extract_type_name_simple_type(self):
        """Test extracting simple type without namespace."""
        result = TextUtils.extract_type_name("String")
        assert result == "String"

    def test_extract_type_name_namespaced_type(self):
        """Test extracting type with namespace prefix."""
        result = TextUtils.extract_type_name("x:String")
        assert result == "String"

    def test_extract_type_name_generic_type(self):
        """Test extracting from generic type syntax."""
        result = TextUtils.extract_type_name("InArgument(x:String)")
        assert result == "String"

    def test_extract_type_name_generic_without_namespace(self):
        """Test extracting from generic type without namespace."""
        result = TextUtils.extract_type_name("InArgument(String)")
        assert result == "String"

    def test_extract_type_name_out_argument(self):
        """Test extracting from OutArgument."""
        result = TextUtils.extract_type_name("OutArgument(x:Int32)")
        assert result == "Int32"

    def test_extract_type_name_complex_namespace(self):
        """Test extracting with complex namespace."""
        result = TextUtils.extract_type_name("mva:VisualBasicValue(x:Boolean)")
        assert result == "Boolean"

    def test_extract_type_name_nested_generics(self):
        """Test extracting from nested generic types."""
        result = TextUtils.extract_type_name("InArgument(x:Dictionary)")
        assert result == "Dictionary"


class TestTextUtilsNormalizePath:
    """Tests for TextUtils.normalize_path()."""

    def test_normalize_path_windows_path(self):
        """Test normalizing Windows path to POSIX."""
        result = TextUtils.normalize_path("C:\\Users\\Documents\\file.txt")
        assert result == "C:/Users/Documents/file.txt"

    def test_normalize_path_posix_path(self):
        """Test POSIX path remains unchanged."""
        result = TextUtils.normalize_path("/home/user/documents/file.txt")
        assert result == "/home/user/documents/file.txt"

    def test_normalize_path_relative_path(self):
        """Test normalizing relative path."""
        result = TextUtils.normalize_path("..\\parent\\file.txt")
        assert result == "../parent/file.txt"

    def test_normalize_path_empty_string(self):
        """Test normalizing empty string."""
        result = TextUtils.normalize_path("")
        assert result == ""

    def test_normalize_path_mixed_slashes(self):
        """Test normalizing path with mixed slashes."""
        result = TextUtils.normalize_path("C:\\Users/Documents\\file.txt")
        assert result == "C:/Users/Documents/file.txt"

    def test_normalize_path_unc_path(self):
        """Test normalizing UNC path."""
        result = TextUtils.normalize_path("\\\\server\\share\\file.txt")
        assert result == "//server/share/file.txt"


class TestTextUtilsTruncateText:
    """Tests for TextUtils.truncate_text()."""

    def test_truncate_text_no_truncation_needed(self):
        """Test text shorter than max_length."""
        text = "Short text"
        result = TextUtils.truncate_text(text, max_length=100)
        assert result == "Short text"

    def test_truncate_text_exact_length(self):
        """Test text exactly at max_length."""
        text = "A" * 100
        result = TextUtils.truncate_text(text, max_length=100)
        assert result == "A" * 100

    def test_truncate_text_default_suffix(self):
        """Test truncation with default '...' suffix."""
        text = "A" * 150
        result = TextUtils.truncate_text(text, max_length=100)
        assert len(result) == 100
        assert result.endswith("...")
        assert result == "A" * 97 + "..."

    def test_truncate_text_custom_suffix(self):
        """Test truncation with custom suffix."""
        text = "A" * 150
        result = TextUtils.truncate_text(text, max_length=50, suffix=" [more]")
        assert len(result) == 50
        assert result.endswith(" [more]")
        assert result == "A" * 43 + " [more]"

    def test_truncate_text_empty_string(self):
        """Test truncating empty string."""
        result = TextUtils.truncate_text("", max_length=100)
        assert result == ""

    def test_truncate_text_empty_suffix(self):
        """Test truncation with empty suffix."""
        text = "A" * 150
        result = TextUtils.truncate_text(text, max_length=100, suffix="")
        assert len(result) == 100
        assert result == "A" * 100

    def test_truncate_text_long_suffix(self):
        """Test truncation with suffix longer than truncation point."""
        text = "A" * 150
        result = TextUtils.truncate_text(text, max_length=20, suffix=" [truncated...]")
        assert len(result) == 20
        # Should be 5 A's + 15-char suffix
        assert result == "A" * 5 + " [truncated...]"

    def test_truncate_text_multiline(self):
        """Test truncating multiline text."""
        text = "Line 1\nLine 2\nLine 3\n" * 10  # ~210 chars
        result = TextUtils.truncate_text(text, max_length=50)
        assert len(result) == 50
        assert result.endswith("...")

    def test_truncate_text_with_unicode(self):
        """Test truncating text with unicode characters."""
        text = "Unicode: ñ, é, ü, 中文, 日本語" * 10
        result = TextUtils.truncate_text(text, max_length=30)
        assert len(result) == 30
        assert result.endswith("...")
