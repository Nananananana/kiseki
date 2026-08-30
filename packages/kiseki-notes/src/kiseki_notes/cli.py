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
    Classification,
    ClassifierUnavailableError,
    NoteTookTooLongError,
    classify,
)
from kiseki_notes.evaluation import read_expectations, score
from kiseki_notes.reader import (
    MAX_BYTES,
    SUFFIXES,
    busiest_day,
    days_of,
    find_notes,
    looks_copied,
)
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
    if looks_copied(days):
        day, count = busiest_day(days)
        print(
            f"\n  {count} of {len(notes)} were last written on {day.isoformat()}."
            "\n  A folder somebody wrote is spread across the days they wrote it,"
            "\n  so this is usually a copy rather than a history: `cp` without -p,"
            "\n  an unzip, or a converter that wrote fresh files. A note carries no"
            "\n  date of its own and the filesystem's is the only one there is, so"
            "\n  every trail in this folder would arrive as one day (ADR-0076)."
            "\n  Nothing is refused: a folder written in one sitting looks the same."
        )
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
    if notes and looks_copied(days_of(notes)):
        day, count = busiest_day(days_of(notes))
        # The command that would record it says so too. `plan` is the
        # one people run first, and it is not the one people run.
        print(
            f"  dates         {count} of {len(notes)} last written on {day.isoformat()},"
            " which is usually a copy rather than a history: see `plan`"
        )
    print()

    records: list[dict[str, object]] = []
    counted: dict[str, int] = {}
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
    if counted:
        print("\n  by category")
        for category, count in sorted(counted.items(), key=lambda pair: -pair[1]):
            print(f"    {category:<12}  {count}")

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


def _command_eval(args: argparse.Namespace) -> int:
    """Read a labelled corpus and say how well the classifier did.

    Three figures, because one would hide the asymmetry: a sensitive
    note read as ordinary has its labels recorded, and an ordinary note
    read as sensitive only costs coverage. The leaks are named, since
    an aggregate says something moved and not what (ADR-0077).
    """
    root = Path(args.corpus).expanduser()
    folder = root / "notes"
    answers_file = root / "expectations.json"
    if not answers_file.is_file():
        print(f"no expectations.json under {root}", file=sys.stderr)
        return EXIT_BAD_INPUT
    expectations = read_expectations(answers_file)

    host, model, boundary, trusted = _settings_from(args)
    endpoint_host = host_of(host)
    if not admitted(endpoint_host, boundary, trusted):
        print(
            f"REFUSED. '{endpoint_host}' is {describe(endpoint_host)},"
            f" outside the {boundary} boundary.",
            file=sys.stderr,
        )
        return EXIT_BAD_INPUT

    notes = find_notes(folder)
    by_relative = {str(note.path.relative_to(folder)).replace("\\", "/"): note for note in notes}
    print(RULE)
    print(f"  corpus        {root.name}, {len(expectations)} notes")
    print(f"  model         {model} at {host}")
    print()

    answers: dict[str, tuple[str, tuple[str, ...]]] = {}
    for expectation in expectations:
        note = by_relative.get(expectation.path)
        if note is None:
            continue
        try:
            excerpt = note.path.read_text(encoding="utf-8", errors="replace")
            settled = classify(excerpt, host, model, timeout=args.timeout)
        except NoteTookTooLongError:
            settled = Classification(
                category="other", labels=(), model=model, refused="took too long"
            )
        except ClassifierUnavailableError as error:
            print(f"the model could not be reached: {error}", file=sys.stderr)
            return EXIT_BAD_INPUT
        answers[expectation.path] = (settled.category, settled.labels)

    result = score(expectations, answers)
    print(
        f"  leak rate         {result.leak_rate:>6.1%}"
        f"   {len(result.leaks)}/{len(result.sensitive)} sensitive notes read as ordinary"
    )
    print(
        f"  over-caution      {result.over_caution_rate:>6.1%}"
        f"   {len(result.over_cautions)}/{len(result.ordinary)} ordinary notes read as sensitive"
    )
    print(f"  exact             {result.exact:>6}   of {len(result.outcomes)}")
    print(f"  acceptable        {result.allowed:>6}   of {len(result.outcomes)}")

    if result.leaks:
        print(f"\n  what leaked ({result.labels_leaked} labels recorded)")
        for outcome in result.leaks:
            labels = ", ".join(outcome.labels) if outcome.labels else "no labels"
            print(f"    {outcome.expected:<11} read as {outcome.answered:<11} {labels}")
    if result.over_cautions:
        print("\n  what was withheld and need not have been")
        for outcome in result.over_cautions:
            print(f"    {outcome.expected:<11} read as {outcome.answered}")

    wrong = [
        outcome
        for outcome in result.outcomes
        if not outcome.acceptable and not outcome.leaked and not outcome.over_cautious
    ]
    if wrong:
        print("\n  otherwise misread")
        for outcome in wrong:
            print(f"    {outcome.expected:<11} read as {outcome.answered}")

    print(
        "\n  a floor to hold, not a claim about your notes: two dozen invented"
        "\n  files say nothing about a real folder"
    )
    return EXIT_BAD_INPUT if result.leaks and args.strict else EXIT_OK


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
    read.add_argument(
        "--timeout",
        type=float,
        default=120.0,
        help="how long one note may take before it counts as refused",
    )
    read.add_argument("--out", default=None, help="where the records go")
    read.add_argument("--apply", action="store_true", help="write the records; without it, nothing")
    read.set_defaults(run=_command_read)

    evaluate = commands.add_parser("eval", help="how well the classifier reads a labelled corpus")
    evaluate.add_argument("corpus", help="a folder holding notes/ and expectations.json")
    evaluate.add_argument("--model-host", default=None, help="where the model is")
    evaluate.add_argument("--model", default=None, help="which model reads them")
    evaluate.add_argument(
        "--boundary",
        default=None,
        choices=["same_host", "private_network", "anywhere"],
        help="how far away the model may be",
    )
    evaluate.add_argument(
        "--timeout",
        type=float,
        default=120.0,
        help="how long one note may take before it counts as refused",
    )
    evaluate.add_argument(
        "--strict",
        action="store_true",
        help="exit non-zero when anything leaked, for a build to fail on",
    )
    evaluate.set_defaults(run=_command_eval)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    exit_code: int = args.run(args)
    return exit_code


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
