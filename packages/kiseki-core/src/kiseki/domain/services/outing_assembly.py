"""Grouping stops into outings.

An outing is a run of stops with no long silence between them. Every stop takes
part; nowhere is dropped for being familiar. Which of them happen to be at a
place the person frequents is answered by the anchors, which annotate rather
than filter.
"""

from collections.abc import Sequence

from kiseki.domain.outing.outing import Outing
from kiseki.domain.outing.stop import Stop
from kiseki.domain.shared.settings import OutingSettings


def assemble_outings(
    stops: Sequence[Stop], settings: OutingSettings | None = None
) -> tuple[Outing, ...]:
    """Group stops into outings, splitting on any silence longer than max_absence."""
    rules = settings if settings is not None else OutingSettings()
    ordered = sorted(stops, key=lambda stop: stop.time_range.start)

    groups: list[list[Stop]] = []
    current: list[Stop] | None = None

    for stop in ordered:
        if current is not None:
            silence = stop.time_range.start - current[-1].time_range.end
            if silence > rules.max_absence:
                current = None
        if current is None:
            current = []
            groups.append(current)
        current.append(stop)

    return tuple(Outing.of(group) for group in groups)
