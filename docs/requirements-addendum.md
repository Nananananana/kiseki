# Requirements addendum

> This tracks requirements and how far they are implemented.
> Decisions are recorded in `docs/adr/`; proposed changes in
> `docs/proposals/`.

Requirements added after the original specification. Each carries the reasoning
that prompted it.

## FR-507 Preference from photographs that form no stop

**Version** v0.2
**Status** Implemented in v0.4 (ADR-0033, ADR-0034, ADR-0035)

### Requirement

Photographs that do not belong to any stop must still contribute to a
preference profile.

### Reasoning

Stop extraction needs several photographs in one place to conclude that someone
stayed there. That threshold is correct for reconstructing a journey, and wrong
for reading a person.

A single photograph of a dish, a shop window, a cat, or a book is a complete
statement of interest on its own. There was no journey, nobody lingered, and
nothing about it fits the shape of an outing. These are also the ordinary days,
which outnumber the trips by a wide margin: in a two year library, isolated
photographs are the majority of what was taken.

Discarding them means the profile describes only how someone travels, when the
subject is what they like.

### Approach

Treat them as a second source of evidence rather than forcing them into the
journey model.

- Photographs left in `in_transit` and `unlocated` are candidates, not waste
- Subject matter comes from captioning, which arrives in v0.2 anyway
- Time and place remain available and still say something: a photograph taken
  on a weekday lunch break near the workplace has a different meaning from one
  taken on a Sunday morning far from home
- The profile combines both sources and states which evidence each statement
  rests on

### Constraint

This must not change stop extraction. The two readings are separate, and mixing
them would make a journey out of a photograph of lunch.

---

## FR-906 Concept diagrams in the README

**Version** v0.1
**Status** Implemented; the README was rewritten again in v0.5

### Requirement

The repository front page must explain what the library does and what it is for,
using diagrams rather than prose alone.

### Reasoning

The premise of this project is not obvious from a description of its parts.
"Reads photo metadata and produces statistics" describes a dozen tools. What
distinguishes this one is the claim that a sequence of photographs says
something about a person that no single photograph does, and that claim is much
easier to show than to write.

A reader arriving from a search result decides in seconds whether the project is
interesting. A diagram of points becoming a line, and of a line becoming a
statement about someone, does that work in a way a paragraph cannot.

### Content

- The central idea: photographs as a sequence, not as individual images
- The pipeline: photographs, stops, outings, anchors, measures, profile
- The boundary: what belongs to the core and what is a replaceable adapter
- The input contract, and why any platform can feed it
- What the library measures, and what it deliberately does not claim
