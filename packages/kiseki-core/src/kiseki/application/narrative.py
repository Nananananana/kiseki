"""The narrative stage: say what the profile says, in prose.

The model is handed a closed, numbered list of facts and asked for
short prose that cites them. It chooses the words; it does not choose
the facts. Anything worth saying that is not in the list is not said.

Subjects speak, coordinates stay silent: place interests are not given
to the model, because a coordinate pair is not something a person
recognises themselves in. Nothing is stored -- a narration costs
seconds and can always be regenerated from the profile it reads.
See ADR-0022.
"""

from __future__ import annotations

from kiseki.application.pipeline import Report
from kiseki.domain.interests import Interest, Profile
from kiseki.ports.models import LanguageModel

MAX_SUBJECT_FACTS = 8
"""Enough subjects for a portrait, few enough that each can be cited.
The full profile always remains one command away."""

LANGUAGE_NAMES = {"ja": "Japanese", "en": "English"}

NARRATIVE_SYSTEM = (
    "You write a short profile of a person, addressed to them as"
    " 'you', from a closed list of numbered facts. Use only these"
    " facts. Do not invent details, do not generalise beyond what a"
    " fact states, and do not mention any coordinates. After each"
    " claim, cite the fact it rests on, like [F3]. Write two to four"
    " short paragraphs in {language}. Warm and concrete; no flattery."
)


def narrative_facts(profile: Profile, report: Report) -> tuple[str, ...]:
    """The closed list: measures first, then the strongest subjects."""
    facts = [
        f"{report.photographs} photographs and {len(report.outings)} outings were measured.",
        f"{len(report.places.places)} distinct places were visited;"
        f" {report.places.one_time_rate:.0%} were never returned to.",
        f"{report.rhythm.weekend_share:.0%} of outings happened on weekends.",
    ]
    for interest in _top_subjects(profile):
        facts.append(
            f"Subject '{interest.topic}' was seen at {len(interest.evidence)} recorded"
            f" sightings between {interest.first_seen:%Y-%m} and {interest.last_seen:%Y-%m}"
            f" (score {interest.score:.2f}, confidence {interest.confidence:.2f})."
        )
    return tuple(facts)


def build_prompt(profile: Profile, report: Report, language: str) -> tuple[str, str]:
    """The system instruction and the numbered facts, deterministically."""
    name = LANGUAGE_NAMES.get(language, "English")
    system = NARRATIVE_SYSTEM.format(language=name)
    numbered = "\n".join(
        f"[F{index}] {fact}" for index, fact in enumerate(narrative_facts(profile, report), start=1)
    )
    return system, numbered


def tell(
    profile: Profile,
    report: Report,
    language_model: LanguageModel,
    language: str = "ja",
) -> str:
    """One narration of the profile. Model errors propagate to the caller."""
    system, prompt = build_prompt(profile, report, language)
    return language_model.complete(system, [prompt])[0].text


def _top_subjects(profile: Profile) -> tuple[Interest, ...]:
    subjects = [
        interest for interest in profile.interests if not interest.topic.startswith("place:")
    ]
    ranked = sorted(
        subjects, key=lambda interest: (-(interest.score * interest.confidence), interest.topic)
    )
    return tuple(ranked[:MAX_SUBJECT_FACTS])
