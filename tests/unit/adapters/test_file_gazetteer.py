"""Names come from the owner's own GeoNames file, offline."""

from pathlib import Path

import pytest
from kiseki.adapters.fake.places import FakeGazetteer
from kiseki.adapters.filesystem.gazetteer import FileGazetteer
from kiseki.domain.shared.geo import Distance, GeoPoint
from kiseki.ports.places import PlaceName

KYOTO = GeoPoint(35.0116, 135.7681)


def _row(name: str, latitude: float, longitude: float, country: str = "JP") -> str:
    return "\t".join(["1", name, name, "", str(latitude), str(longitude), "P", "PPL", country])


def _file(tmp_path: Path, rows: list[str]) -> Path:
    path = tmp_path / "cities.txt"
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return path


def test_loads_the_entries(tmp_path: Path) -> None:
    gazetteer = FileGazetteer(
        _file(tmp_path, [_row("Kyoto", 35.0116, 135.7681), _row("Osaka", 34.6937, 135.5023)])
    )
    assert gazetteer.entries == 2


def test_nearest_names_the_closest_place(tmp_path: Path) -> None:
    gazetteer = FileGazetteer(
        _file(tmp_path, [_row("Kyoto", 35.0116, 135.7681), _row("Osaka", 34.6937, 135.5023)])
    )
    place = gazetteer.nearest(GeoPoint(35.0, 135.77), Distance(30_000))
    assert place is not None
    assert place.name == "Kyoto"


def test_nothing_close_enough_is_none(tmp_path: Path) -> None:
    gazetteer = FileGazetteer(_file(tmp_path, [_row("Kyoto", 35.0116, 135.7681)]))
    assert gazetteer.nearest(GeoPoint(43.06, 141.35), Distance(30_000)) is None


def test_a_missing_file_means_no_names(tmp_path: Path) -> None:
    gazetteer = FileGazetteer(tmp_path / "absent.txt")
    assert gazetteer.entries == 0
    assert gazetteer.nearest(KYOTO, Distance(30_000)) is None


def test_malformed_rows_are_skipped(tmp_path: Path) -> None:
    rows = [
        _row("Kyoto", 35.0116, 135.7681),
        "too\tshort",
        "\t".join(["1", "Bad", "Bad", "", "not-a-number", "135.0", "P", "PPL", "JP"]),
        "\t".join(["1", "Far", "Far", "", "999", "135.0", "P", "PPL", "JP"]),
        "\t".join(["1", "", "", "", "35.0", "135.0", "P", "PPL", "JP"]),
    ]
    gazetteer = FileGazetteer(_file(tmp_path, rows))
    assert gazetteer.entries == 1


def test_the_search_crosses_bucket_edges(tmp_path: Path) -> None:
    gazetteer = FileGazetteer(_file(tmp_path, [_row("Edge", 0.51, 0.51)]))
    place = gazetteer.nearest(GeoPoint(0.49, 0.49), Distance(10_000))
    assert place is not None
    assert place.name == "Edge"


def test_the_label_carries_the_country() -> None:
    assert PlaceName("Nantes", "FR").label == "Nantes (FR)"
    assert PlaceName("Kyoto").label == "Kyoto"


def test_the_fake_answers_the_same_contract() -> None:
    fake = FakeGazetteer([(KYOTO, PlaceName("Kyoto", "JP"))])
    assert fake.nearest(GeoPoint(35.0, 135.77), Distance(30_000)) == PlaceName("Kyoto", "JP")
    assert fake.nearest(GeoPoint(43.0, 141.0), Distance(30_000)) is None


def test_ascii_name_is_preferred(tmp_path: Path) -> None:
    row = "\t".join(["1", "\u014csaka", "Osaka", "", "34.6937", "135.5023", "P", "PPL", "JP"])
    gazetteer = FileGazetteer(_file(tmp_path, [row]))
    place = gazetteer.nearest(GeoPoint(34.69, 135.50), Distance(10_000))
    assert place is not None
    assert place.name == "Osaka"


def test_a_missing_ascii_name_falls_back(tmp_path: Path) -> None:
    row = "\t".join(["1", "Kyoto", "", "", "35.0116", "135.7681", "P", "PPL", "JP"])
    gazetteer = FileGazetteer(_file(tmp_path, [row]))
    place = gazetteer.nearest(KYOTO, Distance(10_000))
    assert place is not None
    assert place.name == "Kyoto"


class TestReadOnce:
    """Measured on the real library: 235,375 rows, 40 MB, 1.6 seconds to
    parse, parsed on every command that named a place and twice by
    `suggest`. So: once per process, and once per file across processes."""

    def setup_method(self) -> None:
        from kiseki.adapters.filesystem.gazetteer import forget_loaded

        forget_loaded()

    def test_a_second_gazetteer_in_one_process_does_not_parse_again(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from kiseki.adapters.filesystem import gazetteer as module

        source = _file(tmp_path, [_row("Kyoto", 35.0116, 135.7681)])
        parses = 0
        real = module._parse

        def counted(path: Path) -> object:
            nonlocal parses
            parses += 1
            return real(path)

        monkeypatch.setattr(module, "_parse", counted)
        FileGazetteer(source)
        FileGazetteer(source)
        assert parses == 1

    def test_the_cache_is_written_once_and_read_after(self, tmp_path: Path) -> None:
        from kiseki.adapters.filesystem.gazetteer import forget_loaded

        source = _file(tmp_path, [_row("Kyoto", 35.0116, 135.7681)])
        cache = tmp_path / "cache"
        first = FileGazetteer(source, cache_dir=cache)
        assert first.entries == 1
        written = list((cache / "gazetteer").glob("cities-*"))
        assert len(written) == 1, written
        # Forget the memo and remove the source: only the cache can answer now.
        forget_loaded()
        stat = source.stat()
        source.unlink()
        from kiseki.adapters.filesystem.gazetteer import _load

        rows = _load(source, stat.st_size, stat.st_mtime_ns, cache)
        assert rows.count == 1

    def test_a_changed_source_is_not_served_from_the_old_cache(self, tmp_path: Path) -> None:
        """Same size, different content, later modification time: the key
        has to notice the time, not only the size. The first version of
        this test also grew the file, and passed with the time ignored."""
        import os

        from kiseki.adapters.filesystem.gazetteer import forget_loaded

        cache = tmp_path / "cache"
        source = _file(tmp_path, [_row("Kyoto", 35.0116, 135.7681)])
        FileGazetteer(source, cache_dir=cache)
        forget_loaded()
        replaced = _file(tmp_path, [_row("Osaka", 34.6937, 135.5023)])
        assert replaced.stat().st_size == source.stat().st_size, "the fixture must keep the size"
        later = replaced.stat().st_mtime_ns + 1_000_000_000
        os.utime(replaced, ns=(later, later))
        again = FileGazetteer(replaced, cache_dir=cache)
        assert again.nearest(GeoPoint(34.69, 135.50), Distance(5_000)) == PlaceName("Osaka", "JP")
        assert again.nearest(GeoPoint(35.01, 135.77), Distance(5_000)) is None, (
            "served from the stale copy"
        )
        assert len(list((cache / "gazetteer").glob("cities-*"))) == 1, "the stale copy was kept"

    def test_cached_and_uncached_answer_alike(self, tmp_path: Path) -> None:
        from kiseki.adapters.filesystem.gazetteer import forget_loaded

        rows = [
            _row("Kyoto", 35.0116, 135.7681),
            _row("Osaka", 34.6937, 135.5023),
            _row("Nara", 34.6851, 135.8048),
        ]
        source = _file(tmp_path, rows)
        asked = [
            (GeoPoint(35.0, 135.77), Distance(5_000)),
            (GeoPoint(34.69, 135.80), Distance(3_000)),
        ]
        plain = [FileGazetteer(source).nearest(point, within) for point, within in asked]
        forget_loaded()
        FileGazetteer(source, cache_dir=tmp_path / "cache")
        forget_loaded()
        cached = FileGazetteer(source, cache_dir=tmp_path / "cache")
        assert [cached.nearest(point, within) for point, within in asked] == plain

    def test_a_cache_that_cannot_be_written_still_answers(self, tmp_path: Path) -> None:
        source = _file(tmp_path, [_row("Kyoto", 35.0116, 135.7681)])
        blocked = tmp_path / "not-a-dir"
        blocked.write_text("a file where a directory was expected", encoding="utf-8")
        found = FileGazetteer(source, cache_dir=blocked)
        assert found.entries == 1
