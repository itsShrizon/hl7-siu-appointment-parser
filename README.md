# HL7 SIU S12 Appointment Parser

Python module that parses HL7 SIU S12 scheduling messages into structured JSON without external HL7 libraries.

## Overview

This parser implements manual HL7 parsing to demonstrate understanding of the HL7 v2 message structure. It handles:
- **Required Segments**: MSH, SCH, PID, PV1
- **Optional Segments**: AIL (location information)
- **Multiple Messages**: Batch processing of concatenated SIU messages
- **Edge Cases**: Missing fields, malformed data, mixed message types

## Quick Start

### Docker Usage

```bash
# Build the image
docker build -t hl7-parser .

# Run with default test_message.hl7
docker run hl7-parser

# Run with strict mode (fail on first error)
docker run hl7-parser --strict test_message.hl7

# Run with a different HL7 file
docker run hl7-parser your_file.hl7

# Run with a file from your host machine
docker run -v $(pwd):/app hl7-parser /app/your_file.hl7

# Run all tests
docker run --entrypoint pytest hl7-parser -v
```

### Local Usage

```bash
# Install dependencies
pip install -r requirements.txt

# Run parser
python3 -m hl7_siu_parser.hl7_parser test_message.hl7

# Run with verbose output
python3 -m hl7_siu_parser.hl7_parser -v test_message.hl7

# Run in strict mode
python3 -m hl7_siu_parser.hl7_parser --strict test_message.hl7

# Run all tests
pytest -v
```

### Python API

```python
from hl7_siu_parser import HL7Parser

parser = HL7Parser()

# Parse file (auto-streams for large files > 1MB)
appointments = parser.parse_file("messages.hl7")

# Parse single message
appt = parser.parse_message(message_string)

# Parse content string
appointments = parser.parse_messages(content)

# Stream explicitly (for maximum control)
for appt in parser.stream_file("large.hl7"):
    process(appt)
```

## Design Architecture

### Core Design Patterns

#### 1. Layered Architecture
- **Separation of Concerns**: Clear boundaries between IO, parsing, validation, and domain logic
- **Dependency Direction**: Lower layers (field_utils, segments) don't depend on higher layers (parser, CLI)
- **Single Responsibility**: Each module has one focused job

#### 2. Parsing Strategy

**Multi-Pass Parsing**
- **First Pass**: Message splitting and MSH validation
- **Second Pass**: Segment extraction and routing
- **Third Pass**: Field-level parsing with safe extraction
- **Complexity**: O(n) where n is message length

**Defensive Parsing**
- All field extraction is bounds-checked
- Empty/missing fields return empty strings, never crash
- Invalid data preserved as-is (e.g., "INVALID_DATE") rather than failing

#### 3. Error Handling Philosophy

**Fault Tolerance by Default**
- **Graceful Degradation**: Bad messages skipped, good ones processed
- **Structured Exceptions**: Exception hierarchy for programmatic handling
- **Dual Modes**: 
  - Default mode: collect errors, continue processing
  - Strict mode: fail-fast on first error

**Error Categories**
- **Validation Errors**: Wrong message type (skippable in mixed feeds)
- **Structural Errors**: Malformed segments (fatal for that message)
- **Data Errors**: Invalid field values (preserved, not failed)

#### 4. Memory Management

**Three Processing Models**

1. **Auto-Detect** (`parse_file()`):
   - Automatically chooses strategy based on file size
   - Files ≤ 1MB: loaded into memory (faster)
   - Files > 1MB: streamed line-by-line (memory efficient)
   - Best for: Most use cases (recommended)

2. **Load-All** (`read_hl7_file()` + `parse_messages()`):
   - Loads entire file into memory
   - Best for: Small to medium files (<100MB)
   - Complexity: O(n) space

3. **Streaming** (`stream_file()`):
   - Line-by-line processing with message buffering
   - Best for: Large feeds (GB+), continuous feeds
   - Complexity: O(1) space (constant memory regardless of file size)

**Configuring Auto-Detect Threshold**

```python
from hl7_siu_parser import HL7Parser

# Default: 1MB threshold
parser = HL7Parser()

# Always stream (threshold = 0)
parser = HL7Parser(stream_threshold=0)

# Never auto-stream (threshold = -1)
parser = HL7Parser(stream_threshold=-1)

# Custom: stream files > 500KB
parser = HL7Parser(stream_threshold=500 * 1024)
```

**Message Buffering**
- Messages accumulated until MSH boundary detected
- Handles multi-line segments without loading entire file
- Buffer cleared after each message processed

#### 5. Validation Strategy

**Pydantic Models**
- **Type Safety**: Automatic type coercion and validation
- **Timestamp Normalization**: HL7 → ISO 8601 conversion in model validators
- **Field Validators**: Custom logic for date/datetime normalization
- **Fail-Safe**: Invalid dates preserved as strings rather than rejected

**MSH Validation Algorithm**
```
is_valid_msh_start(line):
    1. Check starts with "MSH"
    2. Verify field separator at position 3
    3. Validate encoding characters at position 4
    4. Return boolean (not exception)
```
- **Complexity**: O(1) - fixed character checks
- **Purpose**: Prevents false positives when splitting messages

#### 6. Message Splitting Algorithm

**Structural Detection (Not Regex)**
```
For each line in file:
    If is_valid_msh_start(line):
        Yield accumulated buffer
        Start new buffer with this line
    Else:
        Append line to current buffer
```
- **Complexity**: O(n) where n is file size
- **Advantage**: Handles embedded "MSH" text in fields
- **Robustness**: Validates structure, not just string matching

#### 7. Field Extraction Strategy

**Safe Accessors**
- `get_field_value()`: Array bounds checking
- `get_component_value()`: Split + bounds check
- `get_first_repetition()`: Handle repeating fields (~)
- All return empty string on error (never None or exception)

**Complexity**
- Field access: O(1)
- Component extraction: O(k) where k is component count
- Best case: Direct field access
- Worst case: Deep nested components (rare in practice)

#### 8. Timestamp Normalization

**Progressive Parsing**
```
1. Extract timezone if present (+0500 or -0800)
2. Remove fractional seconds if present (.123456)
3. Parse based on length:
   - 14 chars: YYYYMMDDHHMMSS
   - 12 chars: YYYYMMDDHHMM
   - 8 chars: YYYYMMDD
4. Format to ISO 8601
5. Append timezone or 'Z'
```
- **Complexity**: O(1) - fixed string operations
- **Robustness**: Handles partial timestamps gracefully

### Performance Characteristics

**Best Case**
- **Single valid SIU message**: O(n) where n = message length
- **All messages valid**: O(m × n) where m = message count

**Worst Case**
- **All messages invalid**: O(m × n) still, but all skipped
- **Deeply nested components**: O(m × n × c) where c = component depth (rare)

**Space Complexity**
- **Load-all mode**: O(n) where n = file size
- **Streaming mode**: O(m) where m = largest single message size

### Design Trade-offs

1. **Simplicity over Performance**: Clear code prioritized over micro-optimizations
2. **Fault Tolerance over Strictness**: Continues processing by default
3. **Type Safety over Speed**: Pydantic validation adds overhead but prevents bugs
4. **Flexibility over Assumption**: Doesn't assume field counts or message structure

## Code Structure

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
│   ├── __init__.py             
│   ├── hl7Parser.py            # Main HL7Parser class
│   ├── message_parser.py       # Single message parsing logic
│   ├── message_splitter.py     # Split concatenated messages
│   ├── batch_processor.py      # Batch processing with error collection
│   ├── streaming_parser.py     # Memory-efficient streaming parser
│   ├── message_buffer.py       # Line-by-line message accumulation
│   ├── parse_result.py         # Result wrapper for success/error handling
│   ├── parser_state.py         # Parser state tracking
│   └── chunked_reader.py       # Chunked file reading utilities
│
├── exceptions.py               # Custom exception hierarchy
│   ├── HL7ParseError           # Base exception for all parsing errors
│   ├── InvalidMessageTypeError # Wrong message type (not SIU^S12)
│   ├── MissingSegmentError     # Required segment not found
│   ├── MalformedSegmentError   # Invalid segment structure
│   ├── EmptyMessageError       # Empty or whitespace-only message
│   └── FileReadError           # Cannot read input file
│
├── io.py                       # File I/O operations
│   ├── read_hl7_file()         # Read with automatic encoding detection
│   ├── write_json_output()     # Write parsed results to JSON
│   ├── stream_hl7_file()       # Stream large files line-by-line
│   └── stream_json_output()    # Stream JSON output for large datasets
│
├── hl7_parser.py               # Command-line interface
│   └── main()                  # CLI entry point with argument parsing
│
└── segments.py                 # DEPRECATED: Backward compatibility wrapper

tests/
├── conftest.py                 # Pytest fixtures and shared test utilities
├── test_parser.py              # Core parsing logic tests
├── test_segment_parsers.py     # Individual segment parser tests
├── test_field_utils.py         # Field extraction utility tests
├── test_timestamp_normalization.py  # Timestamp conversion tests
├── test_edge_cases.py          # Edge case and error handling tests
├── test_multi_message.py       # Multiple message processing tests
└── fixtures/                   # Test HL7 message files
    ├── valid_single.hl7        # Single valid SIU message
    ├── multiple_siu.hl7        # Multiple concatenated messages
    ├── missing_pid.hl7         # Missing required segment
    ├── missing_sch.hl7         # Missing required segment
    ├── malformed.hl7           # Invalid message structure
    ├── mixed_types.hl7         # SIU and non-SIU messages
    ├── truncated_fields.hl7    # Incomplete field data
    └── extra_segments.hl7      # Additional non-required segments
```

## Module Documentation

### Core Parsing Components

#### `models.py` - Domain Models
**Purpose**: Define data structures with automatic validation and normalization.

**Key Classes**:
- `Patient`: PID segment data (demographics)
- `Provider`: PV1 segment data (attending physician)
- `Appointment`: Complete appointment with patient, provider, scheduling details
- `HL7MessageMetadata`: MSH segment data (message control, timestamps)

**Key Features**:
- Pydantic validation ensures type safety
- Custom validators normalize HL7 timestamps to ISO 8601
- Invalid dates preserved as strings (e.g., "INVALID_DATE") instead of rejection
- Immutable models prevent accidental modification

**Extending**:
To add new fields to existing models:
1. Add field with type annotation and `Field()` descriptor
2. Add `@field_validator` if custom validation needed
3. Update corresponding segment parser to extract the new field
4. Add tests in `test_segment_parsers.py`

#### `field_utils.py` - Safe Field Extraction
**Purpose**: Provide defensive, bounds-checked functions for accessing HL7 field data.

**Key Functions**:
- `get_field_value(fields, index, default="")`: Extract field by 1-based index
- `get_component_value(field, index, separator="^", default="")`: Extract component using ^ separator
- `get_first_repetition(field, separator="~")`: Handle repeating fields
- `looks_like_datetime(value)`: Validate HL7 datetime format
- `extract_datetime_from_timing(timing_quantity)`: Parse TQ1 timing fields

**Key Features**:
- Never raises IndexError - returns default on out-of-bounds
- Handles empty strings, None, and malformed input
- All functions are pure (no side effects)
- Extensively unit tested (see `test_field_utils.py`)

**Extending**:
To add new extraction patterns:
1. Add function following naming convention `get_*_value()`
2. Include bounds checking and default return value
3. Document HL7 specification reference in docstring
4. Add comprehensive tests including edge cases

#### `segments/` - Segment Parsers
**Purpose**: One parser per HL7 segment type for maintainability and clarity.

**Structure**:
Each parser module exports:
- `parse_<segment>(segment_string, separators)`: Main parsing function
- Helper functions for segment-specific logic
- Documentation of HL7 field positions and meanings

**Key Parsers**:
- `msh_parser.py`: Message header, control ID, message type
- `sch_parser.py`: Appointment ID, timing, location, status
- `pid_parser.py`: Patient ID, name, DOB, gender
- `pv1_parser.py`: Attending doctor, visit number
- `ail_parser.py`: Location resource information

**Key Features**:
- Stateless functions (no shared state)
- Consistent interface across all parsers
- Each parser can be tested independently
- Uses `field_utils` for safe extraction

**Extending**:
To add a new segment parser:
1. Create `<segment>_parser.py` in `segments/`
2. Implement `parse_<segment>(segment_str, separators) -> dict`
3. Export from `segments/__init__.py`
4. Update `parser/message_parser.py` to call new parser
5. Update `models.py` if new model needed
6. Add tests in `test_segment_parsers.py`

Example:
```python
# segments/rgs_parser.py
from hl7_siu_parser.field_utils import get_field_value

def parse_rgs(segment_str: str, separators: dict) -> dict:
    """Parse RGS (Resource Group) segment."""
    fields = segment_str.split(separators['field'])
    
    return {
        'set_id': get_field_value(fields, 1),
        'segment_action_code': get_field_value(fields, 2),
        'resource_group_id': get_field_value(fields, 3),
    }
```

#### `parser/` - Core Parsing Logic
**Purpose**: Orchestrate parsing workflow from raw text to validated models.

**Key Modules**:
- `hl7Parser.py`: Main `HL7Parser` class with high-level API
- `message_parser.py`: Parse single message into Appointment model
- `message_splitter.py`: Split multi-message files on MSH boundaries
- `batch_processor.py`: Process multiple messages with error collection
- `streaming_parser.py`: Memory-efficient streaming for large files
- `message_buffer.py`: Accumulate lines until complete message found
- `parse_result.py`: Wrapper for success/error results
- `parser_state.py`: Track parsing state across operations

**Key Features**:
- **Auto-streaming**: `parse_file()` auto-detects large files and streams
- Validates message type before parsing (rejects non-SIU messages)
- MSH structural validation prevents false positives
- Collects all errors without failing entire batch
- Supports both load-all and streaming modes

**API Overview**:

| Method | Use Case | Memory |
|--------|----------|--------|
| `parse_file(path)` | Files (auto-detects size) | Auto |
| `parse_file_with_report(path)` | Files with stats | Auto |
| `parse_message(str)` | Single message | Low |
| `parse_messages(str)` | Content string | Proportional |
| `stream_file(path)` | Explicit streaming | Constant |

**Extending**:
To modify parsing logic:
1. **Message validation**: Edit `hl7Parser.py::_is_valid_msh_start()`
2. **Segment routing**: Edit `message_parser.py::parse_message()`
3. **Batch behavior**: Edit `batch_processor.py::process_batch()`
4. **Streaming**: Edit `streaming_parser.py::stream_parse()`

#### `exceptions.py` - Exception Hierarchy
**Purpose**: Structured exceptions for clear error categorization.

**Exception Tree**:
```
HL7ParseError (base)
├── InvalidMessageTypeError     # Not SIU^S12
├── MissingSegmentError         # Required segment absent
├── MalformedSegmentError       # Invalid segment structure
├── EmptyMessageError           # No content
└── FileReadError               # IO failure
```

**Usage**:
```python
try:
    appointments = parser.parse_file(content)
except InvalidMessageTypeError:
    # Skip non-SIU messages
    pass
except MissingSegmentError as e:
    # Log missing required segment
    logger.error(f"Missing segment: {e}")
except HL7ParseError as e:
    # Catch all parsing errors
    logger.error(f"Parse failed: {e}")
```

**Extending**:
To add new exception types:
1. Inherit from `HL7ParseError` or appropriate subclass
2. Add descriptive docstring explaining when it's raised
3. Update exception handling in `parser/` modules
4. Add test cases in `test_edge_cases.py`

### Supporting Components

#### `io.py` - File Operations
**Purpose**: Handle file I/O with encoding detection and JSON serialization.

**Key Functions**:
- `read_hl7_file(filepath)`: Read file with automatic encoding detection (utf-8, latin-1, cp1252, iso-8859-1)
- `write_json_output(data, filepath)`: Write parsed data as formatted JSON
- `stream_hl7_file(filepath)`: Generator for line-by-line reading
- `stream_json_output(appointments, output_file)`: Stream JSON for large datasets

**Key Features**:
- Tries multiple encodings automatically
- Handles different line endings (\\n, \\r\\n)
- Pretty-printed JSON output for readability
- Memory-efficient streaming mode

**Extending**:
To add new encodings:
1. Add encoding string to `ENCODINGS` list in `read_hl7_file()`
2. Order by likelihood (most common first)

#### `hl7_parser.py` - CLI
**Purpose**: Command-line interface with user-friendly output.

**Features**:
- Argument parsing (input file, output file, verbose, strict mode)
- Silent success (JSON only) vs verbose mode (stats to stderr)
- Graceful error handling with helpful messages
- Exit codes: 0 (success), 1 (error)

**Extending**:
To add CLI options:
1. Add argument to `argparse.ArgumentParser`
2. Pass option through to parser or IO functions
3. Update README usage section
4. Add integration test

## Testing

### Test Coverage

The test suite includes 153 tests covering:

**Core Functionality** (`test_parser.py`):
- Valid single SIU message parsing
- Multiple message parsing
- Message type validation
- Encoding detection

**Segment Parsers** (`test_segment_parsers.py`):
- MSH, SCH, PID, PV1, AIL parsers
- Field extraction accuracy
- Component and sub-component parsing
- Repeating field handling

**Field Utilities** (`test_field_utils.py`):
- Bounds checking
- Empty field handling
- Component extraction
- Repeating field logic

**Timestamp Normalization** (`test_timestamp_normalization.py`):
- HL7 datetime formats (YYYYMMDDHHMMSS, YYYYMMDDHHMM, YYYYMMDD)
- Timezone handling (+/-HHMM)
- Invalid date preservation
- ISO 8601 output format

**Edge Cases** (`test_edge_cases.py`):
- Missing required segments (SCH, PID)
- Empty messages
- Malformed segments
- Invalid message types
- Extra/unexpected segments
- Truncated fields
- Invalid encoding characters

**Multi-Message** (`test_multi_message.py`):
- Multiple SIU messages in one file
- Mixed SIU and non-SIU messages
- Message splitting accuracy
- Batch error handling

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=hl7_siu_parser

# Specific test file
pytest tests/test_parser.py

# Specific test
pytest tests/test_parser.py::test_valid_siu_message

# Verbose output
pytest -v

# In Docker
docker run --entrypoint pytest hl7-parser -v
```

### Writing New Tests

1. **Add fixtures** to `conftest.py` for reusable test data
2. **Follow naming**: `test_<function>_<scenario>`
3. **Use parametrize** for multiple similar cases
4. **Test edge cases**: empty, None, out-of-bounds, malformed
5. **Add fixture files** to `tests/fixtures/` for complex test messages

Example:
```python
# tests/test_new_feature.py
import pytest
from hl7_siu_parser.segments.rgs_parser import parse_rgs

def test_parse_rgs_valid():
    segment = "RGS|1|U|GRP001"
    separators = {'field': '|', 'component': '^'}
    result = parse_rgs(segment, separators)
    assert result['resource_group_id'] == 'GRP001'

def test_parse_rgs_missing_fields():
    segment = "RGS|1"
    separators = {'field': '|', 'component': '^'}
    result = parse_rgs(segment, separators)
    assert result['resource_group_id'] == ''  # Graceful handling
```

## Common Modification Scenarios

### Adding Support for New Message Type

1. Update `parser/hl7Parser.py::parse_message()` to accept new type
2. Add segment parsers for type-specific segments
3. Create new domain model in `models.py`
4. Add test fixtures in `tests/fixtures/`
5. Add integration tests

### Adding New Field to Existing Segment

1. Update segment parser in `segments/<segment>_parser.py`
2. Add field to corresponding model in `models.py`
3. Add test case in `test_segment_parsers.py`
4. Update documentation

### Implementing Custom Validation

1. Add `@field_validator` to model in `models.py`
2. Implement validation logic
3. Add test cases for valid and invalid inputs
4. Document validation rules

### Supporting New Encoding

1. Add encoding to `ENCODINGS` list in `io.py::read_hl7_file()`
2. Test with sample file in that encoding
3. Add test case

## Troubleshooting

### Common Issues

**"MSH segment not found"**: 
- Check file has valid MSH header starting line
- Verify encoding characters at MSH position 4

**"Invalid message type"**: 
- Parser expects SIU^S12 in MSH-9
- Use verbose mode to see actual message type
- Add support for new type if needed

**"Missing required segment"**:
- PID and SCH are required for appointments
- Check if segment is present but malformed
- Use verbose mode to see which segment is missing

**Encoding errors**:
- Add encoding to `ENCODINGS` list in io.py
- Check for BOM (byte order mark) at file start

## Requirements

- Python 3.8 or newer
- Pydantic >= 2.0
- pytest (for running tests)

## License

[Your license here]
