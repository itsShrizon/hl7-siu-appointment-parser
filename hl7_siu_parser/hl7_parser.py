#!/usr/bin/env python3
"""HL7 SIU Parser - Command Line Interface"""
import argparse
import sys
from .parser import HL7Parser
from .io import read_hl7_file, write_json_output
from .exceptions import HL7ParseError, FileReadError


def main(args=None) -> int:
    parser = argparse.ArgumentParser(
        prog="hl7_parser",
        description="Parse HL7 SIU S12 messages into structured JSON."
    )
    parser.add_argument("input", help="Path to HL7 file")
    parser.add_argument("-o", "--output", help="Output JSON file path")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--strict", action="store_true", help="Fail on missing segments")
    parser.add_argument("--safe", action="store_true", help="Collect errors instead of failing")
    opts = parser.parse_args(args)

    try:
        content = read_hl7_file(opts.input)
        hl7 = HL7Parser(strict_mode=opts.strict)

        if opts.safe:
            results = hl7.parse_messages_safe(content)
            appointments = [r["appointment"] for r in results if r["success"]]
            if opts.verbose:
                for r in results:
                    if not r["success"]:
                        print(f"Message {r['index']+1}: {r['error']}", file=sys.stderr)
        else:
            appointments = hl7.parse_messages(content)

        output = write_json_output(appointments, opts.output)
        if output:
            print(output)
        return 0

    except (FileReadError, HL7ParseError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
