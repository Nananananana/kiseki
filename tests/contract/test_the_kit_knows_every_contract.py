"""Every published contract is one a foreign producer can check.

Five contracts exist. Two had a schema and a suite (#373), and the
missing three were the ones written for producers outside this
repository:

    PhotoRecord v1              schema + suite   producer is outside
    ActivityRecord v1           --               converter unwritten
    NoteRecord v1               --               kiseki-notes, and
                                                 musubi's converter
    WebRecord v1                --               kiseki-web
    kiseki-interest-export v1   schema + suite   produced here

#368 found the kit **contradicting** the contract -- refusing a byte
order mark that `docs/records.md` promises and the core accepts. This
is worse in one specific way: a contract absent from the kit cannot
contradict anything. It simply cannot be checked by the people it was
written for, and nothing says so.

**Why note and web cannot be told apart, which is the whole design.**

Both documents are bare arrays carrying the same six field names.
Their category sets overlap in 11 of 13 and 16. The one thing that
looks distinguishing is the reference prefix -- `note:` against
`page:` -- and `docs/note-record.md` refuses to promise it:

    What the reference promises is that it is stable and opaque, and
    nothing else. ... a consumer that matched on it would be coupling
    to a coincidence.

**The kit is a consumer.** Identifying by that prefix would be the kit
doing the exact thing the contract warns consumers against, and a
producer that changed its prefix would still conform while becoming
unidentifiable.

So `--contract` is required for these two, and the refusal says why
rather than reporting the same "names no contract" a malformed
document gets. A guess that is right most of the time is the worst of
the three options: it mislabels, silently, the document that happens
to use only shared categories.
"""

import json
from pathlib import Path

import pytest
from kiseki_conformance.cli import EXIT_OK, EXIT_VIOLATIONS, main
from kiseki_conformance.contracts import BY_OPTION, CONTRACTS

REPO_ROOT = Path(__file__).parents[2]

NOTE = {
    "owner": "me",
    "platform": "obsidian",
    "day": "2026-08-30",
    "reference": "note:9f7630c78bfc0a11",
    "category": "study",
    "labels": ["raft"],
}

PAGE = {
    "owner": "me",
    "platform": "firefox",
    "day": "2026-08-30",
    "reference": "page:1a2b3c4d5e6f0a11",
    "category": "reading",
    "labels": ["raft"],
}

IN_THE_KIT = {
    "photo-record": "photo-record.md",
    "interest-export": "interest-export.md",
    "note-record": "note-record.md",
    "web-record": "web-record.md",
}

NOT_IN_THE_KIT = {
    "activity-record.md": (
        "ActivityRecord v1 has no producer. The converter that would turn "
        "an Apple Health export into one waits for such an export to exist "
        "(v0.10's deferral, still standing), so a schema written now would "
        "be written against an imagined document -- the thing this "
        "repository declined to do when the contract landed. Decide it "
        "again when the first producer appears."
    ),
}


def written(tmp_path: Path, document: object, name: str = "document.json") -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


class TestEveryContractWithADocumentIsInTheKit:
    """The check that stops a fifth instance of this happening quietly."""

    def test_every_contract_document_is_decided(self) -> None:
        pages = {path.name for path in (REPO_ROOT / "docs").glob("*record*.md")}
        pages -= {"records.md"}
        pages.add("interest-export.md")
        assert pages, "no contract documents found, so this check looks in the wrong place"
        undecided = pages - set(IN_THE_KIT.values()) - set(NOT_IN_THE_KIT)
        assert not undecided, (
            f"contracts with a document and no decision about the kit: {sorted(undecided)}. "
            "Give them a schema and a Contract, or say here why not."
        )

    def test_every_option_named_here_exists(self) -> None:
        missing = [option for option in IN_THE_KIT if option not in BY_OPTION]
        assert not missing, f"named here but not in the kit: {missing}"

    def test_the_kit_claims_no_contract_this_file_does_not_know(self) -> None:
        unknown = {contract.option for contract in CONTRACTS} - set(IN_THE_KIT)
        assert not unknown, f"the kit carries contracts this file has not decided about: {unknown}"

    def test_every_excuse_says_something(self) -> None:
        silent = [name for name, why in NOT_IN_THE_KIT.items() if len(why.split()) < 20]
        assert not silent, f"excused without a reason worth reading: {silent}"


class TestANoteDocument:
    def test_it_conforms_when_the_contract_is_named(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        path = written(tmp_path, [NOTE, NOTE | {"reference": "note:aaaa"}])
        assert main([str(path), "--contract", "note-record"]) == EXIT_OK
        assert "NoteRecord v1 (2 reading(s))" in capsys.readouterr().out

    def test_a_sensitive_category_carrying_labels_is_refused(self, tmp_path: Path) -> None:
        """The rule a schema cannot express, and the reason the
        contract exists (ADR-0075)."""
        path = written(tmp_path, [NOTE | {"category": "health", "labels": ["a clinic"]}])
        assert main([str(path), "--contract", "note-record"]) == EXIT_VIOLATIONS

    def test_a_category_it_does_not_know_is_refused(self, tmp_path: Path) -> None:
        path = written(tmp_path, [NOTE | {"category": "shopping"}])
        assert main([str(path), "--contract", "note-record"]) == EXIT_VIOLATIONS


class TestAWebDocument:
    def test_it_conforms_when_the_contract_is_named(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        path = written(tmp_path, [PAGE])
        assert main([str(path), "--contract", "web-record"]) == EXIT_OK
        assert "WebRecord v1 (1 reading(s))" in capsys.readouterr().out

    def test_an_unlabelled_category_carrying_labels_is_refused(self, tmp_path: Path) -> None:
        path = written(tmp_path, [PAGE | {"category": "health", "labels": ["a clinic"]}])
        assert main([str(path), "--contract", "web-record"]) == EXIT_VIOLATIONS

    def test_a_note_only_category_is_refused(self, tmp_path: Path) -> None:
        """`journal` is a note category and not a web one."""
        path = written(tmp_path, [PAGE | {"category": "journal"}])
        assert main([str(path), "--contract", "web-record"]) == EXIT_VIOLATIONS


class TestTellingThemApart:
    """The kit refuses to guess, and says why it will not."""

    def test_a_bare_array_is_not_identified(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert main([str(written(tmp_path, [NOTE]))]) == EXIT_VIOLATIONS
        assert "--contract" in capsys.readouterr().err

    def test_the_refusal_names_both_candidates(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A message saying only *names no contract* sends a producer
        looking for a field to add. There is no such field."""
        main([str(written(tmp_path, [PAGE]))])
        printed = capsys.readouterr().err
        assert "note-record" in printed and "web-record" in printed

    def test_it_does_not_guess_from_the_reference_prefix(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """`note:` is not promised by the contract, so the kit -- which
        is a consumer -- must not couple to it."""
        main([str(written(tmp_path, [NOTE]))])
        assert "NoteRecord" not in capsys.readouterr().out

    def test_a_document_that_is_neither_says_so(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert main([str(written(tmp_path, {"nothing": True}))]) == EXIT_VIOLATIONS
        assert "names no contract" in capsys.readouterr().err

    def test_an_object_contract_is_still_identified(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Naming itself still works where a document can."""
        source = REPO_ROOT / "tests" / "fixtures" / "photo_record" / "valid_full.json"
        document = json.loads(source.read_text(encoding="utf-8"))
        assert main([str(written(tmp_path, document))]) == EXIT_OK
        assert "PhotoRecord v1" in capsys.readouterr().out
