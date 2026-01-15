#!/usr/bin/env python3
"""
HL7 SIU Parser - Command Line Interface

Fault-tolerant CLI that handles mixed HL7 feeds gracefully.
"""
import argparse
import sys
from .parser.hl7Parser import HL7Parser
from .io import read_hl7_file, write_json_output
from .exceptions import FileReadError


def main(args=None) -> int:
    parser = argparse.ArgumentParser(
        prog="hl7_parser",
        description="Parse HL7 SIU S12 messages into structured JSON.",
        epilog="Non-SIU messages (ADT, ORU, etc.) are automatically skipped."
    )
    parser.add_argument("input", help="Path to HL7 file")
    parser.add_argument("-o", "--output", help="Output JSON file path")
    parser.add_argument("-v", "--verbose", action="store_true", 
                       help="Show details about skipped/failed messages")
    parser.add_argument("--strict", action="store_true", 
                       help="Fail on first error instead of skipping")
    opts = parser.parse_args(args)

    try:
        content = read_hl7_file(opts.input)
        hl7_parser = HL7Parser(strict_mode=False)
        
        if opts.strict:
            # Strict mode which fails on first error
            try:
                appointments = hl7_parser.parse_messages_strict(content)
            except Exception as e:
                print(f"Error: {e}", file=sys.stderr)
                return 1
        else:
            # Normal mode which is more fault-tolerant with optional reporting
            result = hl7_parser.parse_messages_with_report(content)
            appointments = result.appointments
            
            if opts.verbose:
                # Report what happened
                print(f"Processed: {result.total_processed} SIU appointments", file=sys.stderr)
                
                if result.skipped:
                    print(f"Skipped: {result.total_skipped} non-SIU messages", file=sys.stderr)
                    for skip in result.skipped:
                        msg_type = skip.get("message_type", "unknown")
                        print(f"  - Message {skip['message_number']}: {msg_type}", file=sys.stderr)
            
            # Always report errors to stderr (fail loudly)
            if result.errors:
                print(f"Error: {result.total_errors} message(s) failed to parse", file=sys.stderr)
                for err in result.errors:
                    print(f"  - Message {err['message_number']}: {err['error']}", file=sys.stderr)
        
        # Output results
        output = write_json_output(appointments, opts.output)
        if output:
            print(output)
        
        # Fail loudly: return non-zero exit code if any errors occurred
        if not opts.strict and result.errors:
            return 1
        
        return 0

    except FileReadError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
