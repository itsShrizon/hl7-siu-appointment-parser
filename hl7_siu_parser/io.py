"""
HL7 SIU Parser - IO Layer

File operations for reading HL7 files and writing JSON output.
Supports both load-all and streaming patterns.
"""
import json
from pathlib import Path
from typing import List, Optional, Union, Iterator
from .models import Appointment
from .exceptions import FileReadError

_ENCODINGS = ["utf-8", "latin-1", "cp1252", "iso-8859-1"]


def read_hl7_file(filepath: Union[str, Path]) -> str:
    """
    Read entire HL7 file into memory.
    
    For large files, consider using stream_hl7_file() instead.
    
    Args:
        filepath: Path to the HL7 file
        
    Returns:
        File contents as string
        
    Raises:
        FileReadError: If file cannot be read
    """
    path = Path(filepath)
    if not path.exists():
        raise FileReadError(str(filepath), "File does not exist")

    for encoding in _ENCODINGS:
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise FileReadError(str(filepath), "Cannot decode file with supported encodings")


def stream_hl7_file(filepath: Union[str, Path], encoding: str = "utf-8") -> Iterator[str]:
    """
    Stream lines from an HL7 file without loading it all into memory.
    
    This is the memory-efficient alternative to read_hl7_file().
    Use with HL7Parser.stream_file() for processing large feeds.
    
    Args:
        filepath: Path to the HL7 file
        encoding: File encoding (default: utf-8)
        
    Yields:
        Lines from the file one at a time
        
    Raises:
        FileReadError: If file cannot be opened
        
    Example:
        for line in stream_hl7_file("large_feed.hl7"):
            process_line(line)
    """
    path = Path(filepath)
    if not path.exists():
        raise FileReadError(str(filepath), "File does not exist")

    try:
        with open(path, 'r', encoding=encoding) as file:
            for line in file:
                yield line
    except UnicodeDecodeError as e:
        raise FileReadError(str(filepath), f"Encoding error: {e}")


def detect_encoding(filepath: Union[str, Path]) -> Optional[str]:
    """
    Detect the encoding of an HL7 file by trying common encodings.
    
    Args:
        filepath: Path to the file
        
    Returns:
        Detected encoding name, or None if detection failed
    """
    path = Path(filepath)
    if not path.exists():
        return None

    for encoding in _ENCODINGS:
        try:
            with open(path, 'r', encoding=encoding) as f:
                f.read(1024)  # Read a small sample
            return encoding
        except UnicodeDecodeError:
            continue
    return None


def write_json_output(
    appointments: List[Appointment],
    output_path: Optional[Union[str, Path]] = None,
    indent: int = 2
) -> Optional[str]:
    """
    Write appointments to JSON file or return as string.
    
    Args:
        appointments: List of Appointment models to serialize
        output_path: If provided, write to file; otherwise return string
        indent: JSON indentation level (default: 2)
        
    Returns:
        JSON string if output_path is None, otherwise None
    """
    data = [appt.model_dump(mode='json', exclude_none=True) for appt in appointments]
    json_str = json.dumps(data, indent=indent, ensure_ascii=False)

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(json_str, encoding="utf-8")
        return None
    return json_str


def stream_json_output(
    appointments: Iterator[Appointment],
    output_path: Union[str, Path],
    indent: int = 2
) -> int:
    """
    Stream appointments to a JSON file one at a time.
    
    Memory-efficient alternative to write_json_output() for large datasets.
    Writes a valid JSON array by handling delimiters correctly.
    
    Args:
        appointments: Iterator of Appointment models
        output_path: Output file path
        indent: JSON indentation level
        
    Returns:
        Number of appointments written
    """
    count = 0
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write("[\n")
        
        for i, appt in enumerate(appointments):
            if i > 0:
                f.write(",\n")
            
            data = appt.model_dump(mode='json', exclude_none=True)
            json_str = json.dumps(data, indent=indent, ensure_ascii=False)
            
            # Indent the object within the array
            indented = "\n".join("  " + line for line in json_str.split("\n"))
            f.write(indented)
            count += 1
        
        f.write("\n]\n")
    
    return count
