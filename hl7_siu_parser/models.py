"""
HL7 SIU Parser - Domain Models

Pydantic models representing the structured data extracted from HL7 SIU messages.
Includes validation logic for normalization.
"""

from typing import Optional, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime



class Patient(BaseModel):
    """Patient demographic information extracted from PID segment."""
    model_config = ConfigDict(extra='ignore')
    
    id: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    dob: Optional[str] = Field(default=None, description="Date of Birth in ISO 8601 format")
    gender: Optional[str] = None

    @field_validator('dob', mode='before')
    @classmethod
    def normalize_dob(cls, v: Any) -> Optional[str]:
        """Normalize HL7 date string to ISO 8601 date format."""
        if not v or not isinstance(v, str):
            return None
        
        date_str = v.strip()[:8]
        if len(date_str) < 8:
            return v  # Return as-is if too short
        
        try:
            dt = datetime.strptime(date_str, "%Y%m%d")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            return v  # Return as-is if parsing fails


class Provider(BaseModel):
    """Provider/clinician information extracted from PV1 segment."""
    model_config = ConfigDict(extra='ignore')
    
    id: Optional[str] = None
    name: Optional[str] = None


class Appointment(BaseModel):
    """
    Represents a scheduled appointment extracted from an HL7 SIU S12 message.
    """
    model_config = ConfigDict(extra='ignore')

    appointment_id: Optional[str] = None
    appointment_datetime: Optional[str] = Field(default=None, description="ISO 8601 datetime")
    patient: Optional[Patient] = None
    provider: Optional[Provider] = None
    location: Optional[str] = None
    reason: Optional[str] = None
    
    # Internal metadata (excluded from default dictionary export depending on usage)
    message_control_id: Optional[str] = Field(default=None, exclude=True)
    sending_facility: Optional[str] = Field(default=None, exclude=True)

    @field_validator('appointment_datetime', mode='before')
    @classmethod
    def normalize_timestamp(cls, v: Any) -> Optional[str]:
        """
        Convert HL7 timestamp to ISO 8601 format.
        """
        if not v or not isinstance(v, str):
            return None
        
        ts = v.strip()
        
        # Extract timezone if present
        tz_offset = None
        if "+" in ts:
            idx = ts.rindex("+")
            tz_offset = ts[idx:]
            ts = ts[:idx]
        elif len(ts) > 8 and "-" in ts[8:]:
             # Be careful not to match YYYY-MM-DD
            idx = ts.rindex("-")
            tz_offset = ts[idx:]
            ts = ts[:idx]

        # Remove fractional seconds
        if "." in ts:
            ts = ts.split(".")[0]
        
        try:
            if len(ts) >= 14:
                dt = datetime.strptime(ts[:14], "%Y%m%d%H%M%S")
            elif len(ts) >= 12:
                dt = datetime.strptime(ts[:12], "%Y%m%d%H%M")
            elif len(ts) >= 8:
                dt = datetime.strptime(ts[:8], "%Y%m%d")
            else:
                return v # Return invalid format as-is, or could raise ValueError
        except ValueError:
            return v

        # Format ISO
        iso_ts = dt.strftime("%Y-%m-%dT%H:%M:%S")
        
        if tz_offset:
            # Convert +0500 to +05:00
            if len(tz_offset) == 5:
                tz_offset = f"{tz_offset[:3]}:{tz_offset[3:]}"
            return iso_ts + tz_offset
        return iso_ts + (tz_offset if tz_offset else "Z")


class HL7MessageMetadata(BaseModel):
    """
    Metadata extracted from MSH segment.
    """
    model_config = ConfigDict(extra='ignore')

    field_separator: str = "|"
    component_separator: str = "^"
    repetition_separator: str = "~"
    escape_character: str = "\\"
    subcomponent_separator: str = "&"
    
    message_type: Optional[str] = None
    message_control_id: Optional[str] = None
    sending_application: Optional[str] = None
    sending_facility: Optional[str] = None
    receiving_application: Optional[str] = None
    receiving_facility: Optional[str] = None
    message_datetime: Optional[str] = None
    version: Optional[str] = None

    def is_siu_s12(self) -> bool:
        """Check if this is an SIU^S12 message."""
        return bool(self.message_type and self.message_type.upper().startswith("SIU^S12"))
