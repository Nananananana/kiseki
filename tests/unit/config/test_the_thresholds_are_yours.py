"""Ten thresholds, reachable, and each one demonstrably deciding something.

Until #387 there was no way to change any of them. `kiseki build
--help` listed one option and it was `--help`, while
`tools/journeys.py` -- the aid built for tuning them -- took six as
flags. The tuning existed and never reached the command anybody runs.

**A setting that resolves but changes nothing is worse than no
setting**, so this file does not stop at *the value arrives*. Each
threshold is shown moving a real result, measured through
`extract_stops` and `estimate_anchors` rather than asserted:

    min_photographs 3 -> 5          2 stops -> 1
    stay_radius 100 -> 1000 m       1 stop  -> 2   (with drift out of the way)
    night_hours 20,6 -> 8,16        night share 0% -> 100%

The `stay_radius` row needed the drift rule taken out of the way, and
that is worth knowing rather than hiding: at 0.8 km/h a wander of 800
metres is held together by `drift_speed` whatever the radius says. Two
rules, and either can be the one that decided.
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from kiseki.config.derivation import (
    KNOWN,
    MEASURED,
    in_force,
    resolve_derivation_settings,
)
from kiseki.domain.photo.observation import PhotoId, PhotoObservation
from kiseki.domain.services.anchor_estimation import estimate_anchors
from kiseki.domain.services.stop_extraction import extract_stops
from kiseki.domain.shared.geo import GeoPoint

BASE = datetime(2025, 5, 3, 10, 0, tzinfo=UTC)
START = GeoPoint(35.0094, 135.6669)
AWAY = GeoPoint(34.6937, 135.5023)


@pytest.fixture(autouse=True)
def no_inherited_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in [name for name in __import__("os").environ if name.startswith("KISEKI_")]:
        monkeypatch.delenv(key)


def resolve(**values: str):  # type: ignore[no-untyped-def]
    return resolve_derivation_settings(values, dotenv=None)


def wandering(metres_per_step: float, steps: int = 12) -> list[PhotoObservation]:
    """A visit that drifts. Whether it is one stay or several is
    exactly what the thresholds are for."""
    return [
        PhotoObservation(
            PhotoId(f"sha256:{step:04d}"),
            BASE + timedelta(minutes=5 * step),
            GeoPoint(START.latitude + step * metres_per_step / 111_194.9, START.longitude),
        )
        for step in range(steps)
    ]


def a_brief_pause(count: int) -> list[PhotoObservation]:
    return [
        PhotoObservation(
            PhotoId(f"sha256:9{step:03d}"),
            BASE + timedelta(hours=4, minutes=step),
            AWAY,
        )
        for step in range(count)
    ]


class TestEachThresholdDecidesSomething:
    """The half that matters. A setting that resolves and changes
    nothing is a setting nobody can use."""

    def stops(self, **values: str) -> int:
        settings = resolve(min_duration_minutes="999", **values)
        observations = wandering(70) + a_brief_pause(3)
        return len(extract_stops(observations, settings.stops).stops)

    def test_min_photographs_decides_whether_a_brief_pause_is_a_stay(self) -> None:
        assert self.stops(min_photographs="3") == 2
        assert self.stops(min_photographs="5") == 1

    def test_stay_radius_decides_whether_a_wander_is_one_visit(self) -> None:
        """With the drift rule out of the way, so the radius is what
        decides -- otherwise 0.8 km/h holds the wander together
        whatever the radius says, and this would pass for the wrong
        reason."""
        tight = {"drift_speed_kmh": "0.001", "min_photographs": "3"}
        assert self.stops(stay_radius_m="100", **tight) == 1
        assert self.stops(stay_radius_m="1000", **tight) == 2

    def test_drift_speed_decides_when_the_radius_does_not(self) -> None:
        """The other half of the pair above, with the radius at one
        metre so only the speed can hold anything together.

        Written the other way round first, from reasoning rather than
        running it. The wander moves at 0.84 km/h: refuse that and its
        twelve photographs become twelve groups of one, none of which
        reaches three, so only the stationary pause survives. Allow it
        and the wander is a stay too -- and the four-hour silence
        before the pause makes that a second one.
        """
        wide = {"stay_radius_m": "1", "min_photographs": "3"}
        assert self.stops(drift_speed_kmh="0.001", **wide) == 1
        assert self.stops(drift_speed_kmh="10", **wide) == 2

    def test_max_gap_ends_a_stay(self) -> None:
        far_apart = [
            PhotoObservation(PhotoId("sha256:a"), BASE, START),
            PhotoObservation(PhotoId("sha256:b"), BASE + timedelta(hours=2), START),
        ]
        settings = resolve(min_duration_minutes="999", min_photographs="2")
        assert len(extract_stops(far_apart, settings.stops).stops) == 0
        wider = resolve(min_duration_minutes="999", min_photographs="2", max_gap_minutes="180")
        assert len(extract_stops(far_apart, wider.stops).stops) == 1

    def test_night_hours_decides_what_a_place_looks_like(self) -> None:
        """The sharpest one, and not a tuning problem.

        An anchor is deliberately never named: the design's answer to
        *is this a home or a workplace* is that the night share speaks
        for itself. For a night-shift worker the default inverts it,
        and the library describes their workplace with the shares that
        mean home.
        """
        daytime = [
            PhotoObservation(
                PhotoId(f"sha256:{day:02d}{hour:02d}"),
                datetime(2025, 5, day, hour, 0, tzinfo=UTC),
                START,
            )
            for day in range(1, 15)
            for hour in (10, 11, 12)
        ]
        stops = extract_stops(daytime, resolve(min_photographs="2").stops).stops

        office = estimate_anchors(stops, resolve(min_visits="3").anchors)
        night_shift = estimate_anchors(stops, resolve(min_visits="3", night_hours="8,16").anchors)
        assert office and night_shift
        assert office[0].night_share == 0.0
        assert night_shift[0].night_share == 1.0, (
            "the same place, described the other way round, which is the point"
        )


class TestTheLayers:
    def test_the_default_is_what_it_always_was(self) -> None:
        settings = resolve()
        assert settings.stops.stay_radius.meters == 300
        assert settings.stops.min_photographs == 5

    def test_an_override_wins(self) -> None:
        assert resolve(stay_radius_m="750").stops.stay_radius.meters == 750

    def test_the_environment_is_read(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("KISEKI_DERIVATION_MIN_VISITS", "12")
        assert resolve().anchors.min_visits == 12

    def test_kiseki_toml_is_read(self, tmp_path: Path) -> None:
        (tmp_path / "kiseki.toml").write_text(
            "[derivation]\nstay_radius_m = 42\n", encoding="utf-8"
        )
        settings = resolve_derivation_settings(dotenv=tmp_path / ".env")
        assert settings.stops.stay_radius.meters == 42

    def test_the_command_line_beats_the_file(self, tmp_path: Path) -> None:
        (tmp_path / "kiseki.toml").write_text(
            "[derivation]\nstay_radius_m = 42\n", encoding="utf-8"
        )
        settings = resolve_derivation_settings({"stay_radius_m": "99"}, dotenv=tmp_path / ".env")
        assert settings.stops.stay_radius.meters == 99


class TestSayingWhereItCameFrom:
    """A reader whose answers look wrong needs to know whether it is
    their data or their configuration."""

    def test_a_default_says_default(self) -> None:
        rows = {name: source for name, _, source, _ in in_force(resolve())}
        assert set(rows.values()) == {"default"}

    def test_an_override_says_command_line(self) -> None:
        rows = {name: source for name, _, source, _ in in_force(resolve(min_visits="9"))}
        assert rows["min_visits"] == "command line"
        assert rows["stay_radius_m"] == "default"

    def test_every_setting_carries_its_provenance(self) -> None:
        """Four of the ten were measured and six were chosen. A reader
        arguing with a number should know which kind it is."""
        for name, _, _, note in in_force(resolve()):
            assert note == KNOWN[name]
            assert note, f"{name} says nothing about where its default came from"

    def test_the_measured_ones_are_the_ones_adr_0006_measured(self) -> None:
        # `note == MEASURED`, not `"measured" in note`: the other
        # string is "chosen, not measured", which contains the word.
        # Written the substring way first, and it matched all ten.
        measured = {name for name, note in KNOWN.items() if note == MEASURED}
        assert measured == {
            "stay_radius_m",
            "drift_speed_kmh",
            "max_gap_minutes",
            "min_duration_minutes",
            "min_photographs",
        }


class TestRefusals:
    def test_an_unknown_setting_is_refused_rather_than_ignored(self) -> None:
        """A typo that silently does nothing leaves a reader believing
        they changed something."""
        with pytest.raises(ValueError, match="not recognised"):
            resolve(stay_radius="300")

    def test_the_refusal_lists_what_is_known(self) -> None:
        with pytest.raises(ValueError) as raised:
            resolve(nonsense="1")
        for name in KNOWN:
            assert name in str(raised.value)

    def test_a_value_that_is_not_a_number_is_refused(self) -> None:
        with pytest.raises(ValueError, match="takes a number"):
            resolve(stay_radius_m="wide")

    def test_hours_outside_a_day_are_refused(self) -> None:
        with pytest.raises(ValueError, match="not an hour"):
            resolve(night_hours="20,30")

    def test_one_hour_where_two_are_needed_is_refused(self) -> None:
        with pytest.raises(ValueError, match="two hours"):
            resolve(night_hours="20")

    def test_a_value_the_domain_refuses_still_refuses(self) -> None:
        """The dataclasses validate too, and this checks the two are
        not talking past each other."""
        with pytest.raises(ValueError):
            resolve(min_photographs="0")
