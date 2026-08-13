"""What a model saw in the photographs of one stay.

A caption is keyed by the photographs it describes, not by the stop
they formed. Stops are derived and replaced wholesale on every rebuild
(ADR-0013); the photographs are named by content hashes and never
change. A caption keyed on them survives every rebuild that reforms
the same stay, and stops being found exactly when the stay itself is
different -- the same reasoning that gave outings a content-derived
identifier. See ADR-0019.
"""

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from kiseki.domain.photo.observation import PhotoId

KEY_LENGTH = 16


@dataclass(frozen=True)
class CaptionKey:
    """Derived from the photographs captioned, so it survives rebuilds."""

    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise ValueError("a caption key cannot be empty")

    @classmethod
    def of(cls, photo_ids: Sequence[PhotoId]) -> "CaptionKey":
        if not photo_ids:
            raise ValueError("a caption key needs at least one photograph")
        joined = "|".join(sorted(identifier.value for identifier in photo_ids))
        return cls(hashlib.sha256(joined.encode("utf-8")).hexdigest()[:KEY_LENGTH])


@dataclass(frozen=True)
class Caption:
    """One model's description of one stay, or its refusal to give one.

    A refusal is kept deliberately: retrying the same request would get
    the same answer (ADR-0015), so recording it is what stops a
    resumable run from asking forever.
    """

    key: CaptionKey
    photo_ids: tuple[PhotoId, ...]
    text: str
    model: str
    created_at: datetime
    refused: str | None = None

    def __post_init__(self) -> None:
        if not self.photo_ids:
            raise ValueError("a caption needs the photographs it describes")
        if self.refused is None and not self.text.strip():
            raise ValueError("an answered caption needs text")

    @property
    def answered(self) -> bool:
        return self.refused is None
