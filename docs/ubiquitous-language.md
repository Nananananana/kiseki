# Ubiquitous language

Every term below has exactly one meaning in this codebase. Class names, module
names, database tables, and API fields all use these words and no synonyms.

## Core terms

| Term | Definition |
|---|---|
| Photo | A single record with a capture time, and optionally a location. The record is the subject, not the image file. |
| Stop | A stay at one place, made up of one or more consecutive photos. |
| Leg | The movement between two consecutive stops. Always inferred, never observed. |
| Outing | One departure from an anchor and return to it. An ordered list of stops. |
| Trip | A sequence of outings spanning at least one night away. |
| Anchor | A place the person returns to repeatedly. Home, workplace, or a second base. |
| Destination | A visited place that is not an anchor. What a person would call a travel destination. |
| Impression | A short description of what a stop was like, produced from its photos. |
| Narrative | A description of a whole outing as a sequence, produced from its stops. |
| PreferenceProfile | A description of what a person tends to do, derived from outings over a period. |
| Suggestion | A proposal returned in response to a question, always accompanied by evidence. |
| Evidence | The outings a suggestion or profile statement was derived from. |
| Owner | The person a photo belongs to. Carries consent flags. |
| Confidence | How well supported a derived statement is, with the number of supporting records. |

## Relationships

```
Photo    -- grouped into -->  Stop
Stop     -- ordered into -->  Outing
Outing   -- spanned by   -->  Trip
Outing   -- located near -->  Anchor or Destination
Outing   -- summarised into --> PreferenceProfile
```

A `Stop` never exists on its own. It only exists inside an `Outing`.

## Terms we avoid

| Avoided | Use instead | Reason |
|---|---|---|
| Event | Outing | Collides with the programming sense of the word. See ADR-0001. |
| Trip (for a single day) | Outing | `Trip` is reserved for stays involving at least one night. |
| Cluster | Stop | `Cluster` describes an algorithm, not a thing in the domain. |
| Location | GeoPoint | `Location` is ambiguous between coordinates and a named place. |
| Place | PlaceLabel | Only used for the human-readable name of a coordinate. |
| Visit | Stop | Redundant with `Stop`. |
| User | Owner | Photos have owners; the library has callers. |

## Observed versus inferred

The domain distinguishes what was recorded from what was derived. This
distinction is expressed in types, not in comments.

| Observed | Inferred |
|---|---|
| Photo capture time | Leg duration and travel mode |
| Photo coordinates (`location_source = measured`) | Coordinates filled in from a companion device (`interpolated`) |
| Stop boundaries when photos are dense | Stop boundaries across a long gap |
| Number of outings in a period | Everything in a PreferenceProfile |

Anything inferred carries a `Confidence`. Nothing inferred is presented as fact.

## Mapping to code

| Term | Type | Kind |
|---|---|---|
| Photo | `Photo` | Aggregate root |
| Stop | `Stop` | Entity, inside `Outing` |
| Leg | `Leg` | Value object |
| Outing | `Outing` | Aggregate root |
| Trip | `Trip` | Aggregate root |
| Anchor | `Anchor` | Aggregate root |
| Destination | `Destination` | Value object |
| Impression | `Impression` | Value object |
| Narrative | `Narrative` | Value object |
| PreferenceProfile | `PreferenceProfile` | Aggregate root |
| Confidence | `Confidence` | Value object |
| Owner | `Owner` | Value object |

References between aggregates are made by identifier, never by object
reference. An `Outing` holds `PhotoId` values, not `Photo` instances.
