"""
HL7 SIU Parser - Core Parser

Orchestrates parsing of HL7 SIU S12 messages.
Designed for fault tolerance in real-world HL7 feeds with mixed message types.
"""
import sys
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from .models import Appointment
from .exceptions import (
    HL7ParseError,
    InvalidMessageTypeError,
    MissingSegmentError,
    EmptyMessageError,
)
from .segments import parse_msh, parse_sch, parse_pid, parse_pv1, parse_ail


@dataclass
class ParseResult:
    """
    Result of parsing a batch of messages.
    
    Provides clear separation between successful parses, 
    skipped messages, and actual errors.
    """
    appointments: List[Appointment] = field(default_factory=list)
    skipped: List[Dict[str, Any]] = field(default_factory=list)  # Non-SIU messages
    errors: List[Dict[str, Any]] = field(default_factory=list)   # Parse failures
    
    @property
    def total_processed(self) -> int:
        return len(self.appointments)
    
    @property
    def total_skipped(self) -> int:
        return len(self.skipped)
    
    @property
    def total_errors(self) -> int:
        return len(self.errors)


class HL7Parser:
    """
    Parser for HL7 SIU S12 (Schedule Information Unsolicited) messages.
    
    Designed for production use with mixed HL7 feeds:
    - Filters SIU^S12 messages from mixed feeds (ADT, ORU, etc.)
    - Continues processing after encountering bad messages
    - Provides detailed reporting of skipped/failed messages
    
    Example:
        parser = HL7Parser()
        
        # Simple: Get only SIU appointments, skip others
        appointments = parser.parse_messages(content)
        
        # Detailed: See what was skipped/failed
        result = parser.parse_messages_with_report(content)
        print(f"Parsed: {result.total_processed}")
        print(f"Skipped: {result.total_skipped} non-SIU messages")
        print(f"Errors: {result.total_errors}")
    """

    def __init__(self, strict_mode: bool = False):
        """
        Initialize parser.
        
        Args:
            strict_mode: If True, raises errors for missing optional segments.
                        If False, gracefully handles missing data.
        """
        self.strict_mode = strict_mode

    def parse_message(self, raw_message: str) -> Appointment:
        """
        Parse a single HL7 SIU S12 message into an Appointment.
        
        Args:
            raw_message: Raw HL7 message string
            
        Returns:
            Appointment model with extracted data
            
        Raises:
            EmptyMessageError: If message is empty
            MissingSegmentError: If required segment is missing
            InvalidMessageTypeError: If not an SIU^S12 message
        """
        # Validate input
        if not raw_message:
            raise EmptyMessageError()
        
        cleaned_message = raw_message.strip()
        if not cleaned_message:
            raise EmptyMessageError()
        
        # Extract lines
        lines = self._split_into_lines(cleaned_message)
        if not lines:
            raise EmptyMessageError()
        
        # Find and parse MSH segment
        msh_line = self._find_segment_line(lines, "MSH")
        if msh_line is None:
            raise MissingSegmentError("MSH", required=True)
        
        # Parse MSH to get metadata
        metadata = parse_msh(msh_line)
        
        # Validate message type
        if not metadata.is_siu_s12():
            actual_type = metadata.message_type if metadata.message_type else "UNKNOWN"
            raise InvalidMessageTypeError(actual_type=actual_type)
        
        # Parse other segments with MSH-defined separators
        field_sep = metadata.field_separator
        comp_sep = metadata.component_separator
        
        # Parse segments
        sch_data = self._parse_sch_segment(lines, field_sep, comp_sep)
        patient = self._parse_pid_segment(lines, field_sep, comp_sep)
        provider = self._parse_pv1_segment(lines, field_sep, comp_sep)
        
        # Get location (from SCH, fallback to AIL)
        location = sch_data.get("location")
        if not location:
            location = self._parse_ail_location(lines, field_sep, comp_sep)
        
        return Appointment(
            appointment_id=sch_data.get("appointment_id"),
            appointment_datetime=sch_data.get("appointment_datetime"),
            patient=patient,
            provider=provider,
            location=location,
            reason=sch_data.get("reason"),
        )

    def parse_messages(self, content: str) -> List[Appointment]:
        """
        Parse messages from content, filtering for SIU^S12 only.
        
        This is the fault-tolerant method for production use:
        - Skips non-SIU messages (ADT, ORU, etc.) silently
        - Skips malformed messages silently
        - Returns only successfully parsed SIU appointments
        
        For detailed error reporting, use parse_messages_with_report().
        
        Args:
            content: Raw content that may contain multiple HL7 messages
            
        Returns:
            List of successfully parsed Appointment models
        """
        result = self.parse_messages_with_report(content)
        return result.appointments

    def parse_messages_with_report(self, content: str) -> ParseResult:
        """
        Parse messages with detailed reporting of what happened.
        
        Processes ALL messages in the feed and categorizes them:
        - appointments: Successfully parsed SIU^S12 messages
        - skipped: Non-SIU messages (ADT, ORU, etc.) - not errors, just different types
        - errors: SIU messages that failed to parse (malformed data)
        
        Args:
            content: Raw content that may contain multiple HL7 messages
            
        Returns:
            ParseResult with appointments, skipped messages, and errors
        """
        result = ParseResult()
        messages = self.split_messages(content)
        
        for index, message in enumerate(messages):
            message_number = index + 1 
            
            try:
                appointment = self.parse_message(message)
                result.appointments.append(appointment)
                
            except InvalidMessageTypeError as error:
                # This is NOT an error - it's a non-SIU message that should be skipped
                result.skipped.append({
                    "message_number": message_number,
                    "reason": str(error),
                    "message_type": error.actual_type,
                })
                
            except EmptyMessageError:
                # Empty messages are skipped, not errors
                result.skipped.append({
                    "message_number": message_number,
                    "reason": "Empty message",
                    "message_type": None,
                })
                
            except HL7ParseError as error:
                # Actual parsing errors for SIU messages
                result.errors.append({
                    "message_number": message_number,
                    "error": str(error),
                    "error_type": type(error).__name__,
                })
                
            except Exception as error:
                # Unexpected errors - still don't crash, but report
                result.errors.append({
                    "message_number": message_number,
                    "error": f"Unexpected error: {error}",
                    "error_type": type(error).__name__,
                })
        
        return result

    def parse_messages_strict(self, content: str) -> List[Appointment]:
        """
        Parse messages with strict error handling (fails on first error).
        
        Use this only when you KNOW the file contains only valid SIU messages.
        For mixed feeds, use parse_messages() instead.
        
        Raises:
            HL7ParseError: On first parsing error
        """
        messages = self.split_messages(content)
        appointments = []
        
        for index, message in enumerate(messages):
            message_number = index + 1
            try:
                appointment = self.parse_message(message)
                appointments.append(appointment)
            except HL7ParseError as error:
                raise type(error)(f"Message {message_number}: {error}") from error
        
        return appointments

    def split_messages(self, content: str) -> List[str]:
        """
        Split content into individual HL7 messages using proper delimiters.
        
        """
        if not content:
            return []
        
        # Normalize line endings to \n
        normalized = content.replace("\r\n", "\n").replace("\r", "\n")
        
        messages = []
        current_buffer = []
        in_message = False
        line_number = 0
        
        for line in normalized.split("\n"):
            line_number += 1
            line = line.strip()
            
            if not line:
                continue  # Skip empty lines
            
            # Check if line starts with "MSH" 
            if line.startswith("MSH"):
                # Validate it's actually a proper MSH segment
                if self._is_valid_msh_start(line):
                    # Save previous message if exists
                    if current_buffer:
                        messages.append("\n".join(current_buffer))
                    
                    # Start new message
                    current_buffer = [line]
                    in_message = True
                else:
                    # Line starts with "MSH" but is malformed
                    print(f"Warning: Line {line_number} looks like MSH but is malformed: {line[:50]}...", 
                          file=sys.stderr)
                    
                    # Should we add it to current message or skip it?
                    if in_message:
                        # Treat as data in current message (might be field content)
                        current_buffer.append(line)
                    else:
                        # No message started yet, skip this garbage
                        print(f"  -> Skipping line (no valid message started)", file=sys.stderr)
                        continue
            
            elif in_message:
                # Add to current message
                current_buffer.append(line)
            else:
                # Data before first valid MSH - this is garbage
                print(f"Warning: Line {line_number} found before first valid MSH segment: {line[:50]}...",
                      file=sys.stderr)
                print(f"  -> Skipping orphaned data", file=sys.stderr)
        
        # Don't forget the last message
        if current_buffer:
            messages.append("\n".join(current_buffer))
        
        return messages

    def _is_valid_msh_start(self, line: str) -> bool:
        """
        Validate that a line is actually an MSH segment, not just contains "MSH".
        
        Valid MSH structure:
        - Starts with exactly "MSH"
        - Followed by field separator (usually |)
        - Then encoding characters (usually ^~\&)
        - Minimum length check
        
        Returns:
            True if valid MSH segment, False otherwise
        """
        if not line.startswith("MSH"):
            return False
        
        # Minimum: "MSH|^~\&" = 8 characters
        if len(line) < 8:
            return False
        
        # Character at index 3 should be the field separator
        field_sep = line[3]
        
        # Field separator must be printable, non-alphanumeric, non-whitespace
        if field_sep.isalnum() or field_sep.isspace():
            return False
        
        # Characters 4-7 should be encoding characters (^~\&)
        # We just check they exist and aren't whitespace
        encoding_chars = line[4:8]
        if len(encoding_chars) < 4:
            return False
        
        if any(c.isspace() for c in encoding_chars):
            return False
        
        return True

    # =========================================================================
    # Private helper methods
    # =========================================================================

    def _split_into_lines(self, content: str) -> List[str]:
        """Split content into lines, handling various line endings."""
        normalized = content.replace("\r\n", "\n").replace("\r", "\n")
        return [line.strip() for line in normalized.split("\n") if line.strip()]

    def _find_segment_line(self, lines: List[str], segment_type: str) -> Optional[str]:
        """Find the first line that matches a segment type."""
        for line in lines:
            if len(line) >= 3 and line[:3].upper() == segment_type.upper():
                return line
        return None

    def _parse_sch_segment(
        self, lines: List[str], field_sep: str, comp_sep: str
    ) -> Dict[str, Any]:
        """Parse SCH segment if present."""
        sch_line = self._find_segment_line(lines, "SCH")
        
        if sch_line:
            return parse_sch(sch_line, field_sep, comp_sep)
        
        if self.strict_mode:
            raise MissingSegmentError("SCH", required=True)
        
        return {}

    def _parse_pid_segment(
        self, lines: List[str], field_sep: str, comp_sep: str
    ) -> Optional["Patient"]:
        """Parse PID segment if present."""
        pid_line = self._find_segment_line(lines, "PID")
        
        if pid_line:
            return parse_pid(pid_line, field_sep, comp_sep)
        
        if self.strict_mode:
            raise MissingSegmentError("PID", required=True)
        
        return None

    def _parse_pv1_segment(
        self, lines: List[str], field_sep: str, comp_sep: str
    ) -> Optional["Provider"]:
        """Parse PV1 segment if present."""
        pv1_line = self._find_segment_line(lines, "PV1")
        
        if pv1_line:
            return parse_pv1(pv1_line, field_sep, comp_sep)
        
        return None

    def _parse_ail_location(
        self, lines: List[str], field_sep: str, comp_sep: str
    ) -> Optional[str]:
        """Parse AIL segment for location fallback."""
        ail_line = self._find_segment_line(lines, "AIL")
        
        if ail_line:
            ail_data = parse_ail(ail_line, field_sep, comp_sep)
            return ail_data.get("location")
        
        return None
