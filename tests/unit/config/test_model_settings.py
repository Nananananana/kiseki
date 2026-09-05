"""Where the model is, and how far away it is allowed to be."""

import os
from pathlib import Path

import pytest
from kiseki.config.model import (
    DEFAULT_HOST,
    ModelSettings,
    resolve_model_settings,
)
from kiseki.domain.trust import TrustBoundary


@pytest.fixture(autouse=True)
def no_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in [name for name in os.environ if name.startswith("KISEKI_MODEL_")]:
        monkeypatch.delenv(key)


def test_the_defaults_are_this_machine_and_the_strictest_boundary() -> None:
    settings = resolve_model_settings()
    assert settings.host == DEFAULT_HOST
    assert settings.boundary is TrustBoundary.SAME_HOST
    assert settings.verdict.admitted


def test_the_environment_moves_the_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KISEKI_MODEL_HOST", "http://llm01.lan:11434")
    monkeypatch.setenv("KISEKI_MODEL_BOUNDARY", "private_network")
    settings = resolve_model_settings()
    assert settings.host == "http://llm01.lan:11434"
    assert settings.verdict.admitted


def test_a_model_on_the_network_is_refused_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KISEKI_MODEL_HOST", "http://llm01.lan:11434")
    verdict = resolve_model_settings().verdict
    assert not verdict.admitted
    assert "same_host" in verdict.reason


def test_a_named_host_is_admitted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KISEKI_MODEL_HOST", "http://llm01.lan:11434")
    monkeypatch.setenv("KISEKI_MODEL_TRUSTED_HOSTS", "llm01.lan, gpu.lan")
    assert resolve_model_settings().verdict.admitted


def test_an_unknown_setting_is_refused_rather_than_ignored(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A typo that silently does nothing is the worst available outcome."""
    monkeypatch.setenv("KISEKI_MODEL_BOUNDRY", "anywhere")
    with pytest.raises(ValueError) as raised:
        resolve_model_settings()
    assert "boundry" in str(raised.value)
    assert "would have done" in str(raised.value)


def test_a_boundary_that_is_not_one_says_the_choices(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KISEKI_MODEL_BOUNDARY", "sometimes")
    with pytest.raises(ValueError) as raised:
        resolve_model_settings()
    assert "same_host" in str(raised.value)


def test_a_toml_file_is_read(tmp_path: Path) -> None:
    (tmp_path / "kiseki.toml").write_text(
        '[model]\nhost = "http://gpu.lan:11434"\n'
        'boundary = "private_network"\n'
        'trusted_hosts = ["gpu.lan"]\n',
        encoding="utf-8",
    )
    settings = resolve_model_settings(dotenv=tmp_path / ".env")
    assert settings.host == "http://gpu.lan:11434"
    assert settings.boundary is TrustBoundary.PRIVATE_NETWORK
    assert settings.trusted_hosts == ("gpu.lan",)


def test_the_command_line_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KISEKI_MODEL_HOST", "http://from-env:11434")
    settings = resolve_model_settings({"host": "http://from-flag:11434"})
    assert settings.host == "http://from-flag:11434"


def test_the_settings_can_be_built_directly() -> None:
    settings = ModelSettings(host="http://127.0.0.1:11434")
    assert settings.verdict.admitted


def test_parallel_defaults_to_one_call_at_a_time() -> None:
    assert resolve_model_settings().parallel == 1


def test_parallel_comes_through_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KISEKI_MODEL_PARALLEL", "4")
    assert resolve_model_settings().parallel == 4


def test_parallel_comes_through_toml(tmp_path: Path) -> None:
    (tmp_path / "kiseki.toml").write_text("[model]\nparallel = 3\n", encoding="utf-8")
    assert resolve_model_settings(dotenv=tmp_path / ".env").parallel == 3


def test_the_command_line_wins_for_parallel_too(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KISEKI_MODEL_PARALLEL", "2")
    assert resolve_model_settings({"parallel": "5"}).parallel == 5


def test_zero_in_flight_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KISEKI_MODEL_PARALLEL", "0")
    with pytest.raises(ValueError, match="at least 1"):
        resolve_model_settings()


def test_a_word_is_not_a_number_of_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KISEKI_MODEL_PARALLEL", "four")
    with pytest.raises(ValueError, match="not a number"):
        resolve_model_settings()
