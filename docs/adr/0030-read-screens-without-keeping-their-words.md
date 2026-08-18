# 0030. Read screens without keeping their words



## Status

Accepted

## Context

Screenshots carry a different kind of information than photographs:
messages, balances, codes, addresses. v0.3 wants them as interest
evidence, and a redaction filter over extracted text would be a list
of things to forget, maintained forever, failing open. The decision
(the Privacy Filter) is to never hold the words at all.

## Decision

- A `ScreenshotReading` is a category from a closed list plus short
  subject labels. It has no text field; the filter is the type.
- The categories `chat`, `auth` and `finance` are sensitive: they are
  recorded (the screenshot was seen) but never carry labels, and the
  adapter empties labels for them regardless of what the model said.
- `ScreenshotReader` is a port. The first adapter is the staged VLM
  (qwen3-vl) with a JSON prompt; a dedicated OCR or extraction engine
  can replace it behind the same port when accuracy demands it. The
  raw model answer is parsed inside the adapter and never leaves it.
- Readings accumulate keyed by the photograph (`kiseki screens`,
  resumable, in the shape of ADR-0019): refusals are recorded and not
  asked again; an unavailable model pauses the run. The table is
  additive to schema version 3.

## Consequences

- Search (v0.4) can only ever surface categories and labels; what was
  never stored cannot leak.
- Turning readings into SCREENSHOT interest evidence is the next
  step, in the shape of ADR-0021.
