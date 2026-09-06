"""Progress as one JSON line per window, on stderr, for a program.

    {"stage": "caption", "done": 12, "total": 360, "resumable": true}

Asked for by an orchestrator whose screen wants a bar and whose
scheduler may take the GPU back mid-run. `total` is what `kiseki cost`
counts for the stage, so the two agree; a loop that knows its own
total (index) says so and wins. stderr, so stdout stays the human
report. No caption text and no photograph identifier is ever on a
progress line: the loops hand over counts and nothing else."""

from __future__ import annotations

import json
import sys
from collections.abc import Sequence
from typing import TextIO

from kiseki.application.estimating import Stage
from kiseki.application.progress import OnProgress

STAGE_FOR = {
    "caption": "stay captions",
    "singles": "single captions",
    "screens": "screen readings",
    "subjects": "subject readings",
}
"""Command name to the estimator's stage name, so a bar's total is the
number `kiseki cost` would have printed."""


def json_lines(stage: str, stages: Sequence[Stage], stream: TextIO | None = None) -> OnProgress:
    """A callback that writes one line per report."""
    out = stream if stream is not None else sys.stderr
    counted = {one.name: one.outstanding for one in stages if one.counted}
    known = counted.get(STAGE_FOR.get(stage, stage))

    def report(done: int, total: int | None) -> None:
        line = {
            "stage": stage,
            "done": done,
            "total": total if total is not None else known,
            "resumable": True,
        }
        out.write(json.dumps(line) + chr(10))
        out.flush()

    return report
