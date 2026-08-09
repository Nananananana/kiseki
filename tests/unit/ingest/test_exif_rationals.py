"""GPS components arrive in more than one shape. All of them must work."""

import pytest
from kiseki_ingest.exif import parse_coordinate
from PIL.TiffImagePlugin import IFDRational

EXPECTED = 35.0094


class TestRationalRepresentations:
    def test_accepts_numerator_denominator_tuples(self) -> None:
        values = ((35, 1), (0, 1), (3384, 100))
        assert parse_coordinate(values, "N") == pytest.approx(EXPECTED, abs=1e-4)

    def test_accepts_pillow_rationals(self) -> None:
        values = (IFDRational(35), IFDRational(0), IFDRational(3384, 100))
        assert parse_coordinate(values, "N") == pytest.approx(EXPECTED, abs=1e-4)

    def test_accepts_plain_numbers(self) -> None:
        assert parse_coordinate((35.0, 0.0, 33.84), "N") == pytest.approx(EXPECTED, abs=1e-4)

    def test_accepts_a_mixture(self) -> None:
        values = (35, IFDRational(0), (3384, 100))
        assert parse_coordinate(values, "N") == pytest.approx(EXPECTED, abs=1e-4)

    def test_rejects_a_zero_denominator(self) -> None:
        """Some cameras write 0/0 into unset GPS fields."""
        with pytest.raises(ValueError, match="denominator"):
            parse_coordinate(((35, 0), (0, 1), (0, 1)), "N")

    def test_rejects_a_non_numeric_component(self) -> None:
        with pytest.raises(ValueError, match="not a number"):
            parse_coordinate(("a", "b", "c"), "N")
