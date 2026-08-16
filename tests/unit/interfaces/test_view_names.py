"""The view labels place topics when names are given (ADR-0040)."""

from datetime import UTC, datetime, timedelta

from kiseki.application.pipeline import Report
from kiseki.domain.analytics.analytics import summarise_places, summarise_rhythm
from kiseki.domain.interests import (
    EvidenceKind,
    Interest,
    InterestEvidence,
    Profile,
)
from kiseki.domain.shared.geo import Distance
from kiseki.domain.trends import TopicTrend, TrendDirection, TrendReport
from kiseki.interfaces.view import render_view

AT = datetime(2026, 6, 1, 12, tzinfo=UTC)
PLACE = "place:35.68123,139.76543"
OTHER = "place:34.70182,135.50150"
NAMES = {PLACE: "Kyoto (JP)"}


def _report() -> Report:
    return Report(
        photographs=0,
        anchors=(),
        outings=(),
        places=summarise_places((), Distance(500)),
        habits=None,
        rhythm=summarise_rhythm(()),
    )


def _interest(topic: str) -> Interest:
    evidence = (
        InterestEvidence(
            kind=EvidenceKind.PHOTOGRAPH,
            reference=f"caption:{topic}",
            observed_at=AT,
        ),
    )
    return Interest(
        topic=topic,
        score=0.5,
        confidence=0.4,
        evidence=evidence,
        first_seen=AT,
        last_seen=AT,
    )


def _render(interests, trends=None, blur=True, names=None):
    profile = Profile(generated_at=AT, interests=tuple(interests))
    return render_view((), _report(), profile, trends, blur=blur, names=names)


def test_a_blurred_view_shows_the_name():
    page = _render([_interest(PLACE)], names=NAMES)
    assert "Kyoto (JP)" in page
    assert "35.68" not in page


def test_a_raw_view_keeps_the_reference_beside_the_name():
    page = _render([_interest(PLACE)], blur=False, names=NAMES)
    assert f"Kyoto (JP) {PLACE}" in page


def test_unnamed_topics_still_blur():
    page = _render([_interest(OTHER)], names=NAMES)
    assert "place:34.70,135.50" in page
    assert "34.70182" not in page


def test_trend_rows_are_named_too():
    trend = TrendReport(
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
    page = _render([], trends=trend, names=NAMES)
    assert "Kyoto (JP)" in page
