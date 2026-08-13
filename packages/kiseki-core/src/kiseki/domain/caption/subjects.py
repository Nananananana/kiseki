"""What the captions were about, one reading per caption.

Stage two of the models (ADR-0014): a language model reads each
caption and names its subjects. A reading is keyed by the caption's
key, so the store doubles as the progress record, exactly as captions
do (ADR-0019). See ADR-0020.
"""

from dataclasses import dataclass
from datetime import datetime

from kiseki.domain.caption.caption import CaptionKey


@dataclass(frozen=True)
class SubjectExtraction:
    """One model's reading of what a caption was about, or its refusal.

    Labels are short lowercase English nouns for concrete things,
    activities and kinds of place. A recorded refusal -- including an
    answer that could not be parsed -- is not asked again (ADR-0015).
    """

    key: CaptionKey
    labels: tuple[str, ...]
    model: str
    created_at: datetime
    refused: str | None = None

    def __post_init__(self) -> None:
        if self.refused is None and not self.labels:
            raise ValueError("an answered extraction needs at least one label")
        if any(not label.strip() for label in self.labels):
            raise ValueError("a label cannot be blank")

    @property
    def answered(self) -> bool:
        return self.refused is None
