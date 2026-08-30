"""Command line entry point for producers written in any language."""

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from kiseki_conformance.contracts import BY_OPTION, CONTRACTS, identify

EXIT_OK = 0
EXIT_VIOLATIONS = 1
EXIT_UNREADABLE = 2

AUTO = "auto"

UNNAMED = (
    "names no contract, so it is refused rather than guessed at. "
    "A PhotoRecord document carries 'schema_version'; "
    "a kiseki-interest-export carries 'schema' and 'version'."
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="kiseki-conformance",
        description="Check that a document conforms to one of the contracts KISEKI publishes.",
    )
    parser.add_argument("path", type=Path, help="path to the JSON document to check")
    parser.add_argument(
        "--contract",
        default=AUTO,
        choices=[AUTO, *(contract.option for contract in CONTRACTS)],
        help="which contract to check against; by default the document is asked",
    )
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

    contract = BY_OPTION[args.contract] if args.contract != AUTO else identify(document)
    if contract is None:
        if not args.quiet:
            print(f"{args.path}: {UNNAMED}", file=sys.stderr)
        return EXIT_VIOLATIONS

    violations = contract.violations(document)
    if violations:
        if not args.quiet:
            print(f"{args.path}: {len(violations)} violation(s)", file=sys.stderr)
            for message in violations:
                print(f"  {message}", file=sys.stderr)
        return EXIT_VIOLATIONS

    if not args.quiet:
        print(f"{args.path}: {contract.summarise(document)}")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
