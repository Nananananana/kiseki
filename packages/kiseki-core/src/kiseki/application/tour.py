"""A guided run through everything the library can say.

`kiseki demo` shows the derivations at a glance. `kiseki demo --full`
walks the whole surface: every command that answers without a model, in
the order a reader would meet them, each with a line saying what it
answers. Run it and you have both a tour of the library and a check
that all of it still works together -- which turn out to be the same
artefact.

Commands that call a model are named and described rather than run. A
tour that took twenty minutes and needed Ollama would not be run, and
one that is not run checks nothing.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Stop:
    """One command on the tour, and what it answers."""

    name: str
    says: str
    runs: bool = True


TOUR: tuple[Stop, ...] = (
    Stop("paths", "where everything is kept, and nothing is guessed"),
    Stop("report", "how much there is, and the rhythm of it"),
    Stop("places", "each place the journeys know, in its own numbers"),
    Stop("trips", "the nights away, as journeys rather than as separate days"),
    Stop("drift", "what moved with what, and each against its own past"),
    Stop("profile", "what the evidence says the owner is interested in"),
    Stop("trend", "what moved between two kept readings"),
    Stop("lifecycle", "where each topic stands: new, growing, dormant, stable"),
    Stop("insights", "the findings, each with the evidence behind it"),
    Stop("discover", "what is worth a look, ranked by novelty and weight"),
    Stop("compare", "what changed between two readings, with the arithmetic"),
    Stop("suggest", "somewhere to go back to, and somewhere to go"),
    Stop("corrections", "the owner's word against a reading, appended and applied"),
    Stop("privacy", "what is stored, in counts, and what never is"),
    Stop("map", "the same journeys, in a format QGIS or pandas reads"),
    Stop("algorithms", "which algorithm decides a stay, and what else is available"),
    Stop("cost", "what the model work still waiting will take, before doing it"),
    Stop("settings", "every threshold in force, and where each value came from"),
    Stop("llm", "where the model is, and whether it is allowed to be there"),
    Stop("retention", "what a decade should look like, as rules that are off"),
    Stop("reread", "what a newer prompt version left behind"),
    Stop("retry", "refusals the environment caused, not the model"),
    Stop("doctor", "what is wrong, by category, before it costs anything"),
    Stop("view", "one self-contained page, with no script and no network"),
    Stop("caption", "describes each stay with a local model", runs=False),
    Stop("singles", "describes the photographs outside every stay", runs=False),
    Stop("screens", "reads screenshots into a category and labels, never text", runs=False),
    Stop("subjects", "names what the captions were about", runs=False),
    Stop("themes", "gathers the labels into themes by similarity", runs=False),
    Stop("index", "indexes the readings for search, embedding each", runs=False),
    Stop("ask", "answers a question from evidence, and cites it", runs=False),
    Stop("tell", "tells the story over a closed fact list, with its doubts", runs=False),
    Stop("serve", "answers the same shapes over local HTTP, loopback only", runs=False),
    Stop("export", "the most that ever leaves, and in what shape", runs=False),
    Stop("forget", "removes photographs and everything that spoke about them", runs=False),
    Stop("activity", "reads days of movement from an ActivityRecord document", runs=False),
    Stop("notes", "reads what a note producer wrote, as categories and labels", runs=False),
    Stop("web", "reads what a web producer wrote, as categories and labels", runs=False),
    Stop("ingest", "takes in a PhotoRecord document", runs=False),
    Stop("build", "recomputes stops, outings and anchors", runs=False),
    Stop("refresh", "the weekly routine, in one idempotent command", runs=False),
    Stop("correct", "records the owner's disagreement with a reading", runs=False),
    Stop("demo", "this", runs=False),
)

MODEL_STAGES = tuple(stop.name for stop in TOUR if not stop.runs)
"""Named once, so a count in a summary cannot drift from the list."""

WALKED = tuple(stop for stop in TOUR if stop.runs)
