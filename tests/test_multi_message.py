"""Tests for multi-message parsing and streaming."""
import pytest
from pathlib import Path
from hl7_siu_parser import HL7Parser
from hl7_siu_parser.parser.streaming_parser import StreamingParser, StreamStats


class TestMultipleSIUMessages:
    """Tests for parsing multiple SIU messages in one file."""

    def test_parse_multiple_messages(self, multiple_siu_messages):
        """Parse multiple SIU messages from content."""
        parser = HL7Parser()
        appointments = parser.parse_messages(multiple_siu_messages)
        
        assert len(appointments) == 3
        
        # Verify each appointment
        assert appointments[0].appointment_id == "FILL001"
        assert appointments[0].patient.first_name == "Alice"
        
        assert appointments[1].appointment_id == "FILL002"
        assert appointments[1].patient.first_name == "Bob"
        
        assert appointments[2].appointment_id == "FILL003"
        assert appointments[2].patient.first_name == "Carol"

    def test_stream_multiple_messages(self, multiple_siu_messages):
        """Stream multiple SIU messages from content."""
        parser = HL7Parser()
        appointments = list(parser.stream_messages(multiple_siu_messages))
        
        assert len(appointments) == 3
        assert appointments[0].appointment_id == "FILL001"
        assert appointments[1].appointment_id == "FILL002"
        assert appointments[2].appointment_id == "FILL003"

    def test_parse_with_report(self, multiple_siu_messages):
        """Parse multiple messages with detailed report."""
        parser = HL7Parser()
        result = parser.parse_messages_with_report(multiple_siu_messages)
        
        assert result.total_processed == 3
        assert result.total_skipped == 0
        assert result.total_errors == 0
        assert len(result.appointments) == 3


class TestMixedMessageTypes:
    """Tests for parsing SIU messages mixed with other types."""

    def test_parse_mixed_types(self, mixed_message_types):
        """Only SIU messages extracted from mixed feed."""
        parser = HL7Parser()
        appointments = parser.parse_messages(mixed_message_types)
        
        # Should only get 2 SIU messages (ADT, ORU, ADT are skipped)
        assert len(appointments) == 2
        
        assert appointments[0].appointment_id == "FILL001"
        assert appointments[0].patient.id == "P003"
        
        assert appointments[1].appointment_id == "FILL002"
        assert appointments[1].patient.id == "P004"

    def test_mixed_types_with_report(self, mixed_message_types):
        """Mixed types parsed with detailed skipped report."""
        parser = HL7Parser()
        result = parser.parse_messages_with_report(mixed_message_types)
        
        assert result.total_processed == 2
        assert result.total_skipped == 3  # ADT^A01, ORU^R01, ADT^A03
        assert len(result.skipped) == 3

    def test_stream_mixed_types(self, mixed_message_types):
        """Streaming handles mixed types correctly."""
        parser = HL7Parser()
        appointments = list(parser.stream_messages(mixed_message_types))
        
        assert len(appointments) == 2
        assert appointments[0].appointment_id == "FILL001"
        assert appointments[1].appointment_id == "FILL002"


class TestStreamingParser:
    """Tests for the streaming parser."""

    def test_stream_from_content(self, multiple_siu_messages):
        """Stream parser processes content correctly."""
        parser = StreamingParser()
        stats = StreamStats()
        
        appointments = list(parser.stream_content(multiple_siu_messages, stats))
        
        assert len(appointments) == 3
        assert stats.messages_found == 3
        assert stats.messages_parsed == 3
        assert stats.messages_errored == 0

    def test_stats_tracking(self, mixed_message_types):
        """Stats correctly track parsed, skipped, and errored."""
        parser = StreamingParser()
        stats = StreamStats()
        
        appointments = list(parser.stream_content(mixed_message_types, stats))
        
        assert len(appointments) == 2
        assert stats.messages_parsed == 2
        assert stats.messages_skipped == 3  # Non-SIU messages


class TestFileBasedParsing:
    """Tests for parsing from fixture files."""

    def test_parse_valid_single_file(self, fixtures_dir):
        """Parse valid single message from file."""
        file_path = fixtures_dir / "valid_single.hl7"
        if not file_path.exists():
            pytest.skip("Fixture file not found")
        
        parser = HL7Parser()
        appointments = list(parser.stream_file(str(file_path)))
        
        assert len(appointments) == 1
        assert appointments[0].appointment_id is not None

    def test_parse_multiple_siu_file(self, fixtures_dir):
        """Parse multiple SIU messages from file."""
        file_path = fixtures_dir / "multiple_siu.hl7"
        if not file_path.exists():
            pytest.skip("Fixture file not found")
        
        parser = HL7Parser()
        appointments = list(parser.stream_file(str(file_path)))
        
        assert len(appointments) == 3

    def test_parse_mixed_types_file(self, fixtures_dir):
        """Parse mixed message types from file."""
        file_path = fixtures_dir / "mixed_types.hl7"
        if not file_path.exists():
            pytest.skip("Fixture file not found")
        
        parser = HL7Parser()
        appointments = list(parser.stream_file(str(file_path)))
        
        # mixed_types.hl7 has 2 SIU messages
        assert len(appointments) == 2

    def test_parse_extra_segments_file(self, fixtures_dir):
        """Parse file with extra segments."""
        file_path = fixtures_dir / "extra_segments.hl7"
        if not file_path.exists():
            pytest.skip("Fixture file not found")
        
        parser = HL7Parser()
        appointments = list(parser.stream_file(str(file_path)))
        
        assert len(appointments) == 1
        assert appointments[0].appointment_id == "FILLER456"

    def test_parse_truncated_fields_file(self, fixtures_dir):
        """Parse file with truncated fields."""
        file_path = fixtures_dir / "truncated_fields.hl7"
        if not file_path.exists():
            pytest.skip("Fixture file not found")
        
        parser = HL7Parser()
        appointments = list(parser.stream_file(str(file_path)))
        
        assert len(appointments) == 1
        assert appointments[0].appointment_id == "12345"


class TestMessageSplitting:
    """Tests for message splitting logic."""

    def test_split_multiple_messages(self, multiple_siu_messages):
        """Split content into individual message strings."""
        parser = HL7Parser()
        messages = parser.split_messages(multiple_siu_messages)
        
        assert len(messages) == 3
        for msg in messages:
            assert msg.startswith("MSH")

    def test_split_mixed_messages(self, mixed_message_types):
        """Split mixed content into individual messages."""
        parser = HL7Parser()
        messages = parser.split_messages(mixed_message_types)
        
        assert len(messages) == 5  # All message types

    def test_split_single_message(self, valid_message):
        """Single message returns list with one element."""
        parser = HL7Parser()
        messages = parser.split_messages(valid_message)
        
        assert len(messages) == 1


class TestStrictModeBatch:
    """Tests for strict mode batch processing."""

    def test_strict_mode_fails_on_error(self, mixed_message_types):
        """Strict mode fails on first non-SIU message."""
        parser = HL7Parser()
        
        with pytest.raises(Exception):
            # First message is ADT^A01, should fail
            parser.parse_messages_strict(mixed_message_types)

    def test_strict_mode_succeeds_clean_input(self, multiple_siu_messages):
        """Strict mode succeeds with all SIU messages."""
        parser = HL7Parser()
        appointments = parser.parse_messages_strict(multiple_siu_messages)
        
        assert len(appointments) == 3


class TestEmptyAndInvalidFiles:
    """Tests for edge cases in file/content parsing."""

    def test_empty_content(self):
        """Empty content returns empty list."""
        parser = HL7Parser()
        appointments = parser.parse_messages("")
        assert len(appointments) == 0

    def test_whitespace_content(self):
        """Whitespace-only content returns empty list."""
        parser = HL7Parser()
        appointments = parser.parse_messages("   \n\n\t\t   ")
        assert len(appointments) == 0

    def test_no_msh_content(self):
        """Content without MSH returns empty list."""
        parser = HL7Parser()
        appointments = parser.parse_messages("PID|||12345||Name\nPV1||O")
        assert len(appointments) == 0
