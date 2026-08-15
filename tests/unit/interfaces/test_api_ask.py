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
    server = _serving(lambda question, language: empty)
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
    server = _serving(lambda question, language: None)
    try:
        try:
            _get(server.server_address[1], "/ask")
            raise AssertionError("expected 400")
        except urllib.error.HTTPError as error:
            assert error.code == 400
    finally:
        server.shutdown()
        server.server_close()
