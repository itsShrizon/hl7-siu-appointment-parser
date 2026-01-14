"""
Message Buffer

Accumulates message segments with size limits to prevent memory exhaustion.
"""
from typing import List, Optional
from dataclasses import dataclass, field

# Safety limits to prevent OOM on malformed data
DEFAULT_MAX_SEGMENTS = 500      # Max segments per message
DEFAULT_MAX_SIZE = 1024 * 1024  # 1MB max per message


@dataclass
class MessageBuffer:
    """
    Accumulates HL7 message segments with safety limits.
    
    Prevents memory exhaustion from malformed data:
    - Limits number of segments (default: 500)
    - Limits total message size (default: 1MB)
    
    Example:
        buffer = MessageBuffer()
        buffer.add_line("MSH|^~\\&|...")
        buffer.add_line("PID|...")
        message = buffer.get_message()
        buffer.reset()
    """
    max_segments: int = DEFAULT_MAX_SEGMENTS
    max_size: int = DEFAULT_MAX_SIZE
    
    # Internal state
    _lines: List[str] = field(default_factory=list)
    _total_size: int = 0
    _overflow: bool = False
    _overflow_reason: Optional[str] = None
    
    def add_line(self, line: str) -> bool:
        """
        Add a line to the buffer.
        
        Args:
            line: The segment line to add
            
        Returns:
            True if added successfully, False if limit exceeded
        """
        if self._overflow:
            return False
        
        line_size = len(line)
        
        # Check segment count limit
        if len(self._lines) >= self.max_segments:
            self._overflow = True
            self._overflow_reason = f"Exceeded max segments: {self.max_segments}"
            return False
        
        # Check size limit
        if self._total_size + line_size > self.max_size:
            self._overflow = True
            self._overflow_reason = f"Exceeded max size: {self.max_size} bytes"
            return False
        
        self._lines.append(line)
        self._total_size += line_size
        return True
    
    def get_message(self) -> str:
        """
        Get accumulated message content.
        
        Returns:
            Complete message with segments joined by newlines
        """
        return "\n".join(self._lines)
    
    def reset(self) -> None:
        """Clear buffer for next message."""
        self._lines = []
        self._total_size = 0
        self._overflow = False
        self._overflow_reason = None
    
    @property
    def is_empty(self) -> bool:
        """Check if buffer has no content."""
        return len(self._lines) == 0
    
    @property
    def segment_count(self) -> int:
        """Get current segment count."""
        return len(self._lines)
    
    @property
    def total_size(self) -> int:
        """Get current total size in bytes."""
        return self._total_size
    
    @property
    def has_overflow(self) -> bool:
        """Check if buffer exceeded limits."""
        return self._overflow
    
    @property
    def overflow_reason(self) -> Optional[str]:
        """Get reason for overflow, if any."""
        return self._overflow_reason
    
    def has_msh(self) -> bool:
        """Check if buffer starts with MSH segment."""
        return len(self._lines) > 0 and self._lines[0].startswith("MSH")
