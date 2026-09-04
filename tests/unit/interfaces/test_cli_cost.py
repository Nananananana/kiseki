"""`kiseki cost`, without reaching a model.

`--no-measure` exists for the case where the model must not be
disturbed, and it is also what makes this testable: the counting is
this repository's work and the rate is the machine's, so they are
separable and the first can be checked on its own.
"""

import json
import os
from pathlib import Path

import pytest
from kiseki.interfaces.cli import EXIT_OK, main


@pytest.fixture(autouse=True)
def isolated_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for key in [name for name in os.environ if name.startswith("KISEKI_")]:
        monkeypatch.delenv(key)
    monkeypatch.chdir(tmp_path)


def a_library(tmp_path: Path) -> Path:
    """A handful of photographs at one place, ingested for real."""
    records = [
        {
            "id": f"sha256:{index:064d}",
            "captured_at": f"2025-05-03T10:{index:02d}:00+09:00",
            "location": {"lat": 35.0094, "lon": 135.6669, "accuracy_m": 12},
            "location_source": "measured",
            "media_type": "image",
            "content_kind": "photo",
            "thumbnail_ref": f"2025/05/{index:04d}.jpg",
            "owner": {"id": "me", "device": "a phone"},
            "consent": {"granted": True, "scope": ["preferences"]},
        }
        for index in range(8)
    ]
    document = tmp_path / "photo-records.json"
    document.write_text(json.dumps({"schema_version": "1.0", "records": records}), encoding="utf-8")
    assert main(["--data-root", str(tmp_path), "ingest", str(document)]) == EXIT_OK
    assert main(["--data-root", str(tmp_path), "build"]) == EXIT_OK
    return tmp_path


def run(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> str:
    assert main(["--data-root", str(tmp_path), "cost", "--no-measure"]) == EXIT_OK
    return capsys.readouterr().out


class TestWithoutTouchingTheModel:
    def test_it_names_every_stage_that_calls_one(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Four stages call a model. A report that listed three would
        be confidently low, which is the failure this exists for."""
        printed = run(a_library(tmp_path), capsys)
        for stage in ("stay captions", "single captions", "screen readings", "subject readings"):
            assert stage in printed

    def test_it_counts_the_work_that_is_waiting(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Eight photographs at one place make one stay, and nothing
        has captioned it.

        Written first with an `or` across two spellings, which made it
        pass on either -- an assertion that cannot fail is the thing
        this repository spent a day removing. The count is parsed out
        of the row instead.
        """
        printed = run(a_library(tmp_path), capsys)
        row = next(line for line in printed.splitlines() if "stay captions" in line)
        counted = row.replace("stay captions", "").split()[0]
        assert counted == "1", f"expected one uncaptioned stay, row was {row!r}"

    def test_it_says_nothing_could_be_estimated(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Counts without a rate are still worth printing, and the
        absence of a total is stated rather than left as a blank."""
        printed = run(a_library(tmp_path), capsys)
        assert "nothing could be estimated" in printed

    def test_it_does_not_invent_a_duration(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """No rate was measured, so no hours may appear. A shipped
        constant here would be a number about somebody else's
        graphics card."""
        printed = run(a_library(tmp_path), capsys)
        assert "hours" not in printed
        assert "altogether" not in printed

    def test_an_empty_library_is_not_an_error(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert main(["--data-root", str(tmp_path), "cost", "--no-measure"]) == EXIT_OK
