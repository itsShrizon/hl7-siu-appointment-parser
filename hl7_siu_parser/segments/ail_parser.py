"""AIL Segment Parser"""
from typing import Dict, Optional
from ..field_utils import get_field_value, get_component_value


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
