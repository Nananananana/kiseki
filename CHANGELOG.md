# Changelog

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
