"""
HL7 SIU Parser - Segment Handlers

Parsers for individual HL7 segments (MSH, SCH, PID, PV1, AIL).
"""
from typing import List, Dict, Any, Optional
from .models import Patient, Provider, HL7MessageMetadata
from .exceptions import MalformedSegmentError


def _get(fields: List[str], idx: int) -> str:
    """Safe field access. Returns empty string if out of bounds or empty."""
    return fields[idx] if idx < len(fields) and fields[idx] else ""


def _comp(field: str, idx: int, sep: str = "^") -> str:
    """Safe component access within a field."""
    if not field:
        return ""
    parts = field.split(sep)
    return parts[idx] if idx < len(parts) and parts[idx] else ""


def parse_msh(segment: str) -> HL7MessageMetadata:
    """Parse MSH segment. Extracts separators and message metadata."""
    if not segment or not segment.startswith("MSH"):
        raise MalformedSegmentError("MSH", "Segment does not start with 'MSH'")
    if len(segment) < 4:
        raise MalformedSegmentError("MSH", "Segment too short")

    sep = segment[3]  # Field separator is always 4th char
    fields = segment.split(sep)
    if len(fields) < 2:
        raise MalformedSegmentError("MSH", "Cannot extract encoding characters")

    enc = fields[1]
    return HL7MessageMetadata(
        field_separator=sep,
        component_separator=enc[0] if len(enc) > 0 else "^",
        repetition_separator=enc[1] if len(enc) > 1 else "~",
        escape_character=enc[2] if len(enc) > 2 else "\\",
        subcomponent_separator=enc[3] if len(enc) > 3 else "&",
        sending_application=_get(fields, 2),
        sending_facility=_get(fields, 3),
        receiving_application=_get(fields, 4),
        receiving_facility=_get(fields, 5),
        message_datetime=_get(fields, 6),
        message_type=_get(fields, 8),
        message_control_id=_get(fields, 9),
        version=_get(fields, 11),
    )


def parse_sch(segment: str, field_sep: str = "|", comp_sep: str = "^") -> Dict[str, Any]:
    """Parse SCH segment. Returns appointment ID, datetime, reason, location."""
    fields = segment.split(field_sep)

    # SCH-1 (Placer) / SCH-2 (Filler) - prefer Filler
    appt_id = _comp(_get(fields, 2), 0, comp_sep) or _comp(_get(fields, 1), 0, comp_sep)

    # SCH-6: Reason - prefer description (comp 1) over code (comp 0)
    reason_field = _get(fields, 6)
    reason = _comp(reason_field, 1, comp_sep) or _comp(reason_field, 0, comp_sep)

    # SCH-11: Timing - find datetime-like component
    timing = _get(fields, 11)
    appt_dt = None
    if timing:
        for comp in timing.split(comp_sep):
            if len(comp) >= 8 and comp[:8].isdigit():
                appt_dt = comp
                break
        if not appt_dt and len(timing) >= 8 and timing[:8].isdigit():
            appt_dt = timing

    # SCH-23 or SCH-20: Location
    loc = _comp(_get(fields, 23), 0, comp_sep) or _get(fields, 23)
    if not loc:
        loc = _comp(_get(fields, 20), 0, comp_sep) or _get(fields, 20)

    return {
        "appointment_id": appt_id or None,
        "appointment_datetime": appt_dt,
        "reason": reason or None,
        "location": loc or None,
    }


def parse_pid(segment: str, field_sep: str = "|", comp_sep: str = "^") -> Patient:
    """Parse PID segment into Patient model."""
    fields = segment.split(field_sep)

    # PID-3: Patient ID (first repetition, first component)
    pid3 = _get(fields, 3).split("~")[0]
    patient_id = _comp(pid3, 0, comp_sep)

    # PID-5: Name (first repetition)
    pid5 = _get(fields, 5).split("~")[0]
    last_name = _comp(pid5, 0, comp_sep)
    first_name = _comp(pid5, 1, comp_sep)

    return Patient(
        id=patient_id or None,
        first_name=first_name or None,
        last_name=last_name or None,
        dob=_get(fields, 7) or None,
        gender=_get(fields, 8) or None,
    )


def parse_pv1(segment: str, field_sep: str = "|", comp_sep: str = "^") -> Provider:
    """Parse PV1 segment into Provider model."""
    fields = segment.split(field_sep)

    # PV1-7 (Attending) -> PV1-8 (Referring) -> PV1-9 (Consulting) fallback
    doc = _get(fields, 7) or _get(fields, 8) or _get(fields, 9)
    doc = doc.split("~")[0] if doc else ""

    provider_id = _comp(doc, 0, comp_sep)
    family = _comp(doc, 1, comp_sep)
    given = _comp(doc, 2, comp_sep)
    prefix = _comp(doc, 5, comp_sep)

    name_parts = [p for p in [prefix, given, family] if p]
    return Provider(id=provider_id or None, name=" ".join(name_parts) or None)


def parse_ail(segment: str, field_sep: str = "|", comp_sep: str = "^") -> Dict[str, Optional[str]]:
    """Parse AIL segment for location."""
    fields = segment.split(field_sep)
    loc = _comp(_get(fields, 3), 0, comp_sep) or _get(fields, 3)
    return {"location": loc or None}
