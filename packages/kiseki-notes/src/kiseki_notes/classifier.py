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

PROMPT_VERSION = "note/2"
"""Bumped when the guidance changes, so readings made under an older
prompt can be told apart and made again (ADR-0051). note/2 rewrote
what `people` and `journal` mean, after the corpus showed both being
missed."""

MAX_ANSWER_TOKENS = 200
"""How long an answer may be before it is stopped.

A classification is a category and a few labels: fifty tokens, and two
hundred is generous. Measured on a real folder, one note took two
hundred seconds while a note four times its size took eleven -- the
excerpt is capped, so the prompts were the same length and the model
was simply still talking. A ceiling turns that into a refusal in a few
seconds instead of a stall."""

EXCERPT_CHARACTERS = 4000
"""How much of a note the model sees. Enough to tell a recipe from a
diary; short enough that a long document does not become a long
prompt. The excerpt is never stored and never leaves this process."""

SYSTEM = """You sort personal notes into one category and a few labels.

Categories, and nothing else:
  note reading study work project recipe travel
  journal health money people credential other

Choose the sensitive ones when they fit. When a note could be two
things and one of them is sensitive, choose the sensitive one.

  journal      a page about a day the writer lived. A date for a
               title, what happened, what they did. It is a diary
               whether or not it says how anything felt.
  health       symptoms, appointments, medication, a body, a check-up
               result, an intention to look after oneself.
  money        balances, salary, debts, rent, what things cost, a
               household budget, a review of spending.
  people       a named person other than the writer appears, and the
               note says something about their situation, their
               wishes, their family or their difficulties. A meeting
               note about a colleague is this, not work.
  credential   passwords, keys, tokens, network names, anything the
               writer would not want read aloud.

Labels are subjects, two or three words at most, in English, and never
sentences. Give at most eight, and none at all for a sensitive
category.

Answer with JSON only: {"category": "...", "labels": ["...", "..."]}"""


class ClassifierUnavailableError(RuntimeError):
    """The model could not be reached at all. Nothing was read.

    Told apart from a note that took too long, because the two mean
    different things: a note that stalled is one refusal and the work
    goes on, while a host that answers nothing will answer nothing for
    every note after it too (ADR-0015, ADR-0052)."""


class NoteTookTooLongError(RuntimeError):
    """This note did not come back in time. The next one might."""


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
            "options": {"temperature": 0.0, "num_predict": MAX_ANSWER_TOKENS},
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
    except TimeoutError as error:
        raise NoteTookTooLongError(str(error)) from error
    except (urllib.error.URLError, OSError) as error:
        if isinstance(getattr(error, "reason", None), TimeoutError):
            raise NoteTookTooLongError(str(error)) from error
        if "timed out" in str(error).lower():
            raise NoteTookTooLongError(str(error)) from error
        raise ClassifierUnavailableError(str(error)) from error
    answer: str = payload.get("response", "")
    return answer


def classify(
    excerpt: str,
    host: str,
    model: str,
    timeout: float = 120.0,
) -> Classification:
    """One note, read once. Raises only when the model cannot be reached.

    An empty note is not asked about. There is nothing in it to
    classify, and a model asked about nothing answers with something.
    """
    if not excerpt.strip():
        return Classification(
            category="other",
            labels=(),
            model=model,
            refused="the note is empty",
        )
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
