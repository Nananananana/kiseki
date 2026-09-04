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
dependencies (sqlite3 and urllib are the whole infrastructure). Three
reference producers sit beside it, none of which the core imports or
is imported by: `kiseki-ingest` for PhotoRecord v1
(`docs/photo-record.md`), `kiseki-notes` for NoteRecord v1
(`docs/note-record.md`), and `kiseki-web` for WebRecord v1
(`docs/web-record.md`; `plan` and `read`, and nothing in the core
reads its output yet). `kiseki-conformance`
checks documents against the contracts KISEKI publishes.

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

Read the ADRs that cover what you are changing. There are 88.

When you write one: a consequence that could stop being true names
what would end it, and a consequence that cannot says so. Most of them
cannot -- a cost a decision accepted does not expire -- and writing
that down is what tells the next reader they are looking at an
accepted cost rather than at something nobody revisited. Measured
before this line existed: eight of eighty-one `## Consequences`
sections named a condition, and the other seventy-three were silent
about which kind they were. The old ones stay as they are; an ADR is
not edited to match the present.

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
  read from the cwd, and an `.env` path no longer outranks `--data-root` (ADR-0079)). A CLI
  test once wrote into the developer's real database.
- Tests that call a real model carry the `llm` marker and are excluded
  from CI; run `uv run pytest -m llm` before merging model-adjacent
  changes.
- Checks before every green commit: `uv run pytest -q`,
  `uv run mypy packages tools`, `uv run lint-imports`,
  `uv run ruff check --fix .`, `uv run ruff format .`,
  `uv run pre-commit run --all-files`. If pre-commit rewrites
  anything, `git add` and run it again -- a commit whose hooks failed
  did not happen.
- Every distribution ships `py.typed`. Without it a consumer's type
  checker skips the package entirely (PEP 561) and says so in one line
  -- the line consumers silence -- and every annotation in here stops
  existing for them. Measured: with that line silenced, assigning the
  conformance kit's `list[str]` to an `int` raised no error at all.
- Packaging is checked by CI rather than by the list above, because it
  takes half a minute:
  `uv run --no-project python tools/check_packaging.py` builds every
  wheel, installs `kiseki-conformance` into an empty environment and
  uses it from a directory outside the repository. Run it by hand
  before touching a `pyproject.toml` or anything under
  `kiseki_conformance/schemas/` -- everything else in this repository
  runs against `uv sync`, which shows the source tree and hides what a
  wheel would not carry.
- Whether the tests would fail if the code were wrong is a separate
  question from whether they pass, and `uv run python
  tools/check_mutations.py` is how it is asked. It changes one module
  on purpose, many times, and counts how many changes the tests fail
  to notice. Minutes per target, so not in CI.
  **It never prints a score without a control** -- the same module
  measured against tests that cannot reach it, which must leave nearly
  every mutant alive. The first hand-run session reported a perfect
  score everywhere because `uv add --dev` had re-synced without
  `--all-packages`, every test command was failing with
  `ModuleNotFoundError`, and a failing command counts as a killed
  mutant. Measured then: stop extraction 87.1%, and 95.5% once the
  boundary tests it asked for existed.
- `uv add` and `uv add --dev` re-sync **without** `--all-packages` and
  uninstall all five workspace packages. Run `uv sync --all-packages`
  after either. `tests/conftest.py` says so rather than letting it
  arrive as an import error in every test.
- Checkpoints: after `git commit`, confirm the `[branch hash]` line.
  Before `gh pr create`, run `git log --oneline -3` and confirm the
  feat/fix commit is there.
- After `gh pr merge`, confirm the work is on main by looking at the
  repository rather than at GitHub:

      git fetch origin
      git diff --stat origin/main $(gh pr view <n> --json headRefOid -q .headRefOid)

  Empty means it arrived. Insertions are the pull request's own work
  missing from main; deletions mean main has moved on since, which is
  why this belongs immediately after the merge. Then pull main and run
  pytest once more.

  `Squashed and merged`, and the green `MERGED` badge, mean that a
  commit reached the base the pull request named. They say nothing
  about main. Four pull requests displayed it on the same afternoon
  while thirteen files and five hundred and thirty-nine lines were not
  on main, because each had merged into the branch below it in a stack
  (#318). The checkpoint was followed and it passed.

  Use `headRefOid`, never the branch name: a branch can be pushed to
  after its pull request merges, and a diff against it then compares
  with something that was never merged.
- Cut every branch from main. A stacked pull request must be
  retargeted to main before it is merged, and nothing warns when that
  is forgotten. If two pull requests would both edit one line -- a
  count in this file, most often -- the second one changes it, and
  that is cheaper than a stack.
- Before `gh release create`, confirm the release note file exists and
  is not empty. A tag and a changelog entry do not reveal an empty
  note; three of them shipped that way. A release also bumps `version` in
  `packages/kiseki-core/pyproject.toml`, which is the only place the
  released version is written; a test compares it with the newest note
  in `docs/releases/`. It said 0.4.0 for six releases.
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
- Count before you replace. `.Replace()` changes every match, and the
  same line appears in more than one place more often than it looks:
  a function-local import reads exactly like the module import at the
  top, and a parser registered as `x = add_parser(...)` reads
  differently from one registered as `add_parser(...).set_defaults(...)`.
  Assert the count is one, then replace.
- Replace one function per operation. Two functions written into one
  function's range leaves the second one indented inside the first,
  and the error surfaces two hundred lines away.
- After any edit to `cli.py`, run
  `python -c "import ast, io; ast.parse(io.open(PATH, encoding='utf-8').read())"`
  before the tests. A syntax error there stops forty test files from
  being collected, and the traceback names none of them.
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

- Version: v0.11.0 released. v0.12 in progress.
- Schema: version 9.
- Commands (44): `paths`, `ingest`, `activity`, `notes`, `web`, `build`, `report`,
  `profile`, `caption`, `singles`, `screens`, `subjects`, `themes`,
  `index`, `ask`, `tell`, `trend`, `lifecycle`, `insights`, `discover`,
  `compare`, `drift`, `places`, `trips`, `suggest`, `correct`,
  `corrections`, `settings`, `cost`, `map`, `llm`, `privacy`, `export`, `forget`,
  `algorithms`, `limits`, `retention`, `doctor`, `reread`, `retry`, `refresh`,
  `demo`, `serve`, `view`.
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
- The interest export is a published contract, not just a command:
  `schemas/interest-export-v1.json` is normative,
  `InterestExportConformance` checks a document against it, and the
  three rules a schema cannot state -- ordering, `last_seen` after
  `first_seen`, stages agreeing with interests -- are checked beside
  it. A document that travels names itself; one that is handed to a
  command names only its version (ADR-0081).
- Input contracts are siblings, and `docs/records.md` holds what they
  share: name the owner and the producer, ignore unknown fields, speak
  the owner's local time, survive a byte order mark, land in a table of
  your own, be optional, and say what you will not carry. A new source
  answers the ten questions in that file before it lands -- question
  three, what this could reveal, is the one that decides.
- The Apple Health converter waits for an export to exist. The
  receiving half -- ActivityRecord v1, the table, `kiseki activity` --
  is done.
- `WebRecord v1` is settled (`docs/web-record.md`, ADR-0084), its
  producer is `kiseki-web` (`plan` and `read`), and the core reads it
  into a table of its own at schema 9. The contract was written first
  on purpose. Its reference is a **salted** hash of the
  URL, which is the one place it must be stronger than NoteRecord --
  a path is a private string and a URL is a public one, so an unsalted
  hash answers membership questions about clinics and parties. The producer is
  given a page's address and title and **fetches nothing** (ADR-0085):
  a history holds no page, and re-requesting every URL would be a
  second browsing session in somebody else's logs.
- The current plan is `docs/proposals/0009`. It keeps 0008's shape and
  changes three things: notes and web pages as sources the owner writes
  rather than takes, the model's location settled before anything else,
  and the commands that say what the library cannot do. Notes come
  before the web because a folder of text files is simpler than a
  browser's locked database, and the contract should be settled against
  the easy source.
- A producer that discards text cannot be checked afterwards, so a
  source of that kind ships with a dry run and is not recorded until
  the owner has seen what would be.
- Every version reserves its last issue for what the previous
  version's data says.
