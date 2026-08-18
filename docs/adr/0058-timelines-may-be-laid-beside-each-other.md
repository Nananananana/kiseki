# ADR-0058: Timelines may be laid beside each other, never blamed

## Status

Accepted. Delivers proposals/0006 and 0007, v0.8: cross-timeline
analysis with drift.

## Context

The library measures several things over time -- photographs taken,
outings made, screens read. Put two of them side by side and a reader
finds a story immediately, and the story they find is causal: the new
job made the photographs stop, the winter made the outings shrink.
The data supports none of that. It supports "these moved together",
which is a smaller and truer thing.

## Decision

compare_timelines counts each series by calendar month, including the
months with nothing in them, and reports one of four relations over
the months they share: moved together, moved apart, no shared
movement, or not enough history to say. Every comparison carries the
caution in its own field, so it cannot be dropped by a caller who
would rather not print it: moving together is not causing.

There is no word for "because" in this vocabulary. Adding one would
be a change to the ubiquitous language, argued for on its own terms,
not a quiet addition to a function.

derive_drift places a series against its own past in four stages --
steady, drifting, changed and stayed changed, a shape its history
does not contain -- and never says whether the change was good. The
recent window is held out of the baseline, because measuring a change
against a history that already contains it is how a change hides:
the first draft of this did exactly that and reported a tripling as
steady.

A timeline must be counted by when the thing happened, not by when
the library noticed. The first run of `kiseki drift` reported the
screens as one month long, because the count used the reading's
created_at -- the day the model was run -- rather than the day the
screenshot was taken. That measured the library instead of the
person. Every series is counted by the moment in the owner's life:
photographs by capture, outings by their start, screens by the
capture of the photograph they read.
## Consequences

- `suggest` and the narration can say what moved together without
  either of them being able to say what caused what.
- v0.9's drift work inherits a vocabulary that already refuses the
  claim it would be tempting to make.
