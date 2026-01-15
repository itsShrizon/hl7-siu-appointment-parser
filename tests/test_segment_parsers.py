"""Unit tests for individual segment parsers."""
import pytest
from hl7_siu_parser.segments import parse_msh, parse_sch, parse_pid, parse_pv1
from hl7_siu_parser.exceptions import MalformedSegmentError


class TestMSHParser:
    """Tests for MSH segment parsing."""

    def test_valid_msh(self):
        """Parse valid MSH segment."""
        segment = "MSH|^~\\&|APP|FAC|RECV|RFAC|20250502130000||SIU^S12|MSG001|P|2.5"
        metadata = parse_msh(segment)
        
        assert metadata.field_separator == "|"
        assert metadata.component_separator == "^"
        assert metadata.repetition_separator == "~"
        assert metadata.escape_character == "\\"
        assert metadata.subcomponent_separator == "&"
        assert metadata.sending_application == "APP"
        assert metadata.sending_facility == "FAC"
        assert metadata.receiving_application == "RECV"
        assert metadata.receiving_facility == "RFAC"
        assert metadata.message_type == "SIU^S12"
        assert metadata.message_control_id == "MSG001"
        assert metadata.version == "2.5"

    def test_is_siu_s12(self):
        """Check SIU^S12 detection."""
        segment = "MSH|^~\\&|APP|FAC|||20250502130000||SIU^S12|MSG001|P|2.5"
        metadata = parse_msh(segment)
        assert metadata.is_siu_s12() is True

    def test_is_not_siu_s12(self):
        """ADT message not detected as SIU."""
        segment = "MSH|^~\\&|APP|FAC|||20250502130000||ADT^A01|MSG001|P|2.5"
        metadata = parse_msh(segment)
        assert metadata.is_siu_s12() is False

    def test_empty_segment_raises(self):
        """Empty segment raises MalformedSegmentError."""
        with pytest.raises(MalformedSegmentError) as exc:
            parse_msh("")
        assert "empty" in str(exc.value).lower()

    def test_not_msh_raises(self):
        """Non-MSH segment raises MalformedSegmentError."""
        with pytest.raises(MalformedSegmentError) as exc:
            parse_msh("PID|||12345")
        assert "MSH" in str(exc.value)

    def test_too_short_raises(self):
        """Too short segment raises MalformedSegmentError."""
        with pytest.raises(MalformedSegmentError) as exc:
            parse_msh("MSH")
        assert "short" in str(exc.value).lower()

    def test_minimal_msh(self):
        """Parse minimal valid MSH."""
        segment = "MSH|^~\\&"
        metadata = parse_msh(segment)
        assert metadata.field_separator == "|"
        assert metadata.component_separator == "^"
        # Empty string for missing fields (field_utils returns "" not None)
        assert metadata.message_type == ""

    def test_custom_field_separator(self):
        """Parse MSH with custom field separator."""
        segment = "MSH#^~\\&#APP#FAC###20250502130000##SIU^S12#MSG001#P#2.5"
        metadata = parse_msh(segment)
        assert metadata.field_separator == "#"
        assert metadata.sending_application == "APP"

    def test_siu_s12_case_insensitive(self):
        """SIU detection is case insensitive."""
        segment = "MSH|^~\\&|APP|FAC|||20250502130000||siu^s12|MSG001|P|2.5"
        metadata = parse_msh(segment)
        assert metadata.is_siu_s12() is True


class TestSCHParser:
    """Tests for SCH segment parsing."""

    def test_valid_sch(self):
        """Parse valid SCH segment."""
        # SCH location falls back to field 20 (0-indexed), needs 21 fields
        # Count: SCH(0)|1|2|3|4|5|6|7|8|9|10|11|12|13|14|15|16|17|18|19|20
        segment = "SCH|PLACER001|FILLER456||||Checkup^Routine Checkup|||||^^^20250502130000|||||||||Room 101"
        result = parse_sch(segment, "|", "^")
        
        assert result["appointment_id"] == "FILLER456"  # Filler preferred
        assert result["reason"] == "Routine Checkup"
        assert result["appointment_datetime"] == "20250502130000"
        # Location is in field 20 (0-indexed)
        assert result["location"] == "Room 101"

    def test_filler_id_preferred(self):
        """Filler ID preferred over placer ID."""
        segment = "SCH|PLACER001|FILLER456"
        result = parse_sch(segment, "|", "^")
        assert result["appointment_id"] == "FILLER456"

    def test_placer_id_fallback(self):
        """Placer ID used when filler missing."""
        segment = "SCH|PLACER001||||||||||^^^20250502130000"
        result = parse_sch(segment, "|", "^")
        assert result["appointment_id"] == "PLACER001"

    def test_no_id(self):
        """No ID when both missing."""
        segment = "SCH|||||||||||^^^20250502130000"
        result = parse_sch(segment, "|", "^")
        assert result["appointment_id"] is None

    def test_reason_description_preferred(self):
        """Reason description preferred over code."""
        segment = "SCH||||||CODE^Description"
        result = parse_sch(segment, "|", "^")
        assert result["reason"] == "Description"

    def test_reason_code_fallback(self):
        """Reason code used when description missing."""
        segment = "SCH||||||JustCode"
        result = parse_sch(segment, "|", "^")
        assert result["reason"] == "JustCode"

    def test_timing_simple(self):
        """Simple datetime in timing field."""
        segment = "SCH||||||||||20250502130000"
        result = parse_sch(segment, "|", "^")
        # Field 11 is timing - adjust based on actual index
        # After split, SCH-11 is at index 11

    def test_timing_with_components(self):
        """Datetime extracted from component-based timing."""
        segment = "SCH|||||||||||^^^20250502130000^20250502140000"
        result = parse_sch(segment, "|", "^")
        assert result["appointment_datetime"] == "20250502130000"

    def test_truncated_sch(self):
        """Truncated SCH handled gracefully."""
        segment = "SCH|12345"
        result = parse_sch(segment, "|", "^")
        assert result["appointment_id"] == "12345"
        assert result["reason"] is None
        assert result["location"] is None

    def test_all_empty_fields(self):
        """All empty fields returns None values."""
        segment = "SCH||||||||||||||||||||||"
        result = parse_sch(segment, "|", "^")
        assert result["appointment_id"] is None
        assert result["reason"] is None
        assert result["appointment_datetime"] is None


class TestPIDParser:
    """Tests for PID segment parsing."""

    def test_valid_pid(self):
        """Parse valid PID segment."""
        segment = "PID|||P12345||Doe^John^M||19850210|M"
        patient = parse_pid(segment, "|", "^")
        
        assert patient.id == "P12345"
        assert patient.first_name == "John"
        assert patient.last_name == "Doe"
        assert patient.dob == "1985-02-10"  # Normalized
        assert patient.gender == "M"

    def test_multiple_ids(self):
        """First ID used when multiple."""
        segment = "PID|||ID001~ID002~ID003||Name^First"
        patient = parse_pid(segment, "|", "^")
        assert patient.id == "ID001"

    def test_complex_name(self):
        """Parse complex name with all components."""
        segment = "PID|||||Smith^Jane^Marie^III^Dr||19750315|F"
        patient = parse_pid(segment, "|", "^")
        assert patient.last_name == "Smith"
        assert patient.first_name == "Jane"

    def test_dob_normalization(self):
        """DOB normalized to ISO format."""
        segment = "PID|||||||19850210"
        patient = parse_pid(segment, "|", "^")
        assert patient.dob == "1985-02-10"

    def test_truncated_pid(self):
        """Truncated PID handled gracefully."""
        segment = "PID|||P001"
        patient = parse_pid(segment, "|", "^")
        assert patient.id == "P001"
        assert patient.first_name is None
        assert patient.last_name is None
        assert patient.dob is None
        assert patient.gender is None

    def test_all_empty_fields(self):
        """All empty fields returns None values."""
        segment = "PID|||||||||"
        patient = parse_pid(segment, "|", "^")
        assert patient.id is None
        assert patient.first_name is None
        assert patient.last_name is None

    def test_custom_separator(self):
        """Works with custom component separator."""
        segment = "PID|||P001||Smith#John||19850210|M"
        patient = parse_pid(segment, "|", "#")
        assert patient.last_name == "Smith"
        assert patient.first_name == "John"


class TestPV1Parser:
    """Tests for PV1 segment parsing."""

    def test_valid_pv1(self):
        """Parse valid PV1 segment."""
        segment = "PV1||O|CLINIC||||D001^Smith^Jane"
        provider = parse_pv1(segment, "|", "^")
        
        assert provider.id == "D001"
        assert provider.name == "Jane Smith"

    def test_attending_preferred(self):
        """Attending doctor (field 7) preferred."""
        segment = "PV1||O|CLINIC||||D001^Attending^Doc|D002^Referring^Doc|D003^Consulting^Doc"
        provider = parse_pv1(segment, "|", "^")
        assert provider.id == "D001"
        assert "Attending" in provider.name

    def test_referring_fallback(self):
        """Referring doctor used when attending missing."""
        segment = "PV1||O|CLINIC|||||D002^Referring^Doc"
        provider = parse_pv1(segment, "|", "^")
        assert provider.id == "D002"
        assert "Referring" in provider.name

    def test_provider_with_prefix(self):
        """Provider name includes prefix."""
        segment = "PV1||O|CLINIC||||D001^Smith^Jane^^^Dr"
        provider = parse_pv1(segment, "|", "^")
        assert provider.id == "D001"
        assert "Dr" in provider.name
        assert "Jane" in provider.name
        assert "Smith" in provider.name

    def test_truncated_pv1(self):
        """Truncated PV1 handled gracefully."""
        segment = "PV1||O"
        provider = parse_pv1(segment, "|", "^")
        assert provider.id is None
        assert provider.name is None

    def test_no_provider(self):
        """No provider fields returns empty provider."""
        segment = "PV1||O|CLINIC||||"
        provider = parse_pv1(segment, "|", "^")
        assert provider.id is None

    def test_multiple_providers(self):
        """First provider from repetitions used."""
        segment = "PV1||O|CLINIC||||D001^First^Doc~D002^Second^Doc"
        provider = parse_pv1(segment, "|", "^")
        assert provider.id == "D001"
