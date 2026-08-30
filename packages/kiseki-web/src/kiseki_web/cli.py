"""The web producer, at the command line.

`plan` looks and counts. `read` classifies and writes, and is not here
yet: it needs a model, and a model needs the trust boundary settled
(ADR-0073). Planning needs neither, which is why it comes first -- the
owner can point this at a real browser profile today and see exactly
what it would consider, with no page opened and nothing sent.

Nothing printed here names a page. Not a URL, not a title, not a host,
not in a dry run and not in a summary. The contract discards them, and
a producer that showed them while planning has shown them.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

from kiseki_web.reader import (
    ABANDONED,
    DWELL_FLOOR,
    UnreadableHistoryError,
    history_in,
    read_window,
)

EXIT_OK = 0
EXIT_BAD_INPUT = 2

RULE = "-" * 70

DEFAULT_WINDOW_DAYS = 30


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
