"""A check with nothing to check is green, and says nothing.

The manager session relayed this from outside the family: a suite
written as `for x in collection: assert ...` passes completely when
the collection is empty, so renaming a package turned every
architecture guarantee green. Measured here, the same shape is in the
one distribution built to be installed by somebody else.

Emptying the 31-case trust table:

    93 passed  ->  3 skipped, exit 0

**Nobody wrote the word skip.** pytest turns an empty `parametrize`
into one by itself, which is why grepping for `pytest.skip` -- zero
hits across 232 test files -- answered a different question than the
one being asked.

Two spellings of the same silence, and this file refuses both:

    for x in []          "everything passed"
    parametrize(())      "not applicable"

The distinction that decides which collections get an assertion:
**empty is a mistake where the collection is a table this kit ships,
and a fact where the collection is a document somebody handed us.** A
library with no photographs really has no records. So the table is
asserted, and the documents are reported on -- a producer running the
kit against an empty document is told the per-record checks proved
nothing, rather than being congratulated.
"""

import importlib.util
from pathlib import Path

import pytest
from kiseki_conformance.suite import InterestExportConformance, PhotoRecordConformance
from kiseki_conformance.trust import CASES


def test_the_trust_table_is_not_empty() -> None:
    """The table is a literal this kit ships. Empty is never a fact
    about the world, only about a mistake."""
    assert CASES, (
        "the trust boundary table is empty. Every case in "
        "TrustBoundaryConformance would report as skipped, and a "
        "sibling repository copying the kit would copy the silence."
    )


def test_the_trust_table_still_covers_what_it_claimed() -> None:
    """31 was the number when the boundary was written three times over.
    A table that shrinks has stopped holding the three copies together,
    and a shrinking table looks exactly like a passing one."""
    assert len(CASES) >= 31, (
        f"the trust boundary table has {len(CASES)} cases and had 31. "
        "Cases may be added; a case removed needs saying why here."
    )


def test_every_case_says_why() -> None:
    """A case with no reason is a case nobody can review."""
    silent = [case.label for case in CASES if len(case.why.split()) < 3]
    assert not silent, f"cases asserting a verdict with no reason: {silent}"


class TestASuiteRunOnAnEmptyDocument:
    """What a producer is told when the kit had nothing to look at."""

    def test_the_photo_suite_says_it_checked_nothing(self) -> None:
        suite = PhotoRecordConformance()
        with pytest.raises(AssertionError, match="nothing to check"):
            suite.test_the_document_had_something_to_check({"schema_version": "1.0"})

    def test_the_export_suite_says_it_checked_nothing(self) -> None:
        suite = InterestExportConformance()
        with pytest.raises(AssertionError, match="nothing to check"):
            suite.test_the_document_had_something_to_check(
                {"schema": "kiseki-interest-export", "version": 1, "interests": []}
            )

    def test_a_document_with_records_passes(self) -> None:
        PhotoRecordConformance().test_the_document_had_something_to_check(
            {"schema_version": "1.0", "records": [{"id": "sha256:aa"}]}
        )

    def test_a_document_with_interests_passes(self) -> None:
        InterestExportConformance().test_the_document_had_something_to_check(
            {"schema": "kiseki-interest-export", "version": 1, "interests": [{"topic": "raft"}]}
        )


class TestTheImportContracts:
    """Two holes were looked for here. **One of them was open.**

    Measured, by breaking `.importlinter` and reading the exit code:

        a contract deleted    "5 kept, 0 broken"    **exit 0**
        a root package renamed                       exit 1

    So `lint-imports` already refuses a root it cannot import -- the
    shape the outside repository hit, where a source root pointing at
    nothing left 35 tests passing, **does not exist here**, and the
    second test below is belt-and-braces rather than a fix.

    The first is not. A contract removed from this file takes its rule
    with it, the count drops by one, and the build stays green.
    """

    CONFIGURATION = Path(__file__).parents[2] / ".importlinter"

    EXPECTED = 6
    """Contracts. Adding one is free; losing one is what this catches."""

    def read(self) -> str:
        return self.CONFIGURATION.read_text(encoding="utf-8")

    def test_every_contract_is_still_declared(self) -> None:
        declared = self.read().count("[importlinter:contract:")
        assert declared >= self.EXPECTED, (
            f".importlinter declares {declared} contracts and had {self.EXPECTED}. "
            "lint-imports reports the number it found and exits 0 either way."
        )

    def test_every_root_package_exists(self) -> None:
        """A root package that is not importable is a set of layering
        rules that are true of nothing."""
        block = self.read().split("root_packages =")[1].split("[")[0]
        roots = [line.strip() for line in block.splitlines() if line.strip()]
        assert roots, ".importlinter names no root packages, so it checks nothing"
        missing = [name for name in roots if importlib.util.find_spec(name) is None]
        assert not missing, f"root packages that cannot be imported: {missing}"
