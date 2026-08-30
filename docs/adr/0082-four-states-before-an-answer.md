# ADR-0082: Four states before an answer, not two

## Status

Accepted. Refines ADR-0015, which typed model failures by whether a
retry could change the answer.

## Context

The Ollama transport turned every `OSError` from `urlopen` into

```text
cannot reach ollama at {host}: {error}
```

A socket timeout is an `OSError`. So a request that waited out the
five-minute timeout reported that the host could not be reached. It
could be reached. It was busy.

That is worse than a silent failure. An absence invites doubt; an
assertion is believed. Somebody reading `cannot reach ollama` checks
whether Ollama is running, finds that it is, and has learned nothing
except that the library is confused.

One Ollama answers one request at a time. On this machine three
libraries share one model image, so the wait may belong to another
program's request entirely -- and neither `ollama ps` nor `nvidia-smi`
shows it, because by the time anyone looks the queue has drained.

A fourth case was found while writing this down: a host that is not an
address raises `ValueError` from `urllib.request.Request` before any
request exists. It was neither of the two typed failures, so it
escaped the taxonomy that `ports/models.py` describes in its own
docstring -- *failures are typed so a caller knows whether to retry* --
and `kiseki retry`, which catches both, would not have caught it.

## Decision

Four states, each with its own sentence and its own consequence.

| State | Type | What a caller does |
|---|---|---|
| unreachable | `ModelUnavailableError` | pause; try again later |
| reachable and slow | `ModelUnavailableError` | pause; try again later |
| reachable and refusing | `ModelRefusedError` | record the refusal, move on |
| could not even ask | `ValueError` | change a setting; nothing was sent |

The first two share a type because the right response to both is to
wait, and ADR-0015 types by response rather than by cause. They do not
share a **message**: a timeout says it reached the host, says how long
it waited, and says the wait may be a queue rather than a slow model.

The fourth is deliberately not a model failure. Nothing was asked of
the model, so a batch that recorded it would write a refusal against a
photograph for a fault the photograph had nothing to do with -- and it
would write one per photograph. It is a `ValueError` naming the host
and the setting, which the CLI already reports at the door as an
unusable setting.

**Where the clock starts is not settled here.** Starting it at the
first token rather than at the request would measure the model
answering instead of the machine queueing, and is the better
primitive. It needs a streaming request, which this transport does not
make. Until then the message carries the classification the code
cannot: *waited N seconds, and the wait may be a queue.*

## Consequences

- A caller that pauses on `ModelUnavailableError` behaves exactly as
  before. The change is what the owner reads.
- `kiseki retry`, which resumes recoverable refusals, is unaffected: a
  misconfigured host now fails before anything is recorded, where
  before it raised an untyped `ValueError` mid-batch.
- **This one could stop being true.** If the transport ever streams,
  the timeout should start at the first token and the message should
  say so; at that point the third sentence of the timeout message is
  the thing to delete. Nothing else here expires: the four states are
  distinctions in the world, not in this implementation.
