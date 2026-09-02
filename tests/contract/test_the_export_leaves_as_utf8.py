"""The document that leaves is UTF-8, out of a real process.

Three things a check of this has to do, arrived at by three sibling
sessions on the same day, each having found their own version of it
short:

1. **Start a real process.** A test that swaps `sys.stdout` in-process
   is testing the console path, and the console path is not where the
   defect was.
2. **Separate the console from the redirect.** Python encodes an
   attached terminal and a redirected file by different rules, and
   akashi's defect lived on the redirect side alone.
3. **Read the bytes, not the exception.** "It did not crash" is what
   made this survivable for months: `--json` wrote a document that was
   not valid JSON **and exited 0**. A check that watches only for a
   traceback sees that as a pass.

`kiseki-interest-export v1` is the sharpest case in this repository.
It is the only document that leaves the machine, ADR-0047 says a
published contract states the most that may ever leave, and the thing
that reads it is a program.

`PYTHONIOENCODING` rather than a console code page, so this runs the
same way on a machine that has never heard of cp932 -- the codec
ships with Python everywhere, and it is the encoding the defect was
actually found in.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parents[2]

NOT_UTF8 = "cp932"
"""The encoding this was found in. Any non-UTF-8 codec would do; this
one is the one a Japanese Windows machine picks by itself."""


LABELS = ["温泉", "ラーメン", "𩸽"]
"""Two stages, and the fixture failed each of them in turn.

**Stage one: no non-ASCII at all.** Written against the sandbox
`kiseki demo` builds, which is entirely English -- 123 bytes of export
with **zero** above 127. cp932 and UTF-8 produced identical bytes, and
all seven assertions held on a document that could not have shown the
defect. Japanese labels fixed that.

**Stage two: non-ASCII, all of it inside cp932.** Raised by the seam
session, who hit the same thing, and measured here before it was
believed:

    温泉 ラーメン   in cp932      -> errors="replace" never fires
    𩸽             not in cp932  -> it does

So the poison that isolates requirement four -- encode to cp932 with
`errors="replace"`, then hand back UTF-8, producing a **valid**
document with question marks where the words were -- **passed all
eight tests** against a fixture of `温泉` and `ラーメン`. Nothing was
replaced, because nothing needed replacing.

`𩸽` (U+29E3D) is outside cp932, so it is the character that makes
requirement four a requirement rather than a sentence. The other two
stay: they are what makes requirement three fail, since a cp932-
encoded `温泉` is not valid UTF-8 at all.

One lesson under both stages, not two: **a fixture has to be asserted
capable of failing, and "carries a non-ASCII character" was not the
capability being relied on.**"""


@pytest.fixture
def library(tmp_path: Path) -> Path:
    """A sandbox with something in it, and with something in it that
    is not ASCII."""
    root = tmp_path / "library"
    run(["demo", "--out", str(root), "--keep"], tmp_path)
    document = tmp_path / "note-records.json"
    document.write_text(
        json.dumps(
            [
                {
                    "owner": "me",
                    "platform": "obsidian",
                    "day": f"2026-08-{day:02d}",
                    "reference": reference,
                    "category": "study",
                    "labels": LABELS,
                }
                for day in range(1, 15)
                for reference in ("note:aaaa", "note:bbbb", "note:cccc")
            ]
        ),
        encoding="utf-8",
    )
    read = run(["--data-root", str(root), "notes", str(document)], tmp_path)
    assert read.returncode == 0, read.stderr.decode("utf-8", "replace")
    return root


def exported(library: Path, tmp_path: Path, encoding: str | None) -> bytes:
    result = run(["--data-root", str(library), "export"], tmp_path, encoding=encoding)
    assert result.returncode == 0, result.stderr.decode("utf-8", "replace")
    return result.stdout


def test_the_document_under_test_has_something_to_get_wrong(library: Path, tmp_path: Path) -> None:
    """Every check below is vacuous without this, and was -- twice.

    Placed first, and asserting the stronger of the two properties,
    because a reader who has seen eight passes printed will take the
    number over a footnote.
    """
    raw = exported(library, tmp_path, encoding=None)
    assert any(byte > 127 for byte in raw), (
        "the export carries no character outside ASCII, so UTF-8 and cp932 "
        f"produce identical bytes and nothing below is tested. {len(raw)} bytes."
    )
    unrepresentable = [
        character for character in raw.decode("utf-8") if not _fits(character, NOT_UTF8)
    ]
    assert unrepresentable, (
        f"every character in this export round-trips through {NOT_UTF8}, so a writer "
        'poisoned with errors="replace" would replace nothing and this suite would '
        "pass with the encoding handling removed. Requirement four needs a character "
        "the console encoding cannot hold."
    )


def _fits(character: str, encoding: str) -> bool:
    try:
        character.encode(encoding)
    except UnicodeEncodeError:
        return False
    return True


def run(
    arguments: list[str], cwd: Path, encoding: str | None = None
) -> subprocess.CompletedProcess[bytes]:
    environment = {key: value for key, value in os.environ.items() if not key.startswith("KISEKI_")}
    environment.pop("PYTHONUTF8", None)
    if encoding is not None:
        environment["PYTHONIOENCODING"] = encoding
    return subprocess.run(
        [sys.executable, "-m", "kiseki.interfaces.cli", *arguments],
        cwd=cwd,
        env=environment,
        capture_output=True,
        check=False,
    )


class TestTheExportRedirected:
    """The path the defect was on: stdout is a file, not a terminal."""

    def test_the_bytes_are_utf8_and_the_json_parses(self, library: Path, tmp_path: Path) -> None:
        document = json.loads(exported(library, tmp_path, NOT_UTF8).decode("utf-8"))
        assert document["schema"] == "kiseki-interest-export"

    def test_the_labels_come_back_exactly_as_they_went_in(
        self, library: Path, tmp_path: Path
    ) -> None:
        """Not *is it valid* but *is the value still the value*.

        The fourth requirement, and the one the first three miss.
        Reported by the mamori session, who poisoned their own writer
        with `errors="replace"` and got exit 0, a valid UTF-8 file,
        valid JSON, and `original_value: "??"`.

        Confirmed here by the same poisoning, before this test was
        split out to say so: with the writer encoding as ASCII with
        `errors="replace"`, `test_it_is_the_same_document_under_either
        _encoding` **passes** -- both encodings produce the same wrong
        bytes. **Consistency is not fidelity**, and a hash agreeing
        with itself proves only that the corruption was deterministic.
        """
        document = json.loads(exported(library, tmp_path, NOT_UTF8).decode("utf-8"))
        topics = {str(interest["topic"]) for interest in document["interests"]}
        missing = [label for label in LABELS if label not in topics]
        assert not missing, (
            f"labels that went in and did not come back: {missing}. "
            f"Present: {sorted(topics)}. A document can be valid UTF-8, parse as "
            "JSON, and carry question marks where the owner's words were."
        )

    def test_exit_zero_is_not_taken_as_the_answer(self, library: Path, tmp_path: Path) -> None:
        """The whole reason this defect lasted. A document that is not
        UTF-8 exits 0, so the bytes have to be the assertion."""
        exported(library, tmp_path, NOT_UTF8).decode("utf-8")  # raises rather than passing

    def test_it_is_the_same_document_under_either_encoding(
        self, library: Path, tmp_path: Path
    ) -> None:
        """A document that differs by the console that produced it is
        not a document, and no hash over one means anything."""
        assert exported(library, tmp_path, NOT_UTF8) == exported(library, tmp_path, "utf-8")


class TestTheOtherMachineReadableCommands:
    """`--json` on the commands a program is likeliest to call."""

    @pytest.mark.parametrize("command", ["privacy", "profile"])
    def test_the_bytes_are_utf8(self, command: str, library: Path, tmp_path: Path) -> None:
        result = run(["--data-root", str(library), command, "--json"], tmp_path, encoding=NOT_UTF8)
        assert result.returncode == 0, result.stderr.decode("utf-8", "replace")
        json.loads(result.stdout.decode("utf-8"))


class TestProseIsLeftAlone:
    """The other half of the rule. A command whose output a person
    reads keeps the console's behaviour, and must not have been broken
    into raising by the change that fixed the documents."""

    def test_a_prose_command_still_runs(self, library: Path, tmp_path: Path) -> None:
        result = run(["--data-root", str(library), "privacy"], tmp_path, encoding=NOT_UTF8)
        assert result.returncode == 0, result.stderr.decode("utf-8", "replace")
        assert result.stdout
