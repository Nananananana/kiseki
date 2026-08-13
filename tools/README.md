# Development tools

Scripts used while building and checking the library. Not part of any package
and not installed.

## journeys.py

Reads a PhotoRecord document and prints the journeys the domain services derive
from it. Used to check stop extraction and outing assembly against a real photo
library.

```bash
uv run python tools/journeys.py records.json --from 2026-07-18 --to 2026-07-18 --verbose
```

## profile.py

Runs the whole pipeline and prints what the measures say about the
photographer: where they are based, which places earned a second visit, how a
day out tends to be shaped, and when they go.

```bash
uv run python tools/profile.py records.json
```

Every threshold is an argument, so tuning means running the command again
rather than editing code.
