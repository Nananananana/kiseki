"""The self-contained view: one HTML file that talks to no one.

No tiles, no CDN, no script sources -- the tests pin that promise as
a string property of the output. Coordinates appear only on the blur
grid, and topic labels blur unless raw is asked for.
See ADR-0027.
"""

from datetime import UTC, datetime, timedelta

from kiseki.application.pipeline import Report
from kiseki.domain.analytics.analytics import summarise_places, summarise_rhythm
from kiseki.domain.interests import (
    EvidenceKind,
    Interest,
    InterestEvidence,
    Profile,
)
from kiseki.domain.photo.observation import PhotoId, PhotoObservation
from kiseki.domain.shared.geo import Distance, GeoPoint
from kiseki.domain.trends import TopicTrend, TrendDirection, TrendReport
from kiseki.interfaces.view import density_cells, render_view

AT = datetime(2026, 6, 1, 12)
PLACE = "place:35.68123,139.76543"
BLURRED = "place:35.68,139.77"


def _photo(identifier: str, latitude: float | None, longitude: float | None) -> PhotoObservation:
    location = GeoPoint(latitude, longitude) if latitude is not None else None
    return PhotoObservation(
        PhotoId(identifier),
        datetime(2026, 6, 1, 12, tzinfo=UTC),
        location,
        thumbnail_ref=None,
    )


def _report() -> Report:
    return Report(
        photographs=0,
        anchors=(),
        outings=(),
        places=summarise_places((), Distance(500)),
        habits=None,
        rhythm=summarise_rhythm(()),
    )


def _interest(topic: str, score: float = 0.5, confidence: float = 0.4) -> Interest:
    evidence = (
        InterestEvidence(
            kind=EvidenceKind.PHOTOGRAPH,
            reference=f"caption:{topic}",
            observed_at=AT,
        ),
    )
    return Interest(
        topic=topic,
        score=score,
        confidence=confidence,
        evidence=evidence,
        first_seen=AT,
        last_seen=AT,
    )


def _trend() -> TrendReport:
    return TrendReport(
        baseline_at=AT,
        latest_at=AT + timedelta(days=20),
        trends=(
            TopicTrend(
                topic=PLACE,
                direction=TrendDirection.RISING,
                strength=0.54,
                baseline=0.2,
            ),
        ),
    )


def _render(
    photos: tuple[PhotoObservation, ...] = (),
    interests: tuple[Interest, ...] = (),
    trends: TrendReport | None = None,
    blur: bool = True,
) -> str:
    profile = Profile(generated_at=AT, interests=interests)
    return render_view(photos, _report(), profile, trends, blur=blur)


class TestDensityCells:
    def test_gathers_photographs_on_the_blur_grid(self) -> None:
        cells = density_cells(
            (
                _photo("a", 35.68123, 139.76143),
                _photo("b", 35.68201, 139.76201),
            )
        )
        assert cells == {(35.68, 139.76): 2}

    def test_unlocated_photographs_are_left_out(self) -> None:
        assert density_cells((_photo("a", None, None),)) == {}


class TestRenderView:
    def test_the_file_talks_to_no_one(self) -> None:
        page = _render(
            photos=(_photo("a", 35.68123, 139.76143),),
            interests=(_interest(PLACE),),
            trends=_trend(),
        )
        assert "http://" not in page
        assert "https://" not in page
        assert "<script" not in page

    def test_place_topics_are_blurred_by_default(self) -> None:
        page = _render(interests=(_interest(PLACE),))
        assert BLURRED in page
        assert "35.68123" not in page

    def test_raw_keeps_the_topics(self) -> None:
        page = _render(interests=(_interest(PLACE),), blur=False)
        assert PLACE in page

    def test_a_short_history_says_so(self) -> None:
        assert "not enough history" in _render()

    def test_a_grown_history_shows_the_directions(self) -> None:
        assert "rising" in _render(trends=_trend())

    def test_topics_are_escaped(self) -> None:
        page = _render(interests=(_interest("<b>bold</b>"),))
        assert "&lt;b&gt;bold&lt;/b&gt;" in page
        assert "<b>bold</b>" not in page

    def test_an_empty_library_still_renders(self) -> None:
        page = _render()
        assert "<html" in page
        assert "no located photographs" in page
