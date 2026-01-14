"""
HL7 SIU Parser - Segment Handlers

DEPRECATED: This file is maintained for backward compatibility.
New code should import from hl7_siu_parser.segments module directly.

Example:
    from hl7_siu_parser.segments import parse_msh, parse_sch, parse_pid
"""

from .segments import parse_msh, parse_sch, parse_pid, parse_pv1, parse_ail
from .field_utils import (
    get_field_value,
    get_component_value,
    get_first_repetition,
    looks_like_datetime,
    extract_datetime_from_timing
)

__all__ = [
    "parse_msh", "parse_sch", "parse_pid", "parse_pv1", "parse_ail",
    "get_field_value", "get_component_value", "get_first_repetition",
    "looks_like_datetime", "extract_datetime_from_timing"
]
