# ADR-0072: One name, many places

## Status

Accepted. Found in the profile and the lifecycle of a real library.

## Context

`Umeda (JP)` appeared twice in one listing, `Toyonaka (JP)` three
times, `Asahikawa (JP)` twice. It read as a clustering bug.

It is not. The clustering is right: a hundred and fifty metres apart
is two places, and the sixteen places that answer to Toyonaka sit up
to three kilometres from each other, with seventy-two visits at one
of them and one visit at another. The gazetteer answers within
twenty-five kilometres because a town's outskirts should still get
the town's name (ADR-0040), and at that radius a suburb is one word.

So the library holds two true statements that disagree in a listing:
these are different places, and they have the same name.

## Decision

A listing folds places that share a name and says how many it folded:

    Toyonaka (JP)   visits  72  first 2024-07-11  last 2026-06-02
                    every ~25d  and 15 more there

The first of a name is the one the listing already ranked highest,
which for `places` is the most visited -- the place the name is
mostly about. `--unfolded` shows them apart.

A place whose name does not resolve stands only for itself. Two
unnamed coordinates are two places and there is nothing to join them
by, and inventing a join would be worse than repeating a number.

`suggest` is deliberately excluded. It offers a specific place to
return to, and a representative of a name would send the owner
somewhere they have not been. Its own rule already spreads
suggestions apart.

## Consequences

- `places` reads as a list of places rather than of coordinates.
- The count is honest in both directions: "213 in 96 named spots"
  says the clustering found more than the gazetteer can name apart.
- A finer gazetteer would reduce the folding without changing this
  code, which is the correct dependency: the naming is the coarse
  part, not the clustering.
