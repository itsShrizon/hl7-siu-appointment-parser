#!/usr/bin/env python3
"""
HL7 SIU Parser - Command Line Interface
"""

import argparse
import sys
from typing import Optional

from .parser import HL7Parser
from .io import read_hl7_file, write_json_output
from .exceptions import HL7ParseError, FileReadError


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hl7_parser",
        description="Parse HL7 SIU S12 messages into structured JSON.",
    )
    parser.add_argument("input", help="Path to HL7 file")
    parser.add_argument("-o", "--output", help="Output JSON file path")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose error output")
    parser.add_argument("--strict", action="store_true", help="Fail on missing optional segments")
    parser.add_argument("--safe", action="store_true", help="Collect errors instead of failing")
    parser.add_argument("--indent", type=int, default=2, help="JSON indentation")
    return parser


def main(args: Optional[list] = None) -> int:
    parser = create_parser()
    opts = parser.parse_args(args)
    
    try:
        content = read_hl7_file(opts.input)
        hl7_parser = HL7Parser(strict_mode=opts.strict)
        
        if opts.safe:
            results = hl7_parser.parse_messages_safe(content)
            successes = [r["appointment"] for r in results if r["success"]]
            if opts.verbose:
                for f in [r for r in results if not r["success"]]:
                    print(f"Message {f['message_index']+1}: {f['error']}", file=sys.stderr)
            appointments = successes
        else:
            appointments = hl7_parser.parse_messages(content)
            
        output = write_json_output(appointments, opts.output, indent=opts.indent)
        if output:
            print(output)
        elif opts.verbose:
            print(f"Wrote to {opts.output}", file=sys.stderr)
            
        return 0
        
    except (FileReadError, HL7ParseError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        if opts.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
