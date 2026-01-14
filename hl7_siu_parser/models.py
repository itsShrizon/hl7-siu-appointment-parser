"""
HL7 SIU Parser - Domain Models

Pydantic models with validation logic for data normalization.
"""
from typing import Optional, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime


class Patient(BaseModel):
    """Patient demographic information from PID segment."""
    model_config = ConfigDict(extra='ignore')

    id: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    dob: Optional[str] = Field(default=None, description="ISO 8601 date")
    gender: Optional[str] = None

    @field_validator('dob', mode='before')
    @classmethod
    def normalize_dob(cls, v: Any) -> Optional[str]:
        """Normalize HL7 date (YYYYMMDD) to ISO 8601 (YYYY-MM-DD)."""
        if not v or not isinstance(v, str):
            return None
        date_str = v.strip()[:8]
        if len(date_str) < 8:
            return v
        try:
            return datetime.strptime(date_str, "%Y%m%d").strftime("%Y-%m-%d")
        except ValueError:
            return v


class Provider(BaseModel):
    """Provider/clinician information from PV1 segment."""
    model_config = ConfigDict(extra='ignore')

    id: Optional[str] = None
    name: Optional[str] = None


class Appointment(BaseModel):
    """Scheduled appointment extracted from HL7 SIU S12 message."""
    model_config = ConfigDict(extra='ignore')

    appointment_id: Optional[str] = None
    appointment_datetime: Optional[str] = Field(default=None, description="ISO 8601 datetime")
    patient: Optional[Patient] = None
    provider: Optional[Provider] = None
    location: Optional[str] = None
    reason: Optional[str] = None

    @field_validator('appointment_datetime', mode='before')
    @classmethod
    def normalize_timestamp(cls, v: Any) -> Optional[str]:
        """Convert HL7 timestamp to ISO 8601 format."""
        if not v or not isinstance(v, str):
            return None

        ts = v.strip()
        tz_offset = None

        # Extract timezone (+0500 or -0800)
        if "+" in ts:
            idx = ts.rindex("+")
            tz_offset, ts = ts[idx:], ts[:idx]
        elif len(ts) > 8 and "-" in ts[8:]:
            idx = ts.rindex("-")
            tz_offset, ts = ts[idx:], ts[:idx]

        # Remove fractional seconds
        if "." in ts:
            ts = ts.split(".")[0]

        # Parse datetime
        try:
            if len(ts) >= 14:
                dt = datetime.strptime(ts[:14], "%Y%m%d%H%M%S")
            elif len(ts) >= 12:
                dt = datetime.strptime(ts[:12], "%Y%m%d%H%M")
            elif len(ts) >= 8:
                dt = datetime.strptime(ts[:8], "%Y%m%d")
            else:
                return v
        except ValueError:
            return v

        iso = dt.strftime("%Y-%m-%dT%H:%M:%S")
        if tz_offset:
            # Convert +0500 -> +05:00
            if len(tz_offset) == 5:
                tz_offset = f"{tz_offset[:3]}:{tz_offset[3:]}"
            return iso + tz_offset
        return iso + "Z"


class HL7MessageMetadata(BaseModel):
    """Metadata extracted from MSH segment."""
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
