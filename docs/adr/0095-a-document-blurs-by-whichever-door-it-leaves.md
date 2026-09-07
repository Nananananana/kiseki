# ADR-0095: A document blurs by whichever door it leaves

## Status

Accepted. Amends ADR-0026, which decided that served payloads blur and
that "the payload shapes live in one module shared with the command
line, so the two interfaces cannot drift apart." They had drifted.

## Context

`kiseki report --json` wrote the owner's anchors -- the places returned
to at night, which is to say home -- at full float precision, about a
centimetre. `GET /report` blurred the same field to two decimals, about
a kilometre.

Seven payloads defaulted to `blur=False`:

```text
report  profile  trend  comparison  discovery  insights  lifecycle
```

and the seven commands that write them took the default, because none
of them had a `--raw` flag to pass. Four newer payloads -- `answer`,
`suggest`, `today`, `now` -- defaulted to `blur=True` and their commands
all took `--raw`. `answer_payload`'s docstring said "blurred by default,
**unlike its siblings**", so the split had been noticed and fixed once,
locally, rather than closed.

The served side was never wrong: `_answer` passes `blur=not raw` and
`raw` defaults to false, so `/report` blurred what `report --json` did
not.

**No test noticed, in either direction.** Flipping every default and
running the whole suite changed nothing: 2,356 passed before and after.
The privacy promise was resting on a default that nothing checked.

## Decision

**Every payload that can blur, blurs by default.** The safe direction is
the default and the owner opts out, which is the shape four of the
eleven already had.

**Every command that writes such a document takes `--raw`.** Seven were
raw with no flag at all, which is not a choice the owner ever made: it
was the only thing the command could do.

**A terminal is still a terminal.** `kiseki report` printed to a screen
keeps its four decimals. ADR-0026's distinction holds -- a served
payload leaves the process, a terminal on the same desk does not -- and
this decision says only that `--json` is the first case and not the
second. A document written for another program has left.

## What is checked, and how

Three tests, because one of them was not enough and the way it failed is
the point.

**Structural.** Every `*_payload` in the module is read by
`inspect.signature`, and a `blur` parameter defaulting to `False` fails
the test. A payload written next year cannot fail open.

**Through the command, on a library with a doorstep in it.** Twenty
nights of photographs at one point make an anchor, `kiseki report
--json` is run, and every anchor coordinate must equal itself rounded to
the blur. The first version of this test checked only that `--raw` was
accepted and that the output parsed, on an *empty* library -- and it
passed with the command hardcoding `blur=False`, which is the original
defect written a second way. A library with nothing in it cannot leak
anything, and a test on one proves nothing.

**Both directions.** `--raw` must still produce a coordinate finer than
the blur, so the test can tell the two apart. A test that only checks
the blurred case passes when everything is blurred, including by
accident.

## Consequences

- Seven commands change what they write by default. Anything that read
  exact coordinates from `report --json` must now pass `--raw`, and a
  consumer that wanted the blur was previously unable to ask for it.
- The eleven payloads now agree, so the sentence in ADR-0026 about the
  two interfaces not drifting is true rather than intended.
- The plain-text output of the same commands is unchanged.
