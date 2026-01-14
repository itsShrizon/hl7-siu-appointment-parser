"""
HL7 SIU Parser - Custom Exceptions

Structured exception hierarchy for clear error categorization.
"""


class HL7ParseError(Exception):
    """Base exception for all HL7 parsing errors."""
    def __init__(self, message: str, segment: str = None, field: int = None):
        self.segment = segment
        self.field = field
        self.message = message
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        parts = [self.message]
        if self.segment:
            parts.append(f"Segment: {self.segment}")
        if self.field is not None:
            parts.append(f"Field: {self.field}")
        return " | ".join(parts)


class InvalidMessageTypeError(HL7ParseError):
    """Raised when the message type is not SIU^S12."""
    def __init__(self, actual_type: str, expected_type: str = "SIU^S12"):
        self.actual_type = actual_type
        self.expected_type = expected_type
        super().__init__(f"Invalid message type: expected '{expected_type}', got '{actual_type}'")


class MissingSegmentError(HL7ParseError):
    """Raised when a required segment is not found."""
    def __init__(self, segment_type: str, required: bool = True):
        self.segment_type = segment_type
        severity = "Required" if required else "Expected"
        super().__init__(f"{severity} segment '{segment_type}' not found", segment=segment_type)


class MalformedSegmentError(HL7ParseError):
    """Raised when a segment's structure is invalid."""
    def __init__(self, segment_type: str, reason: str):
        self.segment_type = segment_type
        self.reason = reason
        super().__init__(f"Malformed segment '{segment_type}': {reason}", segment=segment_type)


class EmptyMessageError(HL7ParseError):
    """Raised when the input message is empty."""
    def __init__(self):
        super().__init__("Empty or whitespace-only message provided")


class FileReadError(HL7ParseError):
    """Raised when there's an issue reading the HL7 file."""
    def __init__(self, filepath: str, reason: str):
        self.filepath = filepath
        self.reason = reason
        super().__init__(f"Cannot read file '{filepath}': {reason}")
