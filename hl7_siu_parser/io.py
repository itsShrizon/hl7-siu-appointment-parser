"""
HL7 SIU Parser - IO Layer

File operations for reading HL7 files and writing JSON output.
"""
import json
from pathlib import Path
from typing import List, Optional, Union
from .models import Appointment
from .exceptions import FileReadError

_ENCODINGS = ["utf-8", "latin-1", "cp1252", "iso-8859-1"]


def read_hl7_file(filepath: Union[str, Path]) -> str:
    """Read HL7 file with automatic encoding detection."""
    path = Path(filepath)
    if not path.exists():
        raise FileReadError(str(filepath), "File does not exist")

    for encoding in _ENCODINGS:
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise FileReadError(str(filepath), "Cannot decode file with supported encodings")


def write_json_output(
    appointments: List[Appointment],
    output_path: Optional[Union[str, Path]] = None,
    indent: int = 2
) -> Optional[str]:
    """Write appointments to JSON file or return as string."""
    data = [appt.model_dump(mode='json', exclude_none=True) for appt in appointments]
    json_str = json.dumps(data, indent=indent, ensure_ascii=False)

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(json_str, encoding="utf-8")
        return None
    return json_str
