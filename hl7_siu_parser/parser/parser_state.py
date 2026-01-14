"""
Parser State Machine

Defines parsing states and transitions for robust message handling.
"""
from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional


class ParserState(Enum):
    """
    States for the streaming parser state machine.
    
    State transitions:
        IDLE → IN_MESSAGE (on valid MSH)
        IN_MESSAGE → IDLE (on next MSH or EOF)
        IN_MESSAGE → ERROR (on validation failure)
        ERROR → IDLE (after error handling)
    """
    IDLE = auto()           # Waiting for first MSH
    IN_MESSAGE = auto()     # Accumulating message segments
    ERROR = auto()          # Error occurred, recovering


@dataclass
class ParseContext:
    """
    Tracks current parsing context.
    
    Maintains state across chunk boundaries for streaming.
    """
    state: ParserState = ParserState.IDLE
    line_number: int = 0
    message_start_line: int = 0
    current_segment_count: int = 0
    current_message_size: int = 0
    last_error: Optional[str] = None
    
    def reset_message(self) -> None:
        """Reset message-specific counters."""
        self.current_segment_count = 0
        self.current_message_size = 0
        self.last_error = None
    
    def start_new_message(self) -> None:
        """Transition to IN_MESSAGE state."""
        self.state = ParserState.IN_MESSAGE
        self.message_start_line = self.line_number
        self.reset_message()
    
    def complete_message(self) -> None:
        """Transition back to IDLE after completing a message."""
        self.state = ParserState.IDLE
        self.reset_message()
    
    def enter_error(self, error: str) -> None:
        """Transition to ERROR state."""
        self.state = ParserState.ERROR
        self.last_error = error
    
    def recover_from_error(self) -> None:
        """Recover from error, transition to IDLE."""
        self.state = ParserState.IDLE
        self.reset_message()
