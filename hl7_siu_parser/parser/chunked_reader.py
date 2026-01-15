"""
Chunked File Reader

Memory-efficient file reading using fixed-size chunks.
Handles line splitting across chunk boundaries.
"""
from typing import Iterator
from pathlib import Path

# Default chunk size: 64KB is optimal for most file systems
DEFAULT_CHUNK_SIZE = 64 * 1024  # 64KB


class ChunkedReader:
    """
    Reads files in fixed-size chunks and yields complete lines.
    
    Memory efficient: never loads entire file into memory.
    Handles lines that span chunk boundaries correctly.
    
    Example:
        reader = ChunkedReader("large_file.hl7")
        for line_number, line in reader.read_lines():
            process(line)
    """
    
    def __init__(
        self, 
        file_path: str, 
        encoding: str = "utf-8",
        chunk_size: int = DEFAULT_CHUNK_SIZE
    ):
        """
        Initialize chunked reader.
        
        Args:
            file_path: Path to the file
            encoding: File encoding (default: utf-8)
            chunk_size: Size of chunks to read (default: 64KB)
        """
        self.file_path = Path(file_path)
        self.encoding = encoding
        self.chunk_size = chunk_size
        
        if not self.file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
    
    def read_lines(self) -> Iterator[tuple[int, str]]:
        """
        Generator that yields (line_number, line) tuples.
        
        Lines are yielded without trailing newlines.
        Handles CR, LF, and CRLF line endings.
        
        Yields:
            Tuple of (1-based line number, stripped line content)
        """
        line_number = 0
        partial_line = ""
        
        with open(self.file_path, 'r', encoding=self.encoding) as file:
            while True:
                chunk = file.read(self.chunk_size)
                
                if not chunk:
                    # EOF reached - yield any remaining partial line
                    if partial_line.strip():
                        line_number += 1
                        yield line_number, partial_line.strip()
                    break
                
                # Combine with any partial line from previous chunk
                data = partial_line + chunk
                
                # Normalize line endings
                data = data.replace("\r\n", "\n").replace("\r", "\n")
                
                # Split into lines
                lines = data.split("\n")
                
                # Last element might be incomplete (no newline yet)
                partial_line = lines.pop()
                
                # Yield complete lines
                for line in lines:
                    stripped = line.strip()
                    if stripped:  # Skip empty lines
                        line_number += 1
                        yield line_number, stripped
    
    def get_file_size(self) -> int:
        """Return file size in bytes."""
        return self.file_path.stat().st_size
    
    def estimate_line_count(self, sample_size: int = 10000) -> int:
        """
        Estimate total line count based on sample.
        
        Useful for progress reporting on large files.
        """
        file_size = self.get_file_size()
        if file_size == 0:
            return 0
        
        # Read sample and count lines
        sample_lines = 0
        sample_bytes = 0
        
        with open(self.file_path, 'r', encoding=self.encoding) as f:
            for line in f:
                sample_lines += 1
                sample_bytes += len(line)
                if sample_bytes >= sample_size:
                    break
        
        if sample_bytes == 0:
            return 0
        
        # Estimate based on sample ratio
        return int((file_size / sample_bytes) * sample_lines)
