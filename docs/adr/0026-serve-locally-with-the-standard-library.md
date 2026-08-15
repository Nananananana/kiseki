# 0026. Serve locally with the standard library

## Status

Accepted

## Context

A thin client -- a phone on the same network, a desktop shell --
should be able to ask what the command line answers without linking
the library. The obvious tool is a web framework, but kiseki-core
deliberately carries zero runtime dependencies: sqlite3 and urllib
are the whole infrastructure, and that austerity is part of what
"no account, no upload, no network required" means in code.

The measures and readings also contain coordinates, and the
constitution blurs coordinates on anything exported or shown. A
served payload leaves the process; a terminal on the same desk does
not.

## Decision

- `kiseki serve` starts an HTTP server built on `http.server` from
  the standard library. No new dependency.
- It binds to 127.0.0.1 unless another address is given explicitly.
  Reaching it from a phone is a deliberate act (`--host 0.0.0.0`),
  never a default.
- GET only, and a GET changes nothing: `/profile` takes a reading
  without keeping it (`Pipeline.profile(keep=False)`); the history a
  trend is computed from grows only through a deliberate
  `kiseki profile`.
- Served payloads blur coordinates to two decimals -- roughly a
  kilometre -- by default; `raw=true` opts out per request. The
  payload shapes live in one module shared with the command line, so
  the two interfaces cannot drift apart.
- `/tell` answers 503 when the model is unavailable or refuses.
  Serving stays read-only and synchronous, sized for one owner on
  one machine.

## Consequences

- Blur happens at the serving boundary, not in storage: the library
  keeps what it measured, and what leaves the process is coarsened.
- A framework (FastAPI or similar) becomes the right tool if the API
  ever grows write operations, streaming, or concurrent clients; it
  would then live in its own package so the core stays
  dependency-free, in the spirit of ADR-0015.
