"""PV1 Segment Parser"""
from ..models import Provider
from ..field_utils import (
    get_field_value,
    get_component_value,
    get_first_repetition
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
