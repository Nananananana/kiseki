"""The narrative stage: say what the profile says, in prose.

The model is handed a closed, numbered list of facts and asked for
short prose that cites them. It chooses the words; it does not choose
the facts. Anything worth saying that is not in the list is not said.

Subjects speak, coordinates stay silent: an unnamed place interest is
not given to the model, because a coordinate pair is not something a
person recognises themselves in. A named place (ADR-0040) does speak,
and may quote the single captions photographed beside it (ADR-0041).
Nothing is stored -- a narration costs seconds and can always be
regenerated from the profile it reads. See ADR-0022.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime

from kiseki.application.pipeline import Report
from kiseki.domain.caption.single import SingleCaption
from kiseki.domain.interests import Interest, Profile
from kiseki.domain.photo.observation import PhotoId, PhotoObservation
from kiseki.domain.shared.geo import Distance, GeoPoint
from kiseki.ports.models import LanguageModel

MAX_SUBJECT_FACTS = 8
"""Enough subjects for a portrait, few enough that each can be cited.
The full profile always remains one command away."""

MAX_PLACE_FACTS = 3
"""Named places worth a sentence each; the strongest first."""

NEARBY_WITHIN = Distance(500)
"""A single photographed this close to the place belongs to it."""

MAX_NEARBY_QUOTES = 2
QUOTE_LENGTH = 90

PLACE_PREFIX = "place:"

LANGUAGE_NAMES = {"ja": "Japanese", "en": "English"}

NARRATIVE_SYSTEM = (
    "You write a short profile of a person, addressed to them as"
    " 'you', from a closed list of numbered facts. Use only these"
    " facts. Do not invent details, do not generalise beyond what a"
    " fact states, and do not mention any coordinates. After each"
    " claim, cite the fact it rests on, like [F3]. Write two to four"
    " short paragraphs in {language}. Warm and concrete; no flattery."
)


def narrative_facts(
    profile: Profile,
    report: Report,
    names: Mapping[str, str] | None = None,
    singles: Sequence[SingleCaption] = (),
    photos: Sequence[PhotoObservation] = (),
) -> tuple[str, ...]:
    """The closed list: measures, then named places, then subjects."""
    facts = [
        f"{report.photographs} photographs and {len(report.outings)} outings were measured.",
        f"{len(report.places.places)} distinct places were visited;"
        f" {report.places.one_time_rate:.0%} were never returned to.",
        f"{report.rhythm.weekend_share:.0%} of outings happened on weekends.",
    ]
    facts.extend(_place_facts(profile, names or {}, singles, photos))
    for interest in _top_subjects(profile):
        facts.append(
            f"Subject '{interest.topic}' was seen at {len(interest.evidence)} recorded"
            f" sightings between {interest.first_seen:%Y-%m} and {interest.last_seen:%Y-%m}"
            f" (score {interest.score:.2f}, confidence {interest.confidence:.2f})."
        )
    return tuple(facts)


def build_prompt(
    profile: Profile,
    report: Report,
    language: str,
    names: Mapping[str, str] | None = None,
    singles: Sequence[SingleCaption] = (),
    photos: Sequence[PhotoObservation] = (),
) -> tuple[str, str]:
    """The system instruction and the numbered facts, deterministically."""
    name = LANGUAGE_NAMES.get(language, "English")
    system = NARRATIVE_SYSTEM.format(language=name)
    facts = narrative_facts(profile, report, names=names, singles=singles, photos=photos)
    numbered = "\n".join(f"[F{index}] {fact}" for index, fact in enumerate(facts, start=1))
    return system, numbered


def tell(
    profile: Profile,
    report: Report,
    language_model: LanguageModel,
    language: str = "ja",
    names: Mapping[str, str] | None = None,
    singles: Sequence[SingleCaption] = (),
    photos: Sequence[PhotoObservation] = (),
) -> str:
    """One narration of the profile. Model errors propagate to the caller."""
    system, prompt = build_prompt(
        profile, report, language, names=names, singles=singles, photos=photos
    )
    return language_model.complete(system, [prompt])[0].text


def _top_subjects(profile: Profile) -> tuple[Interest, ...]:
    subjects = [
        interest for interest in profile.interests if not interest.topic.startswith("place:")
    ]
    ranked = sorted(
        subjects, key=lambda interest: (-(interest.score * interest.confidence), interest.topic)
    )
    return tuple(ranked[:MAX_SUBJECT_FACTS])


def _place_facts(
    profile: Profile,
    names: Mapping[str, str],
    singles: Sequence[SingleCaption],
    photos: Sequence[PhotoObservation],
) -> list[str]:
    """A fact per top named place, each with its nearby single quotes."""
    if not names:
        return []
    by_id = {photo.photo_id: photo for photo in photos}
    facts: list[str] = []
    for interest in _top_places(profile, names):
        label = names[interest.topic]
        facts.append(
            f"Place '{label}' was visited: {len(interest.evidence)} recorded"
            f" sightings between {interest.first_seen:%Y-%m} and"
            f" {interest.last_seen:%Y-%m} (score {interest.score:.2f})."
        )
        quotes = _nearby_quotes(interest.topic, singles, by_id)
        if quotes:
            facts.append(f"Near {label} you photographed: " + " / ".join(quotes))
    return facts


def _top_places(profile: Profile, names: Mapping[str, str]) -> tuple[Interest, ...]:
    places = [interest for interest in profile.interests if interest.topic in names]
    ranked = sorted(
        places, key=lambda interest: (-(interest.score * interest.confidence), interest.topic)
    )
    return tuple(ranked[:MAX_PLACE_FACTS])


def _nearby_quotes(
    topic: str,
    singles: Sequence[SingleCaption],
    by_id: Mapping[PhotoId, PhotoObservation],
) -> list[str]:
    point = _place_point(topic)
    if point is None:
        return []
    found: list[tuple[float, datetime, str]] = []
    for single in singles:
        if not single.answered:
            continue
        photo = by_id.get(single.photo_id)
        if photo is None or photo.location is None:
            continue
        meters = point.distance_to(photo.location).meters
        if meters <= NEARBY_WITHIN.meters:
            found.append((meters, photo.captured_at, _clip(single.text)))
    found.sort()
    return [text for _meters, _at, text in found[:MAX_NEARBY_QUOTES]]


def _place_point(topic: str) -> GeoPoint | None:
    if not topic.startswith(PLACE_PREFIX):
        return None
    try:
        latitude_text, longitude_text = topic[len(PLACE_PREFIX) :].split(",")
        return GeoPoint(float(latitude_text), float(longitude_text))
    except ValueError:
        return None


def _clip(text: str) -> str:
    flattened = " ".join(text.split())
    return flattened if len(flattened) <= QUOTE_LENGTH else flattened[:QUOTE_LENGTH] + "..."
