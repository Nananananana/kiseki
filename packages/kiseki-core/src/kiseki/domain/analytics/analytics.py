"""Measures of how a person spends their time.

Everything here counts and summarises. Nothing here interprets: the sentences a
preference profile eventually says about someone are written in v0.2 by a
language model reading these numbers, not by the numbers themselves. Keeping the
split sharp means the measures stay testable against exact values, and the
interpretation stays replaceable.

The measures were chosen to describe habits rather than journeys. Where someone
went is a fact about a place; how far they tend to go, how much they pack into a
day, and whether they return to what they liked are facts about them.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from kiseki.domain.outing.outing import Outing
from kiseki.domain.outing.stop import Stop
from kiseki.domain.shared.geo import Distance, GeoPoint

WEEKEND = (5, 6)
DAY_NAMES = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
DEFAULT_EARLY_HOUR = 9
DEFAULT_HIGHLIGHT_COUNT = 5


@dataclass(frozen=True)
class Spread:
    """A distribution summarised without a statistics dependency.

    Both the median and the mean are reported because they disagree in a way
    that matters here. One holiday abroad shifts the mean distance of a year's
    outings enormously while leaving the median where it belongs, and the median
    is the better description of a habit.
    """

    count: int
    minimum: float
    median: float
    mean: float
    maximum: float

    @classmethod
    def of(cls, values: Sequence[float]) -> "Spread":
        if not values:
            raise ValueError("cannot summarise an empty sequence")
        ordered = sorted(values)
        middle = len(ordered) // 2
        median = (
            ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2
        )
        return cls(
            count=len(ordered),
            minimum=ordered[0],
            median=median,
            mean=sum(ordered) / len(ordered),
            maximum=ordered[-1],
        )


@dataclass(frozen=True)
class PlaceVisits:
    """A place, and how a person's interest in it played out over time."""

    centre: GeoPoint
    visit_days: int
    first_visit: date
    last_visit: date
    photograph_count: int

    @property
    def was_returned_to(self) -> bool:
        """Going back is the clearest statement of having liked somewhere."""
        return self.visit_days > 1

    @property
    def photographs_per_visit(self) -> float:
        return self.photograph_count / self.visit_days


@dataclass(frozen=True)
class PlacePreference:
    """What a pattern of visits says, independent of where the places are.

    The one time rate is the measure that carries the most about a person. A
    library where most places were visited once describes someone who keeps
    looking for somewhere new; a low rate describes someone who has found what
    they like. Neither is visible from any single photograph.
    """

    places: tuple[PlaceVisits, ...]
    return_rate: float
    one_time_rate: float
    most_returned_to: tuple[PlaceVisits, ...]


@dataclass(frozen=True)
class OutingHabits:
    """How a person's time away tends to be shaped."""

    outing_count: int
    travel_km: Spread
    duration_hours: Spread
    stops_per_outing: Spread
    stay_minutes: Spread
    photographs_per_outing: Spread


@dataclass(frozen=True)
class Rhythm:
    """When a person tends to go out.

    The distributions cover every weekday and every hour, including the empty
    ones, so that a consumer can render a full week or a full day without having
    to fill in gaps.
    """

    by_weekday: dict[str, int]
    by_departure_hour: dict[int, int]
    by_month: dict[str, int]
    weekend_share: float
    early_start_share: float


def _centre(stops: Sequence[Stop]) -> GeoPoint:
    return GeoPoint(
        sum(stop.centroid.latitude for stop in stops) / len(stops),
        sum(stop.centroid.longitude for stop in stops) / len(stops),
    )


def _group_by_place(outings: Sequence[Outing], radius: Distance) -> list[list[Stop]]:
    groups: list[list[Stop]] = []
    for outing in outings:
        for stop in outing.stops:
            for group in groups:
                if _centre(group).distance_to(stop.centroid) <= radius:
                    group.append(stop)
                    break
            else:
                groups.append([stop])
    return groups


def summarise_places(
    outings: Sequence[Outing],
    radius: Distance,
    top: int = DEFAULT_HIGHLIGHT_COUNT,
) -> PlacePreference:
    """Group stops across outings into places and measure the return pattern.

    Visits are counted as distinct days. Photographing a place in the morning and
    again in the evening is one day of evidence for liking it, not two.
    """
    places = []
    for group in _group_by_place(outings, radius):
        days = sorted({stop.time_range.start.date() for stop in group})
        places.append(
            PlaceVisits(
                centre=_centre(group),
                visit_days=len(days),
                first_visit=days[0],
                last_visit=days[-1],
                photograph_count=sum(stop.photograph_count for stop in group),
            )
        )

    ranked = tuple(
        sorted(places, key=lambda place: (place.visit_days, place.photograph_count), reverse=True)
    )
    if not ranked:
        return PlacePreference((), 0.0, 0.0, ())

    returned = sum(1 for place in ranked if place.was_returned_to)
    return PlacePreference(
        places=ranked,
        return_rate=returned / len(ranked),
        one_time_rate=(len(ranked) - returned) / len(ranked),
        most_returned_to=tuple(place for place in ranked[:top] if place.was_returned_to),
    )


def summarise_habits(outings: Sequence[Outing]) -> OutingHabits:
    """Measure the shape of a person's outings.

    Raises rather than returning zeros for an empty input: a summary full of
    zeros reads as a person with no habits, which is a different claim from
    having no data about them.
    """
    if not outings:
        raise ValueError("cannot summarise habits without outings")

    return OutingHabits(
        outing_count=len(outings),
        travel_km=Spread.of([outing.travelled.kilometers for outing in outings]),
        duration_hours=Spread.of([outing.duration.total_seconds() / 3600 for outing in outings]),
        stops_per_outing=Spread.of([float(outing.stop_count) for outing in outings]),
        stay_minutes=Spread.of(
            [stop.duration.total_seconds() / 60 for outing in outings for stop in outing.stops]
        ),
        photographs_per_outing=Spread.of([float(outing.photograph_count) for outing in outings]),
    )


def summarise_rhythm(outings: Sequence[Outing], early_hour: int = DEFAULT_EARLY_HOUR) -> Rhythm:
    """Measure when a person goes out.

    Unlike habits, an empty input is answered with zeros rather than an error,
    because the distributions are shapes to be rendered and an empty week is a
    meaningful thing to draw.
    """
    weekdays = dict.fromkeys(DAY_NAMES, 0)
    hours = dict.fromkeys(range(24), 0)
    months: dict[str, int] = {}

    for outing in outings:
        start = outing.time_range.start
        weekdays[DAY_NAMES[start.weekday()]] += 1
        hours[start.hour] += 1
        month = f"{start:%Y-%m}"
        months[month] = months.get(month, 0) + 1

    total = len(outings)
    weekend = sum(1 for outing in outings if outing.time_range.start.weekday() in WEEKEND)
    early = sum(1 for outing in outings if outing.time_range.start.hour < early_hour)

    return Rhythm(
        by_weekday=weekdays,
        by_departure_hour=hours,
        by_month=dict(sorted(months.items())),
        weekend_share=weekend / total if total else 0.0,
        early_start_share=early / total if total else 0.0,
    )
