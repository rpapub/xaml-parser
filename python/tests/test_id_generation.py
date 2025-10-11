"""Tests for stable ID generation.

Tests:
- Workflow ID generation
- Activity ID generation
- Edge ID generation
- Determinism (same content → same ID)
- Hash stability (minor XML changes don't affect hash with C14N)
- Full hash computation
- Fallback normalization
"""

import pytest

from xaml_parser.id_generation import IdGenerator, generate_stable_id


class TestIdGenerator:
    """Test IdGenerator class."""

    def test_generate_workflow_id(self):
        """Test workflow ID generation."""
        gen = IdGenerator()
        xml_content = (
            '<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"></Activity>'
        )

        wf_id = gen.generate_workflow_id(xml_content)

        assert wf_id.startswith("wf:sha256:")
        # Should be truncated to 16 hex chars
        hash_part = wf_id.replace("wf:sha256:", "")
        assert len(hash_part) == 16
        assert all(c in "0123456789abcdef" for c in hash_part)

    def test_generate_activity_id(self):
        """Test activity ID generation."""
        gen = IdGenerator()
        xml_span = '<Sequence DisplayName="Test"></Sequence>'

        act_id = gen.generate_activity_id(xml_span)

        assert act_id.startswith("act:sha256:")
        hash_part = act_id.replace("act:sha256:", "")
        assert len(hash_part) == 16
        assert all(c in "0123456789abcdef" for c in hash_part)

    def test_generate_edge_id(self):
        """Test edge ID generation."""
        gen = IdGenerator()

        edge_id = gen.generate_edge_id("act:sha256:abc123def456", "act:sha256:789abcdef012", "Then")

        assert edge_id.startswith("edge:sha256:")
        hash_part = edge_id.replace("edge:sha256:", "")
        assert len(hash_part) == 16

    def test_determinism_same_content(self):
        """Test that same content always produces same ID."""
        gen = IdGenerator()
        xml_content = "<Sequence><Assign /></Sequence>"

        # Generate ID multiple times
        ids = [gen.generate_activity_id(xml_content) for _ in range(10)]

        # All IDs should be identical
        assert len(set(ids)) == 1

    def test_determinism_whitespace_normalized(self):
        """Test that whitespace differences are normalized."""
        gen = IdGenerator()

        # Different whitespace formatting
        xml1 = "<Sequence><Assign /></Sequence>"
        xml2 = "<Sequence>  <Assign />  </Sequence>"
        xml3 = "<Sequence>\n  <Assign />\n</Sequence>"

        id1 = gen.generate_activity_id(xml1)
        id2 = gen.generate_activity_id(xml2)
        id3 = gen.generate_activity_id(xml3)

        # All should produce the same ID after normalization
        assert id1 == id2 == id3

    def test_attribute_order_normalized(self):
        """Test that attribute order is normalized by C14N.

        W3C C14N normalizes attribute order to ensure deterministic output.
        Different attribute orders should produce the SAME ID.
        """
        gen = IdGenerator()

        # Different attribute orders
        xml1 = '<Assign DisplayName="Test" To="[var1]" Value="[expr]" />'
        xml2 = '<Assign Value="[expr]" To="[var1]" DisplayName="Test" />'
        xml3 = '<Assign To="[var1]" Value="[expr]" DisplayName="Test" />'

        id1 = gen.generate_activity_id(xml1)
        id2 = gen.generate_activity_id(xml2)
        id3 = gen.generate_activity_id(xml3)

        # C14N normalizes attribute order - all produce same ID
        assert id1 == id2 == id3

    def test_content_changes_affect_id(self):
        """Test that content changes produce different IDs."""
        gen = IdGenerator()

        xml1 = '<Sequence DisplayName="Test1"></Sequence>'
        xml2 = '<Sequence DisplayName="Test2"></Sequence>'

        id1 = gen.generate_activity_id(xml1)
        id2 = gen.generate_activity_id(xml2)

        # Different content should produce different IDs
        assert id1 != id2

    def test_compute_full_hash(self):
        """Test full hash computation."""
        gen = IdGenerator()
        xml_content = "<Activity></Activity>"

        full_hash = gen.compute_full_hash(xml_content)

        assert full_hash.startswith("sha256:")
        # Full hash is 64 hex chars
        hash_part = full_hash.replace("sha256:", "")
        assert len(hash_part) == 64
        assert all(c in "0123456789abcdef" for c in hash_part)

    def test_full_hash_matches_truncated(self):
        """Test that full hash prefix matches truncated ID hash."""
        gen = IdGenerator()
        xml_content = "<Activity></Activity>"

        wf_id = gen.generate_workflow_id(xml_content)
        full_hash = gen.compute_full_hash(xml_content)

        # Extract hash parts
        wf_hash = wf_id.replace("wf:sha256:", "")
        full_hash_part = full_hash.replace("sha256:", "")

        # Truncated hash should be prefix of full hash
        assert full_hash_part.startswith(wf_hash)

    def test_edge_id_determinism(self):
        """Test that edge IDs are deterministic."""
        gen = IdGenerator()

        edge_id1 = gen.generate_edge_id("act:sha256:abc123", "act:sha256:def456", "Then")
        edge_id2 = gen.generate_edge_id("act:sha256:abc123", "act:sha256:def456", "Then")

        assert edge_id1 == edge_id2

    def test_edge_id_different_kind(self):
        """Test that different edge kinds produce different IDs."""
        gen = IdGenerator()

        edge_id_then = gen.generate_edge_id("act:sha256:abc123", "act:sha256:def456", "Then")
        edge_id_else = gen.generate_edge_id("act:sha256:abc123", "act:sha256:def456", "Else")

        assert edge_id_then != edge_id_else

    def test_normalization_strips_bom(self):
        """Test that BOM is stripped during normalization."""
        gen = IdGenerator()

        xml_with_bom = "\ufeff<Activity></Activity>"
        xml_without_bom = "<Activity></Activity>"

        id1 = gen.generate_activity_id(xml_with_bom)
        id2 = gen.generate_activity_id(xml_without_bom)

        # BOM should be stripped, IDs should match
        assert id1 == id2

    def test_fallback_normalize_on_parse_error(self):
        """Test fallback normalization when XML parsing fails."""
        gen = IdGenerator()

        # Invalid XML (missing closing tag)
        invalid_xml = "<Activity>"

        # Should not raise exception, should use fallback
        id1 = gen.generate_activity_id(invalid_xml)
        id2 = gen.generate_activity_id(invalid_xml)

        # Should still be deterministic
        assert id1 == id2
        assert id1.startswith("act:sha256:")

    def test_normalization_line_endings(self):
        """Test that different line endings are normalized."""
        gen = IdGenerator()

        # Different line endings
        xml_lf = "<Activity>\n<Sequence /></Activity>"
        xml_crlf = "<Activity>\r\n<Sequence /></Activity>"
        xml_cr = "<Activity>\r<Sequence /></Activity>"

        id_lf = gen.generate_activity_id(xml_lf)
        id_crlf = gen.generate_activity_id(xml_crlf)
        id_cr = gen.generate_activity_id(xml_cr)

        # All should normalize to same ID
        assert id_lf == id_crlf == id_cr


class TestGenerateStableId:
    """Test convenience function for stable ID generation."""

    def test_generate_stable_id_string(self):
        """Test generating ID from string content."""
        id1 = generate_stable_id("arg", "in_FilePath")
        id2 = generate_stable_id("arg", "in_FilePath")

        assert id1 == id2
        assert id1.startswith("arg:sha256:")

    def test_generate_stable_id_different_prefixes(self):
        """Test different prefixes for different entity types."""
        content = "same_content"

        arg_id = generate_stable_id("arg", content)
        var_id = generate_stable_id("var", content)

        assert arg_id.startswith("arg:sha256:")
        assert var_id.startswith("var:sha256:")
        # Hash parts should be the same
        assert arg_id.split(":")[2] == var_id.split(":")[2]

    def test_generate_stable_id_object(self):
        """Test generating ID from object (converts to string)."""
        obj = {"key": "value"}

        id1 = generate_stable_id("test", obj)
        id2 = generate_stable_id("test", obj)

        assert id1 == id2
        assert id1.startswith("test:sha256:")


class TestRealWorldXaml:
    """Test with realistic UiPath XAML examples."""

    def test_sequence_activity(self):
        """Test ID generation for Sequence activity."""
        gen = IdGenerator()

        xaml = """<Sequence xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
                             xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
                             DisplayName="Main Sequence">
            <Assign>
                <Assign.To>
                    <OutArgument x:TypeArguments="x:String">[varOutput]</OutArgument>
                </Assign.To>
                <Assign.Value>
                    <InArgument x:TypeArguments="x:String">["Hello World"]</InArgument>
                </Assign.Value>
            </Assign>
        </Sequence>"""

        id1 = gen.generate_activity_id(xaml)
        id2 = gen.generate_activity_id(xaml)

        assert id1 == id2
        assert id1.startswith("act:sha256:")

    def test_workflow_with_namespaces(self):
        """Test workflow ID with complex namespaces."""
        gen = IdGenerator()

        xaml = """<Activity mc:Ignorable="sap sap2010"
                             x:Class="Main"
                             xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
                             xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"
                             xmlns:sap="http://schemas.microsoft.com/netfx/2009/xaml/activities/presentation"
                             xmlns:sap2010="http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation"
                             xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
            <Sequence DisplayName="Main Sequence"></Sequence>
        </Activity>"""

        id1 = gen.generate_workflow_id(xaml)
        id2 = gen.generate_workflow_id(xaml)

        assert id1 == id2
        assert id1.startswith("wf:sha256:")


class TestHashCollisionResistance:
    """Test hash collision resistance."""

    def test_similar_content_different_ids(self):
        """Test that similar but different content produces different IDs."""
        gen = IdGenerator()

        # Very similar content, single character difference
        xml1 = '<Sequence DisplayName="Test1"></Sequence>'
        xml2 = '<Sequence DisplayName="Test2"></Sequence>'
        xml3 = '<Sequence DisplayName="Test3"></Sequence>'

        id1 = gen.generate_activity_id(xml1)
        id2 = gen.generate_activity_id(xml2)
        id3 = gen.generate_activity_id(xml3)

        # All should be different
        assert len({id1, id2, id3}) == 3

    def test_truncation_still_unique(self):
        """Test that 16-char truncation maintains uniqueness for typical cases."""
        gen = IdGenerator()

        # Generate IDs for many slightly different activities
        ids = set()
        for i in range(1000):
            xml = f'<Assign DisplayName="Activity{i}" />'
            id = gen.generate_activity_id(xml)
            ids.add(id)

        # All 1000 IDs should be unique
        assert len(ids) == 1000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
