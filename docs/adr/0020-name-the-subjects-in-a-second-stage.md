# 0020 Name the subjects in a second stage, from the captions

## Status

Accepted

## Context

Interests need human-readable topics -- ramen, temples, harbours --
and ADR-0017 promised those labels would come from what is in the
photographs. Three ways of getting them presented themselves: have the
vision model emit structured subjects alongside each caption, which
invalidates every caption already made whenever the format changes;
cluster caption embeddings, which yields groups without names; or read
the finished captions with the language model that stage two of
ADR-0014 already reserves.

## Decision

**Subjects are read from the captions, in a second stage.** The
captioning run is the expensive one, measured in hours; reading 270
captions with the 14B model is measured in minutes. Keeping the two
apart means the caption prompt, the subject prompt and the subject
format can each change without repaying the other's cost.

**The answer contract is a JSON array, parsed tolerantly.** The model
is asked for one to five lowercase English labels for concrete things,
activities and kinds of place -- no proper names, no place names. The
parser accepts a bare array, a fenced array, or an array inside prose;
labels are lowercased, deduplicated and capped. An answer with no
readable array is recorded as a refusal, so a chatty model cannot make
the run retry forever.

**The same run shape as captioning.** Readings are keyed by the
caption's key; the store is the progress record; refusals are
recorded; unavailability pauses (ADR-0019, ADR-0015). Each reading
records the model that made it, so regeneration after a prompt change
can find stale entries.

## Consequences

- Interests can now be grouped by subject label. Deriving PHOTOGRAPH
  interests from these readings is the next issue.
- Labels are English regardless of the library's language. Captions
  and subjects are facts for machines to read; text a user reads is
  written by the narrative stage and can be in their language.
- A caption whose reading was refused can be revisited by a future
  regeneration mechanism; nothing retries it implicitly.
