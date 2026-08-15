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
