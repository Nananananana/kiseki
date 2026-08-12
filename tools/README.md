# Development tools

Scripts used while building and checking the library. Not part of any package
and not installed.

## journeys.py

Reads a PhotoRecord document and prints the journeys the domain services derive
from it. Used to check stop extraction and outing assembly against a real photo
library before committing to threshold defaults.

```bash
uv run python tools/journeys.py records.json --from 2025-05-03 --to 2025-05-03 --verbose
```

Every threshold is an argument, so tuning means running the command again
rather than editing code.
