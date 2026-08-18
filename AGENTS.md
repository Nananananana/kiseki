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
  `singles`, `subjects`, `themes`, `screens`, `thumbnails`,
  `profiles`). Implementers never import the port.
- `adapters/` -- `sqlite` (storage, schema version 4, explicit
  migrations only, ADR-0018), `ollama` (model adapters,
  injectable transport), `filesystem` (thumbnails), `fake` and
  `memory` (test doubles held to the same contract suites).
- `application/` -- `pipeline` (ingest/build/report/profile/trend),
  `captioning`, `single_captioning`, `screen_reading`,
  `subject_extraction`, `theming`, `narrative`.
- `interfaces/` -- `cli.py` (the only composition root), `api.py`
  (stdlib HTTP server, loopback by default), `payloads.py` (the JSON
  shapes both share; blur on request), `view.py` (a self-contained
  HTML view: no tiles, no CDN, no script sources).

Model staging (ADR-0014): stage 1 `qwen3-vl:8b` captions stays;
stage 2 `qwen2.5:14b-instruct-q4_K_M` extracts subjects and writes
prose; `bge-m3` embeds (theme clustering). One model in
VRAM at a time; `keep_alive` is explicit.

Read `docs/adr/` (0001-0033) before changing anything they cover.

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
- Before `gh pr create`, run `git log --oneline -3` and confirm the
  feat/fix commit is actually there. (A red-only branch was once
  PR'd and merged as if it were the feature.)
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
- Read-only dumps for the assistant go outside the working tree
  (for example `..\dump.txt`); a dump swept up by `git add .` once
  broke a green commit through the line-ending hooks.

## Current state

- Version: v0.3.0 released.
- Tests: 1171 passing, 13 llm-marked and deselected in CI.
- The current-state documents were audited against the code after
  v0.7 and now describe today: the context map gained the reading
  context and dropped the claim that preference extraction cannot
  see photographs; the ubiquitous language was rewritten around the
  types that exist, with the four scores and the words that
  outgrew their definitions named as history; concept and
  architecture lost their v0.2 future tense. FR-507 is recorded as
  implemented.
- Where the truth lives: docs/README.md names what each document
  is for and keeps three things apart -- what is true now, why it
  became true (docs/adr, history, never rewritten to match the
  present), and what might become true (docs/proposals, not
  evidence that anything exists). A current-state document that
  disagrees with the code is a defect, not a difference of
  opinion.
- The road to v1.0 (proposals/0007): v0.8 recommends with evidence
  (places from the owner's own reach, the provider boundary,
  cross-timeline drift, kiseki demo, a narration check); v0.9
  merges devices and learns overnight trips; v0.10 adds the
  boundary for other kinds of history -- records are siblings, not
  subclasses, PhotoRecord v1 frozen, adapters converging inside the
  core; v0.11 lands web pages and watched videos as categories and
  labels with the text discarded at ingest; v1.0 goes public and
  adds no new intelligence. Every version reserves its last issue
  for what the previous version's data says.
- v0.7 (incremental build, decided by measurement): held behind a
  measured trigger. At 4,956 photographs a full build takes 0.3
  seconds, profile 1.2, index 0.5. The incremental path is written
  when a full build passes ten seconds or a refresh passes a minute
  outside the model stages -- and an incremental result must equal
  the full rebuild, proven by a test. See proposals/0005.
- Pipeline proven end to end on a real library: 3,756 photographs
  ingested; 271 stops; 144 outings; captions, subject readings,
  themes and screen readings (218 of 221 screenshots); a merged
  profile of place, subject and screen interests; a cited Japanese
  narration via `kiseki tell`.
- CLI: `paths`, `ingest`, `build`, `report`, `profile`, `caption`,
  `subjects`, `tell`, `themes`, `trend`, `serve`, `view`, `screens`,
  `singles`, `index`, `ask`, `lifecycle`, `insights`, `correct`,
  `corrections`, `compare`, `privacy`, `export`, `doctor`,
  `discover`, `places`, `suggest`.
- Shipped since v0.2.0: themes (ADR-0023) -- labels clustered by
  embedding similarity, with stay co-occurrence vouching for
  middling-similarity joins; named from a closed member list with a
  deterministic fallback; `kiseki themes` computes and stores the
  set, keyed by the label universe.
- Fixed: the embed adapter sends chunked requests (32 inputs each);
  a ~300-input batch crashed Ollama's bge-m3 runner on Windows,
  reproduced with a bare HTTP call.
- Shipped: theme merge (ADR-0024) -- themes speak for their members:
  aggregated sightings, absorbed members, ambient excluded even
  inside a theme; the pipeline reads the latest stored theme set and
  stays model-free.
- Shipped: trend (ADR-0025) -- `kiseki trend` compares the latest
  kept profile against the most recent one at least 14 days older,
  through the current theme set; deterministic, model-free; answers
  "not enough history" until the real history spans 14 days.
- v0.4 plan: docs/proposals/0002 -- (1) FR-507 single-photo context,
  (2) hybrid search (FTS5 + bge-m3, `kiseki ask`), (3) temporal
  retrieval, (4) place entities (offline gazetteer), (5) place
  narration, (6) lifecycle labels.
- v0.5-v0.6 direction: docs/proposals/0003 -- the personal context
  engine: insight engine, evidence-grounded ask contract, user
  corrections, derived lifecycle, timeline, evidence explorer,
  export, privacy dashboard and audit; deferred pieces and the
  reasons are in the proposal.
- Shipped: local API (ADR-0026) -- `kiseki serve` answers /health,
  /report, /profile, /trend and /tell as JSON, standard library only,
  bound to loopback by default; a GET changes nothing (served profile
  readings are not kept), and served payloads blur coordinates to a
  ~1 km grid unless raw=true is asked for.
- Shipped: view (ADR-0027) -- `kiseki view` writes one
  self-contained HTML file (photograph density on the blur grid, top
  interests, rhythm, drift); no tiles, no CDN, no script sources;
  --raw keeps raw topic labels only.
- Fixed: density cells clamp to a minimum pixel size, so a
  country-spanning library still shows its cells (they rendered
  sub-pixel before and the map looked empty).
- Shipped: docs/proposals/0001-memory-upgrades.md -- the v0.4 memory
  backlog evaluated, with the ten survey answers.
- v0.3 decided: no raw OCR text is ever stored (category + labels
  only; chat, auth and finance categories yield no labels); the
  screenshot reader is a port, so the VLM-prompt adapter can be
  swapped for a dedicated extractor. Landed: (1) content_kind
  carried end to end (ADR-0028; schema v3, first chained migration;
  non-photos never shape stops or anchors). (2) the producer
  borrows the file-modified time for non-photographs without a
  capture time (opt-in --time-fallback-mtime, declared in
  extra.time_source, ADR-0029); the Japanese screenshot-name pattern
  is verified in the repo and pinned by a test. (3) the refresh
  runbook: docs/runbook.md and examples/refresh.ps1 (parameterised;
  no personal paths in the repo). (4) the screen reader
  (ADR-0030): ScreenshotReading is category + labels with no text
  field -- the Privacy Filter is the type; chat, auth and finance
  never carry labels; the reader is a swappable port with a
  qwen3-vl JSON-prompt adapter; resumable `kiseki screens`.
  (5) screen readings merged into the profile (ADR-0031). (6)
  consent enforced mechanically (ADR-0032): `use_for_story: false`
  is dropped at ingest, and `use_for_preference: false` never
  becomes interest evidence anywhere.

- v1.0: overnight trips, weather, multi-device, incremental rebuild,
  PyPI, cloud VLM swap behind the same ports (ADR-0015).
- v0.4 (FR-507, 1 of 3): single-photo captions (ADR-0033) --
  photographs outside every stop, of kind photo or other, get their
  own captions in `single_captions`, keyed by photo id; resumable
  `kiseki singles --limit`; withheld photographs (ADR-0032) are never
  captioned; screenshots stay with the screen reader (ADR-0030).
- v0.4 (FR-507, 2 of 3): single captions join the subjects
  (ADR-0034) -- the subject run reads them under a key derived from
  their one photograph, so labels share the vocabulary and themes
  absorb them; the derivation pools one sighting per single with
  photo: evidence and re-checks consent at read time. The stop and
  anchor context annotation moved to place narration (proposals/0002,
  item 5).
- v0.4 (FR-507, 3 of 3): stay captions honour consent (ADR-0035) --
  withheld photographs never enter the representative selection, a
  stay of only withheld photographs is counted and skipped, and a
  changed selection re-captions the stay once under its new key.
  FR-507 is complete; next per proposals/0002: (2) hybrid search.
- v0.4 (hybrid search, 1 of 3): the search index (ADR-0036) --
  answered stay captions, single captions and labelled screen
  readings become FTS5 documents plus per-model vectors in the same
  database; the adapter creates its own tables so connect() never
  depends on FTS5; resumable `kiseki index --limit`; withheld
  photographs and sensitive screens are never indexed, and no
  coordinate enters a document.
- v0.4 (hybrid search, 2 of 3): deterministic hybrid retrieval
  (ADR-0037) -- FTS5 words and vector meaning fused by reciprocal
  rank (k=60), ties by document key; raw questions are tokenised into
  safe OR-joined FTS5 queries; an unavailable embedder degrades to
  words alone; since/until bound hits by observed time as the
  temporal hook.
- v0.4 (hybrid search, 3 of 3): `kiseki ask` and /ask (ADR-0038) --
  retrieval chooses the facts, the model phrases one cited answer
  over a closed numbered list (the ADR-0022 shape); confidence, time
  range and evidence come from the retrieval, never from the model;
  no evidence means no model call. Hybrid search is complete.
- v0.4 (temporal, ADR-0039): a closed, deterministic list of
  Japanese and English time expressions ("last year", kyonen,
  YYYY-nen M-gatsu, koko-N-days) becomes the ask window, with no
  model in the loop; explicit --since/--until (CLI) or since/until
  (/ask) override the words; a question without an expression gets
  no window rather than a guess, and the applied window travels in
  the answer contract.
- v0.4 (place entities, 1 of 2): the offline gazetteer (ADR-0040) --
  the owner downloads a GeoNames file (docs/gazetteer.md, CC BY 4.0,
  never bundled, never fetched); the adapter grid-buckets it and
  answers nearest() deterministically; no file means no names.
  Anchors are never named, and names are never stored -- they are
  resolved at presentation time.
- v0.4 (place entities, 2 of 2): names at presentation time -- with
  the file in place, `kiseki profile` and `kiseki view` label place
  topics (the name alone when blurred, the name beside the reference
  when raw); anchors stay unnamed and served payloads are unchanged.
  Place entities complete.
- v0.4 (place narration, ADR-0041): named places speak in `kiseki
  tell` -- a fact per top named place (at most three), plus up to
  two single captions photographed within 500 m quoted beside it,
  nearest first, deterministically; unnamed places stay silent as
  before, /tell over HTTP stays place-silent (blur by default), and
  nothing is stored.
- v0.4 (lifecycle, ADR-0042): where each topic stands -- new,
  returned, growing, declining, dormant, stable -- derived from the
  whole kept history through the trend machinery and never stored;
  `kiseki lifecycle` (--json) and GET /lifecycle answer, with an
  honest "not enough history" until the span exists. proposals/0002
  is feature-complete; released as v0.4.0 (README rewritten,
  docs/releases/v0.4.0.md).
- v0.5/v0.6 direction (proposals/0004, refining 0003 after the
  owner's improvement brief): insights as first-class derived
  objects (topic, kind, direction, magnitude, confidence, evidence
  refs, novelty; never model-invented), corrections that reach every
  derivation (append-only, the ADR-0032 shape), compare with
  deterministic reasons, discovery ranked by novelty and importance
  (kept apart from confidence), mixed-evidence surfacing instead of
  asserted contradictions, evidence-based suggest, privacy
  dashboard, interest export as a one-way privacy boundary; no
  automatic snapshots (opportunity hints only); the avoid list
  stands. README repositioned as a local-first personal context
  engine.
- v0.5 (insights, 1 of 3, ADR-0043): the Insight object and its
  deterministic derivation -- new, returned, rising, declining,
  dormant, enduring -- built on the trend and lifecycle machinery;
  novelty is a per-kind constant (not importance, which waits for
  the v0.6 discovery ranking), magnitude the underlying delta or
  strength, confidence and evidence reused from the latest profile's
  interests (themes expanded to members), derived_from names the
  sources; long-gone dormants and weak stables are not findings.
- v0.5 (insights, 2 of 3): the surface -- Pipeline.insights(),
  `kiseki insights` (--json, place names applied at display), and
  GET /insights; evidence references are blurred like everything
  else served; an honest "not enough history" until the span exists.
- v0.5 (insights, 3 of 3): `kiseki insights --story` narrates the
  findings over a closed, cited fact list (a place topic without a
  name is skipped -- the ADR-0041 rule applied to insights; no
  facts, no model call), and `ask` attaches matched findings to the
  answer contract as supporting_insights -- metadata the model never
  sees, so an answer can never borrow their certainty. Insights are
  complete.
- v0.5 (corrections, 1 of 2, ADR-0044): an append-only correction
  log (reference in the evidence vocabulary, verdict excluded or
  reinstated, latest word wins) applied as a pure read-time filter
  -- an excluded topic drops its interest, an excluded reference
  drops that evidence, an evidence-less interest drops; the Pipeline
  filters the fresh reading and the whole kept history, reaching
  profile, trend, lifecycle, insights, tell, view and
  supporting_insights at once; stored bytes are never rewritten.
  `kiseki correct` / `kiseki corrections`.
- v0.5 (corrections, 2 of 2): ask retrieval obeys the same log --
  an excluded reference maps to its index document (caption: ->
  stay:, photo: -> single:, screen: -> screen:) and drops before
  the facts, the confidence and the window are derived; everything
  excluded means no model call, and the index is never rewritten.
  Corrections are complete.
- v0.5 (compare, 1 of 2, ADR-0045): compare_profiles states, per
  themed topic, appeared / gone / stronger / weaker / steady --
  movement past the trend's own delta -- with the strengths and
  evidence counts on both sides and up to three after-side evidence
  references; loudest first, deterministic, nothing stored. Next:
  (2 of 2) Pipeline.compare(), `kiseki compare` (--from/--to), and
  GET /compare.
- Console-safe names: FileGazetteer prefers the GeoNames asciiname
  column (falling back to name), and the CLI reconfigures stdout
  with errors="replace" at startup -- a cp932 console degrades a
  macron to "?" instead of crashing `kiseki profile`.
