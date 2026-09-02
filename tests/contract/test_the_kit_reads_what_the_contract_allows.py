"""The kit accepts what the contract says a producer may write.

`docs/records.md` tells every producer, in as many words, that a
byte order mark is fine:

    Producers on Windows write one without being asked. Documents are
    read as `utf-8-sig`, which accepts a document with or without one.

The core does exactly that. **The conformance kit did not**, and told
a producer their document was not valid JSON:

    bomdoc.json is not valid JSON: Unexpected UTF-8 BOM
    (decode using utf-8-sig): line 1 column 1 (char 0)

So a document `kiseki notes` reads without complaint was refused by
the tool kiseki publishes for checking documents. The kit is the half
a producer in Swift or Kotlin actually runs, which makes it the copy
that matters, and it was contradicting the contract it exists to
enforce.

The other half, found the same afternoon: a document written in the
machine's locale encoding -- the akashi session's defect, and this
repository's own at `cli.py:976` until today -- came out of the kit as
a **raw traceback**:

    UnicodeDecodeError: 'utf-8' codec can't decode byte 0x82 ...

The producer who most needs a sentence explaining the encoding rule is
exactly the producer who got the encoding wrong.
"""

import json
from pathlib import Path

import pytest
from kiseki_conformance.cli import EXIT_OK, EXIT_UNREADABLE, main

VALID = Path(__file__).parents[1] / "fixtures" / "photo_record" / "valid_full.json"


@pytest.fixture
def document() -> dict[str, object]:
    return json.loads(VALID.read_text(encoding="utf-8"))


def written(path: Path, document: object, encoding: str) -> Path:
    path.write_text(json.dumps(document, ensure_ascii=False), encoding=encoding)
    return path


class TestAByteOrderMark:
    """records.md promises it is accepted. The core keeps that promise."""

    def test_it_is_accepted(
        self, tmp_path: Path, document: dict[str, object], capsys: pytest.CaptureFixture[str]
    ) -> None:
        path = written(tmp_path / "with-bom.json", document, "utf-8-sig")
        assert main([str(path)]) == EXIT_OK
        assert "conforms" in capsys.readouterr().out

    def test_a_document_without_one_is_still_accepted(
        self, tmp_path: Path, document: dict[str, object]
    ) -> None:
        assert main([str(written(tmp_path / "plain.json", document, "utf-8"))]) == EXIT_OK


class TestADocumentThatIsNotUtf8:
    """RFC 8259 section 8.1. A producer that got this wrong needs a
    sentence, not a stack trace."""

    def test_it_is_refused_rather_than_crashing(
        self, tmp_path: Path, document: dict[str, object], capsys: pytest.CaptureFixture[str]
    ) -> None:
        document["records"] = [{"note": "onsen について"}]
        path = written(tmp_path / "cp932.json", document, "cp932")
        assert main([str(path)]) == EXIT_UNREADABLE
        assert "UTF-8" in capsys.readouterr().err

    def test_it_says_what_to_do_about_it(
        self, tmp_path: Path, document: dict[str, object], capsys: pytest.CaptureFixture[str]
    ) -> None:
        """The likeliest cause is a redirect on a machine whose locale
        is not UTF-8, which is not a thing a producer sets out to do."""
        document["records"] = [{"note": "onsen について"}]
        main([str(written(tmp_path / "cp932.json", document, "cp932"))])
        printed = capsys.readouterr().err
        assert "encoding" in printed.lower()

    def test_quiet_stays_quiet(self, tmp_path: Path, document: dict[str, object]) -> None:
        document["records"] = [{"note": "onsen について"}]
        path = written(tmp_path / "cp932.json", document, "cp932")
        assert main([str(path), "--quiet"]) == EXIT_UNREADABLE


class TestEveryContractSaysWhatEncodingToWrite:
    """The akashi session's sentence, which is why this file exists:

        A contract that does not name its encoding is a contract the
        producer who wrote it eventually gets wrong.

    Both projects proved it on themselves the same afternoon. The
    input contracts inherit the rule from `docs/records.md`, which all
    four link to; the export contract is nobody's inheritance and says
    it itself.
    """

    DOCUMENTS = ("records.md", "interest-export.md")

    @pytest.mark.parametrize("name", DOCUMENTS)
    def test_it_names_utf8(self, name: str) -> None:
        page = Path(__file__).parents[2] / "docs" / name
        assert page.is_file(), f"docs/{name} is gone, and this check would pass without it"
        assert "UTF-8" in page.read_text(encoding="utf-8"), (
            f"docs/{name} does not tell a producer what encoding to write. "
            "A producer in another language has no default of ours to fall back on."
        )
