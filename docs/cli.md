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
| `activity` | Take an ActivityRecord document: days of movement |
| `notes` | Take a NoteRecord document: what the owner wrote, as category and labels |
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
| `llm` | Where the model is, whether it is allowed, and whether it answers |
| `privacy` | How the owner's data is treated, in counts |
| `forget` | Remove photographs and everything said about them |
| `retention` | What a decade should look like, as rules |
| `export` | The interest export: a one-way abstraction |
| `doctor` | Categorised, deterministic health checks |
| `discover` | What is worth a look, ranked by novelty and importance |
| `places` | What your journeys say about each place |
| `trips` | The nights away, as journeys |
| `drift` | What moved with what, and each against its own past |
| `suggest` | From your own evidence, pointed forward |
| `reread` | What a newer prompt version left behind |
| `retry` | Refusals the environment caused, not the model |
| `refresh` | The weekly routine, in one idempotent command |
| `demo` | A synthetic library, so the engine can be seen |

Ingesting and building are separate because they cost differently. Taking
photographs in is cheap and additive; rebuilding reconsiders the whole library.
Importing several exports and building once is the normal way to work.

## The other sources

`kiseki activity` reads an [ActivityRecord v1](activity-record.md)
document: a day of movement at a time, with no positions in it. A
library with no photographs can hold activity, and a library with no
activity behaves exactly as it did before it existed (ADR-0065).

`kiseki notes` reads a [NoteRecord v1](note-record.md) document: what
the owner wrote, arriving as a category, a day and up to eight labels.
The text never arrives, because the document has nowhere to put it
(ADR-0075); the producer -- `kiseki-notes`, outside the core -- reads
the folder, classifies each note locally and discards everything else,
and shows what it would record before it records anything.

Both are documents, and both are optional. Each source lands in a
table of its own, so a contract that turns out to be a mistake is
dropped without anything else noticing. See
[the rules every contract shares](records.md).

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
never sees. When an enduring interest and a rising one coexist,
`kiseki insights` holds them together ("held together -- both are
you") instead of resolving them (ADR-0049); the payload carries
them as "mixed".

`kiseki tell` prints the narration check beneath the story: a
narration that cites nothing, cites a fact that does not exist, or
states a number no fact states is reported, never rewritten
(ADR-0057).
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

## Where the model is

`kiseki llm` says which host the models are on, whether that host is
inside the trust boundary and why, and which three models are
configured (ADR-0073). It touches the network only when asked:
`--check` puts one question to the language model and reports whether
it answered. Everything it prints without `--check` is read from
configuration.

## Privacy

`kiseki privacy` reports how the library treats the owner's data,
counted from storage (ADR-0046): what is stored, what the owner has
withheld, where the models are and what therefore leaves, and what is
never stored by construction. The outbound half is computed from this
installation's own settings rather than asserted, and every claim in
the last half names the test that fails if it stops being true
(ADR-0074). Local only -- the dashboard is deliberately not served
over HTTP.

## Export

`kiseki export` (with --out) writes kiseki-interest-export v1: the
corrected profile's interests with month-level time, and the
lifecycle stages (ADR-0047). No place topics, no identifiers, no
exact timestamps, no coordinates -- and deliberately no endpoint;
exporting is a command the owner runs on purpose. The contract is
published like any other: `schemas/interest-export-v1.json` is
normative, `docs/interest-export.md` explains it, and
`kiseki-conformance interests.json` checks a document against it.

## Doctor

`kiseki doctor` runs categorised, deterministic checks -- [schema],
[integrity], [privacy], [evidence], [consistency] -- and fixes
nothing. [consistency] counts photographs whose
reduced copy is missing from the thumbnail directory: the readers
refuse those, and the refusals are recoverable (`kiseki retry`).The [evidence] line is the snapshot opportunity: how many
readings arrived since the last kept profile, and how old that
profile is; the weekly `kiseki profile` habit is the cure, never an
automatic snapshot.

## Discover

`kiseki discover` ranks the insights by novelty times importance --
importance being magnitude scaled by remaining evidence -- and
keeps the top ten (ADR-0048). Confidence is shown and never ranked
on; nothing is stored, and there is no read-state. Over HTTP:
`GET /discover`.

## Places

`kiseki places` reads the owner's own journeys and states, per
place: visits, first and last, and the median gap between revisits
-- deterministic clustering of stops, derived on demand, stored
nowhere. Names come from the gazetteer at display time; an unnamed
place shows a blurred coordinate. Local only. A name is coarser than
a place, so several places answer to one: the line says how many and
how far apart the widest pair is (ADR-0072, ADR-0083), and `--unfolded`
lists every place separately.

`kiseki ask --near "lat,lon" [--within-km N]` keeps answer evidence
within reach of a point, the way a time window keeps it within a
year: the index stays coordinate-free (ADR-0036), locations are
read from the primary store at question time, and a screen reading
never matches a place condition. The reach applies inside
retrieval, before ranking, so a place question is answered from the
place's own evidence instead of being starved by the rest of the
corpus.

## Suggest

`kiseki suggest` also offers a day trip: somewhere inside the reach
the owner's own outings describe, visited once or twice and quiet for
half a year (ADR-0055).
`kiseki suggest` offers, deterministically: places you used to
revisit and have not lately -- a habit, not a single trip: the
visits must span at least a month (go back), and interests that went
dormant after several readings (pick up) -- each with the
arithmetic that earned it (ADR-0050). References speak the
profile's vocabulary, so `kiseki correct` can decline a
suggestion. Local only; no model, no catalogue, nothing stored.

## Refresh

`kiseki refresh` runs the weekly routine in the order the pipeline
needs -- build, caption, singles, screens, subjects, themes, index,
profile -- and finishes with the doctor. Every stage is the same
command you would type, with the same defaults, and every stage is
resumable, so running refresh twice costs only what changed. A
stage that fails stops the run, and nothing after it is attempted.
`--dry-run` prints the order and runs nothing.

Ingest is deliberately not part of it: taking in new records is its
own act, with its own source and its own risks.

## Demo

`kiseki demo` builds a synthetic library in a sandbox, shows every
deterministic derivation against it -- interests, places, lifecycle,
insights, discovery, comparison, suggestions -- and sweeps up, unless
`--keep` is given. No model is called, and no configuration is read:
the sandbox path is the one given and nothing can redirect it, which
is the point. It is how the engine is seen without a real library, and
how CI sees it too.

## Drift

`kiseki drift` counts photographs, outings and screen readings by
month and lays them on one axis: which pairs moved together, which
moved apart, and where each one stands against its own past
(ADR-0058). Moving together is not causing, and the command says so
every time it says anything -- there is no word for "because" in this
vocabulary.

## Trips

`kiseki trips` shows the nights away as journeys rather than as
separate days (ADR-0060). A trip is a run of outings that stayed at
least fifty kilometres from every place you usually set out from, no
more than thirty-six hours apart, spanning at least one night. Outings
are untouched; a trip is derived on top of them.

## Forget

`kiseki forget <photo-id>...` counts what would go -- the photographs,
their captions, their subjects, their screen readings, the indexed
documents and the embeddings -- and shows it. Nothing is removed until
`--apply` is given (ADR-0061). Journeys are not deleted: they are
derived, so `kiseki build` afterwards produces a history without the
photographs. Corrections are kept, because "that reading was wrong"
stays true after the reading is gone.

## Retention

`kiseki retention` says what a decade should look like, as rules
(ADR-0062): photographs older than a span, refusals older than a
span, and kept readings thinned to the last few plus one a month
before them. Every rule is off unless given, nothing runs on a timer,
and nothing goes without `--apply`. Photographs leave through the
same path a deliberate deletion takes, so retention cannot leave
orphans where `kiseki forget` could not.

## The full tour

`kiseki demo --full` walks every command in the order a reader would
meet them, each with a line saying what it answers, against the same
synthetic library. Commands that need a model are described rather
than run: a tour that took twenty minutes and needed Ollama would not
be run, and one that is not run checks nothing. `--write <path>` keeps
it as a document, which is the shortest honest answer to "what does
this library do".
