"""The screen reading run: read every screenshot once, resumably.

The reading store is the progress record, in the shape of ADR-0019:
what is there is skipped, a refusal is recorded and not asked again,
an unavailable model pauses the run. See ADR-0030.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from kiseki.domain.photo.observation import PhotoId
from kiseki.domain.screen.reading import ScreenshotReading
from kiseki.ports.models import ModelRefusedError, ModelUnavailableError
from kiseki.ports.repositories import PhotoRepository
from kiseki.ports.screens import ScreenshotReader, ScreenshotReadingRepository
from kiseki.ports.thumbnails import ThumbnailMissingError, ThumbnailSource

SCREENSHOT = "screenshot"

SCREEN_PROMPT_VERSION = "screen/1"
"""Bump when the reader's prompt changes. See ADR-0051."""


@dataclass(frozen=True)
class ScreenRunReport:
    read: int
    already: int
    refused: int
    unreferenced: int
    paused: bool
    withheld: int = 0


def run_screen_reading(
    photos: PhotoRepository,
    readings: ScreenshotReadingRepository,
    thumbnails: ThumbnailSource,
    reader: ScreenshotReader,
    limit: int | None = None,
    now: Callable[[], datetime] = datetime.now,
) -> ScreenRunReport:
    """Read every unread screenshot, oldest first."""
    read = already = refused = unreferenced = withheld = 0
    paused = False

    for photo in photos.all():
        if photo.content_kind != SCREENSHOT:
            continue
        if not photo.may_inform_preferences:
            withheld += 1
            continue
        if limit is not None and read + refused >= limit:
            break
        if photo.thumbnail_ref is None:
            unreferenced += 1
            continue
        if readings.get(photo.photo_id) is not None:
            already += 1
            continue

        when = now()
        try:
            image = thumbnails.read(photo.thumbnail_ref)
        except ThumbnailMissingError as error:
            readings.save(_refusal(photo.photo_id, str(error), when))
            refused += 1
            continue

        try:
            result = reader.read([image])[0]
        except ModelRefusedError as error:
            readings.save(_refusal(photo.photo_id, str(error), when))
            refused += 1
            continue
        except ModelUnavailableError:
            paused = True
            break

        readings.save(
            ScreenshotReading(
                photo_id=photo.photo_id,
                category=result.category,
                labels=result.labels,
                model=result.model,
                created_at=when,
                prompt_version=SCREEN_PROMPT_VERSION,
            )
        )
        read += 1

    return ScreenRunReport(read, already, refused, unreferenced, paused, withheld)


def _refusal(photo_id: PhotoId, reason: str, when: datetime) -> ScreenshotReading:
    return ScreenshotReading(
        photo_id=photo_id,
        category="other",
        labels=(),
        model="",
        created_at=when,
        refused=reason,
    )
