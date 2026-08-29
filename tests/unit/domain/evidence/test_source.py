"""Sources are named, and the naming reads like a sentence."""

from kiseki.domain.evidence.source import (
    EVERYTHING,
    EvidenceSource,
    describe,
)


def test_every_source_has_a_label() -> None:
    for source in EvidenceSource:
        assert source.label
        assert source.label == source.value


def test_everything_is_every_source() -> None:
    assert frozenset(EvidenceSource) == EVERYTHING
    assert len(EVERYTHING) == 8


def test_nothing_reads_as_nothing() -> None:
    assert describe([]) == "nothing"


def test_one_source_reads_alone() -> None:
    assert describe([EvidenceSource.PHOTOGRAPH]) == "photograph"


def test_several_sources_read_in_pipeline_order() -> None:
    said = describe([EvidenceSource.SCREEN, EvidenceSource.PHOTOGRAPH, EvidenceSource.JOURNEY])
    assert said == "photograph, journey and screen reading"
