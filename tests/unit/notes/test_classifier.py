"""Reading a note, and keeping almost none of it."""

import pytest
from kiseki_notes.classifier import (
    CATEGORIES,
    MAX_LABELS,
    SENSITIVE,
    Classification,
    settle,
)
from kiseki_notes.trust import admitted, describe, host_of


def test_an_ordinary_note_keeps_its_labels() -> None:
    settled = settle("reading", ["Raft", "consensus"], "demo")
    assert settled.category == "reading"
    assert settled.labels == ("raft", "consensus")
    assert settled.answered


@pytest.mark.parametrize("category", sorted(SENSITIVE))
def test_a_sensitive_category_loses_its_labels_whatever_the_model_said(
    category: str,
) -> None:
    settled = settle(category, ["a very bad day", "my doctor"], "demo")
    assert settled.category == category
    assert settled.labels == ()


def test_a_category_nobody_defined_becomes_other() -> None:
    settled = settle("diary of my heart", ["something"], "demo")
    assert settled.category == "other"
    assert settled.category in CATEGORIES


def test_labels_are_tidied_rather_than_argued_with() -> None:
    settled = settle("note", ["  Raft  ", "raft", "", "  ", "Consensus"], "demo")
    assert settled.labels == ("raft", "consensus")


def test_a_note_is_not_a_document_to_be_summarised() -> None:
    settled = settle("note", [f"label {index}" for index in range(20)], "demo")
    assert len(settled.labels) == MAX_LABELS


def test_a_refusal_is_recorded_rather_than_raised() -> None:
    refused = Classification(category="other", labels=(), model="demo", refused="no JSON")
    assert not refused.answered


@pytest.mark.parametrize(
    ("endpoint", "expected"),
    [
        ("http://localhost:11434", "this machine"),
        ("http://127.0.0.1:11434", "this machine"),
        ("http://llm01.lan:11434", "a machine on your network"),
        ("http://192.168.1.20", "a machine on your network"),
        ("https://api.openai.com/v1/", "a machine this producer cannot place"),
    ],
)
def test_a_host_is_placed_by_its_own_shape(endpoint: str, expected: str) -> None:
    assert describe(host_of(endpoint)) == expected


def test_the_default_boundary_admits_only_this_machine() -> None:
    assert admitted("localhost", "same_host")
    assert not admitted("llm01.lan", "same_host")


def test_the_network_boundary_admits_the_network() -> None:
    assert admitted("llm01.lan", "private_network")
    assert not admitted("api.openai.com", "private_network")


def test_a_named_host_is_admitted() -> None:
    assert admitted("api.example.com", "same_host", trusted=("api.example.com",))


def test_the_producer_agrees_with_the_core() -> None:
    """Two copies that must agree, checked against each other.

    The producer cannot import the core, so nothing but a test can
    hold the two judgements together. See the note in trust.py.
    """
    from kiseki.domain.trust import TrustBoundary
    from kiseki.domain.trust import judge as core_judge

    for endpoint in (
        "http://localhost:11434",
        "http://127.0.0.1:11434",
        "http://llm01.lan:11434",
        "http://192.168.1.20:11434",
        "https://api.openai.com/v1/",
        "http://8.8.8.8:11434",
    ):
        host = host_of(endpoint)
        for boundary in TrustBoundary:
            assert admitted(host, boundary.value) == core_judge(endpoint, boundary).admitted, (
                f"{endpoint} under {boundary.value}"
            )
