"""Unit tests for HL7 Parser."""
import pytest
from hl7_siu_parser import HL7Parser, InvalidMessageTypeError, MissingSegmentError, EmptyMessageError


class TestBasicParsing:
    def test_valid_message(self, valid_message):
        parser = HL7Parser()
        appt = parser.parse_message(valid_message)
        assert appt.appointment_id == "FILLER456"
        assert appt.patient.first_name == "John"
        assert appt.patient.dob == "1985-02-10"  # Normalized
        assert appt.appointment_datetime == "2025-05-02T13:00:00Z"

    def test_empty_message_raises(self):
        parser = HL7Parser()
        with pytest.raises(EmptyMessageError):
            parser.parse_message("")

    def test_missing_msh_raises(self):
        parser = HL7Parser()
        with pytest.raises(MissingSegmentError):
            parser.parse_message("PID|||12345")


class TestEmptyFields:
    def test_empty_fields_handled(self, empty_fields_message):
        """Test that || (empty fields) don't crash parser."""
        parser = HL7Parser()
        appt = parser.parse_message(empty_fields_message)
        # Empty fields should result in None values, not crashes
        assert appt.appointment_id is None
        assert appt.patient.id is None
        assert appt.reason is None


class TestMessageTypeValidation:
    def test_invalid_type_raises(self, malformed_message):
        parser = HL7Parser()
        with pytest.raises(InvalidMessageTypeError) as exc:
            parser.parse_message(malformed_message)
        assert "ADT^A01" in str(exc.value)


class TestTimestampNormalization:
    def test_date_only(self):
        from hl7_siu_parser.models import Appointment
        appt = Appointment(appointment_datetime="20250502")
        assert appt.appointment_datetime == "2025-05-02T00:00:00Z"

    def test_with_timezone(self):
        from hl7_siu_parser.models import Appointment
        appt = Appointment(appointment_datetime="20250502130000+0500")
        assert appt.appointment_datetime == "2025-05-02T13:00:00+05:00"
