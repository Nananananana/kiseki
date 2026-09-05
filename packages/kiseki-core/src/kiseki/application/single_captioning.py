"""The single-photo captioning run: describe each lone photograph once.

Stays get their captions from the stay run (ADR-0019). This run covers
the photographs that belong to no stay at all: one-off shots and saved
images that still say something about taste. Same shape as the stay
run: the caption store is the progress record, an unavailable model
pauses the run, and a refusal is recorded so it is not asked again
(ADR-0015). Screenshots and documents are read by the screen reader
instead (ADR-0030), and a withheld photograph (ADR-0032) is never
asked about. See ADR-0033.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from kiseki.application.scheduling import fan_out
from kiseki.domain.caption.single import SingleCaption
from kiseki.domain.photo.observation import PhotoId
from kiseki.ports.models import (
    CaptionRequest,
    ImageCaptioner,
)
from kiseki.ports.repositories import OutingRepository, PhotoRepository
from kiseki.ports.singles import SingleCaptionRepository
from kiseki.ports.thumbnails import ThumbnailMissingError, ThumbnailSource

SINGLE_CAPTION_PROMPT = (
    "Describe what this photograph shows, in one or two sentences."
    " Name the concrete subjects: food, buildings, nature, animals,"
    " objects, activities."
)

SINGLE_CAPTION_PROMPT_VERSION = "single-caption/1"
"""Bump when SINGLE_CAPTION_PROMPT changes. See ADR-0051."""

CAPTIONED_KINDS = ("photo", "other")
"""Screenshots and documents have their own reader (ADR-0030). A kind
of None predates the field; by the rules of its time that was a
camera photograph (ADR-0028)."""


@dataclass(frozen=True)
class SingleCaptionRunReport:
    """What one run did, for reporting back to whoever asked."""

    captioned: int
    already_captioned: int
    refused: int
    unreferenced: int
    paused: bool
    """True when the model became unavailable and the run stopped early.
    Running again continues from where it paused."""

    empty: int = 0
    """Photographs the model answered with no text. Nothing is saved, so
    the next run asks again; see CaptionRunReport.empty."""


@dataclass(frozen=True)
class _Job:
    """One lone photograph, ready to be asked about."""

    photo_id: PhotoId
    request: CaptionRequest
    when: datetime


def run_single_captioning(
    photos: PhotoRepository,
    outings: OutingRepository,
    singles: SingleCaptionRepository,
    thumbnails: ThumbnailSource,
    captioner: ImageCaptioner,
    limit: int | None = None,
    now: Callable[[], datetime] = datetime.now,
    parallel: int = 1,
) -> SingleCaptionRunReport:
    """Caption every eligible lone photograph, oldest first."""
    in_stays = {
        identifier
        for outing in outings.all()
        for stop in outing.stops
        for identifier in stop.photo_ids
    }
    captioned = already = refused = unreferenced = empty = 0
    paused = False

    pending: list[_Job] = []

    def flush() -> None:
        nonlocal captioned, refused, paused, pending, empty
        outcomes = fan_out(pending, lambda job: captioner.caption([job.request])[0], parallel)
        for outcome in outcomes:
            job = outcome.item
            if outcome.unavailable is not None:
                paused = True
                continue
            if outcome.refused is not None:
                singles.save(_refusal(job.photo_id, str(outcome.refused), job.when))
                refused += 1
                continue
            completion = outcome.completed
            assert completion is not None
            if not completion.text.strip():
                # Neither a refusal nor an outage, and SingleCaption
                # refuses to hold it. Nothing is saved, so the next run
                # asks again; see CaptionRunReport.empty for why.
                empty += 1
                continue
            singles.save(
                SingleCaption(
                    photo_id=job.photo_id,
                    text=completion.text,
                    model=completion.model,
                    created_at=job.when,
                    prompt_version=SINGLE_CAPTION_PROMPT_VERSION,
                )
            )
            captioned += 1
        pending = []

    for item in photos.all():
        if limit is not None and captioned + refused + len(pending) >= limit:
            break
        if item.photo_id in in_stays:
            continue
        if item.content_kind is not None and item.content_kind not in CAPTIONED_KINDS:
            continue
        if not item.may_inform_preferences:
            continue
        if item.thumbnail_ref is None:
            unreferenced += 1
            continue
        if singles.get(item.photo_id) is not None:
            already += 1
            continue

        when = now()
        try:
            image = thumbnails.read(item.thumbnail_ref)
        except ThumbnailMissingError as error:
            singles.save(_refusal(item.photo_id, str(error), when))
            refused += 1
            continue

        context = f"Taken around {item.captured_at:%Y-%m-%d %H:%M}."
        pending.append(
            _Job(item.photo_id, CaptionRequest((image,), SINGLE_CAPTION_PROMPT, context), when)
        )
        if len(pending) >= parallel:
            flush()
            if paused:
                break

    if pending and not paused:
        flush()

    return SingleCaptionRunReport(captioned, already, refused, unreferenced, paused, empty)


def _refusal(photo_id: PhotoId, reason: str, when: datetime) -> SingleCaption:
    return SingleCaption(photo_id=photo_id, text="", model="", created_at=when, refused=reason)
