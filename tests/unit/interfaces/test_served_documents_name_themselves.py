"""Every served document says what it is, and suggest is served.

An orchestrator refuses any document whose contract name it does not
know, at every entrance. Served payloads carried no name, so it could
only treat them as its own -- and could not notice when one moved.
ADR-0081's addendum: a document that crosses a socket travels.
"""

import json
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any
from urllib.request import urlopen

import pytest
from kiseki.adapters.fake.profiles import FakeProfileRepository
from kiseki.adapters.memory.repositories import (
    InMemoryAnchorRepository,
    InMemoryOutingRepository,
    InMemoryPhotoRepository,
)
from kiseki.application.pipeline import Pipeline, SuggestionSet
from kiseki.domain.services.suggesting import Suggestion, SuggestionKind
from kiseki.interfaces.api import make_server
from kiseki.interfaces.payloads import named, suggest_payload
from kiseki.ports.models import ModelUnavailableError


class _NoModel:
    def complete(self, system: str, prompts: list[str]) -> list[Any]:
        raise ModelUnavailableError("no model in this test")


@contextmanager
def _serving() -> Iterator[str]:
    def factory() -> Pipeline:
        return Pipeline(
            InMemoryPhotoRepository(),
            InMemoryOutingRepository(),
            InMemoryAnchorRepository(),
            profiles=FakeProfileRepository(),
        )

    server = make_server(factory, _NoModel, host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


def _get(url: str) -> dict[str, Any]:
    with urlopen(url) as response:
        return json.loads(response.read().decode("utf-8"))


ROUTES = (
    "health",
    "report",
    "profile",
    "trend",
    "compare",
    "discover",
    "insights",
    "lifecycle",
    "suggest",
)


def test_the_route_list_is_the_served_list() -> None:
    """If a route is added and not listed here, this file is green about
    less than it claims. Counted against the handler's own branches."""
    from inspect import getsource

    from kiseki.interfaces import api

    served = set(__import__("re").findall(r'path == "/([a-z]+)"', getsource(api)))
    assert served - {"ask", "tell"} == set(ROUTES), served


@pytest.mark.parametrize("route", ROUTES)
def test_every_served_document_names_itself(route: str) -> None:
    with _serving() as base:
        payload = _get(f"{base}/{route}")
    assert payload["schema"] == f"kiseki-{route}"
    assert payload["version"] == 1
    assert list(payload)[:2] == ["schema", "version"], "the name leads the document"


def test_suggest_on_an_empty_library_is_empty_and_still_named() -> None:
    with _serving() as base:
        payload = _get(f"{base}/suggest")
    assert payload["suggestions"] == []
    assert payload["day_trips"] == []
    assert payload["reach"] is None


def _found() -> SuggestionSet:
    place = Suggestion(
        kind=SuggestionKind.REVISIT,
        reference="place:35.68123,139.76543",
        confidence=0.9,
        days_since=40,
        cadence_days=25,
    )
    return SuggestionSet(suggestions=(place,), day_trips=(), reach=None)


def test_a_suggestion_s_place_is_blurred_by_default() -> None:
    served = suggest_payload(_found())
    assert served["suggestions"][0]["reference"] == "place:35.68,139.77"
    assert served["suggestions"][0]["kind"] == "revisit"


def test_raw_keeps_the_coordinates() -> None:
    served = suggest_payload(_found(), blur=False)
    assert served["suggestions"][0]["reference"] == "place:35.68123,139.76543"


def test_named_puts_the_name_first_and_keeps_the_body() -> None:
    document = named("thing", {"a": 1})
    assert list(document) == ["schema", "version", "a"]
    assert document["schema"] == "kiseki-thing"


def test_the_pipeline_suggests_nothing_from_nothing() -> None:
    pipeline = Pipeline(
        InMemoryPhotoRepository(), InMemoryOutingRepository(), InMemoryAnchorRepository()
    )
    found = pipeline.suggest(datetime.now(UTC))
    assert found == SuggestionSet((), (), None)
