# ADR-0005 Publish the schema in two places and test that they match

## Status

Accepted

## Context

The PhotoRecord schema needs to be in two places at once.

At `schemas/photo-record-v1.json` in the repository root it is discoverable: a
producer author browsing the project on GitHub finds it immediately, and it can
be referenced by a stable URL.

Inside `kiseki-conformance` it is needed at runtime, because someone who
installs the package from an index has no repository to read from.

Loading the root copy at runtime is not possible from an installed wheel.
Making the root path a symbolic link is unreliable on Windows, which is a
primary development platform for this project.

## Decision

Keep both copies and add a test that fails when they differ:

```python
def test_bundled_schema_matches_the_published_one() -> None:
    assert load_schema() == load(CANONICAL_SCHEMA)
```

The root copy is canonical when editing. The packaged copy is refreshed from it,
and CI refuses any commit where the two have diverged.

## Consequences

- Editing the schema requires updating both copies in the same commit
- The duplication cannot silently rot, because the build fails
- An installed package is self-contained with no network or repository access
- The comparison is on parsed JSON, so formatting differences are tolerated while
  meaning differences are not
