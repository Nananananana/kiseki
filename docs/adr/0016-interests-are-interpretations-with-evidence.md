# 0016 Interests are interpretations, and interpretations carry their evidence



## Status

Accepted

## Context

v0.1 measures and refuses to interpret. Measures count; anchors are
observations, not categories (ADR-0010, ADR-0012). v0.2 begins the
interpretation the seam was built for: statements about what someone
appears to care about.

A statement of that kind can be wrong, and a wrong statement about a
person is worse than a missing one. The requirements addendum already
commits every profile statement to carrying the outings it rests on
(FR-507); this record extends that commitment to interests in general
and fixes their shape before any derivation exists.

## Decision

An `Interest` is a domain value with a topic, a score, a confidence,
evidence, and a first and last seen time.

**Construction refuses an interest without evidence.** An interest
with no evidence is a guess, and a guess about a person must not be
constructible in this domain.

**Score and confidence are separate numbers.** Score says how strongly
the evidence points at the topic. Confidence says how far the evidence
can be trusted to support that reading at all. Collapsing them into
one number would hide exactly the distinction a reader needs when
deciding whether to believe a claim about themselves.

**Evidence is a reference, not a copy.** Evidence points at an anchor
or a photograph by identifier. The profile never duplicates the
personal data it was read from, which keeps the later split between
"personal data" and "what may be shared" structural rather than
promised.

**`EvidenceKind` names visit, photograph, and screenshot.** Only visit
and photograph will have sources in v0.2. Screenshot is reserved: the
kind is named now so stored evidence stays readable when a source
arrives, and reserving a name costs nothing.

**Topics do not reintroduce categories through the back door.** For
visit evidence the topic is the anchor reference itself, keeping
ADR-0012's refusal to label places. Human-readable topics arrive with
captioning, where the label comes from what is in the photograph
rather than from a category applied to a place.

**Profiles are kept behind a `ProfileRepository` port.** The port is a
protocol with a shared contract suite, like every other port. The fake
is the first implementation; a persistent one joins the same suite
when profiles need to survive a process.

## Consequences

- Derivation from anchors and measures is deliberately absent from
  this record. It needs the existing measure types and deserves its
  own issue; fixing the target shape first means the derivation is
  written against a tested value, not the other way round.
- The application layer gains an obvious seam: build measures, read
  them into a profile, save the profile. Nothing about that seam is
  decided here beyond the types it will exchange.
- Trend (rising, declining) is not part of the value yet. It requires
  comparing profiles across time, and the history the repository keeps
  is the raw material it will be computed from.
