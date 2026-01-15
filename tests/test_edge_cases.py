"""Tests for edge cases: missing segments, extra segments, malformed input."""
import pytest
from hl7_siu_parser import (
    HL7Parser,
    InvalidMessageTypeError,
    MissingSegmentError,
    EmptyMessageError,
    MalformedSegmentError,
)


class TestMissingSegments:
    """Tests for messages with missing segments."""

    def test_missing_sch_handled_gracefully(self, missing_sch_message):
        """Missing SCH segment doesn't crash, returns empty appointment fields."""
        parser = HL7Parser()
        appt = parser.parse_message(missing_sch_message)
        
        # Appointment can still be created, but SCH-derived fields are None
        assert appt.appointment_id is None
        assert appt.appointment_datetime is None
        assert appt.reason is None
        # PID fields should still be populated
        assert appt.patient is not None
        assert appt.patient.id == "P12345"
        assert appt.patient.first_name == "John"

    def test_missing_pid_handled_gracefully(self, missing_pid_message):
        """Missing PID segment doesn't crash, patient is None."""
        parser = HL7Parser()
        appt = parser.parse_message(missing_pid_message)
        
        # SCH fields should be populated
        assert appt.appointment_id == "FILLER456"
        assert appt.reason == "Routine Checkup"
        # Patient should be None
        assert appt.patient is None

    def test_missing_pv1_handled_gracefully(self, missing_pv1_message):
        """Missing PV1 segment doesn't crash, provider is None."""
        parser = HL7Parser()
        appt = parser.parse_message(missing_pv1_message)
        
        # SCH and PID fields should be populated
        assert appt.appointment_id == "FILLER456"
        assert appt.patient is not None
        assert appt.patient.id == "P12345"
        # Provider should be None
        assert appt.provider is None

    def test_minimal_message(self, minimal_message):
        """Minimal message with only MSH and SCH parses correctly."""
        parser = HL7Parser()
        appt = parser.parse_message(minimal_message)
        
        assert appt.appointment_id == "FILLER001"
        assert appt.patient is None
        assert appt.provider is None

    def test_strict_mode_missing_sch(self, missing_sch_message):
        """Strict mode raises error for missing SCH."""
        parser = HL7Parser(strict_mode=True)
        with pytest.raises(MissingSegmentError) as exc:
            parser.parse_message(missing_sch_message)
        assert "SCH" in str(exc.value)

    def test_strict_mode_missing_pid(self, missing_pid_message):
        """Strict mode raises error for missing PID."""
        parser = HL7Parser(strict_mode=True)
        with pytest.raises(MissingSegmentError) as exc:
            parser.parse_message(missing_pid_message)
        assert "PID" in str(exc.value)


class TestExtraSegments:
    """Tests for messages with extra/irrelevant segments."""

    def test_extra_segments_ignored(self, extra_segments_message):
        """Extra segments (NTE, OBX, AL1, etc.) are ignored, core data parsed correctly."""
        parser = HL7Parser()
        appt = parser.parse_message(extra_segments_message)
        
        # Core data should be extracted correctly
        assert appt.appointment_id == "FILLER456"
        assert appt.reason == "Routine Checkup"
        assert appt.patient.id == "P12345"
        assert appt.patient.first_name == "John"
        assert appt.provider.id == "D67890"

    def test_segment_order_irrelevant(self):
        """Segments can appear in non-standard order."""
        message = """MSH|^~\\&|APP|FAC|||20250502130000||SIU^S12|MSG001|P|2.5
PV1||O|CLINIC||||D001^Smith^Jane
PID|||P12345||Doe^John||19850210|M
SCH|12345|FILLER456||||Checkup^Routine|||||^^^20250502130000|||||||||||Room 101"""
        
        parser = HL7Parser()
        appt = parser.parse_message(message)
        
        assert appt.appointment_id == "FILLER456"
        assert appt.patient.id == "P12345"
        assert appt.provider.id == "D001"


class TestTruncatedFields:
    """Tests for messages with truncated/short segments."""

    def test_truncated_segments_handled(self, truncated_segments_message):
        """Truncated segments don't crash parser."""
        parser = HL7Parser()
        appt = parser.parse_message(truncated_segments_message)
        
        # Should get what's available
        assert appt.appointment_id == "12345"
        assert appt.patient.id == "P001"
        # Missing fields should be None
        assert appt.reason is None
        assert appt.location is None

    def test_very_short_pid(self):
        """PID with only ID field works."""
        message = """MSH|^~\\&|APP|FAC|||20250502130000||SIU^S12|MSG001|P|2.5
SCH|12345|FILL001
PID|||P001"""
        
        parser = HL7Parser()
        appt = parser.parse_message(message)
        
        assert appt.patient.id == "P001"
        assert appt.patient.first_name is None
        assert appt.patient.last_name is None


class TestMalformedInput:
    """Tests for invalid/malformed input."""

    def test_empty_message_raises(self):
        """Empty message raises EmptyMessageError."""
        parser = HL7Parser()
        with pytest.raises(EmptyMessageError):
            parser.parse_message("")

    def test_whitespace_only_raises(self, only_whitespace_message):
        """Whitespace-only message raises EmptyMessageError."""
        parser = HL7Parser()
        with pytest.raises(EmptyMessageError):
            parser.parse_message(only_whitespace_message)

    def test_missing_msh_raises(self):
        """Message without MSH raises MissingSegmentError."""
        parser = HL7Parser()
        with pytest.raises(MissingSegmentError) as exc:
            parser.parse_message("PID|||12345")
        assert "MSH" in str(exc.value)

    def test_invalid_message_type_raises(self, malformed_message):
        """Non-SIU message type raises InvalidMessageTypeError."""
        parser = HL7Parser()
        with pytest.raises(InvalidMessageTypeError) as exc:
            parser.parse_message(malformed_message)
        assert "ADT^A01" in str(exc.value)

    def test_various_non_siu_types(self, non_siu_message_types):
        """Various non-SIU message types all raise InvalidMessageTypeError."""
        parser = HL7Parser()
        
        for msg_type, description in non_siu_message_types:
            message = f"MSH|^~\\&|APP|FAC|||20250502130000||{msg_type}|MSG001|P|2.5\nPID|||P001"
            
            with pytest.raises(InvalidMessageTypeError) as exc:
                parser.parse_message(message)
            assert msg_type.split("^")[0] in str(exc.value) or msg_type in str(exc.value)


class TestLineEndings:
    """Tests for different line ending styles."""

    def test_crlf_line_endings(self, crlf_message):
        """Windows-style CRLF line endings handled."""
        parser = HL7Parser()
        appt = parser.parse_message(crlf_message)
        
        assert appt.appointment_id == "FILLER456"
        assert appt.patient.id == "P12345"

    def test_cr_only_line_endings(self, cr_only_message):
        """Old Mac-style CR-only line endings handled."""
        parser = HL7Parser()
        appt = parser.parse_message(cr_only_message)
        
        assert appt.appointment_id == "FILLER456"
        assert appt.patient.id == "P12345"

    def test_mixed_line_endings(self):
        """Mixed line endings in same message handled."""
        message = "MSH|^~\\&|APP|FAC|||20250502130000||SIU^S12|MSG001|P|2.5\r\n" \
                  "SCH|12345|FILLER456||||Checkup^Routine|||||^^^20250502130000\n" \
                  "PID|||P12345||Doe^John\r" \
                  "PV1||O"
        
        parser = HL7Parser()
        appt = parser.parse_message(message)
        
        assert appt.appointment_id == "FILLER456"
        assert appt.patient.id == "P12345"


class TestWhitespace:
    """Tests for whitespace handling."""

    def test_leading_trailing_whitespace(self, whitespace_message):
        """Leading/trailing whitespace in lines handled."""
        parser = HL7Parser()
        appt = parser.parse_message(whitespace_message)
        
        assert appt.appointment_id == "FILLER456"
        assert appt.patient.id == "P12345"

    def test_blank_lines_ignored(self):
        """Blank lines between segments ignored."""
        message = """MSH|^~\\&|APP|FAC|||20250502130000||SIU^S12|MSG001|P|2.5

SCH|12345|FILLER456||||Checkup^Routine|||||^^^20250502130000

PID|||P12345||Doe^John

PV1||O"""
        
        parser = HL7Parser()
        appt = parser.parse_message(message)
        
        assert appt.appointment_id == "FILLER456"
        assert appt.patient.id == "P12345"


class TestEmptyFields:
    """Tests for empty field handling."""

    def test_consecutive_separators(self, empty_fields_message):
        """Consecutive || (empty fields) don't crash parser."""
        parser = HL7Parser()
        appt = parser.parse_message(empty_fields_message)
        
        # Empty fields should result in None values
        assert appt.appointment_id is None
        assert appt.reason is None

    def test_all_empty_fields(self, all_empty_fields_message):
        """Message with all empty optional fields handles gracefully."""
        parser = HL7Parser()
        appt = parser.parse_message(all_empty_fields_message)
        
        assert appt.appointment_id is None
        assert appt.appointment_datetime is None
        assert appt.reason is None
        assert appt.location is None


class TestCustomSeparators:
    """Tests for non-standard separator handling."""

    def test_custom_component_separator(self, custom_separator_message):
        """Custom component separator (#) handled correctly."""
        parser = HL7Parser()
        appt = parser.parse_message(custom_separator_message)
        
        # Parser should use the separator from MSH-2
        assert appt.appointment_id == "FILLER456"
        assert appt.reason == "Routine"  # Component after #
        assert appt.patient.last_name == "Doe"
        assert appt.patient.first_name == "John"

    def test_repetition_separator(self, tilde_in_field_message):
        """Repetition separator (~) handled - first value used."""
        parser = HL7Parser()
        appt = parser.parse_message(tilde_in_field_message)
        
        # First ID from repetitions should be used
        assert appt.patient.id == "P12345"
