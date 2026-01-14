"""
Batch Processor

Handles processing multiple messages with fault tolerance and streaming.
"""
from typing import List, Iterator
from ..exceptions import HL7ParseError, InvalidMessageTypeError, EmptyMessageError
from ..models import Appointment
from .message_parser import MessageParser
from .message_splitter import MessageSplitter
from .parse_result import ParseResult


class BatchProcessor:
    """
    Processes multiple HL7 messages with fault tolerance.
    
    Features:
    - Filters SIU^S12 messages from mixed feeds
    - Continues after encountering bad messages
    - Provides detailed reporting of skipped/failed messages
    - Supports streaming for memory efficiency
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
        Generator that yields appointments one at a time.
        
        Silently skips non-SIU and malformed messages.
        """
        for message in self.splitter.split(content):
            try:
                yield self.parser.parse(message)
            except HL7ParseError:
                continue

    def stream_file(self, file_path: str, encoding: str = "utf-8") -> Iterator[Appointment]:
        """
        Generator that streams appointments from a file.
        
        Uses line-by-line processing for memory efficiency.
        """
        current_message_lines = []
        
        with open(file_path, 'r', encoding=encoding) as file:
            for line in file:
                line = line.replace("\r\n", "\n").replace("\r", "\n").strip()
                
                if not line:
                    continue
                
                if line.startswith("MSH") and self.splitter._is_valid_msh_start(line):
                    if current_message_lines:
                        message_content = "\n".join(current_message_lines)
                        try:
                            yield self.parser.parse(message_content)
                        except HL7ParseError:
                            pass
                    
                    current_message_lines = [line]
                
                elif current_message_lines:
                    current_message_lines.append(line)
        
        # Last message
        if current_message_lines:
            message_content = "\n".join(current_message_lines)
            try:
                yield self.parser.parse(message_content)
            except HL7ParseError:
                pass
