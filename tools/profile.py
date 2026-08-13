"""Print what a photo library says about the person who made it.

Runs the whole v0.1 pipeline over a PhotoRecord document and reports the
measures. A development aid for checking the analytics against a real library;
the proper command line interface arrives in issue #15.

    uv run python tools/profile.py records.json
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from kiseki.domain.analytics.analytics import (
    Rhythm,
    Spread,
    summarise_habits,
    summarise_places,
    summarise_rhythm,
)
from kiseki.domain.photo.observation import PhotoId, PhotoObservation
from kiseki.domain.services.anchor_estimation import estimate_anchors
from kiseki.domain.services.outing_assembly import assemble_outings
from kiseki.domain.services.stop_extraction import extract_stops
from kiseki.domain.shared.geo import Distance, GeoPoint
from kiseki.domain.shared.settings import AnchorSettings, OutingSettings, StopSettings
from kiseki.domain.shared.speed import Speed

HEAVY = "=" * 74
LIGHT = "-" * 74
BAR_WIDTH = 34


def load(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = json.loads(path.read_text(encoding="utf-8"))["records"]
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


def show_spread(label: str, spread: Spread, unit: str) -> None:
    print(
        f"  {label:22} median {spread.median:7.1f} {unit:4} "
        f" mean {spread.mean:7.1f}  range {spread.minimum:.1f} to {spread.maximum:.1f}"
    )


def show_bar(label: str, value: int, largest: int) -> None:
    filled = int(BAR_WIDTH * value / largest) if largest else 0
    print(f"  {label:>5} {'#' * filled:<{BAR_WIDTH}} {value}")


def show_rhythm(rhythm: Rhythm) -> None:
    print()
    print(HEAVY)
    print("WHEN THEY GO OUT")
    print(LIGHT)
    print(f"  weekend share          {rhythm.weekend_share:.0%}")
    print(f"  early start share      {rhythm.early_start_share:.0%}")

    print("\n  by weekday")
    largest = max(rhythm.by_weekday.values(), default=0)
    for day, count in rhythm.by_weekday.items():
        show_bar(day, count, largest)

    print("\n  by departure hour")
    active = {hour: count for hour, count in rhythm.by_departure_hour.items() if count}
    largest = max(active.values(), default=0)
    for hour, count in active.items():
        show_bar(f"{hour:02d}", count, largest)

    print("\n  by month")
    largest = max(rhythm.by_month.values(), default=0)
    for month, count in rhythm.by_month.items():
        show_bar(month[2:], count, largest)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Summarise what a photo library says about its photographer."
    )
    parser.add_argument("records", type=Path)
    parser.add_argument("--from", dest="since", default=None, metavar="YYYY-MM-DD")
    parser.add_argument("--to", dest="until", default=None, metavar="YYYY-MM-DD")
    parser.add_argument("--photos-only", action="store_true")
    parser.add_argument("--place-radius", type=float, default=500, metavar="METRES")
    parser.add_argument("--stay-radius", type=float, default=300, metavar="METRES")
    parser.add_argument("--drift-speed", type=float, default=1.5, metavar="KMH")
    parser.add_argument("--min-photographs", type=int, default=5)
    parser.add_argument("--min-visits", type=int, default=5)
    parser.add_argument("--top", type=int, default=10)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    observations = to_observations(load(args.records), args.photos_only)
    if args.since:
        start = datetime.fromisoformat(args.since).date()
        observations = [item for item in observations if item.captured_at.date() >= start]
    if args.until:
        end = datetime.fromisoformat(args.until).date()
        observations = [item for item in observations if item.captured_at.date() <= end]
    if not observations:
        print("no photographs in that range", file=sys.stderr)
        return 1

    extraction = extract_stops(
        observations,
        StopSettings(
            stay_radius=Distance(args.stay_radius),
            drift_speed=Speed.from_kilometers_per_hour(args.drift_speed),
            min_photographs=args.min_photographs,
        ),
    )
    anchors = estimate_anchors(extraction.stops, AnchorSettings(min_visits=args.min_visits))
    outings = assemble_outings(extraction.stops, OutingSettings())

    moments = sorted(item.captured_at for item in observations)
    days = (moments[-1] - moments[0]).days or 1

    print(HEAVY)
    print("WHAT WAS READ")
    print(LIGHT)
    print(f"  photographs            {len(observations)}")
    print(f"  period                 {moments[0]:%Y-%m-%d} to {moments[-1]:%Y-%m-%d} ({days} days)")
    print(f"  stops                  {len(extraction.stops)}")
    print(f"  outings                {len(outings)}")
    print(f"  in transit             {len(extraction.in_transit)}")
    print(f"  without coordinates    {len(extraction.unlocated)}")

    print()
    print(HEAVY)
    print("PLACES THEY KEEP RETURNING TO")
    print(LIGHT)
    if not anchors:
        print("  no place was photographed on enough separate days")
    for anchor in anchors:
        print(
            f"  ({anchor.area.center.latitude:.4f}, {anchor.area.center.longitude:.4f})"
            f"  {anchor.visit_days:>4} days  {anchor.photograph_count:>5} photos"
            f"   night {anchor.night_share:>4.0%}  weekday {anchor.weekday_share:>4.0%}"
            f"  daytime {anchor.daytime_share:>4.0%}"
        )

    if not outings:
        print("\nno outings away from an anchor were found")
        return 0

    print()
    print(HEAVY)
    print("WHAT THEY SEEK OUT")
    print(LIGHT)
    preference = summarise_places(outings, Distance(args.place_radius), top=args.top)
    print(f"  distinct places        {len(preference.places)}")
    print(f"  never returned to      {preference.one_time_rate:.0%}")
    print(f"  returned to            {preference.return_rate:.0%}")
    if preference.most_returned_to:
        print("\n  places worth going back to")
        for place in preference.most_returned_to:
            print(
                f"    ({place.centre.latitude:.4f}, {place.centre.longitude:.4f})"
                f"  {place.visit_days:>3} days  {place.photograph_count:>5} photos"
                f"  {place.first_visit} to {place.last_visit}"
            )

    print()
    print(HEAVY)
    print("HOW THEY SPEND A DAY OUT")
    print(LIGHT)
    habits = summarise_habits(outings)
    show_spread("distance covered", habits.travel_km, "km")
    show_spread("time out", habits.duration_hours, "h")
    show_spread("places per outing", habits.stops_per_outing, "")
    show_spread("time at each place", habits.stay_minutes, "min")
    show_spread("photographs taken", habits.photographs_per_outing, "")

    show_rhythm(summarise_rhythm(outings))
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
