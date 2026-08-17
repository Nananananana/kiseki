"""The golden retrieval dataset: model-free, deterministic, in CI.

Adding retrieval machinery without measuring retrieval is not
allowed (proposals/0006). Each case seeds an index, asks, and
states which documents must (and must not) come back.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from kiseki.adapters.fake.search import FakeSearchIndex
from kiseki.application.retrieval import retrieve
from kiseki.ports.models import ModelUnavailableError
from kiseki.ports.search import SearchDocument

GOLDEN = Path(__file__).resolve().parents[2] / "golden" / "retrieval.json"
CASES = json.loads(GOLDEN.read_text(encoding="utf-8"))["cases"]
WHEN = datetime(2026, 6, 1, 12, tzinfo=UTC)


class WordsOnlyEmbedder:
    """Keeps the golden runs on the words channel: deterministic."""

    def embed(self, texts):
        raise ModelUnavailableError("golden runs are words-only")

    @property
    def dimensions(self):
        return 2


def _observed(text: str | None) -> datetime:
    if text is None:
        return WHEN
    return datetime.fromisoformat(text).replace(tzinfo=UTC)


@pytest.mark.parametrize("case", CASES, ids=[case["name"] for case in CASES])
def test_the_golden_cases_hold(case):
    index = FakeSearchIndex()
    for entry in case["documents"]:
        index.put_document(
            SearchDocument(entry["key"], "stay", entry["text"], _observed(entry.get("observed")))
        )
    fill = case.get("fill")
    if fill:
        for number in range(fill["count"]):
            index.put_document(
                SearchDocument(f"{fill['prefix']}{number:02d}", "stay", fill["text"], WHEN)
            )
    since_text = case.get("since")
    allowed = case.get("allowed")
    results = retrieve(
        index,
        WordsOnlyEmbedder(),
        "m",
        case["query"],
        since=_observed(since_text) if since_text else None,
        allowed=frozenset(allowed) if allowed is not None else None,
    )
    keys = [item.document.doc_key for item in results]
    for expected in case["expect"]:
        assert expected in keys, f"{case['name']}: {expected} missing from {keys}"
    for forbidden in case.get("forbid", ()):
        assert forbidden not in keys, f"{case['name']}: {forbidden} leaked into {keys}"
    if "expect_total" in case:
        assert len(keys) == case["expect_total"], f"{case['name']}: got {keys}"
