# ADR-0004 Define ports as typing.Protocol

## Status

Accepted

## Context

Language models, vector stores, geocoders, and repositories are all replaceable.
A user may run everything locally with Ollama and Chroma, or call a hosted API,
or plug in something that does not exist yet.

The usual approach is an abstract base class that implementations inherit from.
That works, but it means every implementer must import this library in order to
subclass it, which is a dependency in the wrong direction for a library whose
main claim is replaceability.

## Decision

Define every port as a `typing.Protocol`. Rely on structural subtyping rather
than inheritance.

```python
class LanguageModel(Protocol):
    def complete(self, system: str, user: str) -> str: ...
```

An implementer writes a class with a matching `complete` method and nothing
else. No import, no registration, no base class.

Injection is by constructor argument. No dependency injection container is used;
composition happens in a single place at start-up, in the CLI and the API entry
points.

Optional adapters are distributed as extras, so `pip install kiseki` pulls in
nothing, and `pip install kiseki[ollama,chroma]` pulls in a local setup.

## Consequences

- Users can implement a port without depending on this library
- Type checking of implementations requires `mypy` on the user side; a mismatched
  signature is not caught at import time
- Contract tests become important: one shared test suite is applied to both the
  fake and the real implementation of each port, so the fake cannot drift
- Without a container, the composition root grows as adapters are added. This is
  accepted; an explicit list is easier to read than implicit wiring
