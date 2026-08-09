"""Command line entry point for producers written in any language."""

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from kiseki_conformance.checks import check_semantics, validate_document

EXIT_OK = 0
EXIT_VIOLATIONS = 1
EXIT_UNREADABLE = 2


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="kiseki-conformance",
        description="Check that a document conforms to the PhotoRecord v1 contract.",
    )
    parser.add_argument("path", type=Path, help="path to the JSON document to check")
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="print nothing, report the result through the exit code only",
    )
    args = parser.parse_args(argv)

    try:
        document = json.loads(args.path.read_text(encoding="utf-8"))
    except OSError as error:
        print(f"cannot read {args.path}: {error}", file=sys.stderr)
        return EXIT_UNREADABLE
    except json.JSONDecodeError as error:
        print(f"{args.path} is not valid JSON: {error}", file=sys.stderr)
        return EXIT_UNREADABLE

    violations = validate_document(document)
    if isinstance(document, dict):
        violations += check_semantics(document)

    if violations:
        if not args.quiet:
            print(f"{args.path}: {len(violations)} violation(s)", file=sys.stderr)
            for message in violations:
                print(f"  {message}", file=sys.stderr)
        return EXIT_VIOLATIONS

    if not args.quiet:
        count = len(document.get("records", [])) if isinstance(document, dict) else 0
        print(f"{args.path}: conforms to PhotoRecord v1 ({count} record(s))")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
