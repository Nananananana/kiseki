# 0019 Key captions by their photographs, and let the store be the progress

## Status

Accepted

## Context

Captioning is the expensive stage: hours of model time over a real
library (ADR-0014). Stops, the natural unit to caption, are derived
data and replaced wholesale on every rebuild (ADR-0013). A caption
keyed to a stop would be invalidated by every rebuild, throwing away
hours of work to recompute seconds of it.

The run must also be resumable. An interrupted overnight run has to
continue rather than restart, a refusal must not be asked again, and
an unavailable model should pause the work rather than fail it
(ADR-0014, ADR-0015).

## Decision

**A caption is keyed by the photographs it describes.** The key is
derived from the sorted content-hash identifiers of the captioned
photographs -- the same reasoning that gave outings a content-derived
identifier. When a rebuild reforms the same stay from the same
photographs, the caption is found again; when the stay is genuinely
different, the key changes and it is captioned anew. Selection of
representative photographs is deterministic for the same reason: the
selection is part of the key.

**The caption store is the progress record.** A run computes each
stay's key and skips what is already stored. Nothing else tracks
progress, so resumability cannot drift from reality.

**Refusals are stored as captions.** A refused request would be
refused again (ADR-0015), so the refusal is recorded under the same
key with the reason, and never asked again. A missing thumbnail is
treated the same way: re-asking will not make the file appear.

**Unavailability pauses; it does not record.** A timeout or a stopped
service leaves no trace, so the next run picks the same stay up first.

## Consequences

- Captions accumulate; they are never replaced wholesale. `kiseki
  build` remains cheap and destroys nothing expensive.
- Changing the prompt or the model does not invalidate captions by
  itself. Each caption records the model that made it (ADR-0015), so
  a deliberate regeneration can find stale entries; the mechanism for
  that is future work.
- FR-507's isolated photographs can join later under the same shape:
  a caption of one photograph is a key of one photograph.
