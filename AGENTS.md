# AGENTS.md

Context for AI assistants (and future humans) working on KISEKI.
Read this whole file before proposing or writing any change. The
"Current state" section at the bottom is updated on every merge; the
rest changes rarely.

## What KISEKI is

A local-first Python library that reconstructs journeys from photo
timelines and reads them as an interest profile. The owner's photos
never leave their machine: no account, no upload, no network required.
Models run locally through Ollama.

The constitution, enforced by construction rather than by promise:

- **Facts, measures and interpretations are separate layers.**
  Facts are observations (photos, captions, subject readings).
  Measures count and stay silent about meaning. Interpretations
  (interests, profiles, narrative) are readings of measures and
  facts, and every interpretation carries `confidence` and
  `evidence` -- an `Interest` without evidence cannot be constructed.
- **Derived data is cheap, sourced data is precious.** Stops, outings
  and anchors are replaced wholesale on rebuild (ADR-0013). Captions
  and subject readings cost model-hours; they are keyed by the
  content-hash photographs they describe, so they survive rebuilds
  (ADR-0019, ADR-0020).
- **Anchors describe circumstances, not choices.** Nothing around
  home or work becomes an interest (ADR-0017), and ambient subject
  labels are excluded by share of readings, not by a hand list
  (ADR-0021).
- **Models choose words, never facts.** The narrative stage receives
  a closed, numbered fact list and must cite it (ADR-0022).
- **Coordinates are private.** Raw coordinates never go into README
  examples, issues, or generated prose. Blurring is the default on
  anything exported or shown.

## Architecture map

Monorepo under `packages/`. `kiseki-core` declares zero runtime
dependencies (sqlite3 and urllib are the whole infrastructure);
`kiseki-ingest` is the reference producer of PhotoRecord v1 documents
(the only contract between capture and core; see docs/photo-record.md).

Inside `kiseki-core/src/kiseki/`:

- `domain/` -- pure values and services. No I/O, no external imports.
- `ports/` -- Protocols (`repositories`, `models`, `captions`,
  `subjects`, `thumbnails`, `profiles`). Implementers never import
  the port.
- `adapters/` -- `sqlite` (storage, schema version 2, explicit
  migrations only, ADR-0018), `ollama` (three model adapters,
  injectable transport), `filesystem` (thumbnails), `fake` and
  `memory` (test doubles held to the same contract suites).
- `application/` -- `pipeline` (ingest/build/report/profile),
  `captioning`, `subject_extraction`, `narrative`.
- `interfaces/cli.py` -- the only composition root.

Model staging (ADR-0014): stage 1 `qwen3-vl:8b` captions stays;
stage 2 `qwen2.5:14b-instruct-q4_K_M` extracts subjects and writes
prose; `bge-m3` embeds (reserved for theme clustering). One model in
VRAM at a time; `keep_alive` is explicit.

Read `docs/adr/` (0001-0022) before changing anything they cover.

## Conventions and hard-won rules

- TDD, one issue = one PR, squash merge, close the issue after.
  Red commit uses `--no-verify`; green commit never does.
- Everything in the repo is English. Conversation language may
  differ; committed text may not.
- **All tests must pass before any commit.** One failure means stop
  and investigate, not proceed. (Learned the hard way, twice.)
- Test file names must be unique across the whole repo -- tests are
  not a package, and duplicate basenames break collection.
- Any test that invokes the CLI must isolate itself: chdir to
  tmp_path (the root conftest already strips `KISEKI_*` env vars,
  but `.env` is read from the cwd). A CLI test once wrote into the
  developer's real database.
- Tests that call a real model carry the `llm` marker and are
  excluded from CI by `addopts`; run them deliberately with
  `uv run pytest -m llm` before merging model-adjacent changes.
- Checks before every green commit: `uv run pytest -q`,
  `uv run mypy packages`, `uv run lint-imports`,
  `uv run ruff check --fix .`, `uv run ruff format .`,
  `uv run pre-commit run --all-files`.
- Checkpoints: after `git commit`, confirm the `[branch hash]` line
  printed (a hook failure prints an error instead and the commit did
  not happen); after `gh pr merge`, confirm `Squashed and merged`;
  after pulling main, run pytest once more.
- Windows specifics: set `PYTHONUTF8=1` (cp932 console crashes
  pre-commit output); paste terminal commands one block at a time
  (mangled pastes have created junk files via `>` redirection).
- Working style with an assistant: the assistant never guesses at
  file contents -- it asks for a read-only dump first, proposes a
  design, then delivers a red-phase script (tests only) and a
  green-phase script (implementation). Scripts write files with
  UTF-8 no BOM, LF, resolved absolute paths, and edits that throw
  when their anchor is missing rather than corrupting a file.
- Every raw .NET file call (ReadAllText/WriteAllText/AppendAllText),
  including inline one-offs outside the helper functions, must
  resolve the path with Join-Path $PWD first -- PowerShell's location
  is not the process working directory. (A one-off CHANGELOG edit
  once reached for a file in the user profile.)

## Current state

- Version: v0.2.0 (release in progress).
- Tests: 8 passing, 13 llm-marked and deselected in CI.
- Pipeline proven end to end on a real library: 3,651 photographs
  ingested; 267 stops; 266 captioned; 265 subject readings; a merged
  profile of place and subject interests; a cited Japanese narration
  via `kiseki tell`.
- CLI: `paths`, `ingest`, `build`, `report`, `profile`, `caption`,
  `subjects`, `tell`, `themes`.
- Shipped since v0.2.0: themes (ADR-0023) -- labels clustered by
  embedding similarity, with stay co-occurrence vouching for
  middling-similarity joins; named from a closed member list with a
  deterministic fallback; `kiseki themes` computes and stores the
  set, keyed by the label universe.
- Fixed: the embed adapter sends chunked requests (32 inputs each);
  a ~300-input batch crashed Ollama's bge-m3 runner on Windows,
  reproduced with a bare HTTP call.
- Next (v0.2.x, in order): merge themes into the profile (theme
  interests aggregate their members' sightings; member labels are
  absorbed); trend (rising/declining from the stored profile
  history); local REST API; visualisation with blurring.
- v0.3: screenshots -- lift the `content_kind: screenshot` exclusion,
  ship the Privacy Filter in the same release, OCR, intent evidence.
- v1.0: overnight trips, weather, multi-device, incremental rebuild,
  PyPI, cloud VLM swap behind the same ports (ADR-0015).
