"""The privacy report answers about this installation, not about a README."""

from kiseki.config.model import ModelSettings
from kiseki.domain.trust import TrustBoundary
from kiseki.interfaces.claims import NEVER_STORED, outbound_lines


def _said(settings: ModelSettings) -> str:
    return "\n".join(f"{name}: {value}" for name, value in outbound_lines(settings))


def test_every_claim_names_the_test_that_keeps_it() -> None:
    for subject, reason, test in NEVER_STORED:
        assert subject and reason
        assert test.startswith("tests/"), subject


def test_a_local_model_means_nothing_leaves() -> None:
    said = _said(ModelSettings())
    assert "this machine" in said
    assert "nowhere else" in said


def test_a_model_on_the_network_is_said_plainly() -> None:
    """The report stops claiming nothing is sent the moment it is."""
    settings = ModelSettings(
        host="http://llm01.lan:11434",
        boundary=TrustBoundary.PRIVATE_NETWORK,
    )
    said = _said(settings)
    assert "a machine on your network" in said
    assert "a reduced copy is sent to llm01.lan" in said


def test_the_hosts_the_owner_named_are_shown() -> None:
    settings = ModelSettings(
        host="http://gpu.example.com:11434",
        trusted_hosts=("gpu.example.com",),
    )
    assert "gpu.example.com" in _said(settings)


def test_the_boundary_is_always_stated() -> None:
    assert "same_host" in _said(ModelSettings())
