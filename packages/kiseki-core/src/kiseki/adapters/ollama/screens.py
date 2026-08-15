"""Ollama adapter for the screen reader.

The staged VLM (ADR-0014) reads each screenshot into compact JSON.
The raw answer is parsed here and never leaves the adapter: what
comes out is a category and labels, nothing else. See ADR-0030.
"""

from __future__ import annotations

import base64
import json
from collections.abc import Sequence
from typing import Any

from kiseki.adapters.ollama.models import (
    DEFAULT_CAPTIONING_MODEL,
    DEFAULT_HOST,
    DEFAULT_KEEP_ALIVE,
    DEFAULT_TIMEOUT_SECONDS,
    Post,
    _ChatAdapter,
    _http_post,
)
from kiseki.domain.screen.reading import CATEGORIES, SENSITIVE_CATEGORIES
from kiseki.ports.models import Completion, ModelRefusedError
from kiseki.ports.screens import ScreenRead

MAX_LABELS = 6
SCREEN_PROMPT = (
    "This is a phone screenshot. Answer ONLY compact JSON, nothing"
    ' else: {"category": "<one of: '
    + ", ".join(CATEGORIES)
    + '>", "labels": [up to six short lowercase english nouns for'
    " what the user seems interested in]}."
    " For chat, auth or finance screens, labels MUST be []."
)


class OllamaScreenshotReader(_ChatAdapter):
    """Reads screenshots through Ollama's chat endpoint."""

    def __init__(
        self,
        model: str = DEFAULT_CAPTIONING_MODEL,
        host: str = DEFAULT_HOST,
        keep_alive: str = DEFAULT_KEEP_ALIVE,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        post: Post | None = None,
    ) -> None:
        super().__init__(model, keep_alive, post if post is not None else _http_post(host, timeout))

    def read(self, images: Sequence[bytes]) -> list[ScreenRead]:
        results = []
        for image in images:
            message = {
                "role": "user",
                "content": SCREEN_PROMPT,
                "images": [base64.b64encode(image).decode("ascii")],
            }
            results.append(_parse(self._record(self._ask([message]))))
        return results


def _parse(completion: Completion) -> ScreenRead:
    text = completion.text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        document: Any = json.loads(text)
    except json.JSONDecodeError as error:
        raise ModelRefusedError(f"unparseable screen answer: {text[:80]!r}") from error
    if not isinstance(document, dict):
        raise ModelRefusedError(f"unparseable screen answer: {text[:80]!r}")

    category = str(document.get("category", "")).strip().lower()
    if category not in CATEGORIES:
        category = "other"
    raw = document.get("labels", [])
    labels: tuple[str, ...] = ()
    if isinstance(raw, list):
        cleaned = [str(item).strip().lower() for item in raw]
        labels = tuple(label for label in cleaned if label)[:MAX_LABELS]
    if category in SENSITIVE_CATEGORIES:
        labels = ()
    return ScreenRead(category=category, labels=labels, model=completion.model)
