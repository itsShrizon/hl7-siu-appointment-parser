# HL7 SIU S12 Appointment Parser

Python module that parses HL7 SIU S12 scheduling messages into structured JSON.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Command Line
```bash
python -m hl7_siu_parser.hl7_parser input.hl7
python -m hl7_siu_parser.hl7_parser input.hl7 -o output.json
python -m hl7_siu_parser.hl7_parser input.hl7 --safe --verbose
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

1. **Pydantic for validation**: Timestamp normalization happens in model validators, making models the source of truth.
2. **No regex**: Message splitting uses structural HL7 rules (MSH line boundaries), not pattern matching.
3. **Early validation**: Message type is validated before parsing other segments for efficiency.
4. **Defensive parsing**: Empty fields (`||`) and missing segments are handled gracefully.

## Testing

```bash
pytest tests/ -v
```

## Architecture

```
hl7_siu_parser/
├── models.py      # Pydantic models with validators
├── parser.py      # Core HL7Parser class
├── segments.py    # Segment-specific parsers
├── io.py          # File read/write
├── exceptions.py  # Custom exception hierarchy
└── hl7_parser.py  # CLI entry point
```
