# AGENTS.md

Context for AI assistants (and future humans) working on KISEKI. Read
this whole file before proposing or writing any change.

This file is current state and current rules. It is not a history: why
a thing is the way it is lives in `docs/adr/`, what shipped when lives
in `docs/releases/`, and what might happen next lives in
`docs/proposals/`. `docs/README.md` explains that separation and why it
matters. A statement here that disagrees with the code is a defect.

## What KISEKI is

A local-first Python library that reconstructs journeys from photo
timelines and reads them as an interest profile. The owner's photos
never leave their machine: no account, no upload, no network required.
Models run locally through Ollama.

The constitution, enforced by construction rather than by promise:

- **Facts, measures and interpretations are separate layers.** Facts
  are observations. Measures count and stay silent about meaning.
  Interpretations carry `confidence` and `evidence` -- an `Interest`
  without evidence cannot be constructed.
- **Derived data is cheap, sourced data is precious.** Stops, outings
  and anchors are replaced wholesale on rebuild (ADR-0013). Readings
  cost model-hours and are keyed by content-hash photographs, so they
  survive rebuilds (ADR-0019, ADR-0020).
- **Anchors describe circumstances, not choices.** Nothing around home
  or work becomes an interest (ADR-0017); ambient labels are excluded
  by share, not by a hand list (ADR-0021); labels about the record
  rather than the world are excluded by a criterion (ADR-0053).
- **Models choose words, never facts.** The narrative stage receives a
  closed, numbered fact list and must cite it (ADR-0022) -- and what it
  writes is checked afterwards, never rewritten (ADR-0054, ADR-0057).
- **Coordinates are private.** Blurring is the default on anything
  served or written. Raw coordinates never go into README examples,
  issues, or generated prose.
- **Judgement happens at reading time.** Corrections, the label
  stoplist and spatial filters all leave storage untouched and change
  what a derivation makes of it (ADR-0044, ADR-0053).
- **Every source may be absent.** A derivation declares what it can
  read, works with any subset, and names what it read; a matrix
  removes each source in turn and fails the build if anything requires
  one (ADR-0063).
- **Nothing outside may invent.** A provider annotates a suggestion and
  cannot create one; the port's signature is the guarantee (ADR-0056).

## Architecture map

Monorepo under `packages/`. `kiseki-core` declares zero runtime
dependencies (sqlite3 and urllib are the whole infrastructure);
`kiseki-ingest` is the reference producer of PhotoRecord v1 documents
(the only input contract; see `docs/photo-record.md`).

Inside `kiseki-core/src/kiseki/`:

- `domain/` -- pure values and services. No I/O, no external imports.
  `domain/shared/moment.py` is where two timestamps are compared:
  never `>` on stored datetimes directly (ADR-0064).
- `ports/` -- Protocols for repositories, models, captions, singles,
  subjects, themes, screens, thumbnails, profiles, search, gazetteer
  and providers. Implementers never import the port.
- `adapters/` -- `sqlite` (storage at schema version 5, explicit
  migrations only, ADR-0018; plus the search index), `ollama`,
  `filesystem`, `fake` and `memory` (test doubles held to the same
  contract suites).
- `application/` -- `pipeline`, the reading stages (`captioning`,
  `single_captioning`, `screen_reading`, `subject_extraction`,
  `theming`), `asking`, `narrative`, `retrieval`, `exporting`,
  `annotating`, `forgetting`, `retention`, `sourcing`, `demo`, and
  the two checks (`answer_validation`, `narration_validation`).
- `interfaces/` -- `cli.py` (the only composition root), `api.py`
  (stdlib HTTP server, loopback by default), `payloads.py`,
  `view.py` (a self-contained HTML page: no tiles, no CDN, no
  scripts).

Model staging (ADR-0014): `qwen3-vl:8b` captions; `qwen2.5:14b-
instruct-q4_K_M` extracts subjects and writes prose; `bge-m3` embeds.
One model in VRAM at a time; `keep_alive` is explicit.

Read the ADRs that cover what you are changing. There are 64.

## Conventions and hard-won rules

- TDD, one issue = one PR, squash merge, close the issue after. Red
  commit uses `--no-verify`; green commit never does.
- Everything in the repo is English. Conversation language may differ;
  committed text may not.
- **All tests must pass before any commit.** One failure means stop and
  investigate, not proceed.
- Test file names must be unique across the whole repo -- tests are not
  a package, and duplicate basenames break collection.
- Any test that invokes the CLI must isolate itself: chdir to tmp_path
  and strip `KISEKI_*` (the root conftest strips them, but `.env` is
  read from the cwd, and an `.env` path outranks `--data-root`). A CLI
  test once wrote into the developer's real database.
- Tests that call a real model carry the `llm` marker and are excluded
  from CI; run `uv run pytest -m llm` before merging model-adjacent
  changes.
- Checks before every green commit: `uv run pytest -q`,
  `uv run mypy packages`, `uv run lint-imports`,
  `uv run ruff check --fix .`, `uv run ruff format .`,
  `uv run pre-commit run --all-files`. If pre-commit rewrites
  anything, `git add` and run it again -- a commit whose hooks failed
  did not happen.
- Checkpoints: after `git commit`, confirm the `[branch hash]` line;
  after `gh pr merge`, confirm `Squashed and merged`; after pulling
  main, run pytest once more. Before `gh pr create`, run
  `git log --oneline -3` and confirm the feat/fix commit is there.
- Before `gh release create`, confirm the release note file exists and
  is not empty. A tag and a changelog entry do not reveal an empty
  note; three of them shipped that way.
- Windows specifics: set `PYTHONUTF8=1`; paste terminal commands one
  block at a time. Every raw .NET file call must resolve its path with
  `Join-Path $PWD` -- PowerShell's location is not the process working
  directory.
- Read-only dumps for an assistant go outside the working tree
  (`..\dump.txt`); a dump swept up by `git add .` once broke a commit.

### Editing files from a script

- Never guess at file contents. Ask for a read-only dump first, then
  edit against what is actually there.
- A multi-line anchor is only safe against a fresh dump: `ruff format`
  reflows code, and yesterday's shape is not today's.
- Prefer replacing a whole function or a whole self-written file over
  inserting lines. Line insertion lands inside dict literals and
  comprehensions, and has broken this codebase twice.
- Never insert an expression into an implicit string concatenation --
  make the line one f-string or replace the function.
- To add an import, name an existing import line and put the new one
  after it. Searching for "the last import" fails on files whose
  imports are all relative or all `__future__`.

### Debugging a failure

- Take the traceback before forming a theory. Five guesses cost more
  than one `traceback.print_exc()`.
- When a test swallows exceptions to collect them, temporarily replace
  the `except` with `raise`, run the single test, and restore the file
  from a backup in the same cell.
- Reproduce in a throwaway script outside the test suite, and strip
  `KISEKI_*` there too -- otherwise the environment differs from the
  test and the bug will not appear.

## Current state

- Version: v0.9.0 released. v0.10 in progress.
- Tests: 1282 passing, 13 llm-marked and deselected in CI.
- Schema: version 6.
- Commands: `paths`, `ingest`, `build`, `report`, `profile`,
  `caption`, `singles`, `screens`, `subjects`, `themes`, `index`,
  `ask`, `tell`, `trend`, `lifecycle`, `insights`, `discover`,
  `compare`, `drift`, `places`, `trips`, `suggest`, `correct`,
  `corrections`, `privacy`, `export`, `forget`, `retention`, `doctor`,
  `reread`, `retry`, `refresh`, `demo`, `serve`, `view`.
- The real library it is developed against: 4,950 photographs, 360
  stay captions, 1,244 single captions, 297 screen readings, 1,604
  subject readings, 46 kept readings, 8 trips.
- Held behind measured triggers, not opinions: the incremental build
  (a full build takes 0.3 seconds at 4,956 photographs; write it when
  a build passes ten seconds or a refresh passes a minute outside the
  model stages, and prove it equals a full rebuild) and a vector
  extension (retrieval is measured by the golden dataset in CI).
- Deferred until it can be tested: merging several devices waits for a
  second device.
- Next, per `docs/proposals/0008`: v0.10 finishes the record boundary
  (records as siblings, PhotoRecord v1 frozen, the new-source
  checklist as a gate, provenance graphs, per-source privacy counts);
  v0.11 adds web pages, watched videos and daily step counts; v0.12
  routes a question to the derivation that can answer it and adds
  `kiseki now`; v0.13 builds the typical week and month from whatever
  exists. v1.0 goes public and adds no new intelligence.
- Input contracts are siblings, and `docs/records.md` holds what they
  share: name the owner and the producer, ignore unknown fields, speak
  the owner's local time, survive a byte order mark, land in a table of
  your own, be optional, and say what you will not carry. A new source
  answers the ten questions in that file before it lands -- question
  three, what this could reveal, is the one that decides.
- The Apple Health converter waits for an export to exist. The
  receiving half -- ActivityRecord v1, the table, `kiseki activity` --
  is done.- Every version reserves its last issue for what the previous
  version's data says.
