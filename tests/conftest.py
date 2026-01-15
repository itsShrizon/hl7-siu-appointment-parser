"""Pytest fixtures for HL7 parser tests."""
import pytest
from pathlib import Path


# =============================================================================
# Path Fixtures
# =============================================================================

@pytest.fixture
def fixtures_dir() -> Path:
    """Return the path to the fixtures directory."""
    return Path(__file__).parent / "fixtures"


# =============================================================================
# Valid Message Fixtures
# =============================================================================

@pytest.fixture
def valid_message() -> str:
    """Standard valid SIU^S12 message with all segments."""
    return """MSH|^~\\&|APP|FAC|||20250502130000||SIU^S12|MSG001|P|2.5
SCH|12345|FILLER456||||Checkup^Routine|||||^^^20250502130000|||||||||||Room 101
PID|||P12345||Doe^John||19850210|M
PV1||O|CLINIC||||D001^Smith^Jane"""


@pytest.fixture
def valid_message_full() -> str:
    """Complete valid SIU^S12 message with all fields populated."""
    return """MSH|^~\\&|SCHEDULING|HOSPITAL|RECEIVER|FAC|20250502130000||SIU^S12|MSG001|P|2.5
SCH|PLACER001|FILLER456||||Checkup^Routine Checkup|||||^^^20250502130000|||||||||||Clinic A Room 203
PID|||P12345||Doe^John^Michael||19850210|M
PV1||O|CLINIC||||D67890^Smith^Jane^Dr^MD"""


# =============================================================================
# Empty/Missing Field Fixtures
# =============================================================================

@pytest.fixture
def empty_fields_message() -> str:
    """Message with empty fields (consecutive ||)."""
    return """MSH|^~\\&|APP|FAC|||20250502130000||SIU^S12|MSG002|P|2.5
SCH|||||||||||||||||||||Room 101
PID|||||||||
PV1||O"""


@pytest.fixture
def all_empty_fields_message() -> str:
    """Message where every optional field is empty."""
    return """MSH|^~\\&|APP|FAC|||20250502130000||SIU^S12|MSG003|P|2.5
SCH||||||||||||||||||||||
PID|||||||||||||||||||||||||||||||
PV1||"""


# =============================================================================
# Missing Segment Fixtures
# =============================================================================

@pytest.fixture
def missing_sch_message() -> str:
    """SIU^S12 message missing SCH segment."""
    return """MSH|^~\\&|SCHEDULING|HOSPITAL|RECEIVER|FAC|20250502130000||SIU^S12|MSG001|P|2.5
PID|||P12345||Doe^John^M||19850210|M
PV1||O|CLINIC||||D67890^Smith^Jane^Dr"""


@pytest.fixture
def missing_pid_message() -> str:
    """SIU^S12 message missing PID segment."""
    return """MSH|^~\\&|SCHEDULING|HOSPITAL|RECEIVER|FAC|20250502130000||SIU^S12|MSG001|P|2.5
SCH|12345|FILLER456||||Checkup^Routine Checkup|||||^^^20250502130000|||||||||||Room 101
PV1||O|CLINIC||||D67890^Smith^Jane^Dr"""


@pytest.fixture
def missing_pv1_message() -> str:
    """SIU^S12 message missing PV1 segment (no provider)."""
    return """MSH|^~\\&|SCHEDULING|HOSPITAL|RECEIVER|FAC|20250502130000||SIU^S12|MSG001|P|2.5
SCH|12345|FILLER456||||Checkup^Routine Checkup|||||^^^20250502130000|||||||||||Room 101
PID|||P12345||Doe^John^M||19850210|M"""


@pytest.fixture
def minimal_message() -> str:
    """Minimal valid SIU^S12 with only MSH and SCH."""
    return """MSH|^~\\&|APP|FAC|||20250502130000||SIU^S12|MSG001|P|2.5
SCH|12345|FILLER001||||Checkup^Routine|||||^^^20250502130000"""


# =============================================================================
# Extra Segments Fixtures
# =============================================================================

@pytest.fixture
def extra_segments_message() -> str:
    """SIU message with extra/irrelevant segments that should be ignored."""
    return """MSH|^~\\&|SCHEDULING|HOSPITAL|RECEIVER|FAC|20250502130000||SIU^S12|MSG001|P|2.5
EVN|S12|20250502130000
SCH|12345|FILLER456||||Checkup^Routine Checkup|||||^^^20250502130000|||||||||||Room 101
NTE|1||This is a note segment
PID|||P12345||Doe^John^M||19850210|M
AL1|1||Penicillin|Moderate
OBX|1|ST|12345^Blood Pressure||120/80||||||F
PV1||O|CLINIC||||D67890^Smith^Jane^Dr
RGS|1||AppointmentGroup
AIL|1||Room 101^Clinic A
AIP|1||D67890^Smith^Jane^Dr"""


# =============================================================================
# Truncated/Malformed Fixtures
# =============================================================================

@pytest.fixture
def truncated_segments_message() -> str:
    """Message with truncated segments (fewer fields than expected)."""
    return """MSH|^~\\&|APP|FAC|||20250502130000||SIU^S12|MSG001|P|2.5
SCH|12345
PID|||P001
PV1||O"""


@pytest.fixture
def malformed_message() -> str:
    """Message with wrong message type (ADT instead of SIU)."""
    return """MSH|^~\\&|APP|FAC|||20250502130000||ADT^A01|MSG003|P|2.5
PID|||P999||Bad^Message"""


@pytest.fixture
def non_siu_message_types() -> list:
    """List of various non-SIU message types for testing."""
    return [
        ("ADT^A01", "Admit patient"),
        ("ADT^A03", "Discharge patient"),
        ("ORU^R01", "Lab result"),
        ("ORM^O01", "Order message"),
        ("SIU^S13", "Appointment rescheduled (not S12)"),
        ("SIU^S14", "Appointment modification"),
        ("SIU^S15", "Appointment cancellation"),
    ]


# =============================================================================
# Custom Separator Fixtures
# =============================================================================

@pytest.fixture
def custom_separator_message() -> str:
    """Message with unusual (but valid) component separator."""
    return """MSH|#~\\&|APP|FAC|||20250502130000||SIU^S12|MSG001|P|2.5
SCH|12345|FILLER456||||Checkup#Routine|||||###20250502130000|||||||||||Room 101
PID|||P12345||Doe#John||19850210|M
PV1||O|CLINIC||||D001#Smith#Jane"""


@pytest.fixture
def tilde_in_field_message() -> str:
    """Message with repetition separator (~) in use."""
    return """MSH|^~\\&|APP|FAC|||20250502130000||SIU^S12|MSG001|P|2.5
SCH|APT001~APT001B|FILL001||||Checkup^Routine|||||^^^20250502130000|||||||||||Room 101
PID|||P12345~P12345-ALT~P12345-OLD||Doe^John||19850210|M
PV1||O|CLINIC||||D001^Smith^Jane~D002^Jones^Bob"""


# =============================================================================
# Line Ending Fixtures
# =============================================================================

@pytest.fixture
def crlf_message() -> str:
    """Message with Windows-style CRLF line endings."""
    return "MSH|^~\\&|APP|FAC|||20250502130000||SIU^S12|MSG001|P|2.5\r\n" \
           "SCH|12345|FILLER456||||Checkup^Routine|||||^^^20250502130000|||||||||||Room 101\r\n" \
           "PID|||P12345||Doe^John||19850210|M\r\n" \
           "PV1||O|CLINIC||||D001^Smith^Jane"


@pytest.fixture
def cr_only_message() -> str:
    """Message with old Mac-style CR-only line endings."""
    return "MSH|^~\\&|APP|FAC|||20250502130000||SIU^S12|MSG001|P|2.5\r" \
           "SCH|12345|FILLER456||||Checkup^Routine|||||^^^20250502130000|||||||||||Room 101\r" \
           "PID|||P12345||Doe^John||19850210|M\r" \
           "PV1||O|CLINIC||||D001^Smith^Jane"


# =============================================================================
# Multi-Message Fixtures
# =============================================================================

@pytest.fixture
def multiple_siu_messages() -> str:
    """Content with 3 valid SIU messages."""
    return """MSH|^~\\&|APP|FAC|||20250502090000||SIU^S12|MSG001|P|2.5
SCH|APT001|FILL001||||Morning Checkup^Checkup|||||^^^20250502090000|||||||||||Room 101
PID|||P001||Smith^Alice||19900115|F
PV1||O|CLINIC||||D001^Jones^Bob
MSH|^~\\&|APP|FAC|||20250502100000||SIU^S12|MSG002|P|2.5
SCH|APT002|FILL002||||Consultation^Consult|||||^^^20250502100000|||||||||||Room 202
PID|||P002||Johnson^Bob||19851220|M
PV1||O|CLINIC||||D002^Williams^Sarah
MSH|^~\\&|APP|FAC|||20250502110000||SIU^S12|MSG003|P|2.5
SCH|APT003|FILL003||||Follow-up^Follow-up Visit|||||^^^20250502110000|||||||||||Room 303
PID|||P003||Davis^Carol||19750310|F
PV1||O|CLINIC||||D003^Brown^Mike"""


@pytest.fixture
def mixed_message_types() -> str:
    """Content with SIU messages mixed with other types."""
    return """MSH|^~\\&|APP|FAC|||20250502090000||ADT^A01|MSG001|P|2.5
PID|||P001||Patient^One
MSH|^~\\&|APP|FAC|||20250502100000||ORU^R01|MSG002|P|2.5
PID|||P002||Patient^Two
OBR|1|12345||LAB TEST
MSH|^~\\&|APP|FAC|||20250502110000||SIU^S12|MSG003|P|2.5
SCH|APT001|FILL001||||Checkup^Routine Checkup|||||^^^20250502110000|||||||||||Room 101
PID|||P003||Patient^Three||19850315|M
PV1||O|CLINIC||||D001^Smith^Jane
MSH|^~\\&|APP|FAC|||20250502120000||SIU^S12|MSG004|P|2.5
SCH|APT002|FILL002||||Consult^Consultation|||||^^^20250502120000|||||||||||Room 202
PID|||P004||Patient^Four||19900420|F
PV1||O|CLINIC||||D002^Jones^Bob
MSH|^~\\&|APP|FAC|||20250502130000||ADT^A03|MSG005|P|2.5
PID|||P005||Patient^Five"""


# =============================================================================
# Timestamp Edge Cases
# =============================================================================

@pytest.fixture
def timestamp_formats() -> dict:
    """Dictionary of HL7 timestamp formats and their expected ISO output."""
    return {
        # Date only
        "20250502": "2025-05-02T00:00:00Z",
        # Date + hour/minute
        "202505021300": "2025-05-02T13:00:00Z",
        # Date + full time
        "20250502130000": "2025-05-02T13:00:00Z",
        # With positive timezone
        "20250502130000+0530": "2025-05-02T13:00:00+05:30",
        "20250502130000+0000": "2025-05-02T13:00:00+00:00",
        # With negative timezone
        "20250502130000-0800": "2025-05-02T13:00:00-08:00",
        "20250502130000-0500": "2025-05-02T13:00:00-05:00",
        # With fractional seconds (should be stripped)
        "20250502130000.1234": "2025-05-02T13:00:00Z",
        "20250502130000.1234+0530": "2025-05-02T13:00:00+05:30",
        # Edge cases
        "20251231235959": "2025-12-31T23:59:59Z",  # End of year
        "20250101000000": "2025-01-01T00:00:00Z",  # Start of year
    }


@pytest.fixture
def invalid_timestamps() -> list:
    """List of invalid timestamp strings that should not crash."""
    return [
        "",              # Empty
        "invalid",       # Non-numeric
        "2025",          # Too short
        "202513",        # Invalid month
        "20250532",      # Invalid day
        "abc",           # Letters only
        None,            # None value
    ]


# =============================================================================
# Whitespace Edge Cases
# =============================================================================

@pytest.fixture
def whitespace_message() -> str:
    """Message with extra whitespace that should be handled."""
    return """  MSH|^~\\&|APP|FAC|||20250502130000||SIU^S12|MSG001|P|2.5  
  SCH|12345|FILLER456||||Checkup^Routine|||||^^^20250502130000|||||||||||Room 101  
  PID|||P12345||Doe^John||19850210|M  
  PV1||O|CLINIC||||D001^Smith^Jane  """


@pytest.fixture
def only_whitespace_message() -> str:
    """Message that is only whitespace."""
    return "   \n\n\t\t   \n   "
