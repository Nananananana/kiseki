# ADR-0003 Enforce dependency direction in CI

## Status

Accepted

## Context

The layering rule of this project is that the domain layer depends on nothing
outside the standard library, and that dependencies point inward.

Layering rules stated in documentation decay. The first time a domain service
needs to read a file or call a model, the shortest path is to import the thing
directly, and nothing stops it.

## Decision

Express the layering rule as machine-checked contracts using import-linter, and
run them in CI alongside tests.

Four contracts are defined in `.importlinter`:

1. Layer order: `config` above `adapters` above `application` above `ports`
   above `domain`
2. The domain layer must not import external libraries
3. The domain layer must not import `pathlib`, `os`, `tomllib`, `sqlite3`, or
   the config module
4. `kiseki_ingest` must not import `kiseki.domain` or `kiseki.application`

Contract 3 covers paths specifically. Paths are a technical concern, so the
domain receives a `DomainSettings` object containing thresholds and nothing else.

Contract 4 is what makes ADR-0002 verifiable rather than aspirational.

Additionally, `kiseki-core` declares no runtime dependencies in its
`pyproject.toml`. The packaging metadata states the same rule the contracts
enforce.

## Consequences

- Violating the architecture fails the build, not a review
- Contracts must be updated as modules are added; the `cli` layer is currently
  excluded because it does not exist yet
- Configuration file names must stay ASCII, because import-linter reads
  `.importlinter` using the platform default encoding
- Some convenience is lost: a domain service cannot log to a file or read a
  configuration value directly
