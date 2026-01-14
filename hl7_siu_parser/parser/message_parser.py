"""
Message Parser

Handles parsing a single HL7 SIU S12 message into an Appointment model.
"""
from typing import List, Dict, Any, Optional
from ..exceptions import InvalidMessageTypeError, MissingSegmentError, EmptyMessageError
from ..segments import parse_msh, parse_sch, parse_pid, parse_pv1, parse_ail
from ..models import Appointment, Patient, Provider


class MessageParser:
    """
    Parses a single HL7 SIU S12 message into an Appointment model.
    
    Handles segment extraction, validation, and data assembly.
    """

    def __init__(self, strict_mode: bool = False):
        """
        Initialize parser.
        
        Args:
            strict_mode: If True, raises errors for missing optional segments.
        """
        self.strict_mode = strict_mode

    def parse(self, raw_message: str) -> Appointment:
        """
        Parse a single HL7 SIU S12 message.
        
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
        
        cleaned = raw_message.strip()
        if not cleaned:
            raise EmptyMessageError()
        
        # Extract lines
        lines = self._split_into_lines(cleaned)
        if not lines:
            raise EmptyMessageError()
        
        # Find and parse MSH segment
        msh_line = self._find_segment(lines, "MSH")
        if msh_line is None:
            raise MissingSegmentError("MSH", required=True)
        
        # Parse MSH to get metadata and validate message type
        metadata = parse_msh(msh_line)
        
        if not metadata.is_siu_s12():
            actual_type = metadata.message_type if metadata.message_type else "UNKNOWN"
            raise InvalidMessageTypeError(actual_type=actual_type)
        
        # Extract separators for parsing other segments
        field_sep = metadata.field_separator
        comp_sep = metadata.component_separator
        
        # Parse segments
        sch_data = self._parse_sch(lines, field_sep, comp_sep)
        patient = self._parse_pid(lines, field_sep, comp_sep)
        provider = self._parse_pv1(lines, field_sep, comp_sep)
        
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

    def _split_into_lines(self, content: str) -> List[str]:
        """Split content into lines, handling various line endings."""
        normalized = content.replace("\r\n", "\n").replace("\r", "\n")
        return [line.strip() for line in normalized.split("\n") if line.strip()]

    def _find_segment(self, lines: List[str], segment_type: str) -> Optional[str]:
        """Find the first line that matches a segment type."""
        for line in lines:
            if len(line) >= 3 and line[:3].upper() == segment_type.upper():
                return line
        return None

    def _parse_sch(self, lines: List[str], field_sep: str, comp_sep: str) -> Dict[str, Any]:
        """Parse SCH segment if present."""
        sch_line = self._find_segment(lines, "SCH")
        
        if sch_line:
            return parse_sch(sch_line, field_sep, comp_sep)
        
        if self.strict_mode:
            raise MissingSegmentError("SCH", required=True)
        
        return {}

    def _parse_pid(self, lines: List[str], field_sep: str, comp_sep: str) -> Optional[Patient]:
        """Parse PID segment if present."""
        pid_line = self._find_segment(lines, "PID")
        
        if pid_line:
            return parse_pid(pid_line, field_sep, comp_sep)
        
        if self.strict_mode:
            raise MissingSegmentError("PID", required=True)
        
        return None

    def _parse_pv1(self, lines: List[str], field_sep: str, comp_sep: str) -> Optional[Provider]:
        """Parse PV1 segment if present."""
        pv1_line = self._find_segment(lines, "PV1")
        
        if pv1_line:
            return parse_pv1(pv1_line, field_sep, comp_sep)
        
        return None

    def _parse_ail_location(self, lines: List[str], field_sep: str, comp_sep: str) -> Optional[str]:
        """Parse AIL segment for location fallback."""
        ail_line = self._find_segment(lines, "AIL")
        
        if ail_line:
            ail_data = parse_ail(ail_line, field_sep, comp_sep)
            return ail_data.get("location")
        
        return None
