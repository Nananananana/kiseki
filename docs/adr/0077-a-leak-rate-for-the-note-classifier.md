# ADR-0077: A leak rate for the note classifier

## Status

Accepted. Delivers the measurement part of proposals/0009 for notes.

## Context

Five note categories are recorded and never labelled (ADR-0075). That
makes the classifier a privacy mechanism, and a privacy mechanism
whose accuracy nobody has measured is a hope.

It has two errors and they are not the same error. A sensitive note
read as ordinary has its labels recorded: a diary becomes "moving,
flat, sunlight" in a library that promised to count it and say nothing
else. An ordinary note read as sensitive costs coverage and nothing
more. A single accuracy figure moves the same amount for either.

The first real run showed it. Six notes, five right, and the one that
was wrong was a three-line diary read as `other` -- four labels away
from being recorded.

## Decision

A labelled corpus and three figures: the leak rate over the sensitive
notes, the over-caution rate over the ordinary ones, and how often the
category was exactly right. The leak is the headline.

Every leak is named, with the labels that would have been recorded,
because an aggregate says something moved and not what.

`--strict` exits non-zero when anything leaked, so a build can fail on
it once there is a number worth holding.

Ambiguity is admitted rather than argued with: a note may carry a list
of other categories that would not be wrong -- a trip written like a
diary is both -- and an acceptable answer is counted apart from an
exact one.

## Consequences

- A prompt change stops being an opinion. The corpus says whether it
  helped, which of the two rates it moved, and which notes changed.
- The numbers are a floor to hold rather than a claim: two dozen
  invented files say nothing about a real folder, and the corpus says
  so in its own README.
- The same shape fits the web and video producers when they arrive.
  They have the same asymmetry and will need the same three figures.
