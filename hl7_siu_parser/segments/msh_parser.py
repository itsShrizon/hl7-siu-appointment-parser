"""MSH Segment Parser"""
from ..models import HL7MessageMetadata
from ..exceptions import MalformedSegmentError
from ..field_utils import get_field_value


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
