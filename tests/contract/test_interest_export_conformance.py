"""The export is a published contract, and this is what checks it.

`kiseki export` is the only document this library ever prepares for
the world outside the machine (ADR-0047), which makes it the one
contract other people read. The input contract has had a schema and a
conformance kit since ADR-0005; this gives the output contract the
same, and points the kit at the library's own output.
"""

import json
from collections.abc import Mapping
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pytest
from kiseki.application.exporting import interest_export
from kiseki.domain.interests import EvidenceKind, Interest, InterestEvidence, Profile
from kiseki.domain.lifecycle import LifecycleReport, LifecycleStage, TopicLifecycle
from kiseki_conformance import (
    InterestExportConformance,
    check_export_semantics,
    load_export_schema,
    validate_export,
)
from kiseki_conformance.cli import EXIT_OK, EXIT_VIOLATIONS, main
from kiseki_conformance.contracts import INTEREST_EXPORT, PHOTO_RECORD, identify

REPO_ROOT = Path(__file__).parents[2]
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "interest_export"
CANONICAL_SCHEMA = REPO_ROOT / "schemas" / "interest-export-v1.json"

WHEN = datetime(2026, 6, 1, 12, tzinfo=UTC)
TODAY = date(2026, 8, 30)


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def fixtures(prefix: str) -> list[Path]:
    found = sorted(FIXTURE_DIR.glob(f"{prefix}_*.json"))
    assert found, f"no fixtures found for prefix {prefix!r}"
    return found


def export_of(*interests: Mapping[str, Any], stages: list[dict[str, str]] | None = None) -> Any:
    base = load(FIXTURE_DIR / "valid_nothing_to_say.json")
    base["interests"] = list(interests)
    base["stages"] = stages or []
    return base


def an_interest(
    topic: str,
    score: float = 0.6,
    confidence: float = 0.5,
    first_seen: str = "2026-01",
    last_seen: str = "2026-06",
) -> dict[str, Any]:
    return {
        "topic": topic,
        "score": score,
        "confidence": confidence,
        "first_seen": first_seen,
        "last_seen": last_seen,
    }


class TestTheSchema:
    def test_the_schema_itself_is_valid(self) -> None:
        from jsonschema import Draft202012Validator

        Draft202012Validator.check_schema(load_export_schema())

    def test_the_bundled_copy_matches_the_published_one(self) -> None:
        """The packaged copy must not drift from the one in the repository."""
        assert load_export_schema() == load(CANONICAL_SCHEMA)

    @pytest.mark.parametrize("path", fixtures("valid"), ids=lambda p: p.stem)
    def test_valid_fixtures_report_no_violations(self, path: Path) -> None:
        assert validate_export(load(path)) == []
        assert check_export_semantics(load(path)) == []

    @pytest.mark.parametrize("path", fixtures("invalid"), ids=lambda p: p.stem)
    def test_invalid_fixtures_report_violations(self, path: Path) -> None:
        assert validate_export(load(path)) != []


class TestWhatASchemaCannotSay:
    """The rules left to the semantic pass, and why each one is there."""

    def test_a_topic_appears_once(self) -> None:
        violations = check_export_semantics(export_of(an_interest("ramen"), an_interest("ramen")))
        assert any("duplicate topic" in message for message in violations)

    def test_a_stage_without_its_interest_is_reported(self) -> None:
        """The two halves of the document can never disagree (ADR-0069)."""
        violations = check_export_semantics(
            export_of(an_interest("ramen"), stages=[{"topic": "lesion", "stage": "new"}])
        )
        assert any("lesion" in message for message in violations)

    def test_a_stage_is_given_once(self) -> None:
        violations = check_export_semantics(
            export_of(
                an_interest("ramen"),
                stages=[{"topic": "ramen", "stage": "new"}, {"topic": "ramen", "stage": "stable"}],
            )
        )
        assert any("duplicate topic" in message for message in violations)

    def test_last_seen_is_not_before_first_seen(self) -> None:
        """A schema cannot compare two properties of the same object."""
        violations = check_export_semantics(
            export_of(an_interest("ramen", first_seen="2026-06", last_seen="2026-01"))
        )
        assert any("last_seen" in message for message in violations)

    def test_a_month_that_never_happened_is_reported(self) -> None:
        violations = check_export_semantics(export_of(an_interest("ramen", first_seen="2026-13")))
        assert any("first_seen" in message for message in violations)

    def test_a_day_that_never_happened_is_reported(self) -> None:
        payload = export_of()
        payload["exported_on"] = "2026-02-31"
        assert any("exported_on" in message for message in check_export_semantics(payload))

    def test_the_strongest_interest_comes_first(self) -> None:
        """A consumer showing the first few must be shown the best few."""
        violations = check_export_semantics(
            export_of(
                an_interest("raft", score=0.4, confidence=0.5),
                an_interest("ramen", score=0.82, confidence=0.7),
            )
        )
        assert any("order" in message for message in violations)

    def test_a_place_is_named_in_plain_words(self) -> None:
        """The schema refuses it too; this is the message a producer reads."""
        violations = check_export_semantics(export_of(an_interest("place:kyoto")))
        assert any("place" in message for message in violations)


class TestIdentifyingAContract:
    def test_an_export_names_itself(self) -> None:
        assert identify(load(FIXTURE_DIR / "valid_full.json")) is INTEREST_EXPORT

    def test_a_photo_record_document_names_itself(self) -> None:
        photo = REPO_ROOT / "tests" / "fixtures" / "photo_record" / "valid_full.json"
        assert identify(load(photo)) is PHOTO_RECORD

    def test_a_document_that_names_nothing_is_not_guessed_at(self) -> None:
        assert identify({"interests": []}) is None


def _interest(topic: str, score: float = 0.6, confidence: float = 0.5) -> Interest:
    evidence = tuple(
        InterestEvidence(kind=EvidenceKind.PHOTOGRAPH, reference=f"caption:aa{n}", observed_at=WHEN)
        for n in range(3)
    )
    return Interest(
        topic=topic,
        score=score,
        confidence=confidence,
        evidence=evidence,
        first_seen=WHEN,
        last_seen=WHEN,
    )


def _profile(*interests: Interest) -> Profile:
    return Profile(generated_at=WHEN, interests=interests)


def _lifecycle() -> LifecycleReport:
    items = tuple(
        TopicLifecycle(topic=topic, stage=LifecycleStage.NEW, strength=0.3, seen_profiles=1)
        for topic in ("ramen", "raft")
    )
    return LifecycleReport(oldest_at=WHEN, latest_at=WHEN, lifecycles=items)


class TestTheLibrarysOwnExport:
    """What the issue is actually for: kiseki output against kiseki contract."""

    def test_an_export_of_a_real_profile_conforms(self) -> None:
        payload = interest_export(
            _profile(_interest("ramen", 0.8, 0.7), _interest("raft")), _lifecycle(), TODAY
        )
        assert validate_export(payload) == []
        assert check_export_semantics(payload) == []

    def test_an_export_of_an_empty_library_conforms(self) -> None:
        payload = interest_export(Profile(generated_at=WHEN, interests=()), None, TODAY)
        assert validate_export(payload) == []
        assert check_export_semantics(payload) == []


class TestReferenceExportConformance(InterestExportConformance):
    """Demonstrates how a producer of this document plugs into the suite."""

    @pytest.fixture
    def document(self) -> Mapping[str, Any]:
        result: Mapping[str, Any] = load(FIXTURE_DIR / "valid_full.json")
        return result


class TestTheCommandLine:
    def test_it_recognises_an_export_without_being_told(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert main([str(FIXTURE_DIR / "valid_full.json")]) == EXIT_OK
        assert "kiseki-interest-export v1" in capsys.readouterr().out

    def test_it_rejects_an_export_that_carries_evidence(self) -> None:
        path = FIXTURE_DIR / "invalid_evidence_reference.json"
        assert main([str(path), "--quiet"]) == EXIT_VIOLATIONS

    def test_a_contract_may_be_named_outright(self) -> None:
        path = FIXTURE_DIR / "valid_full.json"
        assert main([str(path), "--contract", "photo-record", "--quiet"]) == EXIT_VIOLATIONS

    def test_a_document_naming_no_contract_is_refused_rather_than_guessed_at(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        path = tmp_path / "anonymous.json"
        path.write_text(json.dumps({"interests": []}), encoding="utf-8")
        assert main([str(path)]) == EXIT_VIOLATIONS
        assert "names no contract" in capsys.readouterr().err
