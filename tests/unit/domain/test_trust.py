"""Where a model is, and whether it is allowed to be there."""

import pytest
from kiseki.domain.trust import (
    Locality,
    TrustBoundary,
    host_of,
    judge,
    locality_of,
)


@pytest.mark.parametrize(
    ("endpoint", "expected"),
    [
        ("http://localhost:11434", "localhost"),
        ("http://127.0.0.1:11434/", "127.0.0.1"),
        ("localhost:11434", "localhost"),
        ("https://llm01.lan:8000/v1/", "llm01.lan"),
        ("http://192.168.1.20", "192.168.1.20"),
    ],
)
def test_the_host_is_found_however_it_was_written(endpoint: str, expected: str) -> None:
    assert host_of(endpoint) == expected


@pytest.mark.parametrize(
    ("host", "expected"),
    [
        ("localhost", Locality.LOOPBACK),
        ("127.0.0.1", Locality.LOOPBACK),
        ("::1", Locality.LOOPBACK),
        ("192.168.1.20", Locality.PRIVATE),
        ("10.0.0.5", Locality.PRIVATE),
        ("172.16.4.4", Locality.PRIVATE),
        ("llm01", Locality.PRIVATE),
        ("llm01.lan", Locality.PRIVATE),
        ("gpu.internal", Locality.PRIVATE),
        ("8.8.8.8", Locality.PUBLIC),
        ("api.openai.com", Locality.UNKNOWN),
        ("llm01.corp", Locality.UNKNOWN),
        ("", Locality.UNKNOWN),
    ],
)
def test_a_host_is_placed_by_its_own_shape(host: str, expected: Locality) -> None:
    assert locality_of(host) is expected


def test_the_default_boundary_admits_only_this_machine() -> None:
    assert judge("http://localhost:11434").admitted
    assert not judge("http://192.168.1.20:11434").admitted


def test_the_network_boundary_admits_the_network() -> None:
    verdict = judge("http://llm01.lan:11434", TrustBoundary.PRIVATE_NETWORK)
    assert verdict.admitted
    assert "your network" in verdict.reason


def test_a_name_that_cannot_be_placed_is_refused() -> None:
    """Resolving it would be a network call, which is the thing being judged."""
    verdict = judge("https://api.openai.com/v1/", TrustBoundary.PRIVATE_NETWORK)
    assert not verdict.admitted
    assert "cannot be placed" in verdict.reason
    assert "trusted_hosts" in verdict.reason


def test_a_named_host_is_admitted_under_every_boundary() -> None:
    verdict = judge(
        "https://api.example.com/v1/",
        TrustBoundary.SAME_HOST,
        trusted_hosts=("api.example.com",),
    )
    assert verdict.admitted
    assert "you named" in verdict.reason


def test_anywhere_admits_anything() -> None:
    assert judge("https://api.openai.com/", TrustBoundary.ANYWHERE).admitted


def test_a_refusal_says_what_would_have_been_sent() -> None:
    verdict = judge("http://203.0.113.7:11434")
    assert not verdict.admitted
    assert "photograph would be sent" in verdict.reason
