"""Names come from the owner's own GeoNames file, offline."""

from pathlib import Path

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
