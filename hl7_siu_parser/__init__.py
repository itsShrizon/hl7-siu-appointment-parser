"""
HL7 SIU Parser - Package initialization
"""

from .models import Patient, Provider, Appointment, HL7MessageMetadata
from .exceptions import (
    HL7ParseError,
    InvalidMessageTypeError,
    MissingSegmentError,
    MalformedSegmentError,
    InvalidTimestampError,
    EmptyMessageError,
    FileReadError,
)
from .parser import HL7Parser

__version__ = "1.0.1"

__all__ = [
    # Models
    "Patient",
    "Provider",
    "Appointment",
    "HL7MessageMetadata",
    # Parser
    "HL7Parser",
    # Exceptions
    "HL7ParseError",
    "InvalidMessageTypeError",
    "MissingSegmentError",
    "MalformedSegmentError",
    "InvalidTimestampError",
    "EmptyMessageError",
    "FileReadError",
]
