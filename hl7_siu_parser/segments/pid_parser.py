"""PID Segment Parser"""
from ..models import Patient
from ..field_utils import (
    get_field_value,
    get_component_value,
    get_first_repetition
)


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
