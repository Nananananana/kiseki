"""The captioning run: describe every stay once, resumably.

The caption store is the progress record (ADR-0019). What is already
there is skipped, so an interrupted overnight run continues rather
than restarts (ADR-0014). An unavailable model pauses the run; a
refusal is recorded so it is not asked again (ADR-0015).
"""

from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from datetime import datetime

from kiseki.domain.caption.caption import Caption, CaptionKey
from kiseki.domain.outing.stop import Stop
from kiseki.domain.photo.observation import PhotoId
from kiseki.ports.captions import CaptionRepository
from kiseki.ports.models import (
    CaptionRequest,
    ImageCaptioner,
    ModelRefusedError,
    ModelUnavailableError,
)
from kiseki.ports.repositories import OutingRepository, PhotoRepository
from kiseki.ports.thumbnails import ThumbnailMissingError, ThumbnailSource

DEFAULT_IMAGES_PER_STOP = 3
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


def run_captioning(
    outings: OutingRepository,
    photos: PhotoRepository,
    captions: CaptionRepository,
    thumbnails: ThumbnailSource,
    captioner: ImageCaptioner,
    images_per_stop: int = DEFAULT_IMAGES_PER_STOP,
    limit: int | None = None,
    now: Callable[[], datetime] = datetime.now,
) -> CaptionRunReport:
    """Caption every stay that has no caption yet, oldest first."""
    references = {item.photo_id: item.thumbnail_ref for item in photos.all() if item.thumbnail_ref}
    captioned = already = refused = unreferenced = 0
    paused = False

    for stop in _stops(outings):
        if limit is not None and captioned + refused >= limit:
            break

        eligible = [identifier for identifier in stop.photo_ids if identifier in references]
        if not eligible:
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
        try:
            completion = captioner.caption([CaptionRequest(images, CAPTION_PROMPT, context)])[0]
        except ModelRefusedError as error:
            captions.save(_refusal(key, selected, str(error), when))
            refused += 1
            continue
        except ModelUnavailableError:
            paused = True
            break

        captions.save(
            Caption(
                key=key,
                photo_ids=selected,
                text=completion.text,
                model=completion.model,
                created_at=when,
            )
        )
        captioned += 1

    return CaptionRunReport(captioned, already, refused, unreferenced, paused)


def _stops(outings: OutingRepository) -> Iterator[Stop]:
    for outing in outings.all():
        yield from outing.stops


def _refusal(
    key: CaptionKey, photo_ids: tuple[PhotoId, ...], reason: str, when: datetime
) -> Caption:
    return Caption(key=key, photo_ids=photo_ids, text="", model="", created_at=when, refused=reason)
