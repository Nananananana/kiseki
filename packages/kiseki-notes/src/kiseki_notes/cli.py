"""The notes producer, at the command line.

`plan` looks and counts. `read` classifies and writes, and is not here
yet: it needs a model, and a model needs the trust boundary settled
first (ADR-0073). Planning needs neither, which is why it comes first
-- the owner can point this at a real folder today and see exactly
what it would consider, with nothing opened and nothing sent.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from kiseki_notes.classifier import (
    SENSITIVE,
    ClassifierUnavailableError,
    classify,
)
from kiseki_notes.reader import MAX_BYTES, SUFFIXES, days_of, find_notes
from kiseki_notes.trust import admitted, describe, host_of

EXIT_OK = 0
EXIT_BAD_INPUT = 2

DEFAULT_HOST = "http://localhost:11434"
DEFAULT_MODEL = "qwen2.5:14b-instruct-q4_K_M"

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


def _settings_from(args: argparse.Namespace) -> tuple[str, str, str, tuple[str, ...]]:
    """Where the model is and what it is called, from flags or environment."""
    host = args.model_host or os.environ.get("KISEKI_MODEL_HOST", DEFAULT_HOST)
    model = args.model or os.environ.get("KISEKI_MODEL_LANGUAGE_MODEL", DEFAULT_MODEL)
    boundary = args.boundary or os.environ.get("KISEKI_MODEL_BOUNDARY", "same_host")
    trusted = tuple(
        name.strip().lower()
        for name in os.environ.get("KISEKI_MODEL_TRUSTED_HOSTS", "").split(",")
        if name.strip()
    )
    return host, model, boundary, trusted


def _command_read(args: argparse.Namespace) -> int:
    """Classify each note, and show what would be recorded.

    A dry run by default, and that is a rule rather than a courtesy: a
    misclassified photograph can be looked at again, and a
    misclassified note cannot, because the text is gone (ADR-0075).
    """
    root = Path(args.folder).expanduser()
    try:
        notes = find_notes(root)
    except NotADirectoryError as error:
        print(str(error), file=sys.stderr)
        return EXIT_BAD_INPUT

    host, model, boundary, trusted = _settings_from(args)
    endpoint_host = host_of(host)
    if not admitted(endpoint_host, boundary, trusted):
        print(
            "REFUSED. The notes will not be read:\n"
            f"  '{endpoint_host}' is {describe(endpoint_host)}, which is outside"
            f" the {boundary} boundary.\n"
            "  The text of every note would be sent there.",
            file=sys.stderr,
        )
        return EXIT_BAD_INPUT

    readable = [note for note in notes if not note.too_large]
    skipped = len(notes) - len(readable)
    if args.limit:
        readable = readable[: args.limit]

    print(RULE)
    print(f"  folder        {root}")
    print(f"  model         {model} at {host} ({describe(endpoint_host)})")
    print(f"  reading       {len(readable)} of {len(notes)}")
    if skipped:
        print(f"  too large     {skipped} skipped")
    print()

    records: list[dict[str, object]] = []
    refusals = 0
    for note in readable:
        try:
            excerpt = note.path.read_text(encoding="utf-8", errors="replace")
        except OSError as error:
            print(f"    {note.reference}  could not be read: {error}")
            refusals += 1
            continue
        try:
            settled = classify(excerpt, host, model)
        except ClassifierUnavailableError as error:
            print(f"the model could not be reached: {error}", file=sys.stderr)
            return EXIT_BAD_INPUT
        if not settled.answered:
            refusals += 1
        labels = ", ".join(settled.labels) if settled.labels else "-"
        print(f"    {note.day.isoformat()}  {settled.category:<12}  {labels}")
        records.append(
            {
                "owner": args.owner,
                "platform": args.platform,
                "day": note.day.isoformat(),
                "reference": note.reference,
                "category": settled.category,
                "labels": list(settled.labels),
            }
        )

    print(f"\n  read          {len(records)}")
    if refusals:
        print(f"  refused       {refusals}")
    sensitive = sum(1 for record in records if record["category"] in SENSITIVE)
    if sensitive:
        print(f"  counted only  {sensitive} in a sensitive category, with no labels")

    if not args.apply:
        print(
            "\n  nothing was written. The text stayed here and is now forgotten;"
            "\n  add --apply --out <file> to record what is above"
        )
        return EXIT_OK
    if not args.out:
        print("--apply needs --out to say where the records go", file=sys.stderr)
        return EXIT_BAD_INPUT
    destination = Path(args.out).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n  written to    {destination}")
    print("  read it with  uv run kiseki notes <that file>")
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

    read = commands.add_parser("read", help="classify each note and show what would be recorded")
    read.add_argument("folder", help="the folder of notes the owner named")
    read.add_argument("--owner", default="me", help="whose notes these are")
    read.add_argument("--platform", default="notes", help="what produced them")
    read.add_argument("--model-host", default=None, help="where the model is")
    read.add_argument("--model", default=None, help="which model reads them")
    read.add_argument(
        "--boundary",
        default=None,
        choices=["same_host", "private_network", "anywhere"],
        help="how far away the model may be",
    )
    read.add_argument("--limit", type=int, default=None, help="read only this many")
    read.add_argument("--out", default=None, help="where the records go")
    read.add_argument("--apply", action="store_true", help="write the records; without it, nothing")
    read.set_defaults(run=_command_read)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    exit_code: int = args.run(args)
    return exit_code


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
