"""What a model saw in one photograph outside every stay.

A single caption is keyed by the photograph it describes. Photographs
are named by content hashes and never change, so the key survives
every rebuild with no derivation at all -- the same reasoning that
keys stay captions on their photographs (ADR-0019). See ADR-0033.
"""

from dataclasses import dataclass
from datetime import datetime

from kiseki.domain.photo.observation import PhotoId


@dataclass(frozen=True)
class SingleCaption:
    """One model's description of one photograph, or its refusal.

    A refusal is kept deliberately: retrying the same request would
    get the same answer (ADR-0015), so recording it is what stops a
    resumable run from asking forever.
    """

    photo_id: PhotoId
    text: str
    model: str
    created_at: datetime
    refused: str | None = None

    def __post_init__(self) -> None:
        if self.refused is None and not self.text.strip():
            raise ValueError("an answered caption needs text")

    @property
    def answered(self) -> bool:
        return self.refused is None
