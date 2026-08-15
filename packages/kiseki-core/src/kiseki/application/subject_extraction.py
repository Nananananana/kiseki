"""Stage two: read each caption once, name its subjects, resumably.

Same shape as the captioning run (ADR-0019): the subject store is the
progress record, a refusal -- including an unparseable answer -- is
recorded and not asked again, and an unavailable model pauses the run.
See ADR-0020.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from kiseki.domain.caption.caption import CaptionKey
from kiseki.domain.caption.subjects import SubjectExtraction
from kiseki.ports.captions import CaptionRepository
from kiseki.ports.models import (
    LanguageModel,
    ModelRefusedError,
    ModelUnavailableError,
)
from kiseki.ports.singles import SingleCaptionRepository
from kiseki.ports.subjects import SubjectRepository

MAX_SUBJECTS = 5
SUBJECT_SYSTEM = (
    "You extract subjects from photo captions. Answer with a JSON array"
    " of 1 to 5 short subject labels: concrete things, activities, or"
    " kinds of place. Lowercase English, singular nouns, no proper"
    " names, no place names, no commentary. Answer with the JSON array"
    " only."
)


def parse_subject_labels(answer: str) -> tuple[str, ...]:
    """Read the labels out of a model's answer, tolerantly.

    Accepts a bare JSON array, an array in a code fence, or an array
    surrounded by prose. Labels are lowercased, stripped, deduplicated
    in order, and capped. An answer with no readable array parses to
    nothing, which the run records as a refusal.
    """
    start = answer.find("[")
    end = answer.rfind("]")
    if start == -1 or end == -1 or end < start:
        return ()
    try:
        items = json.loads(answer[start : end + 1])
    except json.JSONDecodeError:
        return ()
    if not isinstance(items, list):
        return ()

    labels: list[str] = []
    for item in items:
        if not isinstance(item, str):
            continue
        label = item.strip().lower()
        if label and label not in labels:
            labels.append(label)
    return tuple(labels[:MAX_SUBJECTS])


@dataclass(frozen=True)
class SubjectRunReport:
    """What one run did, for reporting back to whoever asked."""

    extracted: int
    already_extracted: int
    refused: int
    paused: bool
    """True when the model became unavailable and the run stopped early.
    Running again continues from where it paused."""


def run_subject_extraction(
    captions: CaptionRepository,
    subjects: SubjectRepository,
    language_model: LanguageModel,
    singles: SingleCaptionRepository | None = None,
    limit: int | None = None,
    now: Callable[[], datetime] = datetime.now,
) -> SubjectRunReport:
    """Read every answered caption that has no reading yet, in order.

    Refused captions are left alone entirely: there is no text to
    read, and the refusal is already recorded on the caption itself.
    Single-photo captions are read through a key derived from their
    one photograph, so one store tracks both kinds (ADR-0034).
    """
    sources: list[tuple[CaptionKey, str]] = [
        (caption.key, caption.text) for caption in captions.all() if caption.answered
    ]
    if singles is not None:
        sources += [
            (CaptionKey.of([single.photo_id]), single.text)
            for single in singles.all()
            if single.answered
        ]

    extracted = already = refused = 0
    paused = False

    for key, text in sources:
        if limit is not None and extracted + refused >= limit:
            break
        if subjects.get(key) is not None:
            already += 1
            continue

        when = now()
        try:
            completion = language_model.complete(SUBJECT_SYSTEM, [text])[0]
        except ModelRefusedError as error:
            subjects.save(_refusal(key, str(error), when))
            refused += 1
            continue
        except ModelUnavailableError:
            paused = True
            break

        labels = parse_subject_labels(completion.text)
        if not labels:
            reason = f"unparseable answer: {completion.text[:80]}"
            subjects.save(_refusal(key, reason, when))
            refused += 1
            continue

        subjects.save(
            SubjectExtraction(
                key=key,
                labels=labels,
                model=completion.model,
                created_at=when,
            )
        )
        extracted += 1

    return SubjectRunReport(extracted, already, refused, paused)


def _refusal(key: CaptionKey, reason: str, when: datetime) -> SubjectExtraction:
    return SubjectExtraction(key=key, labels=(), model="", created_at=when, refused=reason)
