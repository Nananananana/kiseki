"""Labels that describe the record, not the world in front of it.

A reader looking at a screenshot of a boarding pass may answer
"date", "text", "number" -- true about the image, and empty about
the owner. Those words earn scores like any other label and crowd
out the ones that mean something, so the derivations leave them out.

The test for membership, so the list never grows by taste: the word
names the form of a record, an act of recording, or an abstraction
with no thing behind it. "spreadsheet", "code" and "dashboard" stay
out of the list -- they say what the owner actually works with.
Filtering happens at derivation, never at storage: the readings keep
what the model said, and one line of code changes what the profile
makes of it (the ADR-0044 posture). See ADR-0053.
"""

from __future__ import annotations

GENERIC_LABELS = frozenset(
    {
        "annotation",
        "content",
        "data",
        "date",
        "detail",
        "document",
        "element",
        "file",
        "form",
        "identifier",
        "image",
        "information",
        "item",
        "itinerary",
        "label",
        "list",
        "metadata",
        "number",
        "object",
        "page",
        "percentage",
        "photo",
        "picture",
        "qr code",
        "record",
        "result",
        "schedule",
        "screenshot",
        "size",
        "status",
        "text",
        "thing",
        "time",
        "value",
        "version",
    }
)


def is_generic(label: str) -> bool:
    """Whether this label is about the record rather than the world."""
    return label.strip().lower() in GENERIC_LABELS
