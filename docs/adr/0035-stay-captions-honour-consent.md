# ADR-0035: Stay captions honour consent



## Status

Accepted. Completes ADR-0032; closes FR-507.

## Context

ADR-0032 promised that a photograph with `use_for_preference: false`
never becomes interest evidence, and delivered it everywhere except
one place, deferred to FR-507 on purpose: the stay captioning run
still admitted withheld photographs into the representative
selection, so a withheld photograph could still be shown to a model
and shape a stay's caption.

## Decision

The representative selection never sees a withheld photograph. The
run builds its reference table from consenting photographs only; the
spread-selection algorithm itself is unchanged. A stay whose every
photograph is withheld is counted as `withheld` in the run report
and skipped -- distinct from `unreferenced`, which keeps meaning "no
thumbnail to read".

A stay whose selection changes because a photograph left it gets a
new caption key and is captioned once more on the next run; that is
ADR-0019 working as designed. The old caption stays in the
accumulate-only store, unreachable and harmless.

## Consequences

- ADR-0032 is now enforced end to end: journeys still count every
  photograph; no per-photo reading -- caption, single caption,
  screen reading -- ever sees a withheld one, and the derivations
  re-check consent besides.
- On a library with no withheld photographs, nothing is re-captioned
  and every report gains only a `withheld 0` line.
- FR-507 is complete; the next v0.4 item is hybrid search
  (proposals/0002, item 2).
