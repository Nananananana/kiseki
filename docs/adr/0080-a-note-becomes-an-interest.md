# ADR-0080: A note becomes an interest, carefully

## Status

Accepted. Puts the third source to work. Follows ADR-0031, which did
the same for screen readings.

## Context

Notes were being recorded and used for nothing. A source that arrives
and changes no answer is a table, not evidence.

They reach where photographs cannot. The profile says `python` because
a screen was photographed; it says nothing about what the owner was
thinking while they typed. A note is the only thing here that the
owner wrote rather than pointed a camera at.

## Decision

The shape screen readings already use, with three guards.

**A label must appear on two separate days.** Written once it is a
passing thought; written again a week later it is something the owner
came back to -- which is the whole reason a note reading is keyed by
its day (ADR-0076). Two notes written in one sitting count as one day,
because a sitting is a day.

**The sensitive categories contribute nothing.** They carry no labels
at all, since the type refuses them (ADR-0075), so this is a second
lock on a locked door -- worth having for the day somebody adds a
category and forgets.

**The merge is append-only.** A topic the captions already read keeps
its reading: a photograph of a thing is stronger evidence of caring
about it than a word in a file about it.

Confidence saturates at six days rather than the screens' eight. A
person does not write about the same subject six times unless they
mean it.

## Consequences

- `read from` can say "photograph and note", which is what ADR-0063
  built the vocabulary for.
- Both thresholds are guesses. There is one day of note history, and
  a threshold cannot be measured against a day. They are written down
  as guesses, as `MIN_SCREEN_LABEL_COUNT` already is, and calibrated
  when there is a year.
- What a note weighs against a photograph is deliberately unanswered.
  Writing about something might well mean more than photographing it,
  and there is no evidence either way yet, so notes take the weaker
  position rather than a flattering guess.
