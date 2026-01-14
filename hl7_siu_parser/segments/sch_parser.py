"""SCH Segment Parser"""
from typing import Dict, Any
from ..field_utils import (
    get_field_value,
    get_component_value,
    extract_datetime_from_timing
)


def parse_sch(
    segment: str, 
    field_separator: str = "|", 
    component_separator: str = "^"
) -> Dict[str, Any]:
    """
    Parse SCH (Schedule Activity) segment.
    
    Extracts:
    - SCH-1: Placer Appointment ID
    - SCH-2: Filler Appointment ID (preferred)
    - SCH-6: Event Reason
    - SCH-11: Appointment Timing
    - SCH-23: Filler Contact Location (fallback to SCH-20)
    
    Returns:
        Dictionary with appointment_id, appointment_datetime, reason, location
    """
    fields = segment.split(field_separator)
    
    # Extract appointment ID - prefer Filler (SCH-2), fallback to Placer (SCH-1)
    placer_id_field = get_field_value(fields, 1)
    filler_id_field = get_field_value(fields, 2)
    
    placer_id = get_component_value(placer_id_field, 0, component_separator)
    filler_id = get_component_value(filler_id_field, 0, component_separator)
    
    # Prefer filler ID if available
    if filler_id:
        appointment_id = filler_id
    elif placer_id:
        appointment_id = placer_id
    else:
        appointment_id = None
    
    # Extract reason - SCH-6 is a coded element (code^description)
    # We prefer the description (component 1), fallback to code (component 0)
    reason_field = get_field_value(fields, 6)
    reason_description = get_component_value(reason_field, 1, component_separator)
    reason_code = get_component_value(reason_field, 0, component_separator)
    
    if reason_description:
        reason = reason_description
    elif reason_code:
        reason = reason_code
    else:
        reason = None
    
    # Extract appointment datetime from timing field (SCH-11)
    timing_field = get_field_value(fields, 11)
    appointment_datetime = extract_datetime_from_timing(timing_field, component_separator)
    
    # Extract location - try SCH-23 first, then SCH-20
    location_field_23 = get_field_value(fields, 23)
    location_field_20 = get_field_value(fields, 20)
    
    location = get_component_value(location_field_23, 0, component_separator)
    if not location:
        location = location_field_23  # Use full field if no component
    if not location:
        location = get_component_value(location_field_20, 0, component_separator)
    if not location:
        location = location_field_20
    if not location:
        location = None
    
    return {
        "appointment_id": appointment_id,
        "appointment_datetime": appointment_datetime,
        "reason": reason,
        "location": location,
    }
