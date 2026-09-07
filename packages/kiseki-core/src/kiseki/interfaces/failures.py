"""What can go wrong, named, so an orchestrator can fold two of them.

Sora is the only program that talks to all seven libraries, and the
only place that can answer *is it me, or is something broken?*. It
could not: a ledger says what happened in one job, an on-screen notice
says what happened just now and vanishes on reload, and nothing said
what is not working.

Its half is built -- one line per distinct failure, folded by library,
operation, kind and outcome, with a count and a first and last
sighting. **It keeps no values**: it takes the name before the colon on
the first line of stderr and throws the sentence away, because stderr
can quote what it was handed. That is the only shape it could defend
while not controlling seven libraries.

This is the other half: the closed set of names, so that a reader can
be told what a name means without a person having transcribed it, and
so that the day a name is added, a consumer's build fails rather than
its vocabulary quietly going stale.

## Why a catalogue rather than a convention

A convention that stderr starts with a name cannot be checked from
outside. A catalogue can: `line` is the only way a name reaches
stderr, so a test can read this module and the command line's source
and refuse a name in one that is not in the other. That is the
argument the served route list makes, and the reason iriguchi's
`rules --json` is checked by its consumer's CI.

## Nothing here can be a value

No paths, no quoted arguments, no message templates with holes in
them. A template invites a reader to fill it in from a log, and a log
holds the owner's own words. The sentences here describe the shape of
a failure and never an instance of one, and `__post_init__` refuses
what looks like either.

## The Japanese is written here, not translated elsewhere

Two sentences written by one hand cannot disagree; a translation kept
by the consumer drifts from the day it is written. So `detail_ja` is
part of the catalogue, in the same file, reviewed in the same diff.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

CONTRACT = "kiseki.errors/{version}-draft"
"""What the family calls this document, with our served version in it.

The orchestrator gave every sibling one shape to answer in, and six
of them answer in it. A seventh that answered in its own shape would
be a special case in the one program whose whole job is that there
are none -- so this is carried as asked, and the document also names
itself the way every other document here does (ADR-0081). They are
tied together rather than written twice: the version in the contract
name is the served version, and a test refuses them drifting apart."""

REFUSED = "refused"
UNAVAILABLE = "unavailable"
FAILED = "failed"
TIMED_OUT = "timed_out"

OUTCOMES = (REFUSED, UNAVAILABLE, FAILED, TIMED_OUT)
"""The four words the family agreed on. Not an exit code: two kinds can
share a code and mean different things about asking again."""

_NAME = re.compile(r"^[A-Z][A-Za-z]+$")
_A_VALUE = re.compile(r"[{}<>]|[A-Za-z]:[\\/]|/[a-z]+/|--[a-z]")
"""What a sentence must not contain: a template hole, a drive letter, a
path, a flag. Each is a way an instance of a failure creeps into a
description of one."""


@dataclass(frozen=True)
class Failure:
    """One named way a command can stop, and what to do about it."""

    kind: str
    """The stable identifier, exactly as it appears before the colon on
    the first line of stderr. The key a consumer folds by."""

    exit_code: int | None
    """The code, where one always accompanies this kind. `None` where
    it varies -- a stage that stopped carries the code of whatever
    stopped it, and claiming a single number would be a guess."""

    outcome: str
    retryable: bool
    """May the same request be made again, unchanged?

    **Not** whether a second attempt could succeed, which is what this
    said first and is the wrong question. iriguchi found the flaw: a
    failure where asking again is itself a new event -- something
    leaves the machine, something is charged, something is written --
    is false even when a second attempt would work, because a
    consumer should not be handed a reason to send it twice. mamori
    reached the same wording separately, which is what makes it the
    definition rather than anyone's preference.

    Only this library can answer it. A consumer inferring it from the
    outcome is guessing with the face of a rule."""

    detail: str
    detail_ja: str

    def __post_init__(self) -> None:
        if not _NAME.match(self.kind):
            raise ValueError(f"{self.kind!r} is not a name a consumer can fold by")
        if self.outcome not in OUTCOMES:
            raise ValueError(f"{self.outcome!r} is not one of the four outcomes")
        for sentence in (self.detail, self.detail_ja):
            if not sentence.strip():
                raise ValueError(f"{self.kind} says nothing about itself")
            if "\n" in sentence:
                raise ValueError(f"{self.kind} is more than one line")
            if _A_VALUE.search(sentence):
                raise ValueError(
                    f"{self.kind} carries something that looks like a value; a catalogue "
                    "describes the shape of a failure, never an instance of one"
                )


CATALOGUE = (
    Failure(
        kind="ModelRefused",
        exit_code=3,
        outcome=REFUSED,
        retryable=False,
        detail="The model declined to answer. Asking again gives the same answer.",
        detail_ja="モデルが答えることを拒んだ。もう一度聞いても同じ答えになる。",
    ),
    Failure(
        kind="ModelUnavailable",
        exit_code=4,
        outcome=UNAVAILABLE,
        retryable=True,
        detail="The model could not be reached. Running again later continues from here.",
        detail_ja="モデルに届かなかった。あとで実行し直せば、ここから続く。",
    ),
    Failure(
        kind="ModelTimedOut",
        exit_code=5,
        outcome=TIMED_OUT,
        retryable=True,
        detail="The model was reached and did not answer in time. A queue is not an outage.",
        detail_ja="モデルには届いたが、時間内に答えなかった。待ち行列は障害ではない。",
    ),
    # Retryable under the strict definition, and it needed checking: the
    # request did leave this machine. But a timeout is an unavailability
    # here (`_exit_for` asks about it first), so nothing was written for
    # the job that timed out, and the next run asks for exactly the
    # readings that were never answered. Nothing is charged: the model is
    # the owner's own, on a host the owner allowed (ADR-0073). Declaring
    # it false would also contradict this library, which retries it on
    # the next run whatever a consumer decides.
    Failure(
        kind="ModelTooFarAway",
        exit_code=2,
        outcome=REFUSED,
        retryable=False,
        detail="The model is further away than the owner allowed. A decision, not a fault.",
        detail_ja="モデルが所有者の許した範囲より遠い。故障ではなく決定である。",
    ),
    Failure(
        kind="RecordsUnreadable",
        exit_code=2,
        outcome=FAILED,
        retryable=False,
        detail="The records could not be opened, or are not the shape the contract describes.",
        detail_ja="記録を開けなかったか、契約の形になっていない。",
    ),
    Failure(
        kind="ArgumentsConflict",
        exit_code=2,
        outcome=FAILED,
        retryable=False,
        detail="Two options were given that cannot both be meant, or one that needs another.",
        detail_ja="両立しない指定か、片方だけでは意味をなさない指定が与えられた。",
    ),
    Failure(
        kind="ArgumentUnreadable",
        exit_code=2,
        outcome=FAILED,
        retryable=False,
        detail="An option was given in a form this command cannot read.",
        detail_ja="このコマンドが読めない形で指定が与えられた。",
    ),
    Failure(
        kind="SettingUnusable",
        exit_code=2,
        outcome=FAILED,
        retryable=False,
        detail="A setting names something this build does not have, so it would do nothing.",
        detail_ja="設定がこのビルドに無いものを指しており、そのままでは何もしないことになる。",
    ),
    Failure(
        kind="NothingStored",
        exit_code=2,
        outcome=FAILED,
        retryable=False,
        detail="What was named is not in this library, so there is nothing to act on.",
        detail_ja="指定されたものがこのライブラリに無く、対象が存在しない。",
    ),
    Failure(
        kind="StageStopped",
        exit_code=None,
        outcome=FAILED,
        retryable=True,
        detail="A step of a longer routine stopped, and nothing after it ran.",
        detail_ja="長い手順の途中の段が止まり、それより後は実行されなかった。",
    ),
    # Retryable because the routine resumes rather than repeats: every
    # stage does only the work not already done, so a rerun asks the
    # model for the readings that were never answered and no others.
    # It rests on one fact -- keeping a profile is the last stage, so a
    # run that stopped never kept one, and a rerun cannot keep a second
    # (ADR-0070). A test holds that order, because reordering the
    # stages would make this `true` a false claim.
)

OPEN_NAMESPACES: tuple[str, ...] = ()
"""Prefixes under which names are built at run time from somebody
else's vocabulary. Empty, and deliberately: every name this library
prints is written above, so a reader may take the set as closed."""

BY_KIND = {failure.kind: failure for failure in CATALOGUE}

if len(BY_KIND) != len(CATALOGUE):
    raise AssertionError("two failures share a name, and a consumer would fold them together")


def line(kind: str, sentence: str) -> str:
    """The first line of stderr: a name, a colon, and our own words.

    Everything after the colon is this library's to write and the
    consumer's to discard, so the sentence may say whatever helps the
    person reading their own terminal.
    """
    if kind not in BY_KIND:
        raise KeyError(f"{kind!r} is not in the catalogue; add it there first")
    return f"{kind}: {sentence}"
