"""How a long stage says how far it has got, without saying what.

An orchestrator running `caption` for an hour wants a bar, and may take
the GPU back halfway; every loop here is resumable, so it asks again
the next night. What it needs is a count, not a caption: the callback
receives how many items this run has finished and, where the loop
knows it, how many it set out to do. Nothing else -- no text, no
photograph identifier -- ever travels through it. The interface layer
turns the count into a line on stderr; the loops know nothing of
stderr.
"""

from __future__ import annotations

from collections.abc import Callable

OnProgress = Callable[[int, int | None], None]
"""`(done, total)`: items finished in this run, and the run's own count of
what it set out to do, or None where only the caller can say."""
