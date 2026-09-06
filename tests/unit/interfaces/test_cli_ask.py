"""The ask command answers safely on an empty database.

With nothing indexed there is no retrieval and no model call, so this
stays in CI.
"""

import json
from pathlib import Path

import pytest
from kiseki.interfaces.cli import EXIT_OK, main


@pytest.fixture(autouse=True)
def isolated_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the test away from the developer's .env beside the repo."""
    monkeypatch.chdir(tmp_path)


class TestAskCommand:
    def test_answers_an_empty_database(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert main(["--data-root", str(tmp_path), "ask", "ramen"]) == EXIT_OK
        # The wording changed when `ask` gained a second source of
        # facts. What is asserted is the state -- an empty library
        # bears on nothing -- and that the reader is told what to run,
        # rather than the sentence that used to say it.
        printed = capsys.readouterr().out
        assert "bears on that question" in printed
        assert "kiseki build" in printed

    def test_answers_the_contract_as_json(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert main(["--data-root", str(tmp_path), "ask", "--json", "ramen"]) == EXIT_OK
        out = capsys.readouterr().out
        assert '"question"' in out
        assert '"confidence"' in out


class TestAskBlursLikeEverythingElse:
    """`ask --json` had no `--raw`, and passed no `blur` on: the one
    written payload that could carry a coordinate was the one that
    never blurred it."""

    def test_raw_is_accepted_and_off_by_default(self) -> None:
        from kiseki.interfaces.cli import build_parser

        blurred = build_parser().parse_args(["ask", "--json", "ramen"])
        raw = build_parser().parse_args(["ask", "--json", "--raw", "ramen"])
        assert blurred.raw is False
        assert raw.raw is True


class TestTheRouteIsPrinted:
    """An answer that came from the rhythm and does not say so is worse
    than one the reader asked for by typing `report`, because then they
    knew which derivation it was (ADR-0090)."""

    def test_an_empty_library_says_which_derivation_would_answer(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Understood, and nothing derived yet -- which the reader can act
        on, unlike "nothing bears on that question"."""
        assert main(["--data-root", str(tmp_path), "ask", "how often do I go out?"]) == EXIT_OK
        printed = capsys.readouterr().out
        assert "a question about rhythm" in printed
        assert "kiseki report" in printed

    def test_an_unroutable_question_on_an_empty_library_says_the_old_thing(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert main(["--data-root", str(tmp_path), "ask", "what did I eat in Seoul?"]) == EXIT_OK
        assert "bears on that question" in capsys.readouterr().out

    def test_the_route_reaches_the_document(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert (
            main(["--data-root", str(tmp_path), "ask", "--json", "how often do I go out?"])
            == EXIT_OK
        )
        out = capsys.readouterr().out
        document = json.loads(out[out.index("{") :])
        assert document["routed_to"] == ["rhythm"]
        assert {"kind": "rhythm", "phrase": "how often"} in document["routed_by"]

    def test_a_retrieval_question_names_no_route(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert (
            main(["--data-root", str(tmp_path), "ask", "--json", "what did I eat in Seoul?"])
            == EXIT_OK
        )
        out = capsys.readouterr().out
        assert json.loads(out[out.index("{") :])["routed_to"] == []
