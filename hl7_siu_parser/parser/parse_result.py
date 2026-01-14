from typing import List, Dict, Any
from ..models import Appointment
from dataclasses import dataclass, field

@dataclass
class ParseResult:
    """
    Result of parsing a batch of messages.
    
    Provides clear separation between successful parses, 
    skipped messages, and actual errors.
    """
    appointments: List[Appointment] = field(default_factory=list)
    skipped: List[Dict[str, Any]] = field(default_factory=list)  # Non-SIU messages
    errors: List[Dict[str, Any]] = field(default_factory=list)   # Parse failures
    
    @property
    def total_processed(self) -> int:
        return len(self.appointments)
    
    @property
    def total_skipped(self) -> int:
        return len(self.skipped)
    
    @property
    def total_errors(self) -> int:
        return len(self.errors)