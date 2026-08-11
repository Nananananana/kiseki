"""Grouping stops into outings.

An outing is one departure from an anchor and return to it. Anchors are
estimated separately, and on a first pass none are known yet, so this service
accepts them as an argument and falls back on the length of the silences
between stops when the list is empty.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from kiseki.domain.outing.outing import Outing
from kiseki.domain.outing.stop import Stop
from kiseki.domain.shared.geo import GeoArea
from kiseki.domain.shared.settings import OutingSettings


@dataclass(frozen=True)
class OutingAssembly:
    """Every stop appears in exactly one of these two."""

    outings: tuple[Outing, ...]
    at_anchor: tuple[Stop, ...]


def assemble_outings(
    stops: Sequence[Stop],
    anchors: Sequence[GeoArea] = (),
    settings: OutingSettings | None = None,
) -> OutingAssembly:
    """Group stops into outings.

    A stop inside an anchor is not part of any outing: it ends the one in
    progress and is reported separately. Otherwise a silence longer than
    ``max_absence`` starts a new outing, which is the only signal available
    when no anchor is known.
    """
    rules = settings if settings is not None else OutingSettings()
    ordered = sorted(stops, key=lambda stop: stop.time_range.start)

    groups: list[list[Stop]] = []
    at_anchor: list[Stop] = []
    current: list[Stop] | None = None

    for stop in ordered:
        if any(anchor.contains(stop.centroid) for anchor in anchors):
            at_anchor.append(stop)
            current = None
            continue

        if current is not None:
            silence = stop.time_range.start - current[-1].time_range.end
            if silence > rules.max_absence:
                current = None

        if current is None:
            current = []
            groups.append(current)
        current.append(stop)

    return OutingAssembly(tuple(Outing.of(group) for group in groups), tuple(at_anchor))
