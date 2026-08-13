# ADR-0015 Shape the model ports for a hosted service, not for localhost

## Status

Accepted

## Context

v0.2 introduces ports for captioning, prose and embedding. The reference
configuration is Ollama on the same machine, and the obvious interface follows
from that:

```python
def caption(self, images: Sequence[bytes], prompt: str) -> str: ...
```

One call, one answer, no failure to speak of. It is the right shape for a
process on localhost that either works or has crashed.

It is the wrong shape for anything else. There is already an intention to run
the captioning model on AWS, and three assumptions in that signature do not
survive the move.

Calls fail routinely. A hosted service times out, rate limits, and returns
transient errors as a matter of course. A caller has to decide whether to retry,
and a signature that raises nothing in particular gives it nothing to decide on.

Batching stops being an optimisation. Captioning a thousand stops one request at
a time is dominated by round trips, and on a metered service costs more than the
same work batched.

And the work costs money. A local run costs an evening; a hosted run costs an
amount that should be knowable before it is spent, not after.

Retrofitting any of these is a breaking change to every implementation.

## Decision

Write the ports for the harder case from the start.

**Batch by default.** Every method takes a sequence and returns a list of the
same length in the same order. A single item is a batch of one, which costs a
local adapter nothing.

**Two exception types.** `ModelUnavailableError` means retrying may work: a timeout,
a rate limit, a model still loading. `ModelRefusedError` means it will not: a
malformed request, an image too large, content declined. A resumable batch
pauses on the first and records the second.

**Usage travels with the result.** Every `Completion` carries the model name and
token counts, and every adapter exposes a running `Usage`. A local adapter can
report zeros for tokens and still satisfy the contract; a hosted one reports
what it was charged for.

**The model name is part of the output.** A caption made by `qwen3-vl:8b` and a
narrative written from it by `qwen2.5:14b` are traceable to their sources, so
that changing a model invalidates only what depends on it.

## Consequences

- Moving captioning to Bedrock, SageMaker or anything else is an adapter, not a
  redesign
- The local adapter carries a little ceremony it does not need, which is a small
  price for not rewriting the interface later
- Resumable batching becomes expressible, because the failure modes are
  distinguishable
- A run can be costed in advance by captioning a sample and reading the usage
- The fakes must implement all of this too, which is the point: the contract
  suite runs against both, so an adapter written months from now is checked
  against the same expectations
