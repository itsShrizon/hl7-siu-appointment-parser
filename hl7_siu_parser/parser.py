"""
HL7 SIU Parser - Core Parser

Orchestrates message parsing: splitting, validation, segment extraction.
"""
from typing import List, Dict, Iterator, Any
from .models import Appointment
from .exceptions import HL7ParseError, InvalidMessageTypeError, MissingSegmentError, EmptyMessageError
from .segments import parse_msh, parse_sch, parse_pid, parse_pv1, parse_ail


class HL7Parser:
    """Parser for HL7 SIU S12 (Schedule Information Unsolicited) messages."""

    def __init__(self, strict_mode: bool = False):
        self.strict_mode = strict_mode

    def parse_message(self, raw_message: str) -> Appointment:
        """Parse a single HL7 SIU S12 message into an Appointment."""
        if not raw_message or not raw_message.strip():
            raise EmptyMessageError()

        lines = self._normalize_line_endings(raw_message).split("\n")
        lines = [ln.strip() for ln in lines if ln.strip()]
        if not lines:
            raise EmptyMessageError()

        # Validate message type BEFORE parsing other segments (efficiency)
        msh_line = next((ln for ln in lines if ln.startswith("MSH")), None)
        if not msh_line:
            raise MissingSegmentError("MSH", required=True)

        metadata = parse_msh(msh_line)
        if not metadata.is_siu_s12():
            raise InvalidMessageTypeError(metadata.message_type or "UNKNOWN")

        # Now extract all segments with validated separators
        field_sep = metadata.field_separator
        comp_sep = metadata.component_separator
        segments = self._group_segments(lines)

        # Parse remaining segments
        sch_data: Dict[str, Any] = {}
        if "SCH" in segments:
            sch_data = parse_sch(segments["SCH"][0], field_sep, comp_sep)
        elif self.strict_mode:
            raise MissingSegmentError("SCH", required=True)

        patient = None
        if "PID" in segments:
            patient = parse_pid(segments["PID"][0], field_sep, comp_sep)
        elif self.strict_mode:
            raise MissingSegmentError("PID", required=True)

        provider = None
        if "PV1" in segments:
            provider = parse_pv1(segments["PV1"][0], field_sep, comp_sep)

        # Location fallback: SCH -> AIL
        location = sch_data.get("location")
        if not location and "AIL" in segments:
            location = parse_ail(segments["AIL"][0], field_sep, comp_sep).get("location")

        return Appointment(
            appointment_id=sch_data.get("appointment_id"),
            appointment_datetime=sch_data.get("appointment_datetime"),
            patient=patient,
            provider=provider,
            location=location,
            reason=sch_data.get("reason"),
        )

    def parse_messages(self, content: str) -> List[Appointment]:
        """Parse multiple messages from content."""
        appointments = []
        for i, msg in enumerate(self.split_messages(content)):
            try:
                appointments.append(self.parse_message(msg))
            except HL7ParseError as e:
                raise type(e)(f"Message {i + 1}: {e}") from e
        return appointments

    def parse_messages_safe(self, content: str) -> List[Dict[str, Any]]:
        """Parse multiple messages, collecting errors instead of failing."""
        results = []
        for i, msg in enumerate(self.split_messages(content)):
            try:
                results.append({"success": True, "appointment": self.parse_message(msg), "index": i})
            except HL7ParseError as e:
                results.append({"success": False, "error": str(e), "index": i})
        return results

    def split_messages(self, content: str) -> List[str]:
        """Split content into individual HL7 messages (MSH boundary)."""
        if not content or not content.strip():
            return []
        lines = self._normalize_line_endings(content).split("\n")
        messages, current = [], []
        for line in lines:
            if line.startswith("MSH"):
                if current:
                    messages.append("\n".join(current))
                current = [line]
            elif current:
                current.append(line)
        if current:
            messages.append("\n".join(current))
        return [m.strip() for m in messages if m.strip()]

    def stream_messages(self, content: str) -> Iterator[Appointment]:
        """Generator yielding appointments one at a time."""
        for msg in self.split_messages(content):
            yield self.parse_message(msg)

    def _group_segments(self, lines: List[str]) -> Dict[str, List[str]]:
        """Group lines by segment type."""
        segments: Dict[str, List[str]] = {}
        for line in lines:
            if len(line) >= 3:
                segments.setdefault(line[:3].upper(), []).append(line)
        return segments

    def _normalize_line_endings(self, content: str) -> str:
        """Normalize CR/CRLF to LF."""
        return content.replace("\r\n", "\n").replace("\r", "\n")
