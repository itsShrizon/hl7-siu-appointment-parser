"""HL7 SIU Parser - Package API"""
__version__ = "1.1.0"

# Public API
from .models import Patient, Provider, Appointment, HL7MessageMetadata  # noqa: F401
from .parser.hl7Parser import HL7Parser  # noqa: F401
from .parser.parse_result import ParseResult  # noqa: F401
from .exceptions import (  # noqa: F401
    HL7ParseError,
    InvalidMessageTypeError,
    MissingSegmentError,
    MalformedSegmentError,
    EmptyMessageError,
    FileReadError,
)

__all__ = [
    "Patient", "Provider", "Appointment", "HL7MessageMetadata",
    "HL7Parser", "ParseResult",
    "HL7ParseError", "InvalidMessageTypeError", "MissingSegmentError",
    "MalformedSegmentError", "EmptyMessageError", "FileReadError",
]
