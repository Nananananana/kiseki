"""Theming: meaning gathers the labels, co-occurrence vouches for the stretch."""

from collections.abc import Sequence
from datetime import datetime, timezone

from kiseki.adapters.fake.models import FakeLanguageModel
from kiseki.adapters.fake.subjects import FakeSubjectRepository
from kiseki.adapters.fake.themes import FakeThemeSetRepository
from kiseki.application.theming import (
    ThemeRunReport,
    cluster_labels,
    parse_theme_name,
    run_theming,
)
from kiseki.domain.caption.caption import CaptionKey
from kiseki.domain.caption.subjects import SubjectExtraction
from kiseki.domain.photo.observation import PhotoId

NOW = datetime(2026, 6, 1, 12, tzinfo=timezone.utc)

# Hand-built unit vectors. tree/landscape are close (cos 0.96);
# car sits in between (cos ~0.70 to their centroid): above the mid
# threshold, below the high one, so only co-occurrence lets it in.
TREE = (1.0, 0.0)
LANDSCAPE = (0.96, 0.28)
CAR = (0.6, 0.8)
DOOR = (0.0, 1.0)


class StubEmbedder:
    def __init__(self, vectors: dict[str, tuple[float, ...]]) -> None:
        self._vectors = vectors
        self.calls = 0

    def embed(self, texts: Sequence[str]) -> list[tuple[float, ...]]:
        self.calls += 1
        return [self._vectors[text] for text in texts]

    @property
    def dimensions(self) -> int:
        return 2


def _stays(*keys: str) -> frozenset[str]:
    return frozenset(keys)


class TestClusterLabels:
    def test_high_similarity_joins_on_meaning_alone(self) -> None:
        clusters = cluster_labels(
            {"tree": TREE, "landscape": LANDSCAPE},
            {"tree": _stays("s1", "s2", "s3"), "landscape": _stays("s9")},
        )
        assert clusters == (("tree", "landscape"),)

    def test_middling_similarity_needs_co_occurrence(self) -> None:
        vectors = {"tree": TREE, "landscape": LANDSCAPE, "car": CAR}
        together = cluster_labels(
            vectors,
            {
                "tree": _stays("s1", "s2", "s3", "s4"),
                "landscape": _stays("s1", "s2", "s3"),
                "car": _stays("s1", "s2"),
            },
        )
        assert together == (("tree", "landscape", "car"),)

        apart = cluster_labels(
            vectors,
            {
                "tree": _stays("s1", "s2", "s3", "s4"),
                "landscape": _stays("s1", "s2", "s3"),
                "car": _stays("x1", "x2"),
            },
        )
        assert apart == (("tree", "landscape"),)

    def test_the_unrelated_stay_out(self) -> None:
        clusters = cluster_labels(
            {"tree": TREE, "landscape": LANDSCAPE, "door": DOOR},
            {
                "tree": _stays("s1", "s2", "s3"),
                "landscape": _stays("s1", "s2"),
                "door": _stays("s1"),
            },
        )
        assert clusters == (("tree", "landscape"),)

    def test_singletons_are_not_themes(self) -> None:
        clusters = cluster_labels(
            {"tree": TREE, "door": DOOR},
            {"tree": _stays("s1"), "door": _stays("s2")},
        )
        assert clusters == ()


class TestParseThemeName:
    def test_reads_a_json_string(self) -> None:
        assert parse_theme_name('"outdoor"') == "outdoor"

    def test_reads_a_fenced_answer(self) -> None:
        assert parse_theme_name('```json\n"city walk"\n```') == "city walk"

    def test_lowercases_a_bare_word(self) -> None:
        assert parse_theme_name("Outdoor") == "outdoor"

    def test_a_sentence_is_not_a_name(self) -> None:
        assert parse_theme_name("these labels are all about the outdoors") is None

    def test_an_empty_answer_is_not_a_name(self) -> None:
        assert parse_theme_name("   ") is None


def _reading(key_id: str, *labels: str) -> SubjectExtraction:
    return SubjectExtraction(
        key=CaptionKey.of([PhotoId(key_id)]),
        labels=labels,
        model="lm",
        created_at=NOW,
    )


class World:
    def __init__(self, *readings: SubjectExtraction) -> None:
        self.subjects = FakeSubjectRepository()
        for reading in readings:
            self.subjects.save(reading)
        self.themes = FakeThemeSetRepository()
        self.embedder = StubEmbedder(
            {"tree": TREE, "landscape": LANDSCAPE, "car": CAR, "door": DOOR}
        )

    def run(self, language_model: object) -> ThemeRunReport:
        return run_theming(
            subjects=self.subjects,
            themes=self.themes,
            embedder=self.embedder,  # type: ignore[arg-type]
            language_model=language_model,  # type: ignore[arg-type]
            now=lambda: NOW,
        )


def _world() -> World:
    # tree and landscape share stays; car rides along with them; door
    # is off on its own. Four labels, the minimum for a run.
    return World(
        _reading("sha256:s1", "tree", "landscape", "car"),
        _reading("sha256:s2", "tree", "landscape", "car"),
        _reading("sha256:s3", "tree", "landscape"),
        _reading("sha256:s4", "tree", "door"),
    )


class TestThemingRun:
    def test_too_few_labels_touch_no_model(self) -> None:
        world = World(_reading("sha256:s1", "tree", "door"))
        report = world.run(FakeLanguageModel(answer=lambda system, prompt: '"outdoor"'))
        assert report == ThemeRunReport(0, 2, False, 0)
        assert world.embedder.calls == 0

    def test_gathers_names_and_saves(self) -> None:
        world = _world()
        report = world.run(FakeLanguageModel(answer=lambda system, prompt: '"outdoor"'))
        assert report.themes_made == 1
        assert report.labels_considered == 4
        saved = world.themes.latest()
        assert saved is not None
        assert saved.themes[0].name == "outdoor"
        assert saved.themes[0].members == ("tree", "landscape", "car")
        assert saved.model == "fake-language-model"

    def test_a_second_run_is_already_done(self) -> None:
        world = _world()
        model = FakeLanguageModel(answer=lambda system, prompt: '"outdoor"')
        world.run(model)
        report = world.run(model)
        assert report.already_done
        assert world.embedder.calls == 1

    def test_an_unparseable_name_falls_back_to_the_busiest_member(self) -> None:
        world = _world()
        report = world.run(FakeLanguageModel(answer=lambda system, prompt: "no name here at all"))
        assert report.fallback_named == 1
        saved = world.themes.latest()
        assert saved is not None
        assert saved.themes[0].name == "tree"

    def test_an_unavailable_namer_does_not_stop_the_run(self) -> None:
        world = _world()
        failing = FakeLanguageModel(fail_on=lambda prompt: True)
        report = world.run(failing)
        assert report.themes_made == 1
        assert report.fallback_named == 1
        assert world.themes.latest() is not None
