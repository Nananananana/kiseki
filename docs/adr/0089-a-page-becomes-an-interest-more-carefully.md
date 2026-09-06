# ADR-0089: A page becomes an interest, more carefully than a note

## Status

Accepted. Closes #350. Follows ADR-0080, which admitted notes, and
ADR-0031, which admitted screens. Asked for by the first external
producer of WebRecord v1, an orchestrator whose loop -- interest,
news, read, interest moves -- could not close while the core stored
pages and derived nothing from them.

## Context

`kiseki web` has stored page readings since #347. Nothing read them.
That was on purpose: #350 argued that a page is weaker evidence than a
note on three counts, and that a derivation treating them alike would
treat a click as a sentence.

- **Opening is not choosing.** A note exists because somebody sat down
  and wrote it. A page exists because a link was clicked, a tab was
  restored, or somebody sent it.
- **The dwell floor is a guess.** The producer discards a visit under
  ten seconds and over four hours, and the middle is *probably*
  attention.
- **The classification is thinner.** The producer saw an address and
  a title, never the page (ADR-0085).

None of the three is visible in a `PageReading`, which carries a
category and labels exactly as a `NoteReading` does.

#350 also said this should wait for a real corpus. The corpus is now
arriving, from the producer that asked; waiting further would mean
the loop never closes and the corpus is never about anything.

## Decision

**The note derivation's shape, with the thresholds moved and made the
owner's.**

**Its own evidence kind.** `EvidenceKind.PAGE`. `SCREENSHOT` was
reserved for a source that does not exist and a page is not that;
a reader of an export must be able to see that a subject rests on
pages and nothing else.

**A label must recur on four separate days**, against a note's two.
The gap is the three weaknesses above, and it is placed on purpose
above the export gate's three readings (ADR-0069): by the time a page
subject is admitted at all, it has already recurred more than the
gate asks. The first draft of this decision claimed page-derived
interests would *not* pass the gate alone; that was a threshold
picked to make a sentence true, and it is withdrawn. A subject the
owner opened on four separate days may leave, and the export says
`page` beside it.

**Confidence saturates at ten days**, against a note's six.

**Both numbers are chosen, not measured, and are settings.**
`min_page_days` and `page_confidence_full_days` travel through the
five layers like every other threshold and print as *chosen* in
`kiseki settings` (#387, ADR-0088). The producer that asked has been
asked back: after two weeks of real readings, how many page-derived
interests appeared and how many left. The numbers move on that.

**The merge is append-only, and last.** Photographs, then screens,
then notes, then pages: a topic anything else already read keeps its
reading. Two kinds naming one topic are not two witnesses here.
Nothing across kinds is summed until #390 decides how kinds weigh,
and this ADR does not pre-empt it.

**The unlabelled categories contribute nothing**, as the type already
guarantees; the derivation checks again for the day a category is
added and forgotten.

## Consequences

- The producer's loop closes. A page opened on four days moves the
  profile, the export, the trend.
- `read from` can say *page*, and `limits` already counts the
  readings that were withheld by category rather than folding them
  into failures.
- Two more chosen numbers. They are written down as chosen, they are
  the owner's to move, and the first corpus is already on its way.
