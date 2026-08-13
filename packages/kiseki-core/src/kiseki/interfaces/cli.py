"""Command line interface.

Composition happens here and nowhere else: this is the only place that decides
SQLite is the storage and where the database sits. Everything below it is given
what it needs.
"""

import argparse
import json
import sys
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

from kiseki.adapters.sqlite.store import (
    SqliteAnchorRepository,
    SqliteOutingRepository,
    SqlitePhotoRepository,
    connect,
)
from kiseki.application.pipeline import Pipeline, Report
from kiseki.config.paths import StoragePaths, resolve_paths
from kiseki.domain.interests import Profile
from kiseki.domain.photo.observation import PhotoId, PhotoObservation
from kiseki.domain.shared.geo import GeoPoint

EXIT_OK = 0
EXIT_BAD_INPUT = 2
RULE = "-" * 70
DOTENV = Path(".env")


def _read_records(path: Path) -> list[dict[str, Any]]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or "records" not in document:
        raise ValueError("not a PhotoRecord document: no 'records' key")
    records = document["records"]
    if not isinstance(records, list):
        raise ValueError("not a PhotoRecord document: 'records' is not a list")
    return records


def _to_observations(records: list[dict[str, Any]]) -> list[PhotoObservation]:
    observations = []
    for record in records:
        place = record.get("location")
        observations.append(
            PhotoObservation(
                PhotoId(record["id"]),
                datetime.fromisoformat(record["captured_at"]),
                GeoPoint(place["lat"], place["lon"]) if place else None,
            )
        )
    return observations


def _paths_for(args: argparse.Namespace) -> StoragePaths:
    return resolve_paths({"data_root": args.data_root or ""}, dotenv=DOTENV)


def _pipeline_for(args: argparse.Namespace) -> Pipeline:
    connection = connect(_paths_for(args).db_path)
    return Pipeline(
        SqlitePhotoRepository(connection),
        SqliteOutingRepository(connection),
        SqliteAnchorRepository(connection),
    )


def _command_paths(args: argparse.Namespace) -> int:
    for name, value in vars(_paths_for(args)).items():
        print(f"  {name:14} {value}")
    return EXIT_OK


def _command_ingest(args: argparse.Namespace) -> int:
    try:
        records = _read_records(args.records)
    except OSError as error:
        print(f"cannot read {args.records}: {error}", file=sys.stderr)
        return EXIT_BAD_INPUT
    except (json.JSONDecodeError, ValueError) as error:
        print(f"{args.records}: {error}", file=sys.stderr)
        return EXIT_BAD_INPUT

    stored = _pipeline_for(args).ingest(_to_observations(records))
    print(f"{stored} photograph(s) taken in")
    return EXIT_OK


def _command_build(args: argparse.Namespace) -> int:
    result = _pipeline_for(args).rebuild()
    print(RULE)
    print(f"  photographs   {result.photographs}")
    print(f"  stops         {result.stops}")
    print(f"  outings       {result.outings}")
    print(f"  anchors       {result.anchors}")
    print(f"  in transit    {result.in_transit}")
    print(f"  unlocated     {result.unlocated}")
    return EXIT_OK


def _payload(report: Report) -> dict[str, Any]:
    habits = report.habits
    return {
        "photographs": report.photographs,
        "outings": len(report.outings),
        "anchors": [
            {
                "latitude": anchor.area.center.latitude,
                "longitude": anchor.area.center.longitude,
                "visit_days": anchor.visit_days,
                "night_share": anchor.night_share,
                "weekday_share": anchor.weekday_share,
                "daytime_share": anchor.daytime_share,
                "photograph_count": anchor.photograph_count,
            }
            for anchor in report.anchors
        ],
        "places": {
            "distinct": len(report.places.places),
            "return_rate": report.places.return_rate,
            "one_time_rate": report.places.one_time_rate,
        },
        "habits": None
        if habits is None
        else {
            "travel_km_median": habits.travel_km.median,
            "duration_hours_median": habits.duration_hours.median,
            "stops_per_outing_median": habits.stops_per_outing.median,
            "stay_minutes_median": habits.stay_minutes.median,
        },
        "rhythm": {
            "weekend_share": report.rhythm.weekend_share,
            "early_start_share": report.rhythm.early_start_share,
            "by_weekday": report.rhythm.by_weekday,
            "by_month": report.rhythm.by_month,
        },
    }


def _print_report(report: Report) -> None:
    print(RULE)
    print(f"  photographs   {report.photographs}")
    print(f"  outings       {len(report.outings)}")

    if report.anchors:
        print("\n  places returned to")
        for anchor in report.anchors:
            print(
                f"    ({anchor.area.center.latitude:.4f},"
                f" {anchor.area.center.longitude:.4f})"
                f"  {anchor.visit_days:>4} days"
                f"  night {anchor.night_share:>4.0%}"
                f"  weekday {anchor.weekday_share:>4.0%}"
                f"  daytime {anchor.daytime_share:>4.0%}"
            )

    if report.places.places:
        print(f"\n  distinct places    {len(report.places.places)}")
        print(f"  never returned to  {report.places.one_time_rate:.0%}")

    if report.habits is not None:
        print(f"\n  distance covered   median {report.habits.travel_km.median:.1f} km")
        print(f"  time out           median {report.habits.duration_hours.median:.1f} h")
        print(f"  places per outing  median {report.habits.stops_per_outing.median:.1f}")
        print(f"\n  weekend share      {report.rhythm.weekend_share:.0%}")


def _command_report(args: argparse.Namespace) -> int:
    report = _pipeline_for(args).report()
    if args.json:
        print(json.dumps(_payload(report), indent=2))
    else:
        _print_report(report)
    return EXIT_OK


def _profile_payload(profile: Profile) -> dict[str, Any]:
    return {
        "generated_at": profile.generated_at.isoformat(),
        "interests": [
            {
                "topic": interest.topic,
                "score": interest.score,
                "confidence": interest.confidence,
                "first_seen": interest.first_seen.isoformat(),
                "last_seen": interest.last_seen.isoformat(),
                "evidence": [
                    {
                        "kind": evidence.kind.value,
                        "reference": evidence.reference,
                        "observed_at": evidence.observed_at.isoformat(),
                    }
                    for evidence in interest.evidence
                ],
            }
            for interest in profile.ranked()
        ],
    }


def _print_profile(profile: Profile) -> None:
    print(RULE)
    print(f"  interests     {len(profile.interests)}")

    if profile.interests:
        print("\n  places returned to, read as interests")
        for interest in profile.ranked():
            print(
                f"    {interest.topic:<32}"
                f"  score {interest.score:>5.2f}"
                f"  confidence {interest.confidence:>5.2f}"
                f"  evidence {len(interest.evidence)}"
            )


def _command_profile(args: argparse.Namespace) -> int:
    profile = _pipeline_for(args).profile()
    if args.json:
        print(json.dumps(_profile_payload(profile), indent=2))
    else:
        _print_profile(profile)
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kiseki",
        description="Reconstruct journeys from photo timelines and measure them.",
    )
    parser.add_argument("--data-root", default=None, help="override where everything is stored")
    commands = parser.add_subparsers(dest="command")

    commands.add_parser("paths", help="show where things will be stored").set_defaults(
        run=_command_paths
    )

    ingest = commands.add_parser("ingest", help="take in a PhotoRecord document")
    ingest.add_argument("records", type=Path)
    ingest.set_defaults(run=_command_ingest)

    commands.add_parser("build", help="recompute stops, outings and anchors").set_defaults(
        run=_command_build
    )

    report = commands.add_parser("report", help="print what the measures say")
    report.add_argument("--json", action="store_true", help="machine readable output")
    report.set_defaults(run=_command_report)

    profile = commands.add_parser("profile", help="read the measures as interests")
    profile.add_argument("--json", action="store_true", help="machine readable output")
    profile.set_defaults(run=_command_profile)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if getattr(args, "run", None) is None:
        parser.print_usage(sys.stderr)
        return EXIT_BAD_INPUT

    exit_code: int = args.run(args)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
