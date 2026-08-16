# Command line

```bash
uv run kiseki paths
uv run kiseki ingest F:/kiseki-data/run/photo-records.json
uv run kiseki build
uv run kiseki report
uv run kiseki report --json
```

## Commands

| Command | What it does |
|---|---|
| `paths` | Print where everything will be stored, and stop |
| `ingest` | Take a PhotoRecord document into the database |
| `build` | Recompute stops, outings and anchors from what is stored |
| `report` | Print what the measures say |
| `caption` | Describe each stay with a local vision model |
| `subjects` | Name the subjects of the captions |
| `profile` | Read the measures and subjects as interests, and keep the reading |
| `themes` | Gather the subject labels into themes |
| `trend` | Read the drift between kept profiles |
| `tell` | Say what the profile says, in prose |
| `serve` | Answer over local HTTP, loopback by default |
| `view` | Write a self-contained HTML view |
| `screens` | Read the screenshots: category and labels only |
| `singles` | Describe the photographs outside every stay |
| `index` | Index the readings for search |
| `ask` | Answer a question from the readings, with evidence |
| `lifecycle` | Where each topic stands in its life |
| `insights` | The current findings, with evidence |
| `correct` | Exclude a topic or a reading from every derivation |
| `corrections` | The append-only correction log |
| `compare` | What changed between two kept readings |
| `privacy` | How the owner's data is treated, in counts |
| `export` | The interest export: a one-way abstraction |

Ingesting and building are separate because they cost differently. Taking
photographs in is cheap and additive; rebuilding reconsiders the whole library.
Importing several exports and building once is the normal way to work.

## Where things go

Run `kiseki paths` to see. By default everything sits under `~/.kiseki`.

Each location can be moved on its own, which matters when bulk storage and fast
storage are different drives:

```bash
export KISEKI_DATA_ROOT=F:/kiseki-data
export KISEKI_DB_PATH=C:/dev/kiseki-work/db/kiseki.sqlite3
```

| Setting | Default |
|---|---|
| `KISEKI_DATA_ROOT` | `~/.kiseki` |
| `KISEKI_RECORDS_DIR` | `<root>/records` |
| `KISEKI_THUMBS_DIR` | `<root>/thumbs` |
| `KISEKI_DB_PATH` | `<root>/db/kiseki.sqlite3` |
| `KISEKI_CACHE_DIR` | `<root>/cache` |
| `KISEKI_LOG_DIR` | `<root>/logs` |
| `KISEKI_GAZETTEER_PATH` | `<root>/gazetteer/cities500.txt` (see docs/gazetteer.md) |

Precedence, weakest first: defaults, `kiseki.toml`, `.env`, the environment,
then `--data-root`. The environment beats the files so that a container or a CI
run can override without editing anything.

## Machine readable output

`report --json` prints the same measures as a document, for feeding something
else:

```bash
uv run kiseki report --json | jq '.places.one_time_rate'
```

## Serving over HTTP

`kiseki serve` answers what the commands above answer, as JSON over
HTTP, so a thin client can ask without linking the library
(ADR-0026):

```bash
uv run kiseki serve                 # binds to 127.0.0.1:8765
uv run kiseki serve --host 0.0.0.0  # reachable from a phone -- deliberate
```

| Endpoint | Answer |
|---|---|
| `/health` | `{"status": "ok"}` |
| `/report` | the measures |
| `/profile` | the current reading, not kept in the history |
| `/trend` | the drift, or `"not enough history"` |
| `/tell?lang=ja` | a cited narration; 503 while the model is away |

Served payloads blur coordinates to two decimals, about a kilometre;
add `?raw=true` to a request to opt out. A GET changes nothing: the
profile history grows only through a deliberate `kiseki profile`.

## The view

`kiseki view` writes one self-contained HTML file -- no map tiles, no
CDN, no script sources -- with the photograph density on the blur
grid, the top interests, the outing rhythm and the drift (ADR-0027):

```bash
uv run kiseki view                       # writes <cache>/kiseki-view.html
uv run kiseki view --out somewhere.html
uv run kiseki view --raw                 # keep raw topic labels
```

### Tuning

The knobs are constants at the top of
`packages/kiseki-core/src/kiseki/interfaces/view.py`:

| Constant | Default | Effect |
|---|---|---|
| `MIN_CELL_PIXELS` | `3.0` | Smallest rendered density cell. Raise it if the dots feel small; too high and neighbouring cells melt together |
| `MAP_WIDTH`, `MAP_HEIGHT` | `760`, `460` | Canvas limits; a larger canvas gives cells more natural room |
| `TOP_INTERESTS` | `12` | How many interest bars are drawn |

`BLUR_DECIMALS` (in `payloads.py`) is not a tuning knob: it is the
privacy grid shared by the API and the view. Making the picture finer
means making every served coordinate finer.

## Reading the screens

`kiseki screens` reads every screenshot once, resumably, through the
staged VLM. A reading is a category from a closed list plus up to six
short labels -- the raw words on the screen are never stored, and the
chat, auth and finance categories are never labelled (ADR-0030).
Withheld consent (`use_for_preference: false`) skips the photograph
entirely (ADR-0032).

```bash
uv run kiseki screens --limit 20   # try a batch first
uv run kiseki screens              # the rest; safe to interrupt
```

## Captioning the lone photographs

`kiseki singles` describes every photograph that belongs to no stop
-- one-off shots and saved images of kind `other` -- once, resumably,
through the same stage-1 vision model as `caption`, into its own
store keyed by photo id (ADR-0033). Screenshots and documents keep
their own reader (ADR-0030), and withheld consent
(`use_for_preference: false`) skips the photograph entirely
(ADR-0032). A refusal is recorded and never asked again.

```bash
uv run kiseki singles --limit 20   # try a batch first
uv run kiseki singles              # the rest; safe to interrupt
```

## Asking

`kiseki index` turns the readings into a search index (FTS5 words
plus bge-m3 vectors, in the same database); `kiseki ask` answers a
question from it with the evidence, its time range and a derived
confidence. The model phrases the answer over a closed, numbered
fact list and cites it (ADR-0036 to ADR-0038); with no evidence
there is no model call. Over HTTP: `GET /ask?q=...&lang=ja`.

```bash
uv run kiseki index                 # once, then after each refresh
uv run kiseki ask "What do I keep photographing lately?"
uv run kiseki ask --json "ramen"    # the answer contract as JSON
```

Words like "last year" -- or their Japanese equivalents (kyonen,
sakunen, YYYY-nen M-gatsu, koko N days, and so on) -- in the
question become the time window automatically, from a closed,
deterministic list (ADR-0039). `--since` / `--until` (ISO dates)
override the words; `/ask` takes the same as `since`/`until`
parameters, and the applied window travels in the answer contract.

```bash
uv run kiseki ask "What did I keep eating last year?"
uv run kiseki ask --since 2025-01-01 --until 2025-12-31 "ramen"
```

## Lifecycle

`kiseki lifecycle` reads where each topic stands in its life -- new,
returned, growing, declining, dormant or stable -- from the whole
kept profile history (ADR-0042). Nothing is stored; the weekly
`kiseki profile` habit is the data it reads. Over HTTP:
`GET /lifecycle`. Every row shows its arithmetic: the strength now
and at the baseline it was judged against.

## Insights

`kiseki insights` derives the current findings from the kept history
(ADR-0043): new, returned, rising, declining, dormant and enduring
topics, the most novel first, each with its magnitude, confidence
and evidence references. Nothing is stored and no model is involved.
Over HTTP: `GET /insights`. `--story` narrates the findings over a
closed, cited fact list (unnamed places stay silent, as in `tell`);
`kiseki ask` attaches related findings to its answer contract as
`supporting_insights` -- metadata for the reader that the model
never sees.

## Corrections

`kiseki correct topic:<name>` (or caption:<key>, photo:<id>,
screen:<id>) appends the owner's word to an append-only log; every
derivation -- profile, trend, lifecycle, insights, tell, view --
reads through it (ADR-0044). Raw evidence and kept profiles are
never rewritten; `--reinstate` undoes by appending, and
`kiseki corrections` shows the log. Ask retrieval obeys the same
log: an excluded reading never returns as answer evidence.

## Compare

`kiseki compare` states what changed between two kept profiles --
appeared, gone, stronger, weaker, steady -- with the strengths and
evidence counts on both sides (ADR-0045). By default it compares the
trend's pair; `--from` / `--to` pick the latest kept profile at or
before each date. Over HTTP: `GET /compare`.

## Privacy

`kiseki privacy` reports how the library treats the owner's data,
counted from storage (ADR-0046): what is stored, what the owner has
withheld, and what is never stored by construction. Local only --
the dashboard is deliberately not served over HTTP.

## Export

`kiseki export` (with --out) writes kiseki-interest-export v1: the
corrected profile's interests with month-level time, and the
lifecycle stages (ADR-0047). No place topics, no identifiers, no
exact timestamps, no coordinates -- and deliberately no endpoint;
exporting is a command the owner runs on purpose.
