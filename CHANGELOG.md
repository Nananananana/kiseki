# Changelog

## v0.2.1

Reading over time, and two ways to look without leaking.

- Themes: subject labels clustered by embedding similarity, with stay
  co-occurrence vouching for middling joins; named from a closed
  member list (ADR-0023). Themes speak for their members in the
  profile (ADR-0024). Embeddings are sent in chunks of 32.
- Trend: `kiseki trend` compares the latest kept profile against the
  most recent one at least 14 days older, through the current theme
  set, so a pre-theme history stays comparable (ADR-0025). "Not
  enough history" is an answer, not an error.
- Local API: `kiseki serve` answers /health, /report, /profile,
  /trend and /tell as JSON, standard library only, bound to loopback
  by default; a GET changes nothing, and served payloads blur
  coordinates to about a kilometre unless raw=true (ADR-0026).
- View: `kiseki view` writes one self-contained HTML file -- density
  on the blur grid, top interests, rhythm, drift; no tiles, no CDN,
  no script sources (ADR-0027). Density cells clamp to a minimum
  pixel size, so a country-spanning library stays visible.
- New commands: `themes`, `trend`, `serve`, `view`.
- Tests: 618 -> 719 (plus 13 deliberate real-model tests).

## v0.2.0

The interest profile: KISEKI now reads what it measured.

- Interests with mandatory evidence and confidence; profiles kept as
  history in SQLite (ADR-0016).
- Place interests derived from the return pattern; anchored places
  excluded -- circumstances are not choices (ADR-0017).
- Ollama adapters for captioning, prose and embeddings, stdlib-only
  transport, CI-tested against an injected transport (ADR-0014/0015).
- Thumbnail references carried end to end; first explicit schema
  migration, version 1 to 2 (ADR-0018).
- Resumable captioning of stays, keyed by the photographs so rebuilds
  cost nothing (ADR-0019); second-stage subject extraction with a
  tolerant JSON contract (ADR-0020).
- Subject interests with data-driven ambient exclusion, merged with
  place interests into one profile (ADR-0021).
- `kiseki tell`: a cited narration from a closed fact list, in
  Japanese or English (ADR-0022).
- New commands: `caption`, `subjects`, `profile`, `tell`.
- Tests: 404 -> 618 (plus 13 deliberate real-model tests).

This file follows the Keep a Changelog format.

## [Unreleased]

### Added
- Initial repository structure
