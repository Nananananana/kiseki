"""The web producer, at the command line.

`plan` looks and counts, opening nothing and sending nothing. `read`
classifies, and shows what it would record before it records anything.

Nothing printed by either names a page. Not a URL, not a title, not a
host, not in a dry run and not in a summary. The contract discards
them, and a producer that showed them while planning has shown them.

`read` is a dry run by default, and that is a rule rather than a
courtesy: a misclassified photograph can be looked at again, and a
misclassified page cannot, because the address is gone.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

from kiseki_web.classifier import (
    UNLABELLED,
    Classification,
    ClassifierUnavailableError,
    classify,
)
from kiseki_web.reader import (
    ABANDONED,
    DWELL_FLOOR,
    UnreadableHistoryError,
    addresses_for,
    history_in,
    read_window,
)
from kiseki_web.reference import reference_for, salt_in
from kiseki_web.trust import admitted, describe, host_of

EXIT_OK = 0
EXIT_BAD_INPUT = 2

RULE = "-" * 70

DEFAULT_WINDOW_DAYS = 30

DEFAULT_HOST = "http://localhost:11434"
DEFAULT_MODEL = "qwen2.5:14b-instruct-q4_K_M"


def _window(args: argparse.Namespace) -> tuple[date, date]:
    until = date.fromisoformat(args.until) if args.until else date.today()
    since = (
        date.fromisoformat(args.since)
        if args.since
        else until - timedelta(days=DEFAULT_WINDOW_DAYS)
    )
    if since > until:
        raise ValueError(f"--from {since} is after --to {until}")
    return since, until


def _command_plan(args: argparse.Namespace) -> int:
    """What is in the window, counted. No page is opened."""
    profile = Path(args.profile).expanduser()
    try:
        database = history_in(profile)
        since, until = _window(args)
        plan = read_window(database, since, until)
    except (UnreadableHistoryError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return EXIT_BAD_INPUT
    except OSError as error:
        print(f"the history could not be copied: {error}", file=sys.stderr)
        return EXIT_BAD_INPUT

    days = plan.days()
    print(RULE)
    print(f"  profile       {profile}")
    print(f"  history       {database.name}")
    print(f"  window        {since.isoformat()} to {until.isoformat()}")
    print(f"  visits        {len(plan.visits)}")
    if not plan.visits:
        print("\n  nothing in that window. Nothing was opened and nothing was sent")
        return EXIT_OK

    print(f"  attention     {len(plan.kept)} visits over {plan.pages} pages")
    print(
        f"  discarded     {plan.discarded}"
        f" (under {int(DWELL_FLOOR.total_seconds())}s, or over"
        f" {int(ABANDONED.total_seconds() // 3600)}h and so a tab left open)"
    )
    if days:
        print(f"  days          {len(days)}, {min(days)} to {max(days)}")
        print("\n  when they were opened")
        for day, count in list(days.items())[-14:]:
            print(f"    {day.isoformat()}  {count}")
        if len(days) > 14:
            print(f"    ... and {len(days) - 14} earlier days")
    print(
        "\n  no page was opened, and no address was read out of the copy."
        "\n  Row numbers, times and durations are all this needed, and none"
        "\n  of them left this process"
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
    """Classify each page, and show what would be recorded.

    A dry run by default. A misclassified page cannot be looked at
    again, because the address is gone (ADR-0085).
    """
    profile = Path(args.profile).expanduser()
    try:
        database = history_in(profile)
        since, until = _window(args)
        plan = read_window(database, since, until)
    except (UnreadableHistoryError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return EXIT_BAD_INPUT

    host, model, boundary, trusted = _settings_from(args)
    endpoint = host_of(host)
    if not admitted(endpoint, boundary, trusted):
        print(
            "REFUSED. The history will not be read:"
            f"\n  '{endpoint}' is {describe(endpoint)}, which is outside"
            f" the {boundary} boundary."
            "\n  The address and title of every page would be sent there.",
            file=sys.stderr,
        )
        return EXIT_BAD_INPUT

    pages = list(dict.fromkeys(visit.page for visit in plan.kept))
    if args.limit:
        pages = pages[: args.limit]
    addresses = addresses_for(database, pages)
    salt = salt_in(Path(args.state).expanduser())

    print(RULE)
    print(f"  profile       {profile}")
    print(f"  model         {model} at {host} ({describe(endpoint)})")
    print(f"  window        {since.isoformat()} to {until.isoformat()}")
    print(f"  reading       {len(pages)} pages of {plan.pages}")
    print()

    settled: dict[int, Classification] = {}
    refusals = 0
    for page in pages:
        address = addresses.get(page)
        if address is None:
            refusals += 1
            continue
        try:
            answer = classify(address.url, address.title, host, model)
        except ClassifierUnavailableError as error:
            print(f"the model could not be reached: {error}", file=sys.stderr)
            return EXIT_BAD_INPUT
        if not answer.answered:
            refusals += 1
        settled[page] = answer
        labels = ", ".join(answer.labels) if answer.labels else "-"
        print(f"    {reference_for(address.url, salt)}  {answer.category:<11}  {labels}")

    records: list[dict[str, object]] = []
    for visit in plan.kept:
        reading = settled.get(visit.page)
        address = addresses.get(visit.page)
        if reading is None or address is None:
            continue
        record = {
            "owner": args.owner,
            "platform": args.platform,
            "day": visit.day.isoformat(),
            "reference": reference_for(address.url, salt),
            "category": reading.category,
            "labels": list(reading.labels),
        }
        if record not in records:
            records.append(record)

    print(f"\n  read          {len(records)} readings over {len(settled)} pages")
    if refusals:
        print(f"  refused       {refusals}")
    unlabelled = sum(1 for record in records if record["category"] in UNLABELLED)
    if unlabelled:
        print(f"  counted only  {unlabelled} in a category that carries no labels")

    if not args.apply:
        print(
            "\n  nothing was written. The addresses stayed here and are now"
            "\n  forgotten; add --apply --out <file> to record what is above"
        )
        return EXIT_OK
    if not args.out:
        print("--apply needs --out to say where the records go", file=sys.stderr)
        return EXIT_BAD_INPUT
    destination = Path(args.out).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n  written to    {destination}")
    print("  read it with  uv run kiseki web <that file>")
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kiseki-web",
        description="Turn a browser history the owner named into WebRecord documents.",
    )
    commands = parser.add_subparsers(dest="command")
    plan = commands.add_parser("plan", help="count what is in a window of history, opening no page")
    plan.add_argument("profile", help="the browser profile directory")
    plan.add_argument("--from", dest="since", default=None, help="first day, YYYY-MM-DD")
    plan.add_argument("--to", dest="until", default=None, help="last day, YYYY-MM-DD")
    plan.set_defaults(run=_command_plan)

    read = commands.add_parser("read", help="classify each page, and show what would be recorded")
    read.add_argument("profile", help="the browser profile directory")
    read.add_argument("--from", dest="since", default=None, help="first day, YYYY-MM-DD")
    read.add_argument("--to", dest="until", default=None, help="last day, YYYY-MM-DD")
    read.add_argument("--state", default=".kiseki-web", help="where the salt is kept")
    read.add_argument("--owner", default="me", help="whose reading this is")
    read.add_argument("--platform", default="browser", help="what produced it")
    read.add_argument("--model-host", default=None, help="where the model is")
    read.add_argument("--model", default=None, help="which model classifies")
    read.add_argument("--boundary", default=None, help="same_host, private_network or anywhere")
    read.add_argument("--limit", type=int, default=0, help="stop after this many pages")
    read.add_argument("--apply", action="store_true", help="write the records shown")
    read.add_argument("--out", default=None, help="where the records go")
    read.set_defaults(run=_command_read)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "run", None) is None:
        parser.print_usage(sys.stderr)
        return EXIT_BAD_INPUT
    exit_code: int = args.run(args)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
