"""
HL7 SIU Parser - Core Parser

Main parsing orchestration for HL7 SIU S12 messages.
Handles message splitting, segment extraction, and data normalization.
"""

from typing import List, Dict, Iterator, Any

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
    """
    
    def __init__(self, strict_mode: bool = False):
        self.strict_mode = strict_mode
    
    def parse_message(self, raw_message: str) -> Appointment:
        """
        Parse a single HL7 SIU S12 message into an Appointment model.
        """
        if not raw_message or not raw_message.strip():
            raise EmptyMessageError()
        
        segments = self._extract_segments(raw_message)
        if not segments:
            raise EmptyMessageError()
        
        # MSH - defines parsing rules
        msh_segments = segments.get("MSH", [])
        if not msh_segments:
            raise MissingSegmentError("MSH", required=True)
        
        metadata = parse_msh(msh_segments[0])
        
        if not metadata.is_siu_s12():
            raise InvalidMessageTypeError(
                actual_type=metadata.message_type or "UNKNOWN",
                expected_type="SIU^S12"
            )
        
        field_sep = metadata.field_separator
        component_sep = metadata.component_separator
        
        # SCH
        sch_data: Dict[str, Any] = {}
        sch_segments = segments.get("SCH", [])
        if sch_segments:
            sch_data = parse_sch(sch_segments[0], field_sep, component_sep)
        elif self.strict_mode:
            raise MissingSegmentError("SCH", required=True)
        
        # PID
        patient = None
        pid_segments = segments.get("PID", [])
        if pid_segments:
            patient = parse_pid(pid_segments[0], field_sep, component_sep)
        elif self.strict_mode:
            raise MissingSegmentError("PID", required=True)
        
        # PV1
        provider = None
        pv1_segments = segments.get("PV1", [])
        if pv1_segments:
            provider = parse_pv1(pv1_segments[0], field_sep, component_sep)
        
        # Location fallback (AIL)
        location = sch_data.get("location")
        if not location:
            ail_segments = segments.get("AIL", [])
            if ail_segments:
                ail_data = parse_ail(ail_segments[0], field_sep, component_sep)
                location = ail_data.get("location")
        
        # Construct Appointment (Pydantic validators handle normalization)
        return Appointment(
            appointment_id=sch_data.get("appointment_id"),
            appointment_datetime=sch_data.get("appointment_datetime"),
            patient=patient,
            provider=provider,
            location=location,
            reason=sch_data.get("reason"),
            message_control_id=metadata.message_control_id,
            sending_facility=metadata.sending_facility,
        )
    
    def parse_messages(self, content: str) -> List[Appointment]:
        """Parse multiple messages from content."""
        messages = self.split_messages(content)
        appointments = []
        for i, msg in enumerate(messages):
            try:
                appointments.append(self.parse_message(msg))
            except HL7ParseError as e:
                raise type(e)(f"Message {i + 1}: {str(e)}") from e
        return appointments
    
    def parse_messages_safe(self, content: str) -> List[Dict[str, Any]]:
        """Parse multiple messages, collecting errors safe-ly."""
        messages = self.split_messages(content)
        results = []
        for i, msg in enumerate(messages):
            try:
                appt = self.parse_message(msg)
                results.append({"success": True, "appointment": appt, "message_index": i})
            except HL7ParseError as e:
                results.append({"success": False, "error": str(e), "message_index": i})
        return results
    
    def split_messages(self, content: str) -> List[str]:
        """Split content into individual HL7 messages using structural parsing."""
        if not content or not content.strip():
            return []
        
        content = self._normalize_line_endings(content)
        messages: List[str] = []
        current_lines: List[str] = []
        
        for line in content.split("\n"):
            # MSH at line start indicates new message boundary
            if line.startswith("MSH"):
                # Save previous message if exists
                if current_lines:
                    messages.append("\n".join(current_lines))
                current_lines = [line]
            elif current_lines:  # Only append if we're inside a message
                current_lines.append(line)
        
        # Don't forget the last message
        if current_lines:
            messages.append("\n".join(current_lines))
        
        return [msg.strip() for msg in messages if msg.strip()]
    
    def stream_messages(self, content: str) -> Iterator[Appointment]:
        """Generator yielding appointments."""
        for msg in self.split_messages(content):
            yield self.parse_message(msg)
    
    def _extract_segments(self, message: str) -> Dict[str, List[str]]:
        """Extract segments from message."""
        message = self._normalize_line_endings(message)
        segments: Dict[str, List[str]] = {}
        for line in message.split("\n"):
            line = line.strip()
            if not line: continue
            if len(line) >= 3:
                stype = line[:3].upper()
                segments.setdefault(stype, []).append(line)
        return segments
    
    def _normalize_line_endings(self, content: str) -> str:
        """Normalize line endings to \n."""
        return content.replace("\r\n", "\n").replace("\r", "\n")
