# ADR-0075: What a note was about, never what it said

## Status

Accepted. The third source, and the first the owner writes rather than
takes. Delivers part of proposals/0009, v0.11.

## Context

A photograph is something the owner pointed a camera at. A page in a
browser history is something they happened to open. A note is
something they wrote, which makes a folder of notes the most eloquent
thing this library will read -- and the most dangerous. It holds
diaries, other people's confidences, passwords, a resignation letter,
a diagnosis.

It also reaches where photographs cannot. The profile says `python`
because a screen was photographed; it says nothing about what the
owner was thinking while they typed.

## Decision

`NoteReading` is a reference, a day, a category and up to eight
labels. There is no field for the text, the file name or the path, in
the same way and for the same reason a screen reading has no field for
its words (ADR-0030): the rule is the shape of the type, not a pass
over something stored.

The producer classifies and discards before the core sees anything. A
core that read the text and then dropped it could not prove it had
dropped it; a core that never receives it has nothing to prove.

Five categories are recorded and never labelled: `journal`, `health`,
`money`, `people` and `credential`. The count is evidence that the
owner keeps a diary; the labels would be the diary. `people` is on the
list because a note about somebody is mostly about them, and they did
not choose to be in this library.

The reference is a hash of the path, made by the producer. The core
can tell that two readings came from the same note and cannot tell
which note; the owner asks the producer, which holds that mapping --
the division photographs already have between a content hash here and
a reduced copy there.

Eight labels at most. A note is not a document to be summarised, and a
longer list would be the text arriving in instalments.

## Consequences

- Schema 7 adds `note_readings` as a table of its own. If this source
  turns out to be a mistake, the table is dropped and nothing else
  notices.
- The producer inherits the trust boundary (ADR-0073): the note's text
  reaches a classifier before anything is discarded, so where that
  classifier runs is the whole privacy argument.
- The producer must offer a dry run, and that is a rule rather than a
  courtesy: a misclassified photograph can be looked at again, and a
  misclassified note cannot.
