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
        super().__init__(message)
    
    def __str__(self):
        """Return clean error message without recursion."""
        parts = [self.message]
        if self.segment:
            parts.append(f"(Segment: {self.segment})")
        if self.field is not None:
            parts.append(f"(Field: {self.field})")
        return " ".join(parts)


class InvalidMessageTypeError(HL7ParseError):
    """
    Raised when the message type is not SIU^S12.
    
    This is NOT necessarily a fatal error - in mixed feeds,
    non-SIU messages should be skipped, not crashed on.
    """
    
    def __init__(self, actual_type: str, expected_type: str = "SIU^S12"):
        self.actual_type = actual_type
        self.expected_type = expected_type
        # Clean, simple message - no recursion
        message = f"Expected {expected_type}, found {actual_type}"
        super().__init__(message)


class MissingSegmentError(HL7ParseError):
    """Raised when a required segment is not found."""
    
    def __init__(self, segment_type: str, required: bool = True):
        self.segment_type = segment_type
        self.required = required
        severity = "Required" if required else "Expected"
        message = f"{severity} segment '{segment_type}' not found"
        super().__init__(message, segment=segment_type)


class MalformedSegmentError(HL7ParseError):
    """Raised when a segment's structure is invalid."""
    
    def __init__(self, segment_type: str, reason: str):
        self.segment_type = segment_type
        self.reason = reason
        message = f"Malformed {segment_type}: {reason}"
        super().__init__(message, segment=segment_type)


class EmptyMessageError(HL7ParseError):
    """Raised when the input message is empty."""
    
    def __init__(self):
        super().__init__("Empty or whitespace-only message")


class FileReadError(HL7ParseError):
    """Raised when there's an issue reading the HL7 file."""
    
    def __init__(self, filepath: str, reason: str):
        self.filepath = filepath
        self.reason = reason
        message = f"Cannot read '{filepath}': {reason}"
        super().__init__(message)
