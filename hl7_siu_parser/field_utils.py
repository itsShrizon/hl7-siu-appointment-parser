"""
HL7 Field Utilities

Low-level helper functions for safely extracting values from HL7 fields.
Handles edge cases like missing fields, empty values, and malformed data.
"""
from typing import List, Optional


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
        
    Example:
        fields = ["MSH", "^~\\&", "APP", "FAC"]
        get_field_value(fields, 2)  # Returns "APP"
        get_field_value(fields, 99)  # Returns ""
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
    
    Args:
        field: The full field value
        component_index: Zero-based index of the component
        separator: Component separator character (default ^)
        
    Returns:
        The component value, or empty string if not found
        
    Example:
        field = "Doe^John^M"
        get_component_value(field, 0)  # Returns "Doe" (last name)
        get_component_value(field, 1)  # Returns "John" (first name)
        get_component_value(field, 5)  # Returns "" (out of bounds)
    """
    if not field:
        return ""
    
    components = field.split(separator)
    return get_field_value(components, component_index)


def get_first_repetition(field: str, repetition_separator: str = "~") -> str:
    """
    Get the first repetition from a repeating field.
    
    HL7 fields can repeat, separated by ~ (tilde).
    
    Args:
        field: The full field value that may contain repetitions
        repetition_separator: Repetition separator character (default ~)
        
    Returns:
        The first repetition, or empty string if field is empty
        
    Example:
        field = "ID001~ID002~ID003"
        get_first_repetition(field)  # Returns "ID001"
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
    This is a heuristic check, not a full validation.
    
    Args:
        value: String to check
        
    Returns:
        True if the string starts with 8 digits, False otherwise
        
    Examples:
        looks_like_datetime("20250502")         # True (date only)
        looks_like_datetime("20250502130000")   # True (with time)
        looks_like_datetime("20250502130000+0500")  # True (with timezone)
        looks_like_datetime("2025-05-02")       # False (wrong format)
        looks_like_datetime("")                 # False
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
    
    Args:
        timing_field: The raw timing field value
        component_separator: Component separator (usually ^)
        
    Returns:
        The first datetime-like component found, or None
        
    Example:
        timing = "^^^20250502130000^20250502140000"
        extract_datetime_from_timing(timing, "^")  # Returns "20250502130000"
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
