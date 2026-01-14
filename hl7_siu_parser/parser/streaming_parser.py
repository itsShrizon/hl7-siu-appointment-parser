"""
Streaming Parser

Industrial-strength streaming parser for HL7 files of any size.
Uses state machine, chunked reading, and size-limited buffers.
"""
from typing import Iterator, Optional, Callable
from dataclasses import dataclass
from ..models import Appointment
from ..exceptions import HL7ParseError
from .parser_state import ParserState, ParseContext
from .chunked_reader import ChunkedReader
from .message_buffer import MessageBuffer
from .message_parser import MessageParser
from .message_splitter import MessageSplitter


@dataclass
class StreamStats:
    """Statistics from streaming parse operation."""
    total_lines: int = 0
    messages_found: int = 0
    messages_parsed: int = 0
    messages_skipped: int = 0
    messages_errored: int = 0
    buffer_overflows: int = 0


class StreamingParser:
    """
    Industrial-strength streaming parser for HL7 files.
    
    Features:
    - Constant memory usage regardless of file size
    - Handles 2KB to 2GB+ files
    - State machine for robust parsing
    - Size limits to prevent OOM
    - Fail-safe error recovery
    
    Example:
        parser = StreamingParser()
        
        # Stream from file
        for appointment in parser.stream_file("large.hl7"):
            process(appointment)
        
        # With statistics
        stats = StreamStats()
        for appointment in parser.stream_file("large.hl7", stats=stats):
            process(appointment)
        print(f"Parsed {stats.messages_parsed} of {stats.messages_found}")
    """
    
    def __init__(
        self,
        message_parser: Optional[MessageParser] = None,
        max_segments: int = 500,
        max_message_size: int = 1024 * 1024,  # 1MB
        chunk_size: int = 64 * 1024,  # 64KB
    ):
        """
        Initialize streaming parser.
        
        Args:
            message_parser: Parser for individual messages (created if None)
            max_segments: Max segments per message (default: 500)
            max_message_size: Max bytes per message (default: 1MB)
            chunk_size: File read chunk size (default: 64KB)
        """
        self.message_parser = message_parser or MessageParser()
        self.max_segments = max_segments
        self.max_message_size = max_message_size
        self.chunk_size = chunk_size
        self._splitter = MessageSplitter()
    
    def stream_file(
        self,
        file_path: str,
        encoding: str = "utf-8",
        stats: Optional[StreamStats] = None,
        on_error: Optional[Callable[[int, str], None]] = None,
    ) -> Iterator[Appointment]:
        """
        Stream appointments from a file.
        
        Memory efficient: reads in chunks, processes one message at a time.
        
        Args:
            file_path: Path to the HL7 file
            encoding: File encoding (default: utf-8)
            stats: Optional stats object to populate
            on_error: Optional callback for errors (line_number, error_message)
            
        Yields:
            Appointment objects one at a time
        """
        if stats is None:
            stats = StreamStats()
        
        # Initialize components
        reader = ChunkedReader(file_path, encoding, self.chunk_size)
        buffer = MessageBuffer(self.max_segments, self.max_message_size)
        context = ParseContext()
        
        for line_number, line in reader.read_lines():
            stats.total_lines += 1
            context.line_number = line_number
            
            # Check if this line starts a new message
            is_msh = line.startswith("MSH") and self._splitter._is_valid_msh_start(line)
            
            if is_msh:
                # First, yield any pending message
                if not buffer.is_empty:
                    yield from self._finalize_message(buffer, context, stats, on_error)
                
                # Start new message
                buffer.reset()
                context.start_new_message()
                buffer.add_line(line)
                stats.messages_found += 1
            
            elif context.state == ParserState.IN_MESSAGE:
                # Add to current message
                if not buffer.add_line(line):
                    # Buffer overflow - skip this message
                    stats.buffer_overflows += 1
                    if on_error:
                        on_error(line_number, buffer.overflow_reason or "Buffer overflow")
                    buffer.reset()
                    context.enter_error("Buffer overflow")
            
            elif context.state == ParserState.ERROR:
                # Skip lines until next MSH
                pass
            
            # IDLE state: ignore lines before first MSH
        
        # Don't forget the last message
        if not buffer.is_empty:
            yield from self._finalize_message(buffer, context, stats, on_error)
    
    def _finalize_message(
        self,
        buffer: MessageBuffer,
        context: ParseContext,
        stats: StreamStats,
        on_error: Optional[Callable[[int, str], None]],
    ) -> Iterator[Appointment]:
        """Parse completed message buffer and yield appointment if valid."""
        if buffer.has_overflow:
            stats.messages_errored += 1
            context.recover_from_error()
            return
        
        message_content = buffer.get_message()
        
        try:
            appointment = self.message_parser.parse(message_content)
            stats.messages_parsed += 1
            context.complete_message()
            yield appointment
            
        except HL7ParseError as e:
            # Check if it's a non-SIU message (skip silently)
            error_msg = str(e)
            if "Expected SIU^S12" in error_msg:
                stats.messages_skipped += 1
            else:
                stats.messages_errored += 1
                if on_error:
                    on_error(context.message_start_line, error_msg)
            
            context.recover_from_error()
        
        except Exception as e:
            stats.messages_errored += 1
            if on_error:
                on_error(context.message_start_line, f"Unexpected: {e}")
            context.recover_from_error()
    
    def stream_content(
        self,
        content: str,
        stats: Optional[StreamStats] = None,
    ) -> Iterator[Appointment]:
        """
        Stream appointments from in-memory content.
        
        For file-based streaming, use stream_file() instead.
        """
        if stats is None:
            stats = StreamStats()
        
        # Use splitter for in-memory content
        messages = self._splitter.split(content)
        stats.messages_found = len(messages)
        
        for message in messages:
            stats.total_lines += message.count("\n") + 1
            
            try:
                appointment = self.message_parser.parse(message)
                stats.messages_parsed += 1
                yield appointment
                
            except HL7ParseError as e:
                if "Expected SIU^S12" in str(e):
                    stats.messages_skipped += 1
                else:
                    stats.messages_errored += 1
