# KISEKI

A Python library that reconstructs journeys from photo timelines and infers
personal preferences from them.

## What this is

Most photo analysis looks at one image at a time. KISEKI reads photos as a
sequence: it uses capture time and location to rebuild where you went, in what
order, and for how long.

The goal is not to answer "what do you like" but "how do you spend your time".

- Photo density reveals stays; gaps between them reveal movement
- Visit frequency and time of day distinguish your daily area from travel
  destinations
- Revisit rate matters: a place visited once and never again is a signal too

## Status

Under development. v0.1 covers journey reconstruction and analysis.

## Design principles

- The domain layer depends on nothing outside the standard library
- Every technical concern is abstracted behind a port and injected from outside
- Dependency direction is enforced in CI by import-linter

Ports are declared with `typing.Protocol`, so you can supply your own
implementation without importing this library.

## Privacy

- No personal data or images are committed to this repository
- Coordinate blurring is enabled by default in exports and visualizations
- Offline mode rejects any adapter that performs network access

## Input contract

KISEKI does not read EXIF, HEIC, PhotoKit, or MediaStore. It accepts a single
documented JSON contract, `PhotoRecord v1`. Any platform that can emit that
format can feed the library. A reference implementation for EXIF is included,
and a conformance test kit is provided for writing your own.

## Roadmap

| Version | Scope |
|---|---|
| v0.1 | Journey reconstruction, home area estimation, analytics, CLI |
| v0.2 | Image captioning, preference profiles, suggestions, REST API, demo |
| v1.0 | Overnight trips, weather, multi-device merging, incremental updates, PyPI |

## Development

```bash
uv sync --all-packages
uv run pytest
uv run lint-imports
```

Tests that call a real language model are marked `llm` and excluded from CI.

## License

MIT
