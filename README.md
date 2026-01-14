# HL7 SIU Appointment Parser

A Python module that parses HL7 SIU S12 (Schedule Information Unsolicited) messages and converts them into normalized JSON representations of appointments.

## Features

- **Manual HL7 Parsing**: No external HL7 libraries - demonstrates understanding of HL7 v2.x wire format
- **Robust Error Handling**: Custom exception hierarchy with clear error categorization
- **Defensive Parsing**: Gracefully handles missing/empty fields and malformed data
- **Multi-Message Support**: Parse single files containing multiple messages
- **Streaming Support**: Generator-based parsing for large files
- **ISO 8601 Normalization**: Converts HL7 timestamps to standard format
- **CLI Interface**: Command-line tool for easy usage
- **Docker Support**: Containerized execution

## Installation

```bash
cd "HL7 Data"
pip install -r requirements.txt
```

## Usage

### Command Line

```bash
# Parse and print to stdout
python -m hl7_siu_parser.hl7_parser input.hl7

# Save to file
python -m hl7_siu_parser.hl7_parser input.hl7 -o output.json

# Verbose mode with error details
python -m hl7_siu_parser.hl7_parser input.hl7 --verbose

# Safe mode (collect errors instead of failing)
python -m hl7_siu_parser.hl7_parser input.hl7 --safe
```

### Python API

```python
from hl7_siu_parser import HL7Parser

# Parse a file
parser = HL7Parser()
content = open("appointments.hl7").read()
appointments = parser.parse_messages(content)

for appt in appointments:
    print(appt.to_json(indent=2))

# Parse single message
appointment = parser.parse_message(raw_hl7_message)
print(appointment.patient.first_name)
print(appointment.appointment_datetime)
```

### Docker

```bash
docker build -t hl7-parser .
docker run -v $(pwd)/data:/data hl7-parser /data/input.hl7
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

## Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ -v --cov=hl7_siu_parser

# Run specific test file
python -m pytest tests/test_parser.py -v
```

## Architecture

```
hl7_siu_parser/
├── __init__.py      # Package exports
├── models.py        # Dataclasses (Patient, Provider, Appointment)
├── exceptions.py    # Custom exception hierarchy
├── parser.py        # Core HL7Parser class
├── segments.py      # Segment handlers (MSH, SCH, PID, PV1)
├── io.py            # File operations
└── hl7_parser.py    # CLI entry point
```

### Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Dataclasses** | Type safety, immutability, built-in serialization |
| **Custom Exceptions** | Clear error categorization for debugging |
| **Defensive Parsing** | Healthcare data is often incomplete |
| **No External HL7 Libs** | Per requirements; demonstrates format understanding |
| **Streaming Support** | Handle large files without memory issues |

## HL7 Field Mappings

| JSON Field | HL7 Segment | Field Position |
|------------|-------------|----------------|
| `appointment_id` | SCH | SCH-1 or SCH-2 |
| `appointment_datetime` | SCH | SCH-11 |
| `location` | SCH | SCH-23 |
| `reason` | SCH | SCH-6 |
| `patient.id` | PID | PID-3 |
| `patient.first_name` | PID | PID-5.2 |
| `patient.last_name` | PID | PID-5.1 |
| `patient.dob` | PID | PID-7 |
| `patient.gender` | PID | PID-8 |
| `provider.id` | PV1 | PV1-7.1 |
| `provider.name` | PV1 | PV1-7.2-7.6 |

## Edge Cases Handled

- ✅ Missing SCH or PID segments (returns None for affected fields)
- ✅ Extra segments (EVN, NK1, OBX, etc.) - safely ignored
- ✅ Empty field values
- ✅ Unexpected component separators (auto-detected from MSH)
- ✅ Multiple messages in single file
- ✅ Invalid message types (raises `InvalidMessageTypeError`)
- ✅ Various line endings (CR, LF, CRLF)
- ✅ Repeating fields (uses first value)

## Assumptions & Tradeoffs

1. **Filler ID Priority**: When both Placer and Filler appointment IDs exist, Filler is preferred (SCH-2 over SCH-1)
2. **First Repetition**: For repeating fields, the first value is used
3. **Timezone Handling**: If no timezone in HL7 timestamp, `Z` (UTC) is appended
4. **Graceful Degradation**: Missing optional segments produce `None` values rather than errors
5. **Encoding**: Tries UTF-8, Latin-1, CP1252, ISO-8859-1 in order

## Requirements

- Python 3.8+
- pytest (for testing)

## License

MIT
