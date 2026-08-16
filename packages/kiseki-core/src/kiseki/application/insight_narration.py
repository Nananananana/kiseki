"""Narrates the findings, without adding any.

The derivation (ADR-0043) makes the findings; this module only puts
words on them. Each finding becomes one numbered fact, the model is
told to cite and to add nothing, and a place topic without a name is
skipped entirely -- a coordinate is not a story (the ADR-0041 rule,
applied to insights). With no facts there is no model call.
"""

from __future__ import annotations

from collections.abc import Mapping

from kiseki.domain.insight import InsightKind, InsightReport
from kiseki.ports.models import LanguageModel

LANGUAGE_NAMES = {"ja": "Japanese", "en": "English"}

INSIGHT_SYSTEM = (
    "You describe findings about the person's own photo history,"
    " from a closed list of numbered facts. Use only these facts,"
    " cite the fact behind each claim like [F2], never mention any"
    " coordinates, and add nothing the facts do not say. Answer in"
    " {language}, in one short paragraph."
)

INSIGHT_FACT_CAP = 8
"""Enough findings for one story; the full list is one command away."""

KIND_PHRASES = {
    InsightKind.NEW: "appeared for the first time",
    InsightKind.RETURNED: "came back after an absence",
    InsightKind.RISING: "grew",
    InsightKind.DECLINING: "shrank",
    InsightKind.DORMANT: "went quiet",
    InsightKind.ENDURING: "stayed strong throughout",
}

PLACE_PREFIX = "place:"


def insight_facts(report: InsightReport, names: Mapping[str, str] | None = None) -> tuple[str, ...]:
    """One fact per finding, named places only, the most novel first."""
    resolved = names or {}
    facts: list[str] = []
    for item in report.insights:
        if item.topic.startswith(PLACE_PREFIX) and item.topic not in resolved:
            continue
        label = resolved.get(item.topic, item.topic)
        period = ""
        if item.first_seen is not None and item.last_seen is not None:
            period = f", seen {item.first_seen:%Y-%m} to {item.last_seen:%Y-%m}"
        facts.append(
            f"Interest '{label}' {KIND_PHRASES[item.kind]}"
            f" (magnitude {item.magnitude:.2f}, confidence"
            f" {item.confidence:.2f}{period})."
        )
        if len(facts) == INSIGHT_FACT_CAP:
            break
    return tuple(facts)


def tell_insights(
    report: InsightReport,
    language_model: LanguageModel,
    language: str = "ja",
    names: Mapping[str, str] | None = None,
) -> str:
    """One narration of the findings. Model errors propagate."""
    facts = insight_facts(report, names)
    if not facts:
        return ""
    system = INSIGHT_SYSTEM.format(language=LANGUAGE_NAMES.get(language, "English"))
    prompt = "\n".join(f"[F{index}] {fact}" for index, fact in enumerate(facts, start=1))
    return language_model.complete(system, [prompt])[0].text
