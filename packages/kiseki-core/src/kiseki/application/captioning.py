"""The captioning run: describe every stay once, resumably.

The caption store is the progress record (ADR-0019). What is already
there is skipped, so an interrupted overnight run continues rather
than restarts (ADR-0014). An unavailable model pauses the run; a
refusal is recorded so it is not asked again (ADR-0015).
"""

from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from datetime import datetime

from kiseki.application.scheduling import fan_out
from kiseki.domain.caption.caption import Caption, CaptionKey
from kiseki.domain.outing.stop import Stop
from kiseki.domain.photo.observation import PhotoId
from kiseki.ports.captions import CaptionRepository
from kiseki.ports.models import (
    CaptionRequest,
    ImageCaptioner,
)
from kiseki.ports.repositories import OutingRepository, PhotoRepository
from kiseki.ports.thumbnails import ThumbnailMissingError, ThumbnailSource

DEFAULT_IMAGES_PER_STOP = 3
CAPTION_PROMPT_VERSION = "stay-caption/1"
"""Bump when CAPTION_PROMPT changes: `kiseki reread` finds every stay
caption an older prompt wrote. See ADR-0051."""
CAPTION_PROMPT = (
    "Describe what these photographs of one place show, in one or two"
    " sentences. Name the concrete subjects: food, buildings, nature,"
    " animals, objects, activities."
)


def representative_photo_ids(photo_ids: Sequence[PhotoId], limit: int) -> tuple[PhotoId, ...]:
    """Pick up to `limit` photographs spread across the stay.

    Deterministic on purpose: the selection is part of the caption key,
    and the key is what makes a rerun recognise finished work.
    """
    if limit < 1:
        raise ValueError("at least one photograph must be allowed")
    if len(photo_ids) <= limit:
        return tuple(photo_ids)
    if limit == 1:
        return (photo_ids[len(photo_ids) // 2],)
    step = (len(photo_ids) - 1) / (limit - 1)
    indices = sorted({round(index * step) for index in range(limit)})
    return tuple(photo_ids[index] for index in indices)


@dataclass(frozen=True)
class CaptionRunReport:
    """What one run did, for reporting back to whoever asked."""

    captioned: int
    already_captioned: int
    refused: int
    unreferenced: int
    paused: bool
    """True when the model became unavailable and the run stopped early.
    Running again continues from where it paused."""

    withheld: int = 0
    """Stays whose every photograph withheld preference consent
    (ADR-0032); nothing was asked about them. See ADR-0035."""

    empty: int = 0
    """Stays the model answered with no text. Nothing is saved for them,
    so the next run asks again. Measured on the real library: none of
    twelve one at a time, two of twelve with four in flight -- an empty
    answer is what an overloaded server does, not what a model decides,
    so it is not a refusal and is not recorded as one (ADR-0015)."""


@dataclass(frozen=True)
class _Job:
    """One stay, ready to be asked about: everything but the answer."""

    key: CaptionKey
    selected: tuple[PhotoId, ...]
    images: tuple[bytes, ...]
    context: str
    when: datetime


def run_captioning(
    outings: OutingRepository,
    photos: PhotoRepository,
    captions: CaptionRepository,
    thumbnails: ThumbnailSource,
    captioner: ImageCaptioner,
    images_per_stop: int = DEFAULT_IMAGES_PER_STOP,
    limit: int | None = None,
    now: Callable[[], datetime] = datetime.now,
    parallel: int = 1,
) -> CaptionRunReport:
    """Caption every stay that has no caption yet, oldest first.

    A photograph that withheld preference consent (ADR-0032) never
    enters the representative selection; a stay left with nothing to
    select is counted as withheld and skipped. See ADR-0035.
    """
    observations = photos.all()
    references = {
        item.photo_id: item.thumbnail_ref
        for item in observations
        if item.thumbnail_ref and item.may_inform_preferences
    }
    withheld_ids = {item.photo_id for item in observations if not item.may_inform_preferences}
    captioned = already = refused = unreferenced = withheld = empty = 0
    paused = False

    pending: list[_Job] = []

    def flush() -> None:
        nonlocal captioned, refused, paused, pending, empty
        outcomes = fan_out(
            pending,
            lambda job: captioner.caption(
                [CaptionRequest(job.images, CAPTION_PROMPT, job.context)]
            )[0],
            parallel,
        )
        for outcome in outcomes:
            job = outcome.item
            if outcome.unavailable is not None:
                paused = True
                continue
            if outcome.refused is not None:
                captions.save(_refusal(job.key, job.selected, str(outcome.refused), job.when))
                refused += 1
                continue
            completion = outcome.completed
            assert completion is not None
            if not completion.text.strip():
                # A model that answers with nothing is neither refusing
                # nor unavailable, and Caption refuses to hold an empty
                # answer. Left uncaught this killed a run after seven
                # captions on the real library. It is not recorded as a
                # refusal either: two of twelve came back empty with
                # four in flight and none with one, so an empty answer
                # is the server under load, and asking again works.
                empty += 1
                continue
            captions.save(
                Caption(
                    key=job.key,
                    photo_ids=job.selected,
                    text=completion.text,
                    model=completion.model,
                    created_at=job.when,
                    prompt_version=CAPTION_PROMPT_VERSION,
                )
            )
            captioned += 1
        pending = []

    for stop in _stops(outings):
        if limit is not None and captioned + refused + len(pending) >= limit:
            break

        eligible = [identifier for identifier in stop.photo_ids if identifier in references]
        if not eligible:
            if any(identifier in withheld_ids for identifier in stop.photo_ids):
                withheld += 1
            else:
                unreferenced += 1
            continue
        selected = representative_photo_ids(eligible, images_per_stop)

        key = CaptionKey.of(selected)
        if captions.get(key) is not None:
            already += 1
            continue

        when = now()
        try:
            images = tuple(thumbnails.read(references[identifier]) for identifier in selected)
        except ThumbnailMissingError as error:
            captions.save(_refusal(key, selected, str(error), when))
            refused += 1
            continue

        context = f"Taken around {stop.time_range.start:%Y-%m-%d %H:%M}."
        pending.append(_Job(key, selected, images, context, when))
        if len(pending) >= parallel:
            flush()
            if paused:
                break

    if pending and not paused:
        flush()

    return CaptionRunReport(captioned, already, refused, unreferenced, paused, withheld, empty)


def _stops(outings: OutingRepository) -> Iterator[Stop]:
    for outing in outings.all():
        yield from outing.stops


def _refusal(
    key: CaptionKey, photo_ids: tuple[PhotoId, ...], reason: str, when: datetime
) -> Caption:
    return Caption(key=key, photo_ids=photo_ids, text="", model="", created_at=when, refused=reason)
