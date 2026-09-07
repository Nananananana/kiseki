# ADR-0094: A failure says its name

## Status

Accepted. Closes #430, which carries Sora's requirements R-E1 and R-E2.
Follows ADR-0015, which decided that a refusal is not a pause, and
ADR-0081, which decided that a document that travels names itself.

## Context

Sora is the only program that talks to all seven libraries, and so the
only place that can answer *is it me, or is something broken?*. It could
not. Its ledger answers "what happened in job X". Its on-screen notices
answer "what happened just now" and vanish on reload. Nothing answered
"what is not working".

Sora's half is built: one line per distinct failure, folded by library,
operation, kind and outcome, with a count and a first and last sighting.
**It keeps no values.** It takes the name before the colon on the first
line of stderr and throws the sentence away, because stderr can quote
what it was handed, and Sora does not control seven libraries.

Which left this library with two problems. Our stderr lines were
sentences, several of them a bare `str(error)`, so there was no name to
fold by. And our exit codes -- the most settled in the family -- lived
in a document someone had read once and copied, so the day we add a
sixth, nothing notices.

## Decision

**Every line this library writes to stderr on a failure begins with a
name from a closed catalogue.** `Kind: sentence`. Everything after the
colon stays ours to write and the consumer's to discard, so the sentence
may still name the file that could not be read.

Ten names, and no more without a decision:

```text
ModelRefused       3   refused      do not ask again
ModelUnavailable   4   unavailable  ask again later
ModelTimedOut      5   timed_out    ask again later
ModelTooFarAway    2   refused      a decision, not a fault
RecordsUnreadable  2   failed
ArgumentsConflict  2   failed
ArgumentUnreadable 2   failed
SettingUnusable    2   failed
NothingStored      2   failed
StageStopped       -   failed       carries whatever stopped it
```

**`retryable` is ours to state, not the consumer's to infer.** It is the
one field nobody outside can fill. Sora was deriving it from the
outcome, which is a guess wearing the face of a rule: `ModelTooFarAway`
is a refusal that will never succeed however long you wait, and
`StageStopped` has no fixed exit code and is worth resuming.

The definition is the family's, and it is narrower than the one this
first shipped with. Not *could a second attempt succeed* but **may the
same request be made again, unchanged** -- iriguchi found the flaw and
mamori reached the same wording separately, which is what makes it a
definition rather than a preference. A failure where asking again is
itself a new event is false even when a second attempt would work.

The three `true` values here were checked against the narrower reading
rather than carried over. `ModelTimedOut` is the one that needed it:
the request did leave this machine. It stays true because a timeout is
an unavailability here, so nothing was written for the reading that
timed out; because the model is the owner's own on a host the owner
allowed; and because this library retries it on the next run whatever
a consumer decides, so `false` would be a claim the library itself
contradicts. `StageStopped` stays true because the routine resumes
rather than repeats, which rests on keeping a profile being the last
stage -- held by a test, since reordering the stages would turn that
`true` into a false claim about what a rerun writes.

**`StageStopped` declares no exit code.** It carries the code of
whatever stopped it, and a single number there would be a claim we
cannot keep. The field is nullable for exactly this.

**A catalogue, not a convention.** A convention that stderr starts with
a name cannot be checked from outside; a catalogue can. `_stderr` is the
only way a name reaches stderr, so a test reads this module and the
command line's source and refuses a name in one that is not in the
other -- in both directions, because an entry nothing prints is a
promise about a failure that cannot happen. That is the argument the
served route list makes, and the reason iriguchi's `rules --json` is
checked by its consumer's CI.

**Nothing in the catalogue can be a value.** No paths, no drive letters,
no flags, no templates with holes in them; a template invites a reader
to fill it in from a log, and a log holds the owner's own words. The
constructor refuses all four, and the rule is applied to the catalogue
itself rather than only to what a test invents.

**The Japanese is written here.** Two sentences written by one hand
cannot disagree, and a translation kept by the consumer drifts from the
day it is written. `detail_ja` sits beside `detail`, in the same file,
reviewed in the same diff.

**argparse's refusals are named too.** It writes a usage block first, so
the first line of stderr on a mistyped option was usage -- nothing to
fold by, on the commonest failure there is. A parser subclass puts the
name first and lets the usage follow. Subparsers inherit it, so naming
one names all forty-eight.

**The document carries two names, and they are tied together.**
`contract` is what the family calls this document -- Sora gave every
sibling one shape to answer in, and six of them answer in it. A
seventh answering in its own shape would be a special case in the one
program whose whole job is that there are none. `schema` and
`version` are how every document here names itself (ADR-0081), and
Sora already parses that pair from ten of our routes.

They are not written twice. The version inside the contract name *is*
the served version, and a test refuses them drifting apart -- which is
the only real objection to carrying two names, answered rather than
used as a reason to carry one.

## What we could not promise

**The first line of stderr is not always the failure.** When
`--data-root` displaces a path named in a weaker layer, we say so on
stderr, deliberately, because a setting silently ignored is the same
failure as one silently applied (ADR-0079). On a run that then fails,
that advisory is printed first.

It cannot be mistaken for a name -- it begins with spaces and a dash, so
Sora's own rule rejects it -- but Sora would fall back to the outcome
word and lose the kind. Reported rather than papered over: the rule that
holds is *the first line that parses as a name*, not *the first line*.
The alternative, moving a configuration warning to stdout, would put it
in the way of `--json`.

## An outcome is a property of the kind, not of the code

Worth stating on its own, because the orchestrator's manifest for
this library says otherwise. It holds a map from exit code to
outcome, with `2` meaning `failed`, and plans to check every
`exit_code` in this catalogue against it.

That check cannot pass, and should not. `ModelTooFarAway` exits 2
and is a **refusal**: the model is further away than the owner
allowed (ADR-0073), which is a decision rather than a fault, and no
amount of waiting changes it. Six kinds now sit under exit 2 and one
of them is not a failure, so the map stopped being a function the
moment the second kind arrived.

The map is still the right thing to keep -- it is what a consumer
falls back to when no name could be read from stderr. It is just not
an authority to check the catalogue against. The check that holds is
that every code in the catalogue *appears* in the map, not that the
outcomes agree.

## Consequences

- The day a name is added here, a consumer's build fails rather than its
  vocabulary quietly going stale.
- `kiseki errors --json` reads nothing at all: no database, no paths, no
  model. A catalogue that needed the library to exist would be one an
  orchestrator could not read while deciding whether it does.
- `open_namespaces` is empty and is expected to stay so. Every name we
  print is written down; a reader may take the set as closed.
