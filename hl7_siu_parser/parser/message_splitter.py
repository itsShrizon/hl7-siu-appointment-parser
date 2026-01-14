"""
Message Splitter

Handles splitting HL7 content into individual messages.
"""
import sys
from typing import List


class MessageSplitter:
    """
    Splits raw HL7 content into individual messages.
    
    Uses structural validation to identify message boundaries (MSH segments).
    """

    def split(self, content: str) -> List[str]:
        """
        Split content into individual HL7 messages.
        
        Args:
            content: Raw HL7 content (may contain multiple messages)
            
        Returns:
            List of individual message strings
        """
        if not content:
            return []
        
        # Normalize line endings to \n
        normalized = content.replace("\r\n", "\n").replace("\r", "\n")
        
        messages = []
        current_buffer = []
        in_message = False
        line_number = 0
        
        for line in normalized.split("\n"):
            line_number += 1
            line = line.strip()
            
            if not line:
                continue
            
            if line.startswith("MSH"):
                if self._is_valid_msh_start(line):
                    # Save previous message if exists
                    if current_buffer:
                        messages.append("\n".join(current_buffer))
                    
                    # Start new message
                    current_buffer = [line]
                    in_message = True
                else:
                    # Malformed MSH
                    self._warn(f"Line {line_number} looks like MSH but is malformed")
                    if in_message:
                        current_buffer.append(line)
            
            elif in_message:
                current_buffer.append(line)
            else:
                self._warn(f"Line {line_number} found before first valid MSH segment")
        
        # Don't forget the last message
        if current_buffer:
            messages.append("\n".join(current_buffer))
        
        return messages

    def _is_valid_msh_start(self, line: str) -> bool:
        """
        Validate that a line is actually an MSH segment.
        
        Valid MSH structure:
        - Starts with exactly "MSH"
        - Followed by field separator (non-alphanumeric, non-whitespace)
        - Then 4 encoding characters
        - Minimum length of 8
        """
        if not line.startswith("MSH"):
            return False
        
        if len(line) < 8:
            return False
        
        # Character at index 3 should be the field separator
        field_sep = line[3]
        
        # Field separator must not be alphanumeric or whitespace
        if field_sep.isalnum() or field_sep.isspace():
            return False
        
        # Encoding characters (index 4-7) must not be whitespace
        encoding_chars = line[4:8]
        if len(encoding_chars) < 4 or any(c.isspace() for c in encoding_chars):
            return False
        
        return True

    def _warn(self, message: str) -> None:
        """Print warning to stderr."""
        print(f"Warning: {message}", file=sys.stderr)
