"""The /ask endpoint speaks the answer contract over real HTTP."""

import json
import threading
import urllib.error
import urllib.request

from kiseki.application.asking import Answer
from kiseki.interfaces.api import make_server


def _serving(ask_factory):
    server = make_server(
        lambda: None, lambda: None, host="127.0.0.1", port=0, ask_factory=ask_factory
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def _get(port: int, path: str):
    with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}") as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def test_ask_answers_the_contract():
    empty = Answer("ramen", "", 0.0, None, None, (), "")
    server = _serving(lambda question, language, since, until: empty)
    try:
        status, payload = _get(server.server_address[1], "/ask?q=ramen")
        assert status == 200
        assert payload["question"] == "ramen"
        assert payload["answer"] is None
        assert payload["confidence"] == 0.0
        assert payload["evidence"] == []
    finally:
        server.shutdown()
        server.server_close()


def test_ask_requires_a_question():
    server = _serving(lambda question, language, since, until: None)
    try:
        try:
            _get(server.server_address[1], "/ask")
            raise AssertionError("expected 400")
        except urllib.error.HTTPError as error:
            assert error.code == 400
    finally:
        server.shutdown()
        server.server_close()


def _answer_naming_a_place() -> Answer:
    from datetime import UTC, datetime

    from kiseki.domain.insight import Insight, InsightDirection, InsightKind

    now = datetime(2026, 9, 5, tzinfo=UTC)
    insight = Insight(
        topic="place:35.68123,139.76543",
        kind=next(iter(InsightKind)),
        direction=next(iter(InsightDirection)),
        magnitude=1.0,
        first_seen=now,
        last_seen=now,
        confidence=0.9,
        evidence=("place:35.68123,139.76543",),
        novelty=0.5,
        derived_from=("kiseki insights",),
    )
    return Answer("q", "a", 0.5, None, None, (), "m", supporting_insights=(insight,))


def test_ask_serves_a_place_topic_blurred():
    """`/ask` was the one route in `_answer` that did not pass `blur`
    on, so `?raw=true` and its absence served the same coordinate."""
    server = _serving(lambda question, language, since, until: _answer_naming_a_place())
    try:
        _status, payload = _get(server.server_address[1], "/ask?q=q")
        assert payload["supporting_insights"][0]["topic"] == "place:35.68,139.77"
    finally:
        server.shutdown()
        server.server_close()


def test_ask_raw_true_keeps_the_coordinates():
    server = _serving(lambda question, language, since, until: _answer_naming_a_place())
    try:
        _status, payload = _get(server.server_address[1], "/ask?q=q&raw=true")
        assert payload["supporting_insights"][0]["topic"] == "place:35.68123,139.76543"
    finally:
        server.shutdown()
        server.server_close()
