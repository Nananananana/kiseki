"""Every input contract answers the same questions.

The gate of docs/records.md, kept by machine: a contract that skips a
question is a contract nobody argued about, and the questions are
where the privacy design lives.
"""

from pathlib import Path

import pytest

DOCS = Path(__file__).resolve().parents[2] / "docs"

CONTRACTS = ("photo-record.md", "activity-record.md")

SHARED_RULES = DOCS / "records.md"

GATE = (
    "Source.",
    "Schema.",
    "Privacy classification.",
    "Provenance.",
    "Timestamp semantics.",
    "Spatial semantics.",
    "Retention.",
    "Deletion.",
    "Derived outputs.",
    "Export policy.",
)


def test_the_shared_rules_exist() -> None:
    assert SHARED_RULES.is_file()


def test_the_gate_lists_every_question() -> None:
    text = SHARED_RULES.read_text(encoding="utf-8")
    for question in GATE:
        assert question in text, question


@pytest.mark.parametrize("contract", CONTRACTS)
def test_every_contract_has_a_document(contract: str) -> None:
    assert (DOCS / contract).is_file()


@pytest.mark.parametrize("contract", CONTRACTS)
def test_every_contract_says_what_it_will_not_carry(contract: str) -> None:
    """Rule seven: the section naming what is left out is the privacy design."""
    text = (DOCS / contract).read_text(encoding="utf-8").lower()
    assert "does not carry" in text or "never carried" in text, contract


@pytest.mark.parametrize("contract", CONTRACTS)
def test_every_contract_names_the_owner_and_the_producer(contract: str) -> None:
    text = (DOCS / contract).read_text(encoding="utf-8")
    assert "owner" in text
    assert "platform" in text


def test_the_shared_rules_link_every_contract() -> None:
    """A sibling nobody can find from the rules is a sibling in name only."""
    text = SHARED_RULES.read_text(encoding="utf-8")
    for contract in CONTRACTS:
        assert contract in text, contract
