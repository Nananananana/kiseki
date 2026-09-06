"""Which derivation can answer a question, decided without a model.

Two questions, and only one of them is a retrieval question:

    "what did I eat in Seoul?"          a moment. Retrieval answers it well
    "am I going out less than last year?"  a rhythm. Retrieval answers it by
                                        searching captions for those words,
                                        which is how a library sounds
                                        confident and says nothing

The second failure is the dangerous one because it does not look like
one. So a question is read here, before anything is retrieved, and the
kinds of fact that can bear on it are named.

## Deterministic, and not by preference

A router that asked a model which derivation to use would make the
route depend on whether the model is reachable -- and this library
spent a version making sure it can say exactly where the model is and
what it costs (ADR-0073, ADR-0074). It would also route the question
by the judgement of the thing being routed to.

So: literal phrases, in both languages, in one table anybody can read.
The same shape `time_expressions` already uses for "last year"
(ADR-0039), and the Japanese is written as escapes for the same
reason -- the file stays readable in any editor.

## The vocabulary is chosen, and it is small on purpose

There is no dataset of questions to derivations. One written from
imagination would be this module's own rules restated as evidence, so
none was written (#360). What is here instead:

- every phrase is **listed**, so the owner can read the whole router;
- a question that matches **nothing** routes to nothing, and the
  caller does exactly what it did before this module existed;
- a question that matches **several** takes them all, because a
  question about where you keep going and how often is both.

The router therefore only ever *narrows* an answer that would
otherwise have been offered every kind of fact at once. It cannot
make an answer worse than the one before it; it can only fail to
improve one, and that failure is visible because the route is printed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

PLACE = "place"
RHYTHM = "rhythm"
TREND = "trend"
INTEREST = "interest"

KINDS = (PLACE, RHYTHM, TREND, INTEREST)
"""The grounding kinds a question can be routed to. The same names
`application.grounding` gives its facts, so a route names the facts it
selects rather than something that has to be translated."""

COMMAND_FOR = {
    PLACE: "kiseki places",
    RHYTHM: "kiseki report",
    TREND: "kiseki trend",
    INTEREST: "kiseki profile",
}
"""What the reader would have typed themselves. Printed beside a
route so a misroute costs a glance rather than a guess: the reader
who disagrees runs the command and sees the derivation whole."""

# Japanese as escapes, as time_expressions does.
_MODORU = "戻って"  # modotte (returning)
_IKU = "行く"  # iku (go)
_ITTA = "行った"  # itta (went)
_BASHO = "場所"  # basho (place)
_DOKO = "どこ"  # doko (where)
_YOKU_IKU = "よく行"  # yoku iku (go often)
_GAISHUTSU = "外出"  # gaishutsu (going out)
_HINDO = "頻度"  # hindo (frequency)
_DOREKURAI = "どれくらい"  # dorekurai (how much/often)
_NANKAI = "何回"  # nankai (how many times)
_FUETA = "増え"  # fue (increase)
_HETTA = "減っ"  # hetta (decreased)
_HERU = "減る"  # heru (decrease)
_KAWATTA = "変わっ"  # kawatta (changed)
_SAIKIN = "最近"  # saikin (recently)
_KYOUMI = "興味"  # kyoumi (interest)
_SUKI = "好き"  # suki (like)
_HAMATTE = "ハマっ"  # hamatte (into something)

PHRASES: dict[str, tuple[str, ...]] = {
    PLACE: (
        "go back",
        "going back",
        "keep returning",
        "keep going",
        "where do i",
        "which place",
        "what place",
        "places i",
        _MODORU,
        _YOKU_IKU,
        _DOKO + _IKU,
        _DOKO + _ITTA,
        _BASHO,
    ),
    RHYTHM: (
        "go out",
        "going out",
        "how often",
        "how many times",
        "outings",
        "trips",
        _GAISHUTSU,
        _HINDO,
        _DOREKURAI,
        _NANKAI,
    ),
    TREND: (
        "less than",
        "more than",
        "changed",
        "changing",
        "lately",
        "these days",
        "used to",
        "compared to",
        "growing",
        "fading",
        _FUETA,
        _HETTA,
        _HERU,
        _KAWATTA,
        _SAIKIN,
    ),
    INTEREST: (
        "interested in",
        "into",
        "care about",
        "my interests",
        "what am i",
        "what do i like",
        _KYOUMI,
        _SUKI,
        _HAMATTE,
    ),
}
"""Every phrase that routes, and the only ones. Read it as the whole
of the router: nothing else is consulted, and a phrase absent from
here routes to nothing rather than to a guess."""

_WORD_LIKE = re.compile(r"^[a-z ']+$")
"""An English phrase is matched on word boundaries so `into` does not
fire inside `pointed`. Japanese has no such boundaries, so those
phrases are matched as substrings -- which is what
`time_expressions` does with the same alphabet."""


@dataclass(frozen=True)
class Route:
    """Which derivations bear on a question, and what said so."""

    kinds: frozenset[str]
    matched: tuple[tuple[str, str], ...]
    """`(kind, phrase)` for every phrase that fired, in reading order,
    so an answer can say *why* it was routed and not only *where*."""

    def __post_init__(self) -> None:
        unknown = sorted(self.kinds - set(KINDS))
        if unknown:
            raise ValueError(f"not kinds of question: {unknown}")

    @property
    def routed(self) -> bool:
        """Whether anything at all matched."""
        return bool(self.kinds)

    @property
    def commands(self) -> tuple[str, ...]:
        """What the reader could run instead, one per kind."""
        return tuple(COMMAND_FOR[kind] for kind in KINDS if kind in self.kinds)


NO_ROUTE = Route(frozenset(), ())
"""Nothing matched. The state every question was in before this module,
and the one a question still reaches when the table says nothing about
it: the caller offers every kind of fact and retrieval decides."""


def _fires(phrase: str, question: str) -> bool:
    if _WORD_LIKE.match(phrase):
        return re.search(rf"(?<![a-z]){re.escape(phrase)}(?![a-z])", question) is not None
    return phrase in question


def route(question: str) -> Route:
    """The kinds of fact that bear on this question, or none.

    Lowercased for the English phrases; Japanese is unaffected by it.
    """
    lowered = question.lower()
    matched = tuple(
        (kind, phrase) for kind in KINDS for phrase in PHRASES[kind] if _fires(phrase, lowered)
    )
    return Route(kinds=frozenset(kind for kind, _phrase in matched), matched=matched)
