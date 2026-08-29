"""Reading a note, and keeping almost none of it.

The shape of this is borrowed from the way screenshots are read in the
core: a closed list of categories, a handful of labels, and sensitive
categories that are counted and never labelled. The code is not
borrowed. A producer that imported the core would make the record
contract decorative -- the contract is the only thing the two sides
share, and a shared function would be a second thing.

So this speaks to Ollama over `urllib` and depends on nothing, the
same standard the core holds itself to.

What the model returns is checked rather than trusted: an unknown
category becomes `other`, labels beyond the eighth are dropped, and a
sensitive category loses its labels whatever the model said. A model
that ignores its instructions is a weaker classifier, not a leak.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Sequence
from dataclasses import dataclass

CATEGORIES = (
    "note",
    "reading",
    "study",
    "work",
    "project",
    "recipe",
    "travel",
    "journal",
    "health",
    "money",
    "people",
    "credential",
    "other",
)

SENSITIVE = frozenset({"journal", "health", "money", "people", "credential"})

MAX_LABELS = 8

PROMPT_VERSION = "note/1"

EXCERPT_CHARACTERS = 4000
"""How much of a note the model sees. Enough to tell a recipe from a
diary; short enough that a long document does not become a long
prompt. The excerpt is never stored and never leaves this process."""

SYSTEM = """You sort personal notes into one category and a few labels.

Categories, and nothing else:
  note reading study work project recipe travel
  journal health money people credential other

Choose the sensitive ones when they fit, and be generous about it:
  journal      a diary, feelings, a record of a day lived
  health       symptoms, appointments, a body
  money        balances, salary, debts, what things cost
  people       mostly about a named person who is not the writer
  credential   passwords, keys, tokens, anything secret

Labels are subjects, two or three words at most, in English, and never
sentences. Give at most eight, and none at all for a sensitive
category.

Answer with JSON only: {"category": "...", "labels": ["...", "..."]}"""


class ClassifierUnavailableError(RuntimeError):
    """The model could not be reached. Nothing was read."""


@dataclass(frozen=True)
class Classification:
    """What a model made of one note."""

    category: str
    labels: tuple[str, ...]
    model: str
    prompt_version: str = PROMPT_VERSION
    refused: str | None = None

    @property
    def answered(self) -> bool:
        return self.refused is None


def settle(category: str, labels: Sequence[str], model: str) -> Classification:
    """Make a model's answer safe to record, whatever it said.

    A category nobody defined becomes `other`; a sensitive category
    loses its labels; blanks and duplicates go; the ninth label and
    everything after it goes. None of this argues with the model. It
    decides what is recorded, which was never the model's job.
    """
    chosen = category.strip().lower()
    if chosen not in CATEGORIES:
        chosen = "other"
    if chosen in SENSITIVE:
        return Classification(category=chosen, labels=(), model=model)
    cleaned: list[str] = []
    for label in labels:
        text = " ".join(str(label).strip().lower().split())
        if text and text not in cleaned:
            cleaned.append(text)
    return Classification(category=chosen, labels=tuple(cleaned[:MAX_LABELS]), model=model)


def _ask(host: str, model: str, excerpt: str, timeout: float) -> str:
    body = json.dumps(
        {
            "model": model,
            "system": SYSTEM,
            "prompt": excerpt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.0},
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{host.rstrip('/')}/api/generate",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise ClassifierUnavailableError(str(error)) from error
    answer: str = payload.get("response", "")
    return answer


def classify(
    excerpt: str,
    host: str,
    model: str,
    timeout: float = 120.0,
) -> Classification:
    """One note, read once. Raises only when the model cannot be reached."""
    answer = _ask(host, model, excerpt[:EXCERPT_CHARACTERS], timeout)
    try:
        parsed = json.loads(answer)
    except json.JSONDecodeError:
        return Classification(
            category="other",
            labels=(),
            model=model,
            refused="the model did not answer with JSON",
        )
    if not isinstance(parsed, dict):
        return Classification(
            category="other",
            labels=(),
            model=model,
            refused="the model answered with something other than an object",
        )
    labels = parsed.get("labels", [])
    return settle(
        str(parsed.get("category", "other")),
        labels if isinstance(labels, list) else [],
        model,
    )
