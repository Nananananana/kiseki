"""Print the journeys implied by a PhotoRecord document.

A development aid for checking stop extraction and outing assembly against a
real photo library. Every threshold is exposed as an argument so that tuning is
a matter of running the command again rather than editing code.

    uv run python tools/journeys.py records.json --from 2025-05-03 --to 2025-05-03 --verbose

The proper command line interface arrives in issue #15.
"""

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from kiseki.domain.outing.outing import Outing
from kiseki.domain.photo.observation import PhotoId, PhotoObservation
from kiseki.domain.services.outing_assembly import assemble_outings
from kiseki.domain.services.stop_extraction import extract_stops
from kiseki.domain.shared.geo import Distance, GeoPoint
from kiseki.domain.shared.settings import OutingSettings, StopSettings
from kiseki.domain.shared.speed import Speed

RULE = "-" * 78


def load(path: Path) -> list[dict[str, Any]]:
    document = json.loads(path.read_text(encoding="utf-8"))
    records: list[dict[str, Any]] = document["records"]
    return records


def to_observations(records: list[dict[str, Any]], photos_only: bool) -> list[PhotoObservation]:
    observations = []
    for record in records:
        if photos_only and record.get("content_kind") != "photo":
            continue
        place = record.get("location")
        observations.append(
            PhotoObservation(
                PhotoId(record["id"]),
                datetime.fromisoformat(record["captured_at"]),
                GeoPoint(place["lat"], place["lon"]) if place else None,
            )
        )
    return observations


def summarise_input(records: list[dict[str, Any]]) -> None:
    kinds = Counter(record.get("content_kind", "?") for record in records)
    located = sum(1 for record in records if record.get("location"))
    moments = sorted(datetime.fromisoformat(record["captured_at"]) for record in records)

    print(RULE)
    print(f"records            {len(records)}")
    print(f"with coordinates   {located} ({located / len(records):.0%})")
    print(f"content kinds      {dict(kinds)}")
    print(f"date range         {moments[0]:%Y-%m-%d} to {moments[-1]:%Y-%m-%d}")


def report_outing(outing: Outing, index: int, verbose: bool) -> None:
    span = outing.time_range
    same_day = span.start.date() == span.end.date()
    when = (
        f"{span.start:%Y-%m-%d %H:%M}-{span.end:%H:%M}"
        if same_day
        else f"{span.start:%Y-%m-%d %H:%M} - {span.end:%m-%d %H:%M}"
    )
    print(
        f"\n[{index:>3}] {when}  "
        f"{outing.stop_count} stops, {outing.photograph_count} photos, "
        f"{outing.travelled.kilometers:.1f} km"
    )
    if not verbose:
        return
    for stop in outing.stops:
        minutes = int(stop.duration.total_seconds() // 60)
        print(
            f"        {stop.time_range.start:%H:%M}-{stop.time_range.end:%H:%M} "
            f"({minutes:>4} min, {stop.photograph_count:>3} photos)  "
            f"{stop.centroid.latitude:.5f}, {stop.centroid.longitude:.5f}"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Reconstruct journeys from a PhotoRecord document and print them."
    )
    parser.add_argument("records", type=Path)
    parser.add_argument("--from", dest="since", default=None, metavar="YYYY-MM-DD")
    parser.add_argument("--to", dest="until", default=None, metavar="YYYY-MM-DD")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--min-stops", type=int, default=1)
    parser.add_argument("--verbose", action="store_true", help="list every stop")
    parser.add_argument("--photos-only", action="store_true")
    parser.add_argument("--stay-radius", type=float, default=150, metavar="METRES")
    parser.add_argument("--drift-speed", type=float, default=1.5, metavar="KMH")
    parser.add_argument("--max-gap", type=int, default=90, metavar="MINUTES")
    parser.add_argument("--min-duration", type=int, default=10, metavar="MINUTES")
    parser.add_argument("--min-photographs", type=int, default=3)
    parser.add_argument("--max-absence", type=int, default=8, metavar="HOURS")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    records = load(args.records)
    if not records:
        print("the document contains no records", file=sys.stderr)
        return 1

    summarise_input(records)
    observations = to_observations(records, args.photos_only)

    if args.since:
        start = datetime.fromisoformat(args.since).date()
        observations = [item for item in observations if item.captured_at.date() >= start]
    if args.until:
        end = datetime.fromisoformat(args.until).date()
        observations = [item for item in observations if item.captured_at.date() <= end]

    if not observations:
        print("\nno photographs in that range", file=sys.stderr)
        return 1

    stop_settings = StopSettings(
        stay_radius=Distance(args.stay_radius),
        drift_speed=Speed.from_kilometers_per_hour(args.drift_speed),
        max_gap=timedelta(minutes=args.max_gap),
        min_duration=timedelta(minutes=args.min_duration),
        min_photographs=args.min_photographs,
    )
    extraction = extract_stops(observations, stop_settings)
    outings = assemble_outings(
        extraction.stops,
        settings=OutingSettings(max_absence=timedelta(hours=args.max_absence)),
    )

    considered = len(observations)
    in_stops = sum(stop.photograph_count for stop in extraction.stops)
    print(RULE)
    print(f"considered         {considered}")
    print(f"in stops           {in_stops} ({in_stops / considered:.0%})")
    print(f"in transit         {len(extraction.in_transit)}")
    print(f"no coordinates     {len(extraction.unlocated)}")
    print(f"stops              {len(extraction.stops)}")
    print(f"outings            {len(outings)}")

    shown = [outing for outing in outings if outing.stop_count >= args.min_stops]
    print(RULE)
    print(f"showing {min(len(shown), args.limit)} of {len(shown)} outings")
    for index, outing in enumerate(shown[: args.limit], start=1):
        report_outing(outing, index, args.verbose)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
