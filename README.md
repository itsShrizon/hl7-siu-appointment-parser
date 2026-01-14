# HL7 SIU S12 Appointment Parser

Python module that parses HL7 SIU S12 scheduling messages into structured JSON.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Command Line
```bash
python -m hl7_siu_parser.hl7_parser test_message.hl7
python -m hl7_siu_parser.hl7_parser test_message.hl7 -o output.json
python -m hl7_siu_parser.hl7_parser test_message.hl7 --safe --verbose
```

### Python API
```python
from hl7_siu_parser import HL7Parser

parser = HL7Parser()
appointment = parser.parse_message(hl7_content)
print(appointment.model_dump_json(indent=2))
```

## Output Format

```json
{
  "appointment_id": "123456",
  "appointment_datetime": "2025-05-02T13:00:00Z",
  "patient": {
    "id": "P12345",
    "first_name": "John",
    "last_name": "Doe",
    "dob": "1985-02-10",
    "gender": "M"
  },
  "provider": {
    "id": "D67890",
    "name": "Dr. Jane Smith"
  },
  "location": "Clinic A Room 203",
  "reason": "General Consultation"
}
```

## Design Decisions

1. **Modular segment parsers**: Each HL7 segment (MSH, SCH, PID, PV1, AIL) has its own dedicated parser module for maintainability
2. **Pydantic validation**: Automatic type validation and data normalization using Pydantic models
3. **Defensive field extraction**: Safe helper functions handle missing fields, empty values, and malformed data gracefully
4. **Validated MSH detection**: Message splitting uses structural validation, not brittle pattern matching
5. **Detailed error reporting**: Line numbers and context provided for debugging malformed messages
6. **Fault-tolerant parsing**: Can process mixed HL7 feeds containing both SIU and non-SIU messages


## Testing

```bash
pytest tests/ -v
```

## Architecture

```
hl7_siu_parser/
├── __init__.py                 # Package public API and version info
│
├── models.py                   # Pydantic data models with validation
│   ├── Patient                 # Patient demographics (PID segment)
│   ├── Provider                # Healthcare provider info (PV1 segment)
│   ├── Appointment             # Complete appointment details
│   └── HL7MessageMetadata      # Message header information (MSH segment)
│
├── field_utils.py              # Low-level field extraction utilities
│   ├── get_field_value()       # Safely extract field by index
│   ├── get_component_value()   # Extract component from field (^ separator)
│   ├── get_first_repetition()  # Get first value from repeating field (~ separator)
│   ├── looks_like_datetime()   # Validate HL7 datetime format
│   └── extract_datetime_from_timing()  # Parse timing field for datetime
│
├── segments/                   # Modular segment parsers (one file per segment)
│   ├── __init__.py             # Export all segment parsers
│   ├── msh_parser.py           # MSH: Message Header
│   ├── sch_parser.py           # SCH: Schedule Activity Information
│   ├── pid_parser.py           # PID: Patient Identification
│   ├── pv1_parser.py           # PV1: Patient Visit (provider info)
│   └── ail_parser.py           # AIL: Appointment Information - Location
│
├── parser/                     # Core parsing logic
│   ├── hl7Parser.py            # Main HL7Parser class
│   │   ├── parse_message()     # Parse single HL7 message
│   │   ├── parse_file()        # Parse file with multiple messages
│   │   ├── split_messages()    # Split concatenated messages
│   │   └── _is_valid_msh_start()  # Validate MSH segment structure
│   │
│   └── parse_result.py         # ParseResult wrapper for success/error handling
│
├── exceptions.py               # Custom exception hierarchy
│   ├── HL7ParseError           # Base exception for all parsing errors
│   ├── InvalidMessageTypeError # Wrong message type (not SIU^S12)
│   ├── MissingSegmentError     # Required segment not found
│   ├── MalformedSegmentError   # Invalid segment structure
│   ├── EmptyMessageError       # Empty or whitespace-only message
│   └── FileReadError           # Cannot read input file
│
├── io.py                       # File operations
│   ├── read_hl7_file()         # Read with automatic encoding detection
│   └── write_json_output()     # Write parsed results to JSON
│
├── hl7_parser.py               # Command-line interface
│   └── main()                  # CLI entry point with argument parsing
│
└── segments.py                 # DEPRECATED: Backward compatibility wrapper
    └── [warnings.warn]         # Emits deprecation warning when imported
```
## Module Responsibilities

### Core Components

- **`models.py`**: Defines data structures with Pydantic validation. Handles timestamp normalization and data type enforcement.

- **`field_utils.py`**: Provides safe, defensive functions for extracting values from HL7 fields. Handles edge cases like missing fields, empty values, and malformed data.

- **`segments/`**: Contains dedicated parser for each HL7 segment type. Each parser:
  - Takes raw segment string and separators as input
  - Extracts relevant fields using field_utils
  - Returns structured data (model or dictionary)
  - Handles segment-specific edge cases

- **`parser/hl7Parser.py`**: Orchestrates the parsing workflow:
  - Validates message type (SIU^S12)
  - Splits multi-message files
  - Coordinates segment parsers
  - Assembles final Appointment model
  - Provides fault-tolerant batch processing

- **`exceptions.py`**: Structured exception hierarchy for clear error categorization and handling.

### Supporting Components

- **`io.py`**: Handles file I/O with encoding detection and JSON serialization.

- **`hl7_parser.py`**: Command-line interface with argument parsing and user-friendly output.

- **`parse_result.py`**: Wrapper class for parsing results, enabling graceful error handling in batch operations.

## Error Handling Strategy

The parser uses a tiered approach:

1. **Validation Errors**: Caught early (message type, segment structure)
2. **Parse Errors**: Individual segment failures don't crash the entire message
3. **Batch Processing**: Invalid messages are skipped with warnings, valid ones are processed
4. **Strict Mode**: Optional flag (`--strict`) to fail fast on first error
