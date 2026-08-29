"""The notes producer, at the command line.

`plan` looks and counts. `read` classifies and writes, and is not here
yet: it needs a model, and a model needs the trust boundary settled
first (ADR-0073). Planning needs neither, which is why it comes first
-- the owner can point this at a real folder today and see exactly
what it would consider, with nothing opened and nothing sent.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from kiseki_notes.reader import MAX_BYTES, SUFFIXES, days_of, find_notes

EXIT_OK = 0
EXIT_BAD_INPUT = 2

RULE = "-" * 70


def _command_plan(args: argparse.Namespace) -> int:
    """What is there, counted. Nothing is opened and nothing is sent."""
    root = Path(args.folder).expanduser()
    try:
        notes = find_notes(root)
    except NotADirectoryError as error:
        print(str(error), file=sys.stderr)
        return EXIT_BAD_INPUT

    print(RULE)
    print(f"  folder        {root}")
    print(f"  notes         {len(notes)}")
    if not notes:
        print(f"  nothing to read: no {', '.join(SUFFIXES)} under that folder")
        return EXIT_OK

    days = days_of(notes)
    oversized = [note for note in notes if note.too_large]
    print(f"  days          {len(days)}, {min(days)} to {max(days)}")
    print(f"  bytes         {sum(note.size for note in notes):,}")
    if oversized:
        print(f"  too large     {len(oversized)} over {MAX_BYTES:,} bytes, which would be skipped")
    print("\n  when they were last written")
    for day, count in list(days.items())[-14:]:
        print(f"    {day.isoformat()}  {count}")
    if len(days) > 14:
        print(f"    ... and {len(days) - 14} earlier days")
    print(
        "\n  nothing was opened. Names, sizes and dates are all this needed,"
        "\n  and none of them left this process"
    )
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kiseki-notes",
        description="Turn a folder of notes into NoteRecord v1 documents",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    plan = commands.add_parser("plan", help="what is there, counted, with nothing opened")
    plan.add_argument("folder", help="the folder of notes the owner named")
    plan.set_defaults(run=_command_plan)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    exit_code: int = args.run(args)
    return exit_code


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
