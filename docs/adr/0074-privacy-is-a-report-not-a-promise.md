# ADR-0074: Privacy is a report, not a promise

## Status

Accepted. Delivers #279, shipped in #280.

Written ten commits late. The decision was made, the code was merged,
and the record was missed -- `interfaces/claims.py`, `proposals/0009`
and AGENTS.md all cite this number, and `docs/adr/` went straight from
0073 to 0075. What follows is reconstructed from that pull request and
from the code it left behind. Nothing here is a new decision, and the
reasoning is stated as it was made rather than as it looks now.

## Context

`kiseki privacy` printed a list of promises. One of them said that
nothing is sent anywhere and no network call exists.

That stopped being true the day captioning was written. A reduced copy
of a photograph travels to the model in an HTTP body. It went to
localhost, so nothing left the machine and the outcome was right --
while the sentence describing the mechanism was wrong. The library was
telling the truth by accident.

Two things made it possible.

The first is that the promises were prose. A sentence in a list cannot
fail a build; it drifts silently, and the drift is invisible precisely
where it matters, because a privacy claim is read by someone who has
no way to check it.

The second is that they were about defaults rather than about this
installation. ADR-0073 had just made the model's location a
configurable trust boundary: it may now be a machine on the network or
a machine on the internet. A report that recited the default would be
answering a question about somebody else's setup.

It was found by a person reading the output, not by a test. That is
worth recording as plainly as the fix: the sparseness matrix, the
privacy promises and the demo all treated the old sentence as correct,
because it had been written on purpose.

## Decision

The dashboard stops promising and starts reporting.

**Every claim names the test that keeps it true.** The claims move out
of `interfaces/payloads.py` into `interfaces/claims.py`, and each is a
triple: a subject, what is true of it, and the test that fails if it
stops being true. A README describes; this specifies. A claim without
a test is not a claim and does not go in the list.

**What leaves is computed, never asserted.** `outbound_lines` reads
this installation's model settings and says where the model is,
whether the trust boundary admits it, and what therefore travels: on
loopback, that photographs go to the model on this machine and nowhere
else; otherwise, that a reduced copy is sent to the host by name. The
false sentence is gone rather than corrected, because the shape that
produced it was the problem.

**Where the model is becomes a question you can ask on its own.**
`kiseki llm` prints the host, its locality, the boundary, whether it
is admitted and why, and the three models. With `--check` it asks the
model whether it is there; without it, nothing touches the network.

## Consequences

- The privacy payload derives its `never_stored` list from the claims,
  so the served answer and the printed one cannot disagree.
- Adding a claim means writing a test first, which is the only reason
  the list can be trusted.
- A privacy report now differs between installations, and should. Two
  owners with different model hosts are owed different answers.
- The claims file is a specification and belongs to `interfaces`,
  where the surfaces that state it live; it imports the model settings
  and nothing else.
- This ADR is late, and the lateness is the lesson: the decision was
  cited by name in code and in a proposal for ten commits while the
  reasoning existed nowhere. `docs/README.md` says why lives in the
  ADRs. For this one it lived in a pull request body.
