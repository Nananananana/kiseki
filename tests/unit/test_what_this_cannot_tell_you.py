"""`kiseki limits` reports reach, and never invents a number to do it.

Three of these tests are named in `interfaces/claims.py`. That file's
discipline is that every claim carries the test which fails if the
claim stops being true, so the names there are load-bearing: renaming
a test here without following it there leaves a claim pointing at
nothing.

Which was, until this file, possible. `test_every_claim_carries_the_test_that_keeps_it`
asserted only that the string began with `tests/`, so
`tests/unit/test_nothing.py::test_invented` would have passed. Every
existing claim happened to resolve -- checked, all six -- but nothing
was keeping them that way. `test_every_claim_names_a_test_that_exists`
below is the check that was described.
"""

import re
from collections.abc import Sequence
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest
from kiseki.adapters.memory.repositories import (
    InMemoryAnchorRepository,
    InMemoryOutingRepository,
    InMemoryPhotoRepository,
)
from kiseki.application.limits import (
    ACTIVITY,
    LOSS,
    NOTES,
    PAGES,
    PHOTOGRAPHS,
    SCREENS,
    LimitsReport,
    Source,
    Span,
    limits_of,
)
from kiseki.application.pipeline import Pipeline
from kiseki.domain.note.reading import NoteReading
from kiseki.domain.photo.observation import PhotoId, PhotoObservation
from kiseki.domain.screen.reading import ScreenshotReading
from kiseki.domain.services.vocabulary import Overlap
from kiseki.interfaces.claims import NEVER_STORED, UNSEEABLE

REPO_ROOT = Path(__file__).parents[2]
JST = timezone(timedelta(hours=9))

EVERY_SOURCE = (PHOTOGRAPHS, NOTES, PAGES, ACTIVITY, SCREENS)


def full(**counts: int) -> list[Source]:
    """Every source present unless a count says otherwise."""
    return [
        Source(
            name=name,
            count=counts.get(name, 3),
            span=None if counts.get(name, 3) == 0 else Span(date(2026, 1, 1), date(2026, 3, 1)),
        )
        for name in EVERY_SOURCE
    ]


# --------------------------------------------------------------------
# The population, before anything is trusted about it.
# --------------------------------------------------------------------


def test_there_are_limits_to_report_at_all() -> None:
    """A report with no possible limits would make every assertion
    below pass by having nothing to look at."""
    assert len(EVERY_SOURCE) == 5
    assert set(LOSS) == set(EVERY_SOURCE)
    assert UNSEEABLE, "nothing is claimed unseeable, so those tests check nothing"


def test_every_source_says_what_its_absence_costs() -> None:
    for name in EVERY_SOURCE:
        assert LOSS[name].strip(), f"{name} loses nothing by being absent, which cannot be"


def test_a_source_nobody_decided_about_is_refused() -> None:
    """The cost of absence is not optional, so a new source cannot
    reach a report by defaulting to a blank line."""
    with pytest.raises(ValueError, match="cost of absence"):
        Source(name="dreams", count=1)


# --------------------------------------------------------------------
# What is computed.
# --------------------------------------------------------------------


def test_an_absent_source_is_a_limit() -> None:
    report = limits_of(full(notes=0))
    assert [limit.subject for limit in report.limits] == [NOTES]
    assert "what you wrote" in report.limits[0].because


def test_a_source_that_is_thin_but_present_is_not_judged() -> None:
    """The decision this module turns on. One note is not zero notes,
    and no number here knows whether one is enough -- so it is counted
    and left alone (ADR-0010)."""
    report = limits_of(full(notes=1))
    assert report.limits == (), (
        "a threshold was introduced. Whatever number decided that one "
        "note is too few was chosen by its author to make a sentence "
        "true, which is the thing this command exists to replace."
    )


def test_the_span_is_every_source_together() -> None:
    sources = [
        Source(PHOTOGRAPHS, 2, Span(date(2026, 1, 1), date(2026, 2, 1))),
        Source(NOTES, 2, Span(date(2025, 6, 1), date(2026, 5, 1))),
        Source(PAGES, 0),
        Source(ACTIVITY, 0),
        Source(SCREENS, 0),
    ]
    span = limits_of(sources).span
    assert span == Span(date(2025, 6, 1), date(2026, 5, 1))
    assert span.days == 335


def test_each_source_keeps_its_own_span_inside_the_library_s() -> None:
    """The reading that made this worth printing.

    Measured on the real library: 4,950 photographs over 776 days and
    3 days of movement. Both sit under one heading that says 778 days,
    and a reader who saw only that heading would ask how their year
    was spent and be answered from three days in August.

    So each source states its own span, and the arithmetic that would
    hide it -- rolling every source into the library's -- is what this
    guards against.
    """
    sources = [
        Source(PHOTOGRAPHS, 4950, Span(date(2024, 7, 3), date(2026, 8, 17))),
        Source(ACTIVITY, 3, Span(date(2026, 8, 17), date(2026, 8, 19))),
        Source(SCREENS, 0),
        Source(NOTES, 0),
        Source(PAGES, 0),
    ]
    report = limits_of(sources)
    assert report.span.days == 778
    by_name = {source.name: source.span for source in report.sources}
    assert by_name[ACTIVITY].days == 3
    assert by_name[PHOTOGRAPHS].days == 776
    assert by_name[NOTES] is None


def test_a_span_of_one_day_is_one_day() -> None:
    """Inclusive, because a library read on a single day covers that
    day rather than covering nothing."""
    assert Span(date(2026, 1, 1), date(2026, 1, 1)).days == 1


def test_an_empty_library_says_so_rather_than_spanning_nothing() -> None:
    report = limits_of(full(**dict.fromkeys(EVERY_SOURCE, 0)))
    assert report.empty
    assert report.span is None
    assert len(report.limits) == len(EVERY_SOURCE)


def test_an_unsettled_vocabulary_is_a_limit_at_the_measured_threshold() -> None:
    """0.8 is ADR-0071's, earned on nine days of real readings. It is
    reused here rather than re-derived."""
    unsettled = Overlap(before=190, after=695, shared=98)
    assert not unsettled.settled
    report = limits_of(full(), overlap=unsettled)
    assert [limit.subject for limit in report.limits] == ["vocabulary"]
    assert "98 of 787" in report.limits[0].reading


def test_a_settled_vocabulary_is_not_a_limit() -> None:
    report = limits_of(full(), overlap=Overlap(before=100, after=100, shared=95))
    assert report.limits == ()


def test_refusals_and_silent_readings_are_limits() -> None:
    report = limits_of(full(), refusals=4, label_silent=7)
    subjects = {limit.subject: limit.reading for limit in report.limits}
    assert subjects["refused captions"] == "4"
    assert subjects["label-silent readings"] == "7"


def test_a_withheld_reading_is_not_a_failed_one() -> None:
    """The two are never added together, and they never were the same.

    Measured on the real library: all 80 readings the report called
    "label-silent" were sensitive ones -- 32 chat, 31 auth, 17 finance,
    and not one model failure. Summing them described a privacy
    guarantee working correctly as a shortcoming of the library.
    """
    report = limits_of(full(), label_silent=3, withheld=80)
    by_subject = {limit.subject: limit for limit in report.limits}
    assert by_subject["label-silent readings"].reading == "3"
    assert by_subject["withheld by category"].reading == "80"
    assert "working rather than failing" in by_subject["withheld by category"].because


def test_a_withheld_reading_is_still_a_limit() -> None:
    """It narrows an answer exactly as much as an empty reading does.
    Being deliberate is a reason, not an exemption."""
    assert limits_of(full(), withheld=80).limits


def test_a_sensitive_reading_is_counted_as_withheld_not_as_silent() -> None:
    """The split, through the pipeline rather than through a keyword.

    A `chat` screen reading carries no labels because
    `ScreenshotReading.__post_init__` forbids it, not because the model
    came back empty.
    """
    photograph = PhotoObservation(PhotoId("shot"), datetime(2026, 5, 1, tzinfo=JST))
    sensitive = ScreenshotReading(
        photo_id=PhotoId("shot"),
        category="chat",
        labels=(),
        model="a model",
        created_at=datetime(2026, 5, 2, tzinfo=JST),
    )
    pipeline = _pipeline(screens=_Screens([sensitive]))
    pipeline.ingest([photograph])

    subjects = {limit.subject for limit in pipeline.limits().limits}
    assert "withheld by category" in subjects
    assert "label-silent readings" not in subjects, (
        "a category this library refuses to label was reported as a reading that yielded nothing"
    )


def test_nothing_is_reported_when_nothing_is_wrong() -> None:
    """The honest zero. If this ever cannot happen, the command has
    started manufacturing limits to look thorough."""
    assert limits_of(full(), overlap=Overlap(1, 1, 1)).limits == ()


# --------------------------------------------------------------------
# The three claims in `interfaces/claims.py` point here.
# --------------------------------------------------------------------


class _Notes:
    """A wired note repository that happens to hold nothing."""

    def __init__(self, readings: Sequence[NoteReading] = ()) -> None:
        self._readings = tuple(readings)

    def all(self) -> tuple[NoteReading, ...]:
        return self._readings


def _pipeline(**wired: object) -> Pipeline:
    return Pipeline(
        InMemoryPhotoRepository(),
        InMemoryOutingRepository(),
        InMemoryAnchorRepository(),
        **wired,  # type: ignore[arg-type]
    )


def test_nothing_here_claims_to_know_what_is_missing() -> None:
    """A source wired and empty is indistinguishable from one that was
    never wired at all.

    This is what the claim *an interest you never photographed is
    invisible* actually rests on. The library has one word for *you
    kept no notes* and *this installation has no notes repository*,
    and it cannot tell them apart -- so it can never say how much is
    missing, because it does not know the denominator.

    If somebody later teaches `limits` to look at the disk and report
    notes it was never given, this goes red, and the claim in
    `claims.py` should come out of the unseeable list and be computed
    instead.
    """
    wired_and_empty = _pipeline(notes=_Notes()).limits()
    never_wired = _pipeline().limits()
    assert wired_and_empty == never_wired

    photograph = PhotoObservation(PhotoId("a"), datetime(2026, 5, 1, tzinfo=JST))
    seeded = _pipeline()
    seeded.ingest([photograph])
    assert seeded.limits() != never_wired, (
        "a photograph made no difference, so this compares two empty "
        "reports and would pass however limits were computed"
    )


def every_limit() -> LimitsReport:
    """A report with every kind of computed limit in it at once."""
    report = limits_of(
        full(**dict.fromkeys(EVERY_SOURCE, 0)),
        overlap=Overlap(before=190, after=695, shared=98),
        refusals=1,
        label_silent=1,
        withheld=1,
    )
    assert len(report.limits) == len(EVERY_SOURCE) + 4, "not every limit is under test"
    return report


class _Screens:
    """A wired screenshot-reading repository."""

    def __init__(self, readings: Sequence[object] = ()) -> None:
        self._readings = tuple(readings)

    def all(self) -> tuple[object, ...]:
        return self._readings


def test_a_screen_reading_is_dated_by_the_screenshot_not_by_itself() -> None:
    """The defect this test exists for, found on the real library.

    `ScreenshotReading.created_at` is when the *model* read it. A
    captioning run that took five days produced 297 readings, and
    dating them by themselves reported five days of screen evidence
    for screenshots that actually span 2024-07-10 to 2026-08-09 --
    761 days told as 5.

    That is the precise failure `limits` exists to prevent: a number
    that is confidently wrong about its own reach, in the direction
    that makes the library look narrower than it is.
    """
    long_ago = datetime(2025, 1, 2, tzinfo=JST)
    photograph = PhotoObservation(PhotoId("shot"), long_ago)
    reading = ScreenshotReading(
        photo_id=PhotoId("shot"),
        category="other",
        labels=("a label",),
        model="a model",
        created_at=datetime(2026, 8, 17, tzinfo=JST),
    )
    pipeline = _pipeline(screens=_Screens([reading]))
    pipeline.ingest([photograph])

    spans = {source.name: source.span for source in pipeline.limits().sources}
    assert spans[SCREENS] == Span(date(2025, 1, 2), date(2025, 1, 2)), (
        "the screen reading was dated by when the model read it, which "
        "is a fact about a captioning run and not about the owner"
    )


def _shipped_reasons() -> list[str]:
    """Every `because` the computed half can print.

    Not `UNSEEABLE`'s reasons: those are the disclaimer itself, and one
    of them has to contain the word *causing* in order to disclaim it.
    """
    return [limit.because for limit in every_limit().limits]


EXPLAINS_THE_OWNER = (
    "you prefer",
    "you tend",
    "you like",
    "you are",
    "you were",
    "because you",
    "suggests you",
    "means you",
    "you must",
    "you probably",
)


def test_no_limit_explains_the_owner() -> None:
    """A limit is about the library's reach, never about the person.

    *You have no notes* is a count. *You have no notes because you
    prefer photographs* is a claim about somebody, made by the tool
    least equipped to make it, and it is one careless sentence away at
    all times (ADR-0040 refuses the same move for anchors).
    """
    for reason in _shipped_reasons():
        lowered = reason.lower()
        for phrase in EXPLAINS_THE_OWNER:
            assert phrase not in lowered, f"{phrase!r} explains the owner: {reason!r}"


CLAIMS_A_CAUSE = (
    "causes",
    "caused by",
    "leads to",
    "results in",
    "due to",
    "therefore you",
    "which is why you",
)


def test_no_limit_claims_a_cause() -> None:
    """Co-occurrence is not cause (ADR-0049), and a limits report is
    where a causal sentence would look most harmless."""
    for reason in _shipped_reasons():
        lowered = reason.lower()
        for phrase in CLAIMS_A_CAUSE:
            assert phrase not in lowered, f"{phrase!r} claims a cause: {reason!r}"


# --------------------------------------------------------------------
# The claims file's own discipline, actually enforced.
# --------------------------------------------------------------------


@pytest.mark.parametrize(
    "claim",
    [*NEVER_STORED, *UNSEEABLE],
    ids=lambda claim: claim[0] if isinstance(claim, tuple) else str(claim),
)
def test_every_claim_names_a_test_that_exists(claim: tuple[str, str, str]) -> None:
    """The check `test_every_claim_carries_the_test_that_keeps_it`
    described but did not perform: it asserted the string started with
    `tests/` and never opened the file."""
    subject, _reason, reference = claim
    path, _, function = reference.partition("::")
    resolved = REPO_ROOT / path
    assert resolved.exists(), f"{subject}: no such file as {path}"
    if function:
        source = resolved.read_text(encoding="utf-8")
        assert re.search(rf"^\s*def {re.escape(function)}\(", source, re.MULTILINE), (
            f"{subject}: {path} defines no {function}"
        )


def test_the_unseeable_are_kept_apart_from_the_computed() -> None:
    """Neither list may quietly absorb the other. A subject in both
    would be asserted in one place and measured in another, and a
    reader would never know which they were being shown."""
    asserted = {subject for subject, _reason, _test in UNSEEABLE}
    computed = {limit.subject for limit in every_limit().limits}
    assert not (asserted & computed), f"claimed and computed at once: {asserted & computed}"
