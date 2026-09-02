"""What the notes producer accepts, written down and kept true.

#342 came from the musubi session, which is building a converter that
*fills* such a folder. What `kiseki-notes` will read was written in
`reader.py` and nowhere else:

    extensions   .md / .txt / .markdown
    skipped      .git .obsidian node_modules .trash .venv
    size cap     512 KB per file

A producer that writes `.markdown` when this reads `.md` produces a
folder that yields nothing, and the failure arrives as *no notes
found* -- which is also what an empty folder produces, and what a
wrong root produces. Three causes, one message.

`docs/note-record.md` gained the root, the reference and the day when
#342's other halves landed, and said nothing about the suffixes. It
even leaned on them -- *the bookkeeping is `.json` and would be passed
over anyway* -- without ever saying which suffixes are not passed
over.

So the document says it now, and this keeps the two in agreement. Both
directions: a suffix the reader accepts and the document omits leaves
a producer guessing, and a suffix the document promises and the reader
drops is worse, because the producer did as it was told.
"""

import re
from pathlib import Path

from kiseki_notes.reader import MAX_BYTES, SKIPPED_DIRECTORIES, SUFFIXES

DOCUMENT = Path(__file__).parents[2] / "docs" / "note-record.md"

BLOCK = re.compile(r"```text\n(extensions.*?)```", re.DOTALL)
"""The one block in the document that states the layout. Found by its
first word rather than by position, so a document that grows a section
above it does not silently start checking something else."""


def stated() -> dict[str, str]:
    match = BLOCK.search(DOCUMENT.read_text(encoding="utf-8"))
    assert match, (
        "docs/note-record.md no longer states what the producer reads. "
        "A producer written against it would be guessing at the suffixes."
    )
    found = {}
    for line in match.group(1).splitlines():
        if line.strip():
            name, _, value = line.partition("  ")
            found[name.strip()] = value.strip()
    assert found, "the layout block in docs/note-record.md is empty"
    return found


def test_the_document_states_every_suffix_the_reader_accepts() -> None:
    said = stated()["extensions"]
    missing = [suffix for suffix in SUFFIXES if suffix in said.split()]
    assert len(missing) == len(SUFFIXES), (
        f"reader.py accepts {list(SUFFIXES)}; the document says {said!r}"
    )


def test_the_document_promises_no_suffix_the_reader_drops() -> None:
    """The worse direction: the producer did as it was told."""
    promised = [word for word in stated()["extensions"].split() if word.startswith(".")]
    invented = [suffix for suffix in promised if suffix not in SUFFIXES]
    assert not invented, f"the document promises {invented}, which reader.py drops"


def test_the_document_states_every_directory_the_reader_skips() -> None:
    said = stated()["skipped"].split()
    assert sorted(said) == sorted(SKIPPED_DIRECTORIES), (
        f"reader.py skips {sorted(SKIPPED_DIRECTORIES)}; the document says {sorted(said)}"
    )


def test_the_document_states_the_size_cap() -> None:
    said = stated()["size cap"]
    kilobytes = int(re.sub(r"\D", "", said.split()[0]))
    assert kilobytes * 1024 == MAX_BYTES, (
        f"reader.py caps a note at {MAX_BYTES // 1024} KB; the document says {said!r}"
    )
