"""One place builds every JSON payload, blurring on request.

Blur keeps a coordinate to two decimals -- roughly a kilometre --
which is enough to say "around here" without saying "this doorstep".
The command line keeps showing what is stored; anything served asks
for blur explicitly. See ADR-0026.
"""

from datetime import UTC, datetime, timedelta

import pytest
from kiseki.application.asking import Answer
from kiseki.application.pipeline import Report
from kiseki.domain.analytics.analytics import summarise_places, summarise_rhythm
from kiseki.domain.anchor.anchor import Anchor
from kiseki.domain.interests import (
    EvidenceKind,
    Interest,
    InterestEvidence,
    Profile,
)
from kiseki.domain.shared.confidence import Confidence
from kiseki.domain.shared.geo import Distance, GeoArea, GeoPoint
from kiseki.domain.shared.time_range import TimeRange
from kiseki.domain.trends import TopicTrend, TrendDirection, TrendReport
from kiseki.interfaces.payloads import (
    answer_payload,
    profile_payload,
    report_payload,
    trend_payload,
)

AT = datetime(2026, 6, 1, 12)
PLACE = "place:35.68123,139.76543"
BLURRED = "place:35.68,139.77"


def _report() -> Report:
    anchor = Anchor(
        area=GeoArea(GeoPoint(35.68123, 139.76543), Distance(300)),
        period=TimeRange(datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 6, 1, tzinfo=UTC)),
        visit_days=52,
        night_days=40,
        weekday_days=30,
        daytime_days=20,
        photograph_count=200,
        confidence=Confidence(0.9, 52),
    )
    return Report(
        photographs=1,
        anchors=(anchor,),
        outings=(),
        places=summarise_places((), Distance(500)),
        habits=None,
        rhythm=summarise_rhythm(()),
    )


def _interest(topic: str, reference: str) -> Interest:
    evidence = (
        InterestEvidence(
            kind=EvidenceKind.PHOTOGRAPH,
            reference=reference,
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


class TestReportPayload:
    def test_blurs_anchor_coordinates(self) -> None:
        payload = report_payload(_report(), blur=True)
        assert payload["anchors"][0]["latitude"] == pytest.approx(35.68)
        assert payload["anchors"][0]["longitude"] == pytest.approx(139.77)

    def test_keeps_raw_coordinates_without_blur(self) -> None:
        payload = report_payload(_report(), blur=False)
        assert payload["anchors"][0]["latitude"] == pytest.approx(35.68123)


class TestProfilePayload:
    def test_blurs_place_topics_and_their_evidence(self) -> None:
        profile = Profile(generated_at=AT, interests=(_interest(PLACE, PLACE),))
        payload = profile_payload(profile, blur=True)
        assert payload["interests"][0]["topic"] == BLURRED
        assert payload["interests"][0]["evidence"][0]["reference"] == BLURRED

    def test_leaves_caption_references_alone(self) -> None:
        profile = Profile(
            generated_at=AT,
            interests=(_interest("onsen", "caption:abc"),),
        )
        payload = profile_payload(profile, blur=True)
        assert payload["interests"][0]["topic"] == "onsen"
        assert payload["interests"][0]["evidence"][0]["reference"] == "caption:abc"


class TestTrendPayload:
    def test_blurs_place_topics(self) -> None:
        report = TrendReport(
            baseline_at=AT,
            latest_at=AT + timedelta(days=20),
            trends=(
                TopicTrend(
                    topic=PLACE,
                    direction=TrendDirection.STEADY,
                    strength=0.3,
                    baseline=0.3,
                ),
            ),
        )
        assert trend_payload(report, blur=True)["trends"][0]["topic"] == BLURRED

    def test_a_place_it_cannot_parse_is_left_alone(self) -> None:
        report = TrendReport(
            baseline_at=AT,
            latest_at=AT + timedelta(days=20),
            trends=(
                TopicTrend(
                    topic="place:unknown",
                    direction=TrendDirection.STEADY,
                    strength=0.3,
                    baseline=0.3,
                ),
            ),
        )
        assert trend_payload(report, blur=True)["trends"][0]["topic"] == "place:unknown"


class TestAnswerPayload:
    """`answer_payload` accepted `blur` and discarded it.

    An insight's topic can be `place:lat,lon`, and `supporting_insights`
    rode the answer contract raw over HTTP and through `--json` while
    every sibling payload blurred. Found by a probe, not by a test --
    which is why these exist.
    """

    @staticmethod
    def _answer_with(topic: str) -> Answer:
        from kiseki.domain.insight import Insight, InsightDirection, InsightKind

        now = datetime(2026, 9, 5, tzinfo=UTC)
        insight = Insight(
            topic=topic,
            kind=next(iter(InsightKind)),
            direction=next(iter(InsightDirection)),
            magnitude=1.0,
            first_seen=now,
            last_seen=now,
            confidence=0.9,
            evidence=(topic,),
            novelty=0.5,
            derived_from=("kiseki insights",),
        )
        return Answer("q", "a", 0.5, None, None, (), "m", supporting_insights=(insight,))

    def test_a_place_topic_is_blurred_by_default(self) -> None:
        served = answer_payload(self._answer_with("place:35.68123,139.76543"))
        assert served["supporting_insights"][0]["topic"] == "place:35.68,139.77"

    def test_raw_keeps_the_coordinates(self) -> None:
        served = answer_payload(self._answer_with("place:35.68123,139.76543"), blur=False)
        assert served["supporting_insights"][0]["topic"] == "place:35.68123,139.76543"

    def test_a_word_topic_passes_untouched(self) -> None:
        served = answer_payload(self._answer_with("ramen"))
        assert served["supporting_insights"][0]["topic"] == "ramen"
