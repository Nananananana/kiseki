# Changelog

## v0.4.0

Ask your own library: search over your captions, answers with
evidence, named places and topic lifecycles -- all local, nothing
new stored about you.

- Single photographs join the profile (FR-507, ADR-0033 to 0035):
  photographs outside every stop get their own caption, feed the
  subjects and the profile; consent governs the representative
  selection of stay captions.
- A search index beside the stores (ADR-0036): FTS5 words plus
  per-model vectors over the answered readings; resumable
  `kiseki index`; nothing withheld, sensitive or coordinate-shaped
  is ever indexed.
- Deterministic hybrid retrieval and `kiseki ask` / GET /ask
  (ADR-0037, ADR-0038): retrieval chooses numbered facts, the model
  phrases one cited answer; confidence, time range and evidence
  derive from the retrieval, never from the model; no evidence, no
  model call.
- Time in the question (ADR-0039): a closed list of Japanese and
  English time expressions becomes the ask window; --since/--until
  override the words.
- The offline gazetteer (ADR-0040): a GeoNames file the owner
  downloads names place topics at presentation time; anchors are
  never named, names are never stored.
- Places speak in the story (ADR-0041): `kiseki tell` narrates named
  places and quotes the single captions photographed beside them;
  /tell over HTTP stays place-silent.
- Lifecycle is read, never stored (ADR-0042): new, returned,
  growing, declining, dormant, stable, from the whole kept history;
  `kiseki lifecycle` and GET /lifecycle.
- New commands: `singles`, `index`, `ask`, `lifecycle`.
- Tests: 781 -> 948.

## v0.3.0

The privacy release: screenshots become interest evidence without
their words ever being stored.

- Content kinds are carried end to end (ADR-0028): schema version 3,
  the first chained migration; non-photographs never shape stops or
  anchors.
- The producer can borrow the file-modified time for non-photographs
  without EXIF time (opt-in `--time-fallback-mtime`, declared in
  `extra.time_source`; ADR-0029). The previously skipped saved
  images and every screenshot now enter the library.
- The screen reader (ADR-0030): a reading is a category from a
  closed list plus short labels, with no text field -- the Privacy
  Filter is the type. Chat, auth and finance screens are never
  labelled. The reader is a swappable port; the first adapter
  prompts the staged VLM. Resumable `kiseki screens`.
- Screens join the profile (ADR-0031): a label on two or more
  screenshots becomes an interest with SCREENSHOT evidence; settings
  screens contribute nothing; the merge never overwrites what the
  captions read.
- Consent is honoured mechanically (ADR-0032): `use_for_story:
  false` is dropped at ingest; `use_for_preference` rides on the
  observation (schema version 4), keeps journeys and blocks every
  per-photo reading.
- The refresh runbook (docs/runbook.md, examples/refresh.ps1).
- New command: `screens`. Tests: 719 -> 781.

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
