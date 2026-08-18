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
        "color",
        "data",
        "description",
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
        "location",
        "itinerary",
        "label",
        "list",
        "metadata",
        "number",
        "object",
        "page",
        "pattern",
        "percentage",
        "property",
        "photo",
        "picture",
        "qr code",
        "record",
        "revision",
        "result",
        "score",
        "schedule",
        "screenshot",
        "selection",
        "size",
        "space",
        "status",
        "symbol",
        "text",
        "timeline",
        "thing",
        "transformation",
        "time",
        "value",
        "version",
    }
)


DECLINED = {
    "note": "a note can be a thing on a desk",
    "system": "may name what the owner actually works on",
    "service": "the same",
    "japan": "a country is not an abstraction; place scale is another problem",
    "python": "a real interest of this owner, and of many",
    "vscode": "the same",
    "ikea": "a shop is a place someone went",
    "yolo": "a model someone works with",
}
"""Words that came up and were left in, with the reason.

A stoplist that only grows is a stoplist nobody can argue with. Each
entry here was considered against the criterion and kept out of it, so
the next reader can see where the line was drawn rather than guess.
"""


def is_generic(label: str) -> bool:
    """Whether this label is about the record rather than the world."""
    return label.strip().lower() in GENERIC_LABELS
