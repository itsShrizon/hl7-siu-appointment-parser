"""
HL7 SIU Parser - Core Parser

Orchestrates parsing of HL7 SIU S12 messages.
Handles message splitting, validation, and segment extraction.
"""
from typing import List, Dict, Iterator, Any, Optional
from .models import Appointment
from .exceptions import (
    HL7ParseError,
    InvalidMessageTypeError,
    MissingSegmentError,
    EmptyMessageError,
)
from .segments import parse_msh, parse_sch, parse_pid, parse_pv1, parse_ail


class HL7Parser:
    """
    Parser for HL7 SIU S12 (Schedule Information Unsolicited) messages.
    
    This parser:
    - Validates message type before parsing
    - Handles missing/malformed segments gracefully
    - Supports multiple messages per file
    - Uses dynamic field separators from MSH
    
    Example:
        parser = HL7Parser()
        appointment = parser.parse_message(hl7_content)
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
        
        The parsing follows this order:
        1. Validate input is not empty
        2. Find and parse MSH segment (required)
        3. Validate message type is SIU^S12
        4. Parse remaining segments with MSH-defined separators
        
        Args:
            raw_message: Raw HL7 message string
            
        Returns:
            Appointment model with extracted data
            
        Raises:
            EmptyMessageError: If message is empty
            MissingSegmentError: If required segment is missing
            InvalidMessageTypeError: If not an SIU^S12 message
        """
        # Step 1: Validate input
        if not raw_message:
            raise EmptyMessageError()
        
        cleaned_message = raw_message.strip()
        if not cleaned_message:
            raise EmptyMessageError()
        
        # Step 2: Normalize line endings and extract lines
        lines = self._split_into_lines(cleaned_message)
        if not lines:
            raise EmptyMessageError()
        
        # Step 3: Find MSH segment (must be present)
        msh_line = self._find_segment_line(lines, "MSH")
        if msh_line is None:
            raise MissingSegmentError("MSH", required=True)
        
        # Step 4: Parse MSH to get separators and validate message type
        metadata = parse_msh(msh_line)
        
        if not metadata.is_siu_s12():
            actual_type = metadata.message_type if metadata.message_type else "UNKNOWN"
            raise InvalidMessageTypeError(actual_type=actual_type)
        
        # Step 5: Now parse other segments with validated separators
        field_sep = metadata.field_separator
        comp_sep = metadata.component_separator
        
        # Parse SCH segment (appointment data)
        sch_data = self._parse_sch_segment(lines, field_sep, comp_sep)
        
        # Parse PID segment (patient data)
        patient = self._parse_pid_segment(lines, field_sep, comp_sep)
        
        # Parse PV1 segment (provider data)
        provider = self._parse_pv1_segment(lines, field_sep, comp_sep)
        
        # Get location (from SCH, fallback to AIL)
        location = sch_data.get("location")
        if not location:
            location = self._parse_ail_location(lines, field_sep, comp_sep)
        
        # Build and return the Appointment
        return Appointment(
            appointment_id=sch_data.get("appointment_id"),
            appointment_datetime=sch_data.get("appointment_datetime"),
            patient=patient,
            provider=provider,
            location=location,
            reason=sch_data.get("reason"),
        )

    def _split_into_lines(self, content: str) -> List[str]:
        """
        Split content into lines, handling various line endings.
        
        HL7 messages can use CR, LF, or CRLF as line endings.
        """
        # Normalize all line endings to \n
        normalized = content.replace("\r\n", "\n").replace("\r", "\n")
        
        # Split and filter empty lines
        lines = []
        for line in normalized.split("\n"):
            stripped = line.strip()
            if stripped:
                lines.append(stripped)
        
        return lines

    def _find_segment_line(self, lines: List[str], segment_type: str) -> Optional[str]:
        """
        Find the first line that matches a segment type.
        
        Args:
            lines: List of message lines
            segment_type: 3-character segment type (e.g., "MSH", "PID")
            
        Returns:
            The matching line, or None if not found
        """
        for line in lines:
            if len(line) >= 3:
                line_segment_type = line[:3].upper()
                if line_segment_type == segment_type.upper():
                    return line
        return None

    def _parse_sch_segment(
        self, 
        lines: List[str], 
        field_sep: str, 
        comp_sep: str
    ) -> Dict[str, Any]:
        """Parse SCH segment if present."""
        sch_line = self._find_segment_line(lines, "SCH")
        
        if sch_line:
            return parse_sch(sch_line, field_sep, comp_sep)
        
        if self.strict_mode:
            raise MissingSegmentError("SCH", required=True)
        
        # Return empty dict if not in strict mode
        return {}

    def _parse_pid_segment(
        self, 
        lines: List[str], 
        field_sep: str, 
        comp_sep: str
    ) -> Optional["Patient"]:
        """Parse PID segment if present."""
        pid_line = self._find_segment_line(lines, "PID")
        
        if pid_line:
            return parse_pid(pid_line, field_sep, comp_sep)
        
        if self.strict_mode:
            raise MissingSegmentError("PID", required=True)
        
        return None

    def _parse_pv1_segment(
        self, 
        lines: List[str], 
        field_sep: str, 
        comp_sep: str
    ) -> Optional["Provider"]:
        """Parse PV1 segment if present."""
        pv1_line = self._find_segment_line(lines, "PV1")
        
        if pv1_line:
            return parse_pv1(pv1_line, field_sep, comp_sep)
        
        # PV1 is always optional, even in strict mode
        return None

    def _parse_ail_location(
        self, 
        lines: List[str], 
        field_sep: str, 
        comp_sep: str
    ) -> Optional[str]:
        """Parse AIL segment for location fallback."""
        ail_line = self._find_segment_line(lines, "AIL")
        
        if ail_line:
            ail_data = parse_ail(ail_line, field_sep, comp_sep)
            return ail_data.get("location")
        
        return None

    def parse_messages(self, content: str) -> List[Appointment]:
        """
        Parse multiple messages from content.
        
        Args:
            content: Raw content that may contain multiple HL7 messages
            
        Returns:
            List of Appointment models
            
        Raises:
            HL7ParseError: With message index prefix if any message fails
        """
        messages = self.split_messages(content)
        appointments = []
        
        for index, message in enumerate(messages):
            try:
                appointment = self.parse_message(message)
                appointments.append(appointment)
            except HL7ParseError as error:
                # Re-raise with message index for debugging
                error_message = f"Message {index + 1}: {error}"
                raise type(error)(error_message) from error
        
        return appointments

    def parse_messages_safe(self, content: str) -> List[Dict[str, Any]]:
        """
        Parse multiple messages, collecting errors instead of failing.
        
        Useful for batch processing where you want to continue
        even if some messages are invalid.
        
        Returns:
            List of dicts with keys:
            - success: True if parsed successfully
            - appointment: Appointment model (if success)
            - error: Error message (if failed)
            - index: Message index (0-based)
        """
        messages = self.split_messages(content)
        results = []
        
        for index, message in enumerate(messages):
            try:
                appointment = self.parse_message(message)
                results.append({
                    "success": True,
                    "appointment": appointment,
                    "index": index
                })
            except HL7ParseError as error:
                results.append({
                    "success": False,
                    "error": str(error),
                    "index": index
                })
        
        return results

    def split_messages(self, content: str) -> List[str]:
        """
        Split content into individual HL7 messages.
        
        Each message starts with "MSH" at the beginning of a line.
        This uses structural HL7 rules, not regex pattern matching.
        
        Args:
            content: Raw content that may contain multiple messages
            
        Returns:
            List of individual message strings
        """
        if not content:
            return []
        
        cleaned = content.strip()
        if not cleaned:
            return []
        
        # Normalize line endings
        normalized = cleaned.replace("\r\n", "\n").replace("\r", "\n")
        
        messages = []
        current_message_lines = []
        
        for line in normalized.split("\n"):
            # Check if this line starts a new message
            if line.startswith("MSH"):
                # Save the previous message if we have one
                if current_message_lines:
                    message_text = "\n".join(current_message_lines)
                    messages.append(message_text)
                
                # Start a new message
                current_message_lines = [line]
            elif current_message_lines:
                # We're inside a message, add this line
                current_message_lines.append(line)
            # Ignore lines before the first MSH
        
        # Don't forget the last message
        if current_message_lines:
            message_text = "\n".join(current_message_lines)
            messages.append(message_text)
        
        # Filter out empty messages
        return [msg.strip() for msg in messages if msg.strip()]

    def stream_messages(self, content: str) -> Iterator[Appointment]:
        """
        Generator that yields appointments one at a time.
        
        Useful for processing large files without loading
        all appointments into memory.
        """
        for message in self.split_messages(content):
            yield self.parse_message(message)
