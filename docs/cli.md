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
