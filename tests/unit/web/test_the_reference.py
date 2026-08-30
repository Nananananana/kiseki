"""A reference the core can tell apart and cannot look up.

ADR-0084: a path is a private string and a URL is a public one, so an
unsalted hash of a URL is a membership oracle -- anybody holding a
records file and a list of clinics can hash the list and test for
membership. The salt is what makes the handle opaque rather than
merely opaque-looking.
"""

from pathlib import Path

import pytest
from kiseki_web.reference import (
    SALT_FILE,
    reference_for,
    salt_in,
)

A_PAGE = "https://en.example.org/wiki/Raft_(algorithm)"
ANOTHER = "https://en.example.org/wiki/Paxos"


class TestTheSalt:
    def test_it_is_made_once_and_read_back(self, tmp_path: Path) -> None:
        first = salt_in(tmp_path)
        assert salt_in(tmp_path) == first

    def test_it_is_written_where_the_owner_can_find_it(self, tmp_path: Path) -> None:
        salt_in(tmp_path)
        assert (tmp_path / SALT_FILE).is_file()

    def test_two_installations_do_not_share_one(self, tmp_path: Path) -> None:
        assert salt_in(tmp_path / "a") != salt_in(tmp_path / "b")

    def test_it_is_long_enough_to_be_worth_having(self, tmp_path: Path) -> None:
        assert len(salt_in(tmp_path)) >= 32


class TestTheReference:
    def test_the_same_page_is_the_same_reference(self, tmp_path: Path) -> None:
        """Two readings of one page across months are recognisably one
        page. That trail is the entire value of this source."""
        salt = salt_in(tmp_path)
        assert reference_for(A_PAGE, salt) == reference_for(A_PAGE, salt)

    def test_a_different_page_is_a_different_reference(self, tmp_path: Path) -> None:
        salt = salt_in(tmp_path)
        assert reference_for(A_PAGE, salt) != reference_for(ANOTHER, salt)

    def test_it_carries_no_part_of_the_address(self, tmp_path: Path) -> None:
        reference = reference_for(A_PAGE, salt_in(tmp_path))
        for fragment in ("example", "wiki", "Raft", "https"):
            assert fragment not in reference

    def test_it_has_the_shape_a_record_expects(self, tmp_path: Path) -> None:
        reference = reference_for(A_PAGE, salt_in(tmp_path))
        assert reference.startswith("page:")
        assert len(reference) == len("page:") + 16
        assert all(character in "0123456789abcdef" for character in reference[5:])

    def test_two_installations_do_not_agree_about_one_page(self, tmp_path: Path) -> None:
        """Correct, and the point. Two owners' histories are not meant
        to line up, and a contract that let them would be a contract for
        building a graph of people by what they read."""
        here = reference_for(A_PAGE, salt_in(tmp_path / "a"))
        there = reference_for(A_PAGE, salt_in(tmp_path / "b"))
        assert here != there

    def test_without_the_salt_the_reference_cannot_be_reproduced(self, tmp_path: Path) -> None:
        """Which is the whole mechanism: a list of URLs plus a hash
        function is not enough to test what is in a records file."""
        unsalted = reference_for(A_PAGE, b"")
        assert reference_for(A_PAGE, salt_in(tmp_path)) != unsalted

    def test_an_empty_address_is_refused(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError):
            reference_for("", salt_in(tmp_path))
