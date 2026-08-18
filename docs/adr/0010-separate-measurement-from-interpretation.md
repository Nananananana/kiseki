# ADR-0010 Separate measurement from interpretation



## Status

Accepted

## Context

The purpose of this library is to describe what someone likes. The obvious way
to get there is to hand a set of outings to a language model and ask it what
sort of person took these photographs.

Doing that directly has two problems.

Nothing is testable. A sentence like "prefers unhurried days close to home" can
be judged by a reader but not by an assertion, so a change in prompt or model
cannot be told apart from a change in the data.

And the interpretation carries claims that were never measured. A model given
raw outings will readily conclude things about mood, company, and taste that the
photographs cannot support, and there is no seam at which to check.

## Decision

Split the work in two, with a boundary made of numbers.

The analytics module measures. It counts visits, summarises distributions, and
computes rates. It is pure, deterministic, and asserted against exact values. It
never produces a sentence.

The preference profile, in v0.2, interprets. It reads those numbers and writes
statements about the person. It is non-deterministic and evaluated rather than
asserted.

The measures were chosen to describe habits rather than journeys, because the
subject is the photographer and not the trip:

| Measure | What it says about the person |
|---|---|
| One time rate | Whether they keep seeking new places or return to known ones |
| Return rate and most returned to | Which places actually earned a second visit |
| Travel distance spread | Near or far by habit, with the median resisting one holiday |
| Stops per outing | Whether days are packed or unhurried |
| Stay duration spread | Whether they linger or move on |
| Photographs per outing and per visit | How much a place engages them |
| Departure hour and early start share | Morning person or afternoon starter |
| Weekend share and weekday distribution | Whether time away is confined to weekends |
| Monthly distribution | Seasonal variation in going out at all |

Both the median and the mean are reported wherever a distribution is summarised,
because they disagree in a way that matters: one long trip moves the mean and
leaves the median, and the median is the better description of a habit.

Empty input is handled differently by design. `summarise_habits` raises, because
a summary full of zeros reads as a person with no habits, which is a different
claim from having no data. `summarise_rhythm` returns zeros, because its output
is a shape to be drawn and an empty week is a meaningful drawing.

## Consequences

- The measures can be unit tested to exact values, and are
- Changing the model or the prompt in v0.2 cannot silently change what was
  measured
- A poor profile can be diagnosed: either the numbers are wrong or the reading
  of them is
- The numbers are also directly usable by the visualisation package, which needs
  distributions rather than prose
- Anything not measured here cannot be claimed later without adding a measure
  first, which is the intended constraint
