"""The HTTP interface: what the command line answers, served as JSON.

Loopback, standard library, read-only. The tests start a real server
on an ephemeral port and ask it with urllib, so what is specified is
the wire itself. Model-dependent answers are exercised with a stub
that fails the way an absent Ollama fails.
"""

import json
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest
from kiseki.adapters.fake.profiles import FakeProfileRepository
from kiseki.adapters.memory.repositories import (
    InMemoryAnchorRepository,
    InMemoryOutingRepository,
    InMemoryPhotoRepository,
)
from kiseki.application.pipeline import Pipeline
from kiseki.domain.interests import (
    EvidenceKind,
    Interest,
    InterestEvidence,
    Profile,
)
from kiseki.interfaces.api import make_server
from kiseki.ports.models import ModelUnavailableError

BASE = datetime(2026, 6, 1, 12)
PLACE = "place:35.68123,139.76543"


class _UnavailableModel:
    """Fails the way an absent Ollama fails."""

    def complete(self, system: str, prompts: object) -> object:
        raise ModelUnavailableError("no model runs in these tests")


def _interest(topic: str, score: float, confidence: float) -> Interest:
    evidence = (
        InterestEvidence(
            kind=EvidenceKind.PHOTOGRAPH,
            reference=f"caption:{topic}",
            observed_at=BASE,
        ),
    )
    return Interest(
        topic=topic,
        score=score,
        confidence=confidence,
        evidence=evidence,
        first_seen=BASE,
        last_seen=BASE,
    )


def _profile(days: int, *interests: Interest) -> Profile:
    return Profile(generated_at=BASE + timedelta(days=days), interests=interests)


@contextmanager
def _serving(profiles: FakeProfileRepository | None = None) -> Iterator[str]:
    def factory() -> Pipeline:
        return Pipeline(
            InMemoryPhotoRepository(),
            InMemoryOutingRepository(),
            InMemoryAnchorRepository(),
            profiles=profiles,
        )

    server = make_server(factory, _UnavailableModel, host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


def _get(url: str) -> dict[str, Any]:
    with urlopen(url) as response:
        payload: dict[str, Any] = json.loads(response.read().decode("utf-8"))
        return payload


class TestApi:
    def test_health_answers(self) -> None:
        with _serving() as base:
            assert _get(f"{base}/health") == {"status": "ok"}

    def test_a_served_profile_does_not_grow_the_history(self) -> None:
        repository = FakeProfileRepository()
        with _serving(repository) as base:
            _get(f"{base}/profile")
            _get(f"{base}/profile")
        assert repository.history() == ()

    def test_trend_answers_a_short_history(self) -> None:
        with _serving(FakeProfileRepository()) as base:
            payload = _get(f"{base}/trend")
        assert payload["trends"] is None
        assert payload["reason"] == "not enough history"

    def test_trend_serves_the_drift_blurred(self) -> None:
        repository = FakeProfileRepository()
        repository.save(_profile(0, _interest(PLACE, 0.5, 0.4)))
        repository.save(_profile(20, _interest(PLACE, 0.9, 0.6)))
        with _serving(repository) as base:
            payload = _get(f"{base}/trend")
        assert payload["trends"][0]["topic"] == "place:35.68,139.77"
        assert payload["trends"][0]["direction"] == "rising"

    def test_raw_true_keeps_the_coordinates(self) -> None:
        repository = FakeProfileRepository()
        repository.save(_profile(0, _interest(PLACE, 0.5, 0.4)))
        repository.save(_profile(20, _interest(PLACE, 0.9, 0.6)))
        with _serving(repository) as base:
            payload = _get(f"{base}/trend?raw=true")
        assert payload["trends"][0]["topic"] == PLACE

    def test_an_unknown_path_is_404(self) -> None:
        with _serving() as base:
            with pytest.raises(HTTPError) as caught:
                _get(f"{base}/nothing")
            assert caught.value.code == 404

    def test_only_get_is_served(self) -> None:
        with _serving() as base:
            request = Request(f"{base}/health", data=b"{}", method="POST")
            with pytest.raises(HTTPError) as caught:
                urlopen(request)
            assert caught.value.code == 405

    def test_tell_without_a_model_is_503(self) -> None:
        with _serving() as base:
            with pytest.raises(HTTPError) as caught:
                _get(f"{base}/tell")
            assert caught.value.code == 503

    def test_tell_rejects_an_unknown_language(self) -> None:
        with _serving() as base:
            with pytest.raises(HTTPError) as caught:
                _get(f"{base}/tell?lang=fr")
            assert caught.value.code == 400