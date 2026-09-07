"""Every failure names itself, and the catalogue holds every name.

Sora folds failures across seven libraries by the name before the colon
on the first line of stderr, and keeps nothing else. A name it has
never seen is an incident it cannot explain; a catalogue entry nothing
prints is a promise about a failure that cannot happen.

The pair of tests below is the point of the whole exercise: a
convention that stderr starts with a name cannot be checked from
outside, and a catalogue can.
"""

import json
import os
import re
from inspect import getsource
from pathlib import Path

import pytest
from kiseki.interfaces import cli
from kiseki.interfaces.cli import EXIT_BAD_INPUT, EXIT_OK, main
from kiseki.interfaces.failures import (
    BY_KIND,
    CATALOGUE,
    CONTRACT,
    OPEN_NAMESPACES,
    OUTCOMES,
    Failure,
    line,
)

PRINTED = re.compile(r'_stderr\(\s*"([A-Za-z]+)"')


@pytest.fixture(autouse=True)
def isolated_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the test away from the developer's .env and KISEKI_* environment."""
    for key in [name for name in os.environ if name.startswith("KISEKI_")]:
        monkeypatch.delenv(key)
    monkeypatch.chdir(tmp_path)


class TestTheCatalogueIsTheSourceOfNames:
    def test_every_name_the_command_line_prints_is_in_the_catalogue(self) -> None:
        """A name Sora has never seen is an incident it cannot explain."""
        printed = set(PRINTED.findall(getsource(cli)))
        assert printed <= set(BY_KIND), sorted(printed - set(BY_KIND))

    def test_every_name_in_the_catalogue_is_printed_somewhere(self) -> None:
        """A catalogue entry nothing prints is a promise about a failure
        that cannot happen. The model kinds arrive through `_kind_for`,
        which is read the same way."""
        printed = set(PRINTED.findall(getsource(cli)))
        printed |= set(re.findall(r'return "([A-Za-z]+)"', getsource(cli._kind_for)))
        assert set(BY_KIND) <= printed, sorted(set(BY_KIND) - printed)

    def test_the_command_line_writes_no_unnamed_line_to_stderr(self) -> None:
        """`_stderr` is the only way a failure reaches stderr.

        The two exceptions are the helper's own body and the advisory
        about a displaced setting, which is printed on a run that
        succeeds and is deliberately not a failure.
        """
        source = getsource(cli).splitlines()
        unnamed = [
            number
            for number, text in enumerate(source, start=1)
            if "file=sys.stderr" in text or text.strip() == "file=sys.stderr,"
        ]
        assert len(unnamed) == 2, [source[number - 1] for number in unnamed]

    def test_a_name_outside_the_catalogue_is_refused_at_the_call(self) -> None:
        with pytest.raises(KeyError, match="add it there first"):
            line("SomethingNobodyDecidedAbout", "a sentence")


class TestNothingInItCanBeAValue:
    """A catalogue that carried a path would be a catalogue that leaked
    one. The sentences describe the shape of a failure, never one."""

    @pytest.mark.parametrize(
        "sentence",
        [
            "The file at C:/Users/someone/photos.db could not be read.",
            "Nothing was found under /home/someone/notes.",
            "The option --data-root was not understood.",
            "Could not read {path}.",
        ],
        ids=["a drive", "a path", "a flag", "a template"],
    )
    def test_a_sentence_that_looks_like_an_instance_is_refused(self, sentence: str) -> None:
        with pytest.raises(ValueError, match="never an instance"):
            Failure(
                kind="Whatever",
                exit_code=2,
                outcome="failed",
                retryable=False,
                detail=sentence,
                detail_ja="値。",
            )

    def test_every_catalogued_sentence_survives_that_rule(self) -> None:
        """The rule is applied to the catalogue itself, not only to what
        a test invents."""
        for failure in CATALOGUE:
            assert failure.detail.strip()
            assert failure.detail_ja.strip()

    def test_a_kind_that_cannot_be_folded_by_is_refused(self) -> None:
        with pytest.raises(ValueError, match="fold by"):
            Failure(
                kind="not a name",
                exit_code=2,
                outcome="failed",
                retryable=False,
                detail="A sentence.",
                detail_ja="文。",
            )

    def test_an_outcome_the_family_never_agreed_on_is_refused(self) -> None:
        with pytest.raises(ValueError, match="four outcomes"):
            Failure(
                kind="Whatever",
                exit_code=2,
                outcome="bad",
                retryable=False,
                detail="A sentence.",
                detail_ja="文。",
            )


class TestTheDocument:
    def test_it_names_itself_and_says_which_release_wrote_it(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert main(["errors", "--json"]) == EXIT_OK
        document = json.loads(capsys.readouterr().out)
        assert document["schema"] == "kiseki-errors"
        assert document["by"].startswith("kiseki/")
        assert document["open_namespaces"] == list(OPEN_NAMESPACES)

    def test_the_two_names_for_it_cannot_drift_apart(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """`contract` is what the family calls this document and six
        other libraries answer with; `schema` and `version` are how
        every document here names itself. The version inside the
        contract name is the served version, so neither can move alone."""
        assert main(["errors", "--json"]) == EXIT_OK
        document = json.loads(capsys.readouterr().out)
        version = document["version"]
        assert document["contract"] == CONTRACT.format(version=version)

    def test_every_entry_carries_what_a_consumer_cannot_work_out(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """`retryable` is the field only this library can fill."""
        assert main(["errors", "--json"]) == EXIT_OK
        entries = json.loads(capsys.readouterr().out)["errors"]
        assert len(entries) == len(CATALOGUE)
        for entry in entries:
            assert entry["outcome"] in OUTCOMES
            assert isinstance(entry["retryable"], bool)
            assert entry["detail_ja"] != entry["detail"]

    def test_a_kind_whose_code_varies_says_so_rather_than_guessing(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A stage carries the code of whatever stopped it."""
        assert main(["errors", "--json"]) == EXIT_OK
        entries = {entry["kind"]: entry for entry in json.loads(capsys.readouterr().out)["errors"]}
        assert entries["StageStopped"]["exit_code"] is None

    def test_it_reads_nothing_at_all(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A catalogue that needed a library to exist would be one an
        orchestrator could not read while deciding whether the library
        is working. No --data-root, and no database is made."""
        assert main(["errors", "--json"]) == EXIT_OK
        assert not list(tmp_path.iterdir())


class TestStderrLeadsWithTheName:
    def test_a_conflicting_pair_of_options_says_which_kind_it_is(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert main(["--data-root", str(tmp_path), "retry", "--apply"]) == EXIT_BAD_INPUT
        assert capsys.readouterr().err.startswith("ArgumentsConflict: ")

    def test_an_unreadable_option_says_which_kind_it_is(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = main(["--data-root", str(tmp_path), "compare", "--from", "yesterday", "--to", "now"])
        assert code == EXIT_BAD_INPUT
        assert capsys.readouterr().err.startswith("ArgumentUnreadable: ")

    def test_records_that_cannot_be_read_say_which_kind_it_is(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        missing = tmp_path / "nothing.json"
        code = main(["--data-root", str(tmp_path), "notes", str(missing)])
        assert code == EXIT_BAD_INPUT
        assert capsys.readouterr().err.startswith("RecordsUnreadable: ")

    def test_a_mistyped_option_says_which_kind_it_is(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """The commonest failure there is. argparse writes usage
        first, so before this the first line of stderr was a usage
        block and there was nothing to fold by."""
        with pytest.raises(SystemExit) as left:
            main(["--data-root", str(tmp_path), "notes", "--nonsense"])
        assert left.value.code == EXIT_BAD_INPUT
        assert capsys.readouterr().err.startswith("ArgumentUnreadable: ")

    def test_the_usage_block_still_follows_for_the_person_reading_it(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        with pytest.raises(SystemExit):
            main(["--data-root", str(tmp_path), "notes", "--nonsense"])
        assert "usage:" in capsys.readouterr().err

    def test_the_sentence_after_the_colon_is_still_ours(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Everything after the colon is this library's to write and the
        consumer's to discard, so it may still name the file."""
        assert main(["--data-root", str(tmp_path), "retry", "--apply"]) == EXIT_BAD_INPUT
        assert "--stage" in capsys.readouterr().err
