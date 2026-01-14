"""
HL7 Parser - Main Facade

Simple, clean API that delegates to specialized components.
"""
from typing import List, Iterator
from ..models import Appointment
from .message_parser import MessageParser
from .message_splitter import MessageSplitter
from .batch_processor import BatchProcessor
from .parse_result import ParseResult


class HL7Parser:
    """
    Parser for HL7 SIU S12 (Schedule Information Unsolicited) messages.
    
    This is the main entry point. It provides a simple API while
    delegating to specialized components internally.
    
    Example:
        parser = HL7Parser()
        
        # Parse single message
        appointment = parser.parse_message(message)
        
        # Parse multiple messages (fault-tolerant)
        appointments = parser.parse_messages(content)
        
        # Stream from file (memory-efficient)
        for appointment in parser.stream_file("large.hl7"):
            process(appointment)
    """

    def __init__(self, strict_mode: bool = False):
        """
        Initialize parser.
        
        Args:
            strict_mode: If True, raises errors for missing optional segments.
        """
        self.strict_mode = strict_mode
        
        # Compose internal components
        self._message_parser = MessageParser(strict_mode=strict_mode)
        self._message_splitter = MessageSplitter()
        self._batch_processor = BatchProcessor(self._message_parser, self._message_splitter)

    # =========================================================================
    # Single Message API
    # =========================================================================

    def parse_message(self, raw_message: str) -> Appointment:
        """
        Parse a single HL7 SIU S12 message.
        
        Raises:
            EmptyMessageError: If message is empty
            MissingSegmentError: If required segment is missing
            InvalidMessageTypeError: If not an SIU^S12 message
        """
        return self._message_parser.parse(raw_message)

    # =========================================================================
    # Batch Processing API
    # =========================================================================

    def parse_messages(self, content: str) -> List[Appointment]:
        """
        Parse multiple messages, filtering for SIU^S12 only.
        
        Fault-tolerant: skips non-SIU and malformed messages silently.
        """
        return self._batch_processor.process(content)

    def parse_messages_with_report(self, content: str) -> ParseResult:
        """
        Parse multiple messages with detailed reporting.
        
        Returns ParseResult with appointments, skipped, and errors.
        """
        return self._batch_processor.process_with_report(content)

    def parse_messages_strict(self, content: str) -> List[Appointment]:
        """
        Parse multiple messages with strict error handling.
        
        Fails on first error. Use only for clean SIU-only files.
        """
        return self._batch_processor.process_strict(content)

    # =========================================================================
    # Streaming API
    # =========================================================================

    def stream_messages(self, content: str) -> Iterator[Appointment]:
        """
        Generator that yields appointments from in-memory content.
        """
        return self._batch_processor.stream(content)

    def stream_file(self, file_path: str, encoding: str = "utf-8") -> Iterator[Appointment]:
        """
        Generator that streams appointments from a file.
        
        Memory-efficient: reads file line-by-line.
        """
        return self._batch_processor.stream_file(file_path, encoding)

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def split_messages(self, content: str) -> List[str]:
        """
        Split content into individual message strings.
        """
        return self._message_splitter.split(content)
