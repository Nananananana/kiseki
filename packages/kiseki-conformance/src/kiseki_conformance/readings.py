"""The rules a schema cannot express, for the two reading contracts.

`NoteRecord v1` and `WebRecord v1` are the same shape and not the same
contract. Each names a set of categories that **never carry labels**,
and the sets differ because the sources differ: a note about an
illness is one somebody sat down to write, and a symptom typed into a
search box at two in the morning is not deliberate at all.

A schema can say which categories exist. It cannot say *this category,
and only this category, must arrive with an empty list* -- so that is
here, where the other contracts keep their unexpressible rules too.

**Refused, not trimmed.** A kit that tidied the labels away would be
telling a producer its document conformed while quietly repairing the
promise it had broken. The core refuses these documents outright
(`kiseki notes`, `kiseki web`), and a kit that were more forgiving
than the library would be worse than no kit: the producer would ship.
"""

from collections.abc import Mapping, Sequence
from typing import Any

NOTE_SCHEMA_RESOURCE = "note-record-v1.json"
WEB_SCHEMA_RESOURCE = "web-record-v1.json"

NOTE_UNLABELLED = frozenset({"journal", "health", "money", "people", "credential"})
"""`docs/note-record.md`, and `SENSITIVE_CATEGORIES` in the core."""

WEB_UNLABELLED = frozenset(
    {"health", "money", "people", "credential", "shopping", "news", "private"}
)
"""`docs/web-record.md`. Two more than the notes list, and `news` is
the one worth reading the reason for: labels on news reading would be
an inference about politics and religion from what somebody opened
once, and nothing separates follows-seismology from reads-one-party's-
paper."""


def _labelled_when_it_should_not_be(document: object, unlabelled: frozenset[str]) -> list[str]:
    if not isinstance(document, Sequence) or isinstance(document, str | bytes):
        return []
    messages = []
    for index, record in enumerate(document):
        if not isinstance(record, Mapping):
            continue
        category = record.get("category")
        labels = record.get("labels")
        if category in unlabelled and isinstance(labels, Sequence) and len(labels) > 0:
            messages.append(
                f"{index}: category {category!r} never carries labels, and this one carries "
                f"{len(labels)}. The core refuses the whole document rather than trimming it."
            )
    return messages


def check_note_semantics(document: object) -> list[str]:
    return _labelled_when_it_should_not_be(document, NOTE_UNLABELLED)


def check_web_semantics(document: object) -> list[str]:
    return _labelled_when_it_should_not_be(document, WEB_UNLABELLED)


def count(document: object) -> int:
    """How many readings a document carries."""
    if isinstance(document, Sequence) and not isinstance(document, str | bytes):
        return len(document)
    return 0


def anything(_document: Mapping[str, Any]) -> bool:
    """Never true: neither contract has a field that names it.

    Both are bare arrays of the same six field names, their category
    sets overlap in eleven, and the one thing that looks
    distinguishing -- the `note:` and `page:` reference prefixes --
    is explicitly not promised:

        What the reference promises is that it is stable and opaque,
        and nothing else. ... a consumer that matched on it would be
        coupling to a coincidence.  (docs/note-record.md)

    **This kit is a consumer.** So it does not guess, and the command
    line asks instead. A guess right most of the time is the worst of
    the three options available: it mislabels, in silence, the
    document that happens to use only shared categories.
    """
    return False
