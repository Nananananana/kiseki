# ADR-0034: Single captions join the subjects



## Status

Accepted.

## Context

ADR-0033 gave every lone photograph its own caption, but nothing read
those captions: subject extraction (ADR-0020) walks the stay caption
store only, and the interest derivation (ADR-0021) drops any reading
it cannot match to a stay. The single captions carried preference
signal and none of it reached the profile.

## Decision

One subject run reads both kinds. A single caption is read under a
caption key derived from its one photograph -- CaptionKey.of([photo])
-- so the existing subject store, resume mechanics, prompt and label
vocabulary are shared unchanged, and themes (ADR-0023) can absorb the
labels without knowing where they came from.

The derivation pools single readings with stay readings: each single
contributes one sighting, dated by its photograph, so the existing
score, confidence and ambient-share formulas apply unchanged.
Evidence from a single points at the photograph itself (photo:<id>),
where stay evidence keeps pointing at the caption (caption:<key>).
Consent is re-checked at read time: a photograph whose
use_for_preference is false never becomes evidence, even if a caption
for it exists (ADR-0032).

Anchor proximity does not exclude single subjects. ADR-0017 excludes
places around home and work from becoming interests, because an
anchor describes circumstance rather than choice -- but what someone
photographs at home (a dish, a cat) is a choice. Household noise is
handled where it always was: by the ambient share and by themes.

The stop-and-anchor context annotation originally sketched for
FR-507 moves to place narration (proposals/0002, item 5), where the
nearby single photographs can be cited as facts in the ADR-0022
shape instead of becoming a stored category.

## Consequences

- kiseki subjects now covers about 1,200 more captions, resumably,
  with no new command and no new table.
- Refusals and unparseable answers are recorded per key and never
  asked again (ADR-0015), for singles exactly as for stays.
- Part 3 of FR-507 remains: the representative-selection rebuild and
  the stay-side consent exclusion.
