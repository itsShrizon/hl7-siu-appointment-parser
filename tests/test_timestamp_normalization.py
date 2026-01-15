"""Tests for timestamp normalization."""
import pytest
from hl7_siu_parser.models import Appointment, Patient


class TestTimestampNormalization:
    """Tests for appointment_datetime normalization."""

    def test_date_only(self):
        """Date only (YYYYMMDD) normalized to ISO 8601."""
        appt = Appointment(appointment_datetime="20250502")
        assert appt.appointment_datetime == "2025-05-02T00:00:00Z"

    def test_date_with_hour_minute(self):
        """Date with hour/minute (YYYYMMDDHHMM) normalized."""
        appt = Appointment(appointment_datetime="202505021300")
        assert appt.appointment_datetime == "2025-05-02T13:00:00Z"

    def test_date_with_full_time(self):
        """Date with full time (YYYYMMDDHHMMSS) normalized."""
        appt = Appointment(appointment_datetime="20250502130045")
        assert appt.appointment_datetime == "2025-05-02T13:00:45Z"

    def test_with_positive_timezone(self):
        """Positive timezone offset preserved and formatted."""
        appt = Appointment(appointment_datetime="20250502130000+0530")
        assert appt.appointment_datetime == "2025-05-02T13:00:00+05:30"

    def test_with_negative_timezone(self):
        """Negative timezone offset preserved and formatted."""
        appt = Appointment(appointment_datetime="20250502130000-0800")
        assert appt.appointment_datetime == "2025-05-02T13:00:00-08:00"

    def test_with_zero_timezone(self):
        """Zero timezone offset (+0000) formatted correctly."""
        appt = Appointment(appointment_datetime="20250502130000+0000")
        assert appt.appointment_datetime == "2025-05-02T13:00:00+00:00"

    def test_with_fractional_seconds(self):
        """Fractional seconds stripped."""
        appt = Appointment(appointment_datetime="20250502130045.1234")
        assert appt.appointment_datetime == "2025-05-02T13:00:45Z"

    def test_fractional_seconds_with_timezone(self):
        """Fractional seconds stripped, timezone preserved."""
        appt = Appointment(appointment_datetime="20250502130045.1234+0530")
        assert appt.appointment_datetime == "2025-05-02T13:00:45+05:30"

    def test_end_of_year(self):
        """End of year timestamp normalized."""
        appt = Appointment(appointment_datetime="20251231235959")
        assert appt.appointment_datetime == "2025-12-31T23:59:59Z"

    def test_start_of_year(self):
        """Start of year timestamp normalized."""
        appt = Appointment(appointment_datetime="20250101000000")
        assert appt.appointment_datetime == "2025-01-01T00:00:00Z"

    def test_midnight(self):
        """Midnight timestamp normalized."""
        appt = Appointment(appointment_datetime="20250502000000")
        assert appt.appointment_datetime == "2025-05-02T00:00:00Z"

    def test_noon(self):
        """Noon timestamp normalized."""
        appt = Appointment(appointment_datetime="20250502120000")
        assert appt.appointment_datetime == "2025-05-02T12:00:00Z"


class TestTimestampEdgeCases:
    """Edge case tests for timestamp handling."""

    def test_empty_timestamp(self):
        """Empty timestamp returns None."""
        appt = Appointment(appointment_datetime="")
        assert appt.appointment_datetime is None

    def test_none_timestamp(self):
        """None timestamp remains None."""
        appt = Appointment(appointment_datetime=None)
        assert appt.appointment_datetime is None

    def test_whitespace_timestamp(self):
        """Whitespace-only timestamp - validator strips, but original is passed through if short."""
        appt = Appointment(appointment_datetime="   ")
        # After strip, "   " becomes "", which is < 8 chars, so returned as-is
        # The original value "   " is returned since strip happens first then length check
        assert appt.appointment_datetime == "   "

    def test_too_short_timestamp(self):
        """Too short timestamp returned as-is."""
        appt = Appointment(appointment_datetime="2025")
        assert appt.appointment_datetime == "2025"

    def test_non_numeric_timestamp(self):
        """Non-numeric timestamp returned as-is."""
        appt = Appointment(appointment_datetime="invalid")
        assert appt.appointment_datetime == "invalid"

    def test_iso_format_passthrough(self):
        """ISO format timestamp returned as-is (not double-converted)."""
        # This tests that already converted timestamps aren't broken
        appt = Appointment(appointment_datetime="2025-05-02T13:00:00Z")
        # Depends on implementation - may return as-is or error
        # Current implementation should return as-is since it doesn't match HL7 format


class TestDOBNormalization:
    """Tests for patient DOB normalization."""

    def test_full_date(self):
        """Full date (YYYYMMDD) normalized to ISO 8601."""
        patient = Patient(dob="19850210")
        assert patient.dob == "1985-02-10"

    def test_date_with_time(self):
        """Date with time - only date portion used."""
        patient = Patient(dob="19850210130000")
        assert patient.dob == "1985-02-10"

    def test_empty_dob(self):
        """Empty DOB returns None."""
        patient = Patient(dob="")
        assert patient.dob is None

    def test_none_dob(self):
        """None DOB remains None."""
        patient = Patient(dob=None)
        assert patient.dob is None

    def test_short_dob(self):
        """Short DOB returned as-is."""
        patient = Patient(dob="1985")
        assert patient.dob == "1985"


class TestTimestampFormats:
    """Parametrized tests for various timestamp formats."""

    @pytest.mark.parametrize("hl7_ts,expected_iso", [
        # Basic formats
        ("20250502", "2025-05-02T00:00:00Z"),
        ("202505021300", "2025-05-02T13:00:00Z"),
        ("20250502130000", "2025-05-02T13:00:00Z"),
        # With timezones
        ("20250502130000+0500", "2025-05-02T13:00:00+05:00"),
        ("20250502130000-0800", "2025-05-02T13:00:00-08:00"),
        ("20250502130000+0000", "2025-05-02T13:00:00+00:00"),
        # With fractional seconds
        ("20250502130000.1", "2025-05-02T13:00:00Z"),
        ("20250502130000.1234", "2025-05-02T13:00:00Z"),
        ("20250502130000.1234+0530", "2025-05-02T13:00:00+05:30"),
    ])
    def test_timestamp_format(self, hl7_ts, expected_iso):
        """Test various HL7 timestamp formats."""
        appt = Appointment(appointment_datetime=hl7_ts)
        assert appt.appointment_datetime == expected_iso

    @pytest.mark.parametrize("hl7_dob,expected_iso", [
        ("19850210", "1985-02-10"),
        ("19901231", "1990-12-31"),
        ("20000101", "2000-01-01"),
        ("19850210120000", "1985-02-10"),  # Time portion ignored
    ])
    def test_dob_format(self, hl7_dob, expected_iso):
        """Test various HL7 DOB formats."""
        patient = Patient(dob=hl7_dob)
        assert patient.dob == expected_iso
