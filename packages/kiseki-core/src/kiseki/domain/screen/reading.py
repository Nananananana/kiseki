"""What a screenshot was about -- never what it said.

The raw text of a screenshot has no field to live in: the Privacy
Filter is the shape of this type, not a redaction pass over stored
words. Sensitive categories are recorded but never carry labels.
See ADR-0030.
"""

from dataclasses import dataclass
from datetime import datetime

from kiseki.domain.photo.observation import PhotoId

CATEGORIES = (
    "map",
    "place",
    "product",
    "food",
    "article",
    "event",
    "media",
    "settings",
    "code",
    "chat",
    "auth",
    "finance",
    "other",
)

SENSITIVE_CATEGORIES = frozenset({"chat", "auth", "finance"})
"""Recorded, so the run does not ask again, but never labelled: what
someone talks about, logs into or pays for is not interest evidence."""


@dataclass(frozen=True)
class ScreenshotReading:
    """One model's reading of one screenshot, or its refusal."""

    photo_id: PhotoId
    category: str
    labels: tuple[str, ...]
    model: str
    created_at: datetime
    refused: str | None = None

    def __post_init__(self) -> None:
        if self.refused is None and self.category not in CATEGORIES:
            raise ValueError(f"{self.category!r} is not a screen category")
        if self.category in SENSITIVE_CATEGORIES and self.labels:
            raise ValueError("a sensitive category never carries labels")
        if any(not label.strip() for label in self.labels):
            raise ValueError("a label cannot be blank")

    @property
    def answered(self) -> bool:
        return self.refused is None
