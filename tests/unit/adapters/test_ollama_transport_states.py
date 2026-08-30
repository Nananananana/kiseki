"""Four things can go wrong before a model answers, and they are not one thing.

The transport turned every `OSError` into `cannot reach ollama at {host}`.
A socket timeout is an `OSError`, so a request that waited out five
minutes reported that the host could not be reached. It could be
reached. It was busy -- with this library's own queue, or with another
program's, since one Ollama serves one request at a time.

A message that asserts a cause it does not know is worse than a silent
failure: an absence is doubted, an assertion is believed.
"""

import urllib.error
import urllib.request
from typing import Any

import pytest
from kiseki.adapters.ollama.models import _http_post
from kiseki.ports.models import ModelUnavailableError

HOST = "http://127.0.0.1:11434"


def raising(error: BaseException) -> Any:
    def urlopen(*_args: Any, **_kwargs: Any) -> Any:
        raise error

    return urlopen


class TestReachableAndSlow:
    def test_a_timeout_says_it_waited(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(urllib.request, "urlopen", raising(TimeoutError("timed out")))
        with pytest.raises(ModelUnavailableError) as raised:
            _http_post(HOST, 12.0)("/api/chat", {})
        assert "waited" in str(raised.value)
        assert "12" in str(raised.value)

    def test_a_timeout_does_not_claim_the_host_is_unreachable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(urllib.request, "urlopen", raising(TimeoutError("timed out")))
        with pytest.raises(ModelUnavailableError) as raised:
            _http_post(HOST, 12.0)("/api/chat", {})
        assert "cannot reach" not in str(raised.value)

    def test_a_timeout_wrapped_by_urllib_is_read_the_same_way(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """urllib reports a socket timeout either way depending on where
        in the exchange it happens."""
        wrapped = urllib.error.URLError(TimeoutError("timed out"))
        monkeypatch.setattr(urllib.request, "urlopen", raising(wrapped))
        with pytest.raises(ModelUnavailableError) as raised:
            _http_post(HOST, 12.0)("/api/chat", {})
        assert "waited" in str(raised.value)

    def test_it_says_the_wait_may_be_a_queue(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """One Ollama answers one request at a time, so the wait may
        belong to somebody else's request entirely."""
        monkeypatch.setattr(urllib.request, "urlopen", raising(TimeoutError("timed out")))
        with pytest.raises(ModelUnavailableError) as raised:
            _http_post(HOST, 12.0)("/api/chat", {})
        assert "queue" in str(raised.value)


class TestUnreachable:
    def test_a_refused_connection_still_says_it_could_not_reach(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        refused = urllib.error.URLError(ConnectionRefusedError("refused"))
        monkeypatch.setattr(urllib.request, "urlopen", raising(refused))
        with pytest.raises(ModelUnavailableError) as raised:
            _http_post(HOST, 12.0)("/api/chat", {})
        assert "cannot reach" in str(raised.value)
        assert "waited" not in str(raised.value)


class TestCouldNotEvenAsk:
    """Not reached and failed, and not tried and could not reach: no
    request was ever formed. Retrying cannot help, and a setting has to
    change, so this is said at the door like any other bad setting."""

    def test_a_host_that_is_not_a_url_names_the_host(self) -> None:
        with pytest.raises(ValueError) as raised:
            _http_post("not a url", 12.0)("/api/chat", {})
        assert "not a url" in str(raised.value)

    def test_it_is_not_reported_as_a_failure_to_reach(self) -> None:
        with pytest.raises(ValueError) as raised:
            _http_post("not a url", 12.0)("/api/chat", {})
        assert "cannot reach" not in str(raised.value)

    def test_it_says_nothing_was_sent(self) -> None:
        with pytest.raises(ValueError) as raised:
            _http_post("not a url", 12.0)("/api/chat", {})
        assert "nothing was sent" in str(raised.value)

    def test_it_is_not_one_of_the_two_model_failures(self) -> None:
        """A misconfiguration is not a model that refused and not a model
        that was busy. A batch must not record it against a photograph."""
        from kiseki.ports.models import ModelRefusedError

        with pytest.raises(ValueError) as raised:
            _http_post("not a url", 12.0)("/api/chat", {})
        assert not isinstance(raised.value, ModelRefusedError | ModelUnavailableError)
