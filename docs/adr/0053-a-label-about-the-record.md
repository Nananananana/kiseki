# ADR-0053: A label about the record is not a label about the world



## Status

Accepted. Delivers the label calibration of proposals/0005, v0.7.

## Context

With real data the profile grew to 794 interests, and its strongest
two were "date" and "flight" at score 1.00. "date" is not an
interest; it is what a reader says when it looks at a boarding pass
or a calendar screenshot. Alongside it: "text", "label", "number",
"screenshot", "itinerary", "qr code". These words scored like any
other label and crowded out the ones that mean something.

The same run showed a second flaw: a theme named "food" and a
surviving label "food" were emitted as two interests with the same
word, so the profile said one thing twice with different numbers.

## Decision

A closed stoplist, GENERIC_LABELS, names the words that describe the
record rather than the world: the form of a record, an act of
recording, or an abstraction with no thing behind it. Membership has
a test, so the list never grows by taste -- and words like
"spreadsheet", "code" and "dashboard" stay out of it, because they
say what the owner actually works with.

The filter applies at derivation, never at storage. The readings
keep exactly what the model said; one line of code changes what the
profile makes of them, and no model has to run again. This is the
posture corrections already established (ADR-0044).

A theme now absorbs the label that shares its name: same word, same
meaning, one interest, with the evidence of both.

A theme name is a label too: the naming model can call a cluster
"text" as readily as a reader can call a screenshot that. A theme
whose name is generic is not emitted, and its members speak for
themselves -- the cluster was real, the word for it was not.

The list grows by its test, not by taste. A refresh that reads new
screens surfaces new words -- location, property, description,
timeline -- and each is admitted only if it names the form of a
record, an act of recording, or an abstraction with no thing behind
it. Words considered and left out are recorded beside the list with
the reason: python, vscode, ikea and yolo are what this owner
actually works with, and a stoplist nobody can argue with is a
stoplist nobody can correct.
## Consequences

- The profile shrinks and means more; `kiseki correct` no longer has
  to be spent one generic label at a time.
- A label the owner disagrees with is still theirs to exclude: the
  stoplist handles the words that are wrong for everyone.
- v0.8's suggest inherits a cleaner vocabulary to reason over.
