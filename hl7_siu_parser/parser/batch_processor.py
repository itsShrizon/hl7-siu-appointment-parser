"""
Batch Processor

Handles processing multiple messages with fault tolerance and streaming.
Uses the new industrial-strength StreamingParser for file operations.
"""
from typing import List, Iterator, Optional, Callable
from ..exceptions import HL7ParseError, InvalidMessageTypeError, EmptyMessageError
from ..models import Appointment
from .message_parser import MessageParser
from .message_splitter import MessageSplitter
from .streaming_parser import StreamingParser, StreamStats
from .parse_result import ParseResult


class BatchProcessor:
    """
    Processes multiple HL7 messages with fault tolerance.
    
    Features:
    - Filters SIU^S12 messages from mixed feeds
    - Continues after encountering bad messages
    - Provides detailed reporting of skipped/failed messages
    - Supports streaming for any file size (2KB to 2GB+)
    """

    def __init__(self, parser: MessageParser, splitter: MessageSplitter):
        """
        Initialize batch processor.
        
        Args:
            parser: MessageParser instance for parsing individual messages
            splitter: MessageSplitter instance for splitting content
        """
        self.parser = parser
        self.splitter = splitter
        self._streaming_parser = StreamingParser(message_parser=parser)

    def process(self, content: str) -> List[Appointment]:
        """
        Process messages, returning only successful SIU appointments.
        
        Silently skips non-SIU and malformed messages.
        """
        result = self.process_with_report(content)
        return result.appointments

    def process_with_report(self, content: str) -> ParseResult:
        """
        Process messages with detailed reporting.
        
        Returns:
            ParseResult with appointments, skipped messages, and errors
        """
        result = ParseResult()
        messages = self.splitter.split(content)
        
        for index, message in enumerate(messages):
            message_number = index + 1
            
            try:
                appointment = self.parser.parse(message)
                result.appointments.append(appointment)
                
            except InvalidMessageTypeError as error:
                result.skipped.append({
                    "message_number": message_number,
                    "reason": str(error),
                    "message_type": error.actual_type,
                })
                
            except EmptyMessageError:
                result.skipped.append({
                    "message_number": message_number,
                    "reason": "Empty message",
                    "message_type": None,
                })
                
            except HL7ParseError as error:
                result.errors.append({
                    "message_number": message_number,
                    "error": str(error),
                    "error_type": type(error).__name__,
                })
                
            except Exception as error:
                result.errors.append({
                    "message_number": message_number,
                    "error": f"Unexpected error: {error}",
                    "error_type": type(error).__name__,
                })
        
        return result

    def process_strict(self, content: str) -> List[Appointment]:
        """
        Process messages with strict error handling (fails on first error).
        """
        messages = self.splitter.split(content)
        appointments = []
        
        for index, message in enumerate(messages):
            message_number = index + 1
            try:
                appointment = self.parser.parse(message)
                appointments.append(appointment)
            except HL7ParseError as error:
                raise type(error)(f"Message {message_number}: {error}") from error
        
        return appointments

    def stream(self, content: str) -> Iterator[Appointment]:
        """
        Generator that yields appointments from in-memory content.
        
        Silently skips non-SIU and malformed messages.
        """
        return self._streaming_parser.stream_content(content)

    def stream_file(
        self,
        file_path: str,
        encoding: str = "utf-8",
        on_error: Optional[Callable[[int, str], None]] = None,
    ) -> Iterator[Appointment]:
        """
        Generator that streams appointments from a file.
        
        Uses industrial-strength streaming:
        - Constant memory regardless of file size
        - 64KB chunked reading
        - State machine for robust parsing
        - Size limits to prevent OOM
        
        Args:
            file_path: Path to the HL7 file
            encoding: File encoding
            on_error: Optional callback for errors (line_number, error_msg)
        """
        return self._streaming_parser.stream_file(file_path, encoding, on_error=on_error)
    
    def stream_file_with_stats(
        self,
        file_path: str,
        encoding: str = "utf-8",
    ) -> tuple[Iterator[Appointment], StreamStats]:
        """
        Stream file with statistics tracking.
        
        Returns:
            Tuple of (appointment iterator, stats object)
            
        Example:
            appointments, stats = processor.stream_file_with_stats("large.hl7")
            for appt in appointments:
                process(appt)
            print(f"Parsed {stats.messages_parsed} messages")
        """
        stats = StreamStats()
        iterator = self._streaming_parser.stream_file(file_path, encoding, stats=stats)
        return iterator, stats
