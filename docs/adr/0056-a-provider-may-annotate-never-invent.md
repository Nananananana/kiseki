# ADR-0056: A provider may annotate, never invent

## Status

Accepted. Delivers proposals/0004 and 0007, v0.8: the external
provider boundary.

## Context

A suggestion the owner can act on wants things KISEKI cannot know:
whether it will rain on Saturday, whether the museum is open. Those
belong to services outside the library. The risk is not that they are
wrong; it is that once something outside can add a candidate, the
promise that every suggestion comes from the owner's own evidence
stops being structural and becomes a habit.

## Decision

The port is shaped to make the dangerous thing impossible rather than
discouraged. A SuggestionAnnotator receives suggestions and returns
notes; there is no return path by which it could add, reorder or
remove a suggestion. A note names the suggestion it is about, says who
said it, and is short enough to annotate rather than narrate.

Everything a provider returns passes through annotate_suggestions,
where the boundary is enforced instead of assumed: a note about
something never offered is dropped, a note claiming a source other
than the provider's own is dropped, and a provider that raises costs
the owner nothing -- the suggestions stand, the notes are empty, the
same way an unavailable embedder leaves retrieval on the words
channel (ADR-0037).

Notes are attached beside suggestions, never merged into them. The
suggestion keeps saying exactly what the owner's evidence earned.

No adapter ships with this. The boundary exists first, tested against
a fake that misbehaves in the three ways that matter, so that the day
a real provider arrives it has a shape to fit rather than a shape to
negotiate.

## Consequences

- "Personal evidence first" is enforced by a type signature rather
  than by review.
- A provider can be added, or deleted, without the core noticing --
  and with no network call existing until one is.
- v0.11's new sources face the same discipline in the other
  direction: a producer may add evidence, never a derivation.
