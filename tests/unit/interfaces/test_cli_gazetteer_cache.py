"""A command that names places writes the gazetteer's compact copy under
the data root's cache, and reads it next time.

Twelve commands built their own FileGazetteer and none passed a cache
directory, because none existed. `_gazetteer(paths)` is the one place
the gazetteer path and the cache directory meet; this holds that it
actually hands the cache over, which no adapter test can see.
"""

import json
import os
from pathlib import Path

import pytest
from kiseki.adapters.filesystem.gazetteer import forget_loaded
from kiseki.interfaces.cli import EXIT_OK, main


@pytest.fixture(autouse=True)
def isolated_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for key in [name for name in os.environ if name.startswith("KISEKI_")]:
        monkeypatch.delenv(key)
    monkeypatch.chdir(tmp_path)
    forget_loaded()


def _library_with_a_gazetteer(tmp_path: Path) -> Path:
    records = [
        {
            "id": f"sha256:{index:064d}",
            "captured_at": f"2025-05-03T10:{index:02d}:00+09:00",
            "location": {"lat": 35.0116, "lon": 135.7681, "accuracy_m": 12},
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
    gazetteer = tmp_path / "gazetteer" / "cities500.txt"
    gazetteer.parent.mkdir(parents=True, exist_ok=True)
    row = "\t".join(["1", "Kyoto", "Kyoto", "", "35.0116", "135.7681", "P", "PPL", "JP"])
    gazetteer.write_text(row + "\n", encoding="utf-8")
    return tmp_path


def test_places_writes_the_copy_under_the_data_root_s_cache(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _library_with_a_gazetteer(tmp_path)
    assert main(["--data-root", str(root), "places"]) == EXIT_OK
    written = list((root / "cache" / "gazetteer").glob("cities500-*"))
    assert len(written) == 1, "the command named places without handing the cache over"
    assert "Kyoto" in capsys.readouterr().out
