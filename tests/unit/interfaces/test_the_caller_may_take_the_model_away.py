"""Who calls the model when this library is one of several.

Running alone, kiseki decides: `refresh` runs the reading stages and
each one asks. Running as one of seven libraries on one machine, that
is the wrong default -- seven programs each deciding to load a model
onto one GPU is not a schedule, and the orchestrator that can see all
seven is the only place a schedule can exist.

So the caller may take the model away. The point of these tests is the
distinction underneath it: **a model withheld by policy is not a model
that is away.** An outage may change in a minute; a policy answers the
same way every time, and a consumer told the second was the first would
retry it forever.
"""

import json
import os
from pathlib import Path

import pytest
from kiseki.config.model import ModelUse, resolve_model_settings
from kiseki.interfaces.cli import EXIT_BAD_INPUT, EXIT_OK, main
from kiseki.interfaces.failures import BY_KIND


@pytest.fixture(autouse=True)
def isolated_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the test away from the developer's .env and KISEKI_* environment."""
    for key in [name for name in os.environ if name.startswith("KISEKI_")]:
        monkeypatch.delenv(key)
    monkeypatch.chdir(tmp_path)


class TestTheSettingItself:
    def test_the_default_is_that_this_process_calls_the_model(self) -> None:
        """A person at their own terminal wants the library to work."""
        assert resolve_model_settings().use is ModelUse.SELF
        assert resolve_model_settings().withheld is False

    def test_the_environment_can_take_it_away(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("KISEKI_MODEL_USE", "withheld")
        assert resolve_model_settings().withheld is True

    def test_a_word_nobody_decided_about_is_refused_rather_than_ignored(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A typo in this setting means the model gets called after the
        caller said not to, which is the whole failure."""
        monkeypatch.setenv("KISEKI_MODEL_USE", "sora")
        with pytest.raises(ValueError, match="not a way of using the model"):
            resolve_model_settings()

    def test_the_command_line_beats_the_environment(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setenv("KISEKI_MODEL_USE", "self")
        assert main(["--data-root", str(tmp_path), "--model-use", "withheld", "llm"]) == EXIT_OK
        assert "used by         withheld" in capsys.readouterr().out


class TestAPolicyIsNotAnOutage:
    """The distinction the whole thing rests on."""

    def test_a_command_that_needs_the_model_says_which_kind_it_is(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setenv("KISEKI_MODEL_USE", "withheld")
        code = main(["--data-root", str(tmp_path), "caption"])
        assert code == EXIT_BAD_INPUT
        assert capsys.readouterr().err.startswith("ModelWithheld: ")

    def test_it_is_refused_rather_than_unavailable(self) -> None:
        """An orchestrator told this was an outage would retry a policy
        at whatever interval it retries outages, forever."""
        withheld = BY_KIND["ModelWithheld"]
        assert withheld.outcome == "refused"
        assert withheld.retryable is False

    def test_it_is_a_different_kind_from_the_boundary_refusal(self) -> None:
        """Same exit code, different name. The fold key is the kind, so
        an orchestrator can tell *you told me not to* from *the owner's
        boundary refused it* without a second code."""
        assert BY_KIND["ModelWithheld"].exit_code == BY_KIND["ModelTooFarAway"].exit_code
        assert BY_KIND["ModelWithheld"].detail != BY_KIND["ModelTooFarAway"].detail

    def test_it_points_at_what_can_still_be_asked(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A refusal that does not say what is still possible sends the
        caller away with nothing."""
        monkeypatch.setenv("KISEKI_MODEL_USE", "withheld")
        main(["--data-root", str(tmp_path), "caption"])
        assert "cost --no-measure" in capsys.readouterr().err


class TestEverythingElseStillWorks:
    """A library that answered nothing while the model was withheld
    would be a library the orchestrator could not use at all."""

    NEEDS_NO_MODEL = ("report", "places", "limits", "privacy", "doctor", "now", "today", "errors")

    @pytest.mark.parametrize("command", NEEDS_NO_MODEL)
    def test_a_derivation_answers_with_the_model_withheld(
        self,
        command: str,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setenv("KISEKI_MODEL_USE", "withheld")
        assert main(["--data-root", str(tmp_path), command]) == EXIT_OK
        capsys.readouterr()

    def test_privacy_answers_because_that_is_when_the_answer_matters_most(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """The command that reports what leaves this machine must not
        stop because the model was withheld -- that is exactly the case
        where the answer is the strongest *no* the library can give."""
        monkeypatch.setenv("KISEKI_MODEL_USE", "withheld")
        assert main(["--data-root", str(tmp_path), "privacy"]) == EXIT_OK
        assert "where the models are" in capsys.readouterr().out

    def test_cost_still_says_what_the_work_would_take(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """The question an orchestrator asks before scheduling anything:
        what would this cost, without doing it."""
        monkeypatch.setenv("KISEKI_MODEL_USE", "withheld")
        assert main(["--data-root", str(tmp_path), "cost", "--no-measure"]) == EXIT_OK
        capsys.readouterr()

    def test_llm_says_which_is_in_force(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A setting silently applied is the same failure as one
        silently ignored (ADR-0079)."""
        monkeypatch.setenv("KISEKI_MODEL_USE", "withheld")
        assert main(["--data-root", str(tmp_path), "llm"]) == EXIT_OK
        said = capsys.readouterr().out
        assert "used by         withheld" in said
        assert "will not call it" in said

    def test_the_catalogue_is_readable_with_it_withheld(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A catalogue that needed a model would be one an orchestrator
        could not read while deciding whether to give it one."""
        monkeypatch.setenv("KISEKI_MODEL_USE", "withheld")
        assert main(["errors", "--json"]) == EXIT_OK
        kinds = {entry["kind"] for entry in json.loads(capsys.readouterr().out)["errors"]}
        assert "ModelWithheld" in kinds
