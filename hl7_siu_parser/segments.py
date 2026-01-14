"""
HL7 SIU Parser - Segment Handlers

Parsers for individual HL7 segments (MSH, SCH, PID, PV1, AIL).
Each function extracts structured data from raw segment strings.
"""
from typing import List, Dict, Any, Optional
from .models import Patient, Provider, HL7MessageMetadata
from .exceptions import MalformedSegmentError


def get_field_value(fields: List[str], index: int) -> str:
    """
    Safely retrieve a field value from a list of fields.
    
    Args:
        fields: List of field values from splitting a segment
        index: Zero-based index of the field to retrieve
        
    Returns:
        The field value as a string, or empty string if:
        - Index is out of bounds
        - Field value is None or empty
    """
    if index < 0 or index >= len(fields):
        return ""
    
    value = fields[index]
    if value is None:
        return ""
    
    return value


def get_component_value(field: str, component_index: int, separator: str = "^") -> str:
    """
    Safely retrieve a component value from a field.
    
    HL7 fields can contain multiple components separated by ^ (or custom separator).
    Example: "LastName^FirstName^MiddleName" -> component 1 is "FirstName"
    
    Args:
        field: The full field value
        component_index: Zero-based index of the component
        separator: Component separator character (default ^)
        
    Returns:
        The component value, or empty string if not found
    """
    if not field:
        return ""
    
    components = field.split(separator)
    return get_field_value(components, component_index)


def get_first_repetition(field: str, repetition_separator: str = "~") -> str:
    """
    Get the first repetition from a repeating field.
    
    HL7 fields can repeat, separated by ~ (tilde).
    Example: "ID1~ID2~ID3" -> returns "ID1"
    """
    if not field:
        return ""
    
    parts = field.split(repetition_separator)
    if parts:
        return parts[0]
    return ""


def looks_like_datetime(value: str) -> bool:
    """
    Check if a string looks like an HL7 datetime.
    
    HL7 datetimes start with 8+ digits representing YYYYMMDD.
    Examples that should return True:
        - "20250502" (date only)
        - "20250502130000" (with time)
        - "20250502130000+0500" (with timezone)
    """
    if not value:
        return False
    
    if len(value) < 8:
        return False
    
    date_portion = value[:8]
    return date_portion.isdigit()


def extract_datetime_from_timing(timing_field: str, component_separator: str) -> Optional[str]:
    """
    Extract a datetime value from a timing field.
    
    The timing field (SCH-11) can have various formats:
    - Simple datetime: "20250502130000"
    - Component-based: "^^^20250502130000^20250502140000"
    
    We search through components to find one that looks like a datetime.
    """
    if not timing_field:
        return None
    
    # First, check if the entire field is a datetime
    if looks_like_datetime(timing_field):
        return timing_field
    
    # Otherwise, search components for a datetime-like value
    components = timing_field.split(component_separator)
    for component in components:
        if looks_like_datetime(component):
            return component
    
    return None


def parse_msh(segment: str) -> HL7MessageMetadata:
    """
    Parse MSH (Message Header) segment.
    
    The MSH segment is special:
    - The 4th character (index 3) IS the field separator
    - MSH-1 is the field separator itself
    - MSH-2 contains encoding characters (^~\\&)
    
    Args:
        segment: Raw MSH segment string
        
    Returns:
        HL7MessageMetadata with extracted values
        
    Raises:
        MalformedSegmentError: If segment structure is invalid
    """
    # Validate segment starts with MSH
    if not segment:
        raise MalformedSegmentError("MSH", "Segment is empty")
    
    if not segment.startswith("MSH"):
        raise MalformedSegmentError("MSH", "Segment does not start with 'MSH'")
    
    if len(segment) < 4:
        raise MalformedSegmentError("MSH", "Segment too short to contain field separator")
    
    # The field separator is always the 4th character
    field_separator = segment[3]
    
    # Split the segment by the field separator
    fields = segment.split(field_separator)
    
    if len(fields) < 2:
        raise MalformedSegmentError("MSH", "Cannot extract encoding characters")
    
    # MSH-2 contains encoding characters
    encoding_chars = fields[1]
    
    # Extract encoding characters with defaults
    component_sep = encoding_chars[0] if len(encoding_chars) > 0 else "^"
    repetition_sep = encoding_chars[1] if len(encoding_chars) > 1 else "~"
    escape_char = encoding_chars[2] if len(encoding_chars) > 2 else "\\"
    subcomponent_sep = encoding_chars[3] if len(encoding_chars) > 3 else "&"
    
    return HL7MessageMetadata(
        field_separator=field_separator,
        component_separator=component_sep,
        repetition_separator=repetition_sep,
        escape_character=escape_char,
        subcomponent_separator=subcomponent_sep,
        sending_application=get_field_value(fields, 2),
        sending_facility=get_field_value(fields, 3),
        receiving_application=get_field_value(fields, 4),
        receiving_facility=get_field_value(fields, 5),
        message_datetime=get_field_value(fields, 6),
        message_type=get_field_value(fields, 8),
        message_control_id=get_field_value(fields, 9),
        version=get_field_value(fields, 11),
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


def parse_pid(
    segment: str, 
    field_separator: str = "|", 
    component_separator: str = "^"
) -> Patient:
    """
    Parse PID (Patient Identification) segment.
    
    Extracts:
    - PID-3: Patient Identifier List
    - PID-5: Patient Name
    - PID-7: Date of Birth
    - PID-8: Administrative Sex
    
    Returns:
        Patient model with extracted data
    """
    fields = segment.split(field_separator)
    
    # PID-3: Patient ID (may have repetitions, take first)
    patient_id_field = get_field_value(fields, 3)
    first_patient_id = get_first_repetition(patient_id_field)
    patient_id = get_component_value(first_patient_id, 0, component_separator)
    
    # PID-5: Patient Name (Family^Given^Middle^Suffix^Prefix)
    name_field = get_field_value(fields, 5)
    first_name_entry = get_first_repetition(name_field)
    
    last_name = get_component_value(first_name_entry, 0, component_separator)
    first_name = get_component_value(first_name_entry, 1, component_separator)
    
    # PID-7: Date of Birth
    dob = get_field_value(fields, 7)
    
    # PID-8: Gender
    gender = get_field_value(fields, 8)
    
    return Patient(
        id=patient_id if patient_id else None,
        first_name=first_name if first_name else None,
        last_name=last_name if last_name else None,
        dob=dob if dob else None,
        gender=gender if gender else None,
    )


def parse_pv1(
    segment: str, 
    field_separator: str = "|", 
    component_separator: str = "^"
) -> Provider:
    """
    Parse PV1 (Patient Visit) segment.
    
    Extracts provider from:
    - PV1-7: Attending Doctor (primary)
    - PV1-8: Referring Doctor (fallback)
    - PV1-9: Consulting Doctor (fallback)
    
    Returns:
        Provider model with extracted data
    """
    fields = segment.split(field_separator)
    
    # Try to find a provider - prioritize attending, then referring, then consulting
    attending_field = get_field_value(fields, 7)
    referring_field = get_field_value(fields, 8)
    consulting_field = get_field_value(fields, 9)
    
    # Use the first non-empty provider field
    if attending_field:
        provider_field = attending_field
    elif referring_field:
        provider_field = referring_field
    elif consulting_field:
        provider_field = consulting_field
    else:
        provider_field = ""
    
    # Get first repetition (in case of multiple providers)
    provider_entry = get_first_repetition(provider_field)
    
    # Extract components: ID^FamilyName^GivenName^Middle^Suffix^Prefix
    provider_id = get_component_value(provider_entry, 0, component_separator)
    family_name = get_component_value(provider_entry, 1, component_separator)
    given_name = get_component_value(provider_entry, 2, component_separator)
    prefix = get_component_value(provider_entry, 5, component_separator)
    
    # Build provider name
    name_parts = []
    if prefix:
        name_parts.append(prefix)
    if given_name:
        name_parts.append(given_name)
    if family_name:
        name_parts.append(family_name)
    
    provider_name = " ".join(name_parts) if name_parts else None
    
    return Provider(
        id=provider_id if provider_id else None,
        name=provider_name,
    )


def parse_ail(
    segment: str, 
    field_separator: str = "|", 
    component_separator: str = "^"
) -> Dict[str, Optional[str]]:
    """
    Parse AIL (Appointment Information - Location) segment.
    
    Extracts:
    - AIL-3: Location Resource ID
    
    Returns:
        Dictionary with location
    """
    fields = segment.split(field_separator)
    
    location_field = get_field_value(fields, 3)
    location = get_component_value(location_field, 0, component_separator)
    
    if not location:
        location = location_field
    
    return {
        "location": location if location else None
    }
