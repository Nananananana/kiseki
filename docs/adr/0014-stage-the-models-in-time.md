# ADR-0014 Stage the models in time rather than in memory

## Status

Accepted

## Context

v0.2 needs three kinds of model: one that reads images, one that writes prose,
and one that embeds text. On the reference hardware they total around 16 GB,
which is exactly the VRAM available, leaving no room for the runtime overhead
each one needs.

Three ways out present themselves.

Use smaller models throughout. An 8B writing model would fit alongside the
captioner, but the prose is noticeably worse, and the profile is the part a user
actually reads.

Move something to a hosted API. That works, and the ports allow it, but the
project's position is that nothing has to leave the machine. Making the default
configuration require an account would undermine that.

Or run them one after another.

## Decision

Run the models in stages, unloading between them.

| Stage | Model | Duration | When |
|---|---|---|---|
| Captioning | `qwen3-vl:8b` | hours | Overnight, in a resumable batch |
| Narrative and profile | `qwen2.5:14b` | minutes | After captioning completes |
| Embedding | `bge-m3` | minutes | Last |

This falls out of the pipeline anyway. Narratives are written from captions, and
embeddings are computed over both, so the stages are already ordered by
dependency. Nothing is being sacrificed for memory that the data flow did not
already require.

Captioning is the only expensive stage, and it must be resumable: an interrupted
overnight run has to continue rather than restart. Progress is recorded per
stop, so a rerun does the remaining work.

Ollama holds a model resident after a request. Each stage sets `keep_alive`
explicitly so the next one is not denied memory by the last.

## Consequences

- The reference configuration runs on one 16 GB card with no account and no
  network
- Quality is not compromised for memory, because the stages were sequential
  regardless
- A user with more VRAM can run the stages back to back with no change; a user
  with less can substitute smaller models through the ports
- Captioning needs progress tracking, which it needed anyway for a run measured
  in hours
- A caption made by one model and a narrative written from it by another must
  agree well enough to be useful. Both stages record which model produced them,
  so a mismatch is diagnosable rather than mysterious
