# Ubiquitous language

> This defines the domain words in current use. Decisions are recorded
> in `docs/adr/`; proposed changes in `docs/proposals/`.

Every term below has exactly one meaning in this codebase. Class names,
module names, database tables and API fields use these words and no
synonyms.

## What the library works with

| Term | Definition | Type |
|---|---|---|
| Photograph | A record with a capture time, optionally a location, a thumbnail reference and consent flags. The record is the subject, not the image file. | `PhotoObservation` |
| Stop | A stay at one place, made of consecutive photographs. | `Stop` |
| Outing | A departure and a return: an ordered list of stops. | `Outing` |
| Anchor | A place the person returns to repeatedly. | `Anchor` |
| Place | A cluster of stops read back as one place, with visits, first and last, and a revisit cadence. | `PlaceProfile` |
| Place name | The human-readable name of a coordinate, resolved at display time and never stored. | `PlaceName` |

## What the readers say

| Term | Definition | Type |
|---|---|---|
| Caption | One model's description of the photographs of one stay, or its recorded refusal. | `Caption` |
| Single caption | The same, for one photograph that belongs to no stay. | `SingleCaption` |
| Screen reading | What a reader found on one screenshot: a category and labels, never text. | `ScreenshotReading` |
| Subjects | The labels a caption was about. | `SubjectExtraction` |
| Theme | Labels gathered under a name; a set of them is keyed by the label universe. | `Theme`, `ThemeSet` |
| Prompt version | Which prompt made a reading; NULL means it was not recorded. | field on every reading |

## What is derived

| Term | Definition | Type |
|---|---|---|
| Interest | A topic the evidence supports, with a score, a confidence and the evidence behind it. | `Interest` |
| Evidence | A reference to what a statement rests on, in the profile's own vocabulary: `topic:`, `caption:`, `photo:`, `screen:`, `place:`. | `InterestEvidence` |
| Profile | Every interest as of one reading, kept when asked. | `Profile` |
| Trend | What moved between two kept profiles. | `TrendReport` |
| Lifecycle | Where a topic stands: new, returned, growing, declining, dormant, stable. | `TopicLifecycle` |
| Insight | A finding derived from the trend and lifecycle machinery, with its novelty. | `Insight`, `InsightReport` |
| Discovery | An insight ranked for attention, by novelty times importance. | `Discovery`, `DiscoveryFeed` |
| Comparison | What changed between two readings, with the arithmetic on both sides. | `Comparison`, `ComparisonEntry` |
| Mixed pair | Two tendencies held side by side, neither resolved away. | `MixedPair` |
| Correction | The owner's word against a reading, appended and applied at read. | `Correction` |
| Suggestion | Something to do next, derived from the owner's own evidence, with the arithmetic that earned it. | `Suggestion` |
| Retrieval | One document found for a question, with the channels that found it. | `Retrieval` |
| Answer | A reply that cites its evidence, with a confidence and a time range. | `Answer` |

## The four scores, which are never one

| Score | Says |
|---|---|
| Confidence | How strongly the evidence supports a statement |
| Importance | How much a finding deserves attention |
| Novelty | How new or changed a finding is |
| Similarity | How close a document is to a question |

Similarity is never confidence, and confidence never ranks a feed. See
`docs/proposals/0006`.

## Terms we avoid

| Avoided | Use instead | Reason |
|---|---|---|
| Event | Outing | Collides with the programming sense of the word. See ADR-0001. |
| Cluster | Stop | Describes an algorithm, not a thing in the domain. |
| Location | GeoPoint | Ambiguous between coordinates and a named place. |
| Visit | Stop | Redundant. |
| User | Owner | Photographs have owners; the library has callers. |
| Recommendation | Suggestion | A suggestion carries its evidence; a recommendation implies a catalogue. |

## Observed versus inferred

The domain distinguishes what was recorded from what was derived, in
types rather than in comments.

| Observed | Inferred |
|---|---|
| Capture time and coordinates | Stop boundaries across a long gap |
| What a reader said, including a refusal | Every interest, trend, insight and suggestion |
| The owner's corrections | Which readings a correction reaches |

Anything inferred carries a confidence, and nothing inferred is
presented as fact. References between aggregates are made by
identifier, never by object reference: an `Outing` holds `PhotoId`
values, not observations.

## Words that outgrew their definitions

`Trip`, `Leg`, `Impression` and `Narrative` were defined before the
code existed and no type carries them today. Overnight trips are
planned (`docs/proposals/0007`, v0.9); the others were replaced by
`Caption` and by narration that is generated and never stored. They are
listed here so that a reader meeting them in an old ADR knows they are
history, not vocabulary.
