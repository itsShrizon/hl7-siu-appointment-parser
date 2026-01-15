"""
HL7 Parser - Main Facade

Simple, clean API that delegates to specialized components.
"""
import os
from typing import List, Iterator
from ..models import Appointment
from .message_parser import MessageParser
from .message_splitter import MessageSplitter
from .batch_processor import BatchProcessor
from .parse_result import ParseResult


# Default threshold for switching to streaming (1MB)
DEFAULT_STREAM_THRESHOLD = 1024 * 1024


class HL7Parser:
    """
    Parser for HL7 SIU S12 (Schedule Information Unsolicited) messages.
    
    This is the main entry point. It provides a simple API while
    delegating to specialized components internally.
    
    Example:
        parser = HL7Parser()
        
        # Parse single message
        appointment = parser.parse_message(message)
        
        # Parse file (auto-detects large files and streams)
        appointments = parser.parse_file("messages.hl7")
        
        # Parse multiple messages (fault-tolerant)
        appointments = parser.parse_messages(content)
        
        # Stream from file (memory-efficient)
        for appointment in parser.stream_file("large.hl7"):
            process(appointment)
    """

    def __init__(
        self, 
        strict_mode: bool = False,
        stream_threshold: int = DEFAULT_STREAM_THRESHOLD,
    ):
        """
        Initialize parser.
        
        Args:
            strict_mode: If True, raises errors for missing optional segments.
            stream_threshold: File size in bytes above which streaming is used
                              automatically. Default is 1MB (1048576 bytes).
                              Set to 0 to always stream, or -1 to never auto-stream.
        """
        self.strict_mode = strict_mode
        self.stream_threshold = stream_threshold
        
        # Compose internal components
        self._message_parser = MessageParser(strict_mode=strict_mode)
        self._message_splitter = MessageSplitter()
        self._batch_processor = BatchProcessor(self._message_parser, self._message_splitter)

    # =========================================================================
    # Smart File API (Auto-detects large files)
    # =========================================================================

    def parse_file(
        self, 
        file_path: str, 
        encoding: str = "utf-8",
    ) -> List[Appointment]:
        """
        Parse an HL7 file, automatically using streaming for large files.
        
        Behavior:
        - Files smaller than stream_threshold: loaded into memory (faster for small files)
        - Files larger than stream_threshold: streamed line-by-line (memory efficient)
        
        Args:
            file_path: Path to the HL7 file
            encoding: File encoding (default: utf-8)
            
        Returns:
            List of Appointment objects
            
        Example:
            parser = HL7Parser()
            appointments = parser.parse_file("messages.hl7")
        """
        file_size = os.path.getsize(file_path)
        
        # Decide whether to stream based on file size
        if self.stream_threshold >= 0 and file_size > self.stream_threshold:
            # Large file: use streaming to conserve memory
            return list(self.stream_file(file_path, encoding))
        else:
            # Small file: load into memory for speed
            with open(file_path, "r", encoding=encoding) as f:
                content = f.read()
            return self.parse_messages(content)

    def parse_file_with_report(
        self, 
        file_path: str, 
        encoding: str = "utf-8",
    ) -> ParseResult:
        """
        Parse an HL7 file with detailed reporting.
        
        For large files, streaming is used automatically, but report
        statistics are still collected.
        
        Args:
            file_path: Path to the HL7 file
            encoding: File encoding (default: utf-8)
            
        Returns:
            ParseResult with appointments, skipped, and errors
        """
        file_size = os.path.getsize(file_path)
        
        if self.stream_threshold >= 0 and file_size > self.stream_threshold:
            # Large file: stream with stats tracking
            from .streaming_parser import StreamingParser, StreamStats
            
            streaming_parser = StreamingParser(message_parser=self._message_parser)
            stats = StreamStats()
            appointments = list(streaming_parser.stream_file(file_path, encoding, stats))
            
            return ParseResult(
                appointments=appointments,
                skipped=[{"message_number": i, "message_type": "unknown"} 
                         for i in range(stats.messages_skipped)],
                errors=[{"message_number": i, "error": "parse error"} 
                        for i in range(stats.messages_errored)],
            )
        else:
            # Small file: load into memory
            with open(file_path, "r", encoding=encoding) as f:
                content = f.read()
            return self.parse_messages_with_report(content)

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

