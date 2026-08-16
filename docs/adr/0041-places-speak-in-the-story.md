# ADR-0041: Places speak in the story

## Status

Accepted. Delivers proposals/0002, item 5.

## Context

The narration (ADR-0022) kept every place silent, because a
coordinate pair is not something a person recognises themselves in.
With the gazetteer (ADR-0040) a place can carry a name, and the
single captions (ADR-0033) know what was photographed right there --
the context annotation FR-507 once sketched, without storing
anything.

## Decision

Named places join the closed fact list: after the measures and
before the subjects, up to three named place interests each become a
fact, and each may carry one more fact quoting up to two single
captions photographed within 500 m of the place, nearest first,
deterministically. Quotes are clipped, refusals never quoted.

Unnamed places stay exactly as silent as before, so without a
gazetteer file nothing changes. The names and quotes are assembled
at narration time and stored nowhere.

`/tell` over HTTP stays place-silent: a story that names places is
location disclosure, and the served surface blurs by default. Place
narration is a local `kiseki tell` feature.

## Consequences

- The story can finally say "you kept going back to Hirara and
  photographed ramen there [F4]" with every word resting on a fact.
- proposals/0002 has one item left: (6) lifecycle labels.
