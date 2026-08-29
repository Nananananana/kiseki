# ADR-0068: A listing says each subject once

## Status

Accepted. Found in the profile of a real library, after ADR-0066 made
it short enough to read and ADR-0067 made it honest about names.

## Context

The naming model does not produce one flat layer of themes. On two
years of photographs it produced three, and twenty-three theme names
turned out to be members of other themes:

    eating > dining > table
    nature > plant  > tree
    display > screen

Each layer is a true reading of the same photographs, and each earns a
high score from the same evidence. Ranked together they arrive
together: the top of the profile was eating 1.00, dining 0.99, table
0.99 -- one subject, three lines, and eighteen places left for
everything else the owner is.

Folding at derivation was considered and refused. An owner told only
that they are "interested in eating" has been told nothing; the
specific word -- ramen, sashimi, burger -- is the thing this library
exists to find. The layers are evidence and stay.

## Decision

A family is a chain of themes read to its top. A listing shows the
strongest member of each family and says how many readings sit under
it: "eating ... and 2 more like it". `--unfolded` shows every reading
apart, for a reader who wants the layers.

The fold happens at reading time and nothing is discarded, the posture
corrections (ADR-0044), the stoplist (ADR-0053) and the spatial filter
already take.

The first of a family is whichever ranked highest, so a specific
reading that outranks its theme is the one shown. Depth is capped at
eight: a set that names a loop gives a stable answer rather than
hanging.

## Consequences

- Twenty lines of profile now hold twenty subjects.
- The layers remain in storage, in `--json`, and in `--unfolded`, so
  nothing is lost by the choice.
- The same fold belongs in trend, lifecycle and compare, where the
  layers move together for the same reason. That is a separate change,
  because those listings rank by movement rather than by score and the
  strongest of a family is a different question there.
