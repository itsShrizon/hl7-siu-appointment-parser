"""
HL7 SIU Parser - Segment Handlers

Individual handlers for parsing specific HL7 segments (MSH, SCH, PID, PV1).
Each handler extracts relevant data from raw segment strings.
"""

from typing import List, Dict, Any, Optional
from .models import Patient, Provider, HL7MessageMetadata
from .exceptions import MalformedSegmentError


def safe_get_field(fields: List[str], index: int, default: str = "") -> str:
    """Safe field access."""
    try:
        value = fields[index] if index < len(fields) else default
        return value if value else default
    except (IndexError, TypeError):
        return default


def safe_get_component(
    field_value: str, 
    component_index: int, 
    component_sep: str = "^",
    default: str = ""
) -> str:
    """Safe component access."""
    if not field_value:
        return default
    components = field_value.split(component_sep)
    return safe_get_field(components, component_index, default)


def parse_msh(segment: str) -> HL7MessageMetadata:
    """
    Parse MSH (Message Header) segment.
    Dynamic detection of field separator from 4th character (position 3).
    """
    if not segment or not segment.startswith("MSH"):
        raise MalformedSegmentError("MSH", "Segment does not start with 'MSH'")
    
    if len(segment) < 4:
        raise MalformedSegmentError("MSH", "Segment too short for separator detection")
    
    # Dynamic separator detection: MSH|^~\&|...  -> separator is at index 3
    # MSH-1 IS the separator
    actual_field_sep = segment[3]
    
    fields = segment.split(actual_field_sep)
    
    if len(fields) < 2:
        raise MalformedSegmentError("MSH", "Cannot extract encoding characters")
    
    encoding_chars = fields[1]
    
    component_sep = encoding_chars[0] if len(encoding_chars) > 0 else "^"
    repetition_sep = encoding_chars[1] if len(encoding_chars) > 1 else "~"
    escape_char = encoding_chars[2] if len(encoding_chars) > 2 else "\\"
    subcomponent_sep = encoding_chars[3] if len(encoding_chars) > 3 else "&"
    
    return HL7MessageMetadata(
        field_separator=actual_field_sep,
        component_separator=component_sep,
        repetition_separator=repetition_sep,
        escape_character=escape_char,
        subcomponent_separator=subcomponent_sep,
        sending_application=safe_get_field(fields, 2),
        sending_facility=safe_get_field(fields, 3),
        receiving_application=safe_get_field(fields, 4),
        receiving_facility=safe_get_field(fields, 5),
        message_datetime=safe_get_field(fields, 6),
        message_type=safe_get_field(fields, 8),
        message_control_id=safe_get_field(fields, 9),
        version=safe_get_field(fields, 11),
    )


def parse_sch(
    segment: str, 
    field_sep: str = "|", 
    component_sep: str = "^"
) -> Dict[str, Any]:
    """
    Parse SCH segment. Returns dict (intermediate step before Pydantic model creation).
    """
    fields = segment.split(field_sep)
    
    # SCH-1/SCH-2
    placer_id = safe_get_component(safe_get_field(fields, 1), 0, component_sep)
    filler_id = safe_get_component(safe_get_field(fields, 2), 0, component_sep)
    
    # SCH-6: Reason (index 6 - actually should be parsed from index 6 or 7 depending on logic)
    # Correct HL7: SCH is segment, SCH-1 is index 1.
    # In 'split', "SCH" is index 0. So SCH-6 is fields[6].
    reason_field = safe_get_field(fields, 6)
    reason = safe_get_component(reason_field, 1, component_sep) or \
             safe_get_component(reason_field, 0, component_sep)
    
    # SCH-11: Timing (fields[11])
    timing_field = safe_get_field(fields, 11)
    appointment_datetime = None
    if timing_field:
        # Search components for datetime-like value
        for comp in timing_field.split(component_sep):
            if comp and len(comp) >= 8 and comp[:8].isdigit():
                appointment_datetime = comp
                break
        # Fallback to whole field if no component matched
        if not appointment_datetime and timing_field[:8].isdigit():
            appointment_datetime = timing_field
            
    # SCH-23 or SCH-20
    location_field = safe_get_field(fields, 23)
    location = safe_get_component(location_field, 0, component_sep) or location_field
    if not location:
        location_field = safe_get_field(fields, 20)
        location = safe_get_component(location_field, 0, component_sep) or location_field

    return {
        "appointment_id": filler_id or placer_id or None,
        "appointment_datetime": appointment_datetime,
        "reason": reason or None,
        "location": location or None,
    }


def parse_pid(
    segment: str, 
    field_sep: str = "|", 
    component_sep: str = "^"
) -> Patient:
    """Parse PID segment into Patient model."""
    fields = segment.split(field_sep)
    
    # PID-3
    patient_id_field = safe_get_field(fields, 3)
    first_id = patient_id_field.split("~")[0] if patient_id_field else ""
    patient_id = safe_get_component(first_id, 0, component_sep)
    
    # PID-5
    name_field = safe_get_field(fields, 5)
    first_name_entry = name_field.split("~")[0] if name_field else ""
    last_name = safe_get_component(first_name_entry, 0, component_sep)
    first_name = safe_get_component(first_name_entry, 1, component_sep)
    
    # PID-7
    dob = safe_get_field(fields, 7)
    
    # PID-8
    gender = safe_get_field(fields, 8)
    
    return Patient(
        id=patient_id or None,
        first_name=first_name or None,
        last_name=last_name or None,
        dob=dob or None,
        gender=gender or None,
    )


def parse_pv1(
    segment: str, 
    field_sep: str = "|", 
    component_sep: str = "^"
) -> Provider:
    """Parse PV1 segment into Provider model."""
    fields = segment.split(field_sep)
    
    attending = safe_get_field(fields, 7)
    if not attending:
        attending = safe_get_field(fields, 8)
    if not attending:
        attending = safe_get_field(fields, 9)
    
    first_provider = attending.split("~")[0] if attending else ""
    provider_id = safe_get_component(first_provider, 0, component_sep)
    
    family_name = safe_get_component(first_provider, 1, component_sep)
    given_name = safe_get_component(first_provider, 2, component_sep)
    prefix = safe_get_component(first_provider, 5, component_sep)
    
    name_parts = []
    if prefix: name_parts.append(prefix)
    if given_name: name_parts.append(given_name)
    if family_name: name_parts.append(family_name)
    
    return Provider(
        id=provider_id or None,
        name=" ".join(name_parts) if name_parts else None,
    )


def parse_ail(
    segment: str, 
    field_sep: str = "|", 
    component_sep: str = "^"
) -> Dict[str, Optional[str]]:
    """Parse AIL segment."""
    fields = segment.split(field_sep)
    loc = safe_get_component(safe_get_field(fields, 3), 0, component_sep) or safe_get_field(fields, 3)
    return {"location": loc or None}
