"""
HL7 SIU Parser - Custom Exceptions

Structured exception hierarchy for clear error categorization and fail-fast behavior.
"""


class HL7ParseError(Exception):
    """
    Base exception for all HL7 parsing errors.
    
    All custom exceptions inherit from this for easy catching of any parse error.
    """
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
    """
    Raised when the message type is not SIU^S12.
    
    This is a fatal error - we cannot proceed with parsing a non-SIU message.
    """
    def __init__(self, actual_type: str, expected_type: str = "SIU^S12"):
        self.actual_type = actual_type
        self.expected_type = expected_type
        super().__init__(
            f"Invalid message type: expected '{expected_type}', got '{actual_type}'"
        )


class MissingSegmentError(HL7ParseError):
    """
    Raised when a required segment is not found in the message.
    
    Some segments (like MSH) are always required; others may be optional
    depending on the use case.
    """
    def __init__(self, segment_type: str, required: bool = True):
        self.segment_type = segment_type
        self.required = required
        severity = "Required" if required else "Expected"
        super().__init__(
            f"{severity} segment '{segment_type}' not found in message",
            segment=segment_type
        )


class MalformedSegmentError(HL7ParseError):
    """
    Raised when a segment's structure is invalid or cannot be parsed.
    
    This indicates the segment exists but its content doesn't conform
    to expected HL7 structure.
    """
    def __init__(self, segment_type: str, reason: str, raw_content: str = None):
        self.segment_type = segment_type
        self.reason = reason
        self.raw_content = raw_content
        super().__init__(
            f"Malformed segment '{segment_type}': {reason}",
            segment=segment_type
        )


class InvalidTimestampError(HL7ParseError):
    """
    Raised when an HL7 timestamp cannot be parsed or normalized.
    """
    def __init__(self, timestamp: str, reason: str = "Invalid format"):
        self.timestamp = timestamp
        self.reason = reason
        super().__init__(f"Cannot parse timestamp '{timestamp}': {reason}")


class EmptyMessageError(HL7ParseError):
    """
    Raised when the input message is empty or contains only whitespace.
    """
    def __init__(self):
        super().__init__("Empty or whitespace-only message provided")


class FileReadError(HL7ParseError):
    """
    Raised when there's an issue reading the HL7 file from disk.
    """
    def __init__(self, filepath: str, reason: str):
        self.filepath = filepath
        self.reason = reason
        super().__init__(f"Cannot read file '{filepath}': {reason}")
