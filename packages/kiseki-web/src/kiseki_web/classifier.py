"""Reading a page's address, and keeping almost none of it.

The model is given the address and the title, and nothing else -- the
producer never fetches a page (ADR-0085). What comes back is a
category and a handful of labels, and everything else is discarded
here, in this process, before a record exists.

The shape is borrowed from the notes producer. The code is not: a
producer that imported another would make the record contract
decorative, and the contract is the only thing any of these sides is
meant to share.

What the model returns is checked rather than trusted. An unknown
category becomes `other`, labels past the eighth are dropped, and a
category that carries no labels loses them whatever the model said. A
model that ignores its instructions is a weaker classifier, not a
leak.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Sequence
from dataclasses import dataclass

CATEGORIES = (
    "reading",
    "study",
    "work",
    "project",
    "reference",
    "recipe",
    "travel",
    "video",
    "health",
    "money",
    "people",
    "credential",
    "shopping",
    "news",
    "private",
    "other",
)

UNLABELLED = frozenset({"health", "money", "people", "credential", "shopping", "news", "private"})
"""Recorded, and never labelled. `docs/web-record.md` argues each one.

`news` is the deliberate loss: labels on news reading would be the
most useful thing the web could give a profile, and they would be an
inference about politics and religion from what somebody read once.
`private` is the catch-all, so that what cannot be placed does not
land in `other` and get labels."""

MAX_LABELS = 8

PROMPT_VERSION = "page/1"

MAX_ANSWER_TOKENS = 200

SYSTEM = """You sort web pages into one category and a few labels.

You are given a page's address and its title. You have not seen the
page and must not guess at what is on it beyond what those two say.

Categories, and nothing else:
  reading study work project reference recipe travel video
  health money people credential shopping news private other

Choose the unlabelled ones when they fit. When a page could be two
things and one of them is unlabelled, choose the unlabelled one.

  health       symptoms, conditions, medication, appointments, a
               clinic, a body. A search for a symptom is this.
  money        banking, tax, debts, salary, what things cost.
  people       a named person's page, profile or situation. They did
               not choose to be in this library.
  credential   a sign-in, a password manager, a key, a network.
  shopping     a product, a basket, an order, a delivery. The count is
               evidence; the labels would be the receipt.
  news         an article about events. Do not label what somebody
               read about the world.
  private      anything the reader would not read aloud.

Labels are subjects, two or three words at most, in English, never
sentences. Give at most eight, and none at all for an unlabelled
category.

Answer with JSON only: {"category": "...", "labels": ["...", "..."]}"""


class ClassifierUnavailableError(RuntimeError):
    """The model could not be reached at all. Nothing was read."""


class PageTookTooLongError(RuntimeError):
    """This page did not come back in time. The next one might."""


@dataclass(frozen=True)
class Classification:
    """What a model made of one address."""

    category: str
    labels: tuple[str, ...]
    model: str
    prompt_version: str = PROMPT_VERSION
    refused: str | None = None

    @property
    def answered(self) -> bool:
        return self.refused is None


def settle(category: str, labels: Sequence[str], model: str) -> Classification:
    """Make a model's answer safe to record, whatever it said."""
    chosen = category.strip().lower()
    if chosen not in CATEGORIES:
        chosen = "other"
    if chosen in UNLABELLED:
        return Classification(category=chosen, labels=(), model=model)
    cleaned: list[str] = []
    for label in labels:
        text = " ".join(str(label).strip().lower().split())
        if text and text not in cleaned:
            cleaned.append(text)
    return Classification(category=chosen, labels=tuple(cleaned[:MAX_LABELS]), model=model)


def asked_about(address: str, title: str) -> str:
    """What the model is shown. Never stored, and never a record."""
    said = title.strip()
    return f"address: {address.strip()}\ntitle: {said}" if said else f"address: {address.strip()}"


def _ask(host: str, model: str, prompt: str, timeout: float) -> str:
    body = json.dumps(
        {
            "model": model,
            "system": SYSTEM,
            "prompt": prompt,
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
        raise PageTookTooLongError(str(error)) from error
    except (urllib.error.URLError, OSError) as error:
        if isinstance(getattr(error, "reason", None), TimeoutError):
            raise PageTookTooLongError(str(error)) from error
        if "timed out" in str(error).lower():
            raise PageTookTooLongError(str(error)) from error
        raise ClassifierUnavailableError(str(error)) from error
    answer: str = payload.get("response", "")
    return answer


def classify(
    address: str,
    title: str,
    host: str,
    model: str,
    timeout: float = 120.0,
) -> Classification:
    """One page, read once, from its address and its title."""
    if not address.strip():
        return Classification(
            category="other",
            labels=(),
            model=model,
            refused="the page has no address",
        )
    answer = _ask(host, model, asked_about(address, title), timeout)
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
