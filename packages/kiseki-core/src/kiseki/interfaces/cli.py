"""Command line interface.

Composition happens here and nowhere else: this is the only place that decides
SQLite is the storage and where the database sits. Everything below it is given
what it needs.
"""

import argparse
import json
import sqlite3
import sys
from collections.abc import Callable, Sequence
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from kiseki.adapters.filesystem.gazetteer import FileGazetteer
from kiseki.adapters.filesystem.thumbnails import FilesystemThumbnailSource
from kiseki.adapters.ollama.models import (
    DEFAULT_EMBEDDING_MODEL,
    OllamaImageCaptioner,
    OllamaLanguageModel,
    OllamaTextEmbedder,
)
from kiseki.adapters.ollama.screens import OllamaScreenshotReader
from kiseki.adapters.sqlite.search import SqliteSearchIndex
from kiseki.adapters.sqlite.store import (
    SCHEMA_VERSION,
    SqliteAnchorRepository,
    SqliteCaptionRepository,
    SqliteCorrectionRepository,
    SqliteOutingRepository,
    SqlitePhotoRepository,
    SqliteProfileRepository,
    SqliteScreenshotReadingRepository,
    SqliteSingleCaptionRepository,
    SqliteSubjectRepository,
    SqliteThemeSetRepository,
    clear_outdated,
    clear_recoverable,
    connect,
    count_outdated,
    count_recoverable,
)
from kiseki.application.answer_validation import validate_answer
from kiseki.application.asking import Answer, ask
from kiseki.application.captioning import CAPTION_PROMPT_VERSION, run_captioning
from kiseki.application.exporting import interest_export
from kiseki.application.forgetting import forget, plan_forget
from kiseki.application.indexing import run_indexing
from kiseki.application.insight_narration import tell_insights
from kiseki.application.narration_validation import validate_narration
from kiseki.application.narrative import narrative_facts, tell
from kiseki.application.pipeline import Pipeline, Report
from kiseki.application.retention import (
    RetentionPolicy,
    apply_retention,
    plan_retention,
)
from kiseki.application.screen_reading import SCREEN_PROMPT_VERSION, run_screen_reading
from kiseki.application.single_captioning import (
    SINGLE_CAPTION_PROMPT_VERSION,
    run_single_captioning,
)
from kiseki.application.sourcing import read_from
from kiseki.application.subject_extraction import SUBJECT_PROMPT_VERSION, run_subject_extraction
from kiseki.application.theming import THEME_PROMPT_VERSION, run_theming
from kiseki.config.paths import StoragePaths, resolve_paths
from kiseki.domain.activity.daily import DailyActivity
from kiseki.domain.comparison import ChangeKind
from kiseki.domain.correction import Correction, CorrectionVerdict, active_exclusions
from kiseki.domain.interests import Profile
from kiseki.domain.photo.observation import PhotoId, PhotoObservation
from kiseki.domain.services.cross_timeline import (
    ALIGNMENT_STRONG,
    compare_timelines,
    derive_drift,
    monthly_counts,
)
from kiseki.domain.services.day_trips import (
    REGULAR_SPAN_DAYS,
    REGULAR_VISITS,
    derive_day_trips,
    derive_reach,
    spread_out,
)
from kiseki.domain.services.mixing import derive_mixed
from kiseki.domain.services.place_reading import (
    PlaceProfile,
    derive_place_profiles,
)
from kiseki.domain.services.suggesting import SuggestionKind, derive_suggestions
from kiseki.domain.services.trend_derivation import MIN_TREND_SPAN_DAYS
from kiseki.domain.services.trips import derive_trips
from kiseki.domain.shared.geo import Distance, GeoPoint
from kiseki.domain.trends import TrendReport
from kiseki.interfaces.api import DEFAULT_HOST, DEFAULT_PORT, serve
from kiseki.interfaces.naming import place_names
from kiseki.interfaces.payloads import (
    BLURRED_BY_DEFAULT,
    NEVER_STORED,
    answer_payload,
    comparison_payload,
    discovery_payload,
    insights_payload,
    lifecycle_payload,
    privacy_payload,
    profile_payload,
    report_payload,
    trend_payload,
)
from kiseki.interfaces.view import render_view
from kiseki.ports.models import ModelRefusedError, ModelUnavailableError

EXIT_OK = 0
EXIT_BAD_INPUT = 2
RULE = "-" * 70
DOTENV = Path(".env")


def _read_records(path: Path) -> list[dict[str, Any]]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or "records" not in document:
        raise ValueError("not a PhotoRecord document: no 'records' key")
    records = document["records"]
    if not isinstance(records, list):
        raise ValueError("not a PhotoRecord document: 'records' is not a list")
    return records


def _to_observations(records: list[dict[str, Any]]) -> list[PhotoObservation]:
    observations = []
    for record in records:
        consent = record.get("consent") or {}
        if consent.get("use_for_story") is False:
            continue
        place = record.get("location")
        observations.append(
            PhotoObservation(
                PhotoId(record["id"]),
                datetime.fromisoformat(record["captured_at"]),
                GeoPoint(place["lat"], place["lon"]) if place else None,
                thumbnail_ref=record.get("thumbnail_ref"),
                content_kind=record.get("content_kind"),
                use_for_preference=consent.get("use_for_preference"),
            )
        )
    return observations


def _paths_for(args: argparse.Namespace) -> StoragePaths:
    return resolve_paths({"data_root": args.data_root or ""}, dotenv=DOTENV)


def _pipeline_from(db_path: Path) -> Pipeline:
    connection = connect(db_path)
    return Pipeline(
        SqlitePhotoRepository(connection),
        SqliteOutingRepository(connection),
        SqliteAnchorRepository(connection),
        profiles=SqliteProfileRepository(connection),
        captions=SqliteCaptionRepository(connection),
        subjects=SqliteSubjectRepository(connection),
        themes=SqliteThemeSetRepository(connection),
        singles=SqliteSingleCaptionRepository(connection),
        screens=SqliteScreenshotReadingRepository(connection),
        corrections=SqliteCorrectionRepository(connection),
    )


def _pipeline_for(args: argparse.Namespace) -> Pipeline:
    return _pipeline_from(_paths_for(args).db_path)


def _command_paths(args: argparse.Namespace) -> int:
    for name, value in vars(_paths_for(args)).items():
        print(f"  {name:14} {value}")
    return EXIT_OK


def _command_ingest(args: argparse.Namespace) -> int:
    try:
        records = _read_records(args.records)
    except OSError as error:
        print(f"cannot read {args.records}: {error}", file=sys.stderr)
        return EXIT_BAD_INPUT
    except (json.JSONDecodeError, ValueError) as error:
        print(f"{args.records}: {error}", file=sys.stderr)
        return EXIT_BAD_INPUT

    stored = _pipeline_for(args).ingest(_to_observations(records))
    print(f"{stored} photograph(s) taken in")
    return EXIT_OK


def _to_days(records: list[dict[str, Any]]) -> list[DailyActivity]:
    """Turn ActivityRecord v1 documents into days.

    Unknown fields are ignored rather than refused: a producer may carry
    its own notes, and the contract does not argue with them
    (docs/activity-record.md).
    """
    from datetime import date as _date

    return [
        DailyActivity(
            day=_date.fromisoformat(str(record["day"])),
            steps=int(record["steps"]),
            distance_m=(
                float(record["distance_m"]) if record.get("distance_m") is not None else None
            ),
            floors=(int(record["floors"]) if record.get("floors") is not None else None),
        )
        for record in records
    ]


def _command_activity(args: argparse.Namespace) -> int:
    """Read days of movement from an ActivityRecord v1 document.

    A second contract beside PhotoRecord v1, independent of it: a library
    with no photographs can hold activity, and a library with no activity
    behaves exactly as it did before (ADR-0065).
    """
    from kiseki.adapters.sqlite.store import SqliteDailyActivityRepository

    try:
        document = json.loads(Path(args.records).read_text(encoding="utf-8"))
        if not isinstance(document, list):
            raise ValueError("an ActivityRecord document is a list of days")
        days = _to_days(document)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"the records could not be read: {error}", file=sys.stderr)
        return EXIT_BAD_INPUT
    connection = connect(_paths_for(args).db_path)
    repository = SqliteDailyActivityRepository(connection)
    repository.save_all(days)
    print(RULE)
    print(f"  days read     {len(days)}")
    print(f"  days held     {repository.count()}")
    return EXIT_OK


def _command_build(args: argparse.Namespace) -> int:
    result = _pipeline_for(args).rebuild()
    print(RULE)
    print(f"  photographs   {result.photographs}")
    print(f"  stops         {result.stops}")
    print(f"  outings       {result.outings}")
    print(f"  anchors       {result.anchors}")
    print(f"  in transit    {result.in_transit}")
    print(f"  unlocated     {result.unlocated}")
    return EXIT_OK


def _print_report(report: Report) -> None:
    print(RULE)
    print(f"  photographs   {report.photographs}")
    print(f"  outings       {len(report.outings)}")

    if report.anchors:
        print("\n  places returned to")
        for anchor in report.anchors:
            print(
                f"    ({anchor.area.center.latitude:.4f},"
                f" {anchor.area.center.longitude:.4f})"
                f"  {anchor.visit_days:>4} days"
                f"  night {anchor.night_share:>4.0%}"
                f"  weekday {anchor.weekday_share:>4.0%}"
                f"  daytime {anchor.daytime_share:>4.0%}"
            )

    if report.places.places:
        print(f"\n  distinct places    {len(report.places.places)}")
        print(f"  never returned to  {report.places.one_time_rate:.0%}")

    if report.habits is not None:
        print(f"\n  distance covered   median {report.habits.travel_km.median:.1f} km")
        print(f"  time out           median {report.habits.duration_hours.median:.1f} h")
        print(f"  places per outing  median {report.habits.stops_per_outing.median:.1f}")
        print(f"\n  weekend share      {report.rhythm.weekend_share:.0%}")


def _command_report(args: argparse.Namespace) -> int:
    report = _pipeline_for(args).report()
    if args.json:
        print(json.dumps(report_payload(report), indent=2))
    else:
        _print_report(report)
    return EXIT_OK


def _print_profile(profile: Profile, names: dict[str, str]) -> None:
    print(RULE)
    print(f"  interests     {len(profile.interests)}")

    if profile.interests:
        print("\n  read as interests")
        for interest in profile.ranked():
            print(
                f"    {names.get(interest.topic, interest.topic):<32}"
                f"  score {interest.score:>5.2f}"
                f"  confidence {interest.confidence:>5.2f}"
                f"  evidence {len(interest.evidence)}"
            )


def _command_profile(args: argparse.Namespace) -> int:
    paths = _paths_for(args)
    profile = _pipeline_from(paths.db_path).profile()
    if args.json:
        print(json.dumps(profile_payload(profile), indent=2))
    else:
        gazetteer = FileGazetteer(paths.gazetteer_path)
        names = place_names((interest.topic for interest in profile.interests), gazetteer)
        _print_profile(profile, names)
    return EXIT_OK


def _command_caption(args: argparse.Namespace) -> int:
    paths = _paths_for(args)
    connection = connect(paths.db_path)
    report = run_captioning(
        outings=SqliteOutingRepository(connection),
        photos=SqlitePhotoRepository(connection),
        captions=SqliteCaptionRepository(connection),
        thumbnails=FilesystemThumbnailSource(paths.thumbs_dir),
        captioner=OllamaImageCaptioner(),
        limit=args.limit,
    )
    print(RULE)
    print(f"  captioned     {report.captioned}")
    print(f"  already done  {report.already_captioned}")
    print(f"  refused       {report.refused}")
    print(f"  unreferenced  {report.unreferenced}")
    print(f"  withheld      {report.withheld}")
    if report.paused:
        print("\n  paused: the model was unavailable; run again to resume")
    return EXIT_OK


def _command_subjects(args: argparse.Namespace) -> int:
    connection = connect(_paths_for(args).db_path)
    report = run_subject_extraction(
        captions=SqliteCaptionRepository(connection),
        subjects=SqliteSubjectRepository(connection),
        language_model=OllamaLanguageModel(),
        singles=SqliteSingleCaptionRepository(connection),
        limit=args.limit,
    )
    print(RULE)
    print(f"  extracted     {report.extracted}")
    print(f"  already done  {report.already_extracted}")
    print(f"  refused       {report.refused}")
    if report.paused:
        print("\n  paused: the model was unavailable; run again to resume")
    return EXIT_OK


def narration_checks(story: str, facts: Sequence[str]) -> None:
    """Print what the narration check found, if it found anything.

    The story is printed as the model wrote it, and the doubts are
    printed beneath it: the reader sees both at once (ADR-0057).
    """
    for defect in validate_narration(story, facts):
        print(f"  check         {defect.value}")


def _command_tell(args: argparse.Namespace) -> int:
    paths = _paths_for(args)
    connection = connect(paths.db_path)
    photos = SqlitePhotoRepository(connection)
    singles = SqliteSingleCaptionRepository(connection)
    pipeline = _pipeline_from(paths.db_path)
    report = pipeline.report()
    profile = pipeline.profile()
    gazetteer = FileGazetteer(paths.gazetteer_path)
    names = place_names((interest.topic for interest in profile.interests), gazetteer)
    try:
        story = tell(
            profile,
            report,
            OllamaLanguageModel(),
            language=args.lang,
            names=names,
            singles=singles.all(),
            photos=photos.all(),
        )
    except (ModelRefusedError, ModelUnavailableError) as error:
        print(f"the model could not answer: {error}", file=sys.stderr)
        return EXIT_BAD_INPUT
    print(story)
    narration_checks(
        story,
        narrative_facts(
            profile,
            report,
            names=names,
            singles=singles.all(),
            photos=photos.all(),
        ),
    )
    return EXIT_OK


def _command_themes(args: argparse.Namespace) -> int:
    connection = connect(_paths_for(args).db_path)
    try:
        report = run_theming(
            subjects=SqliteSubjectRepository(connection),
            themes=SqliteThemeSetRepository(connection),
            embedder=OllamaTextEmbedder(),
            language_model=OllamaLanguageModel(),
        )
    except (ModelRefusedError, ModelUnavailableError) as error:
        print(f"the model could not answer: {error}", file=sys.stderr)
        return EXIT_BAD_INPUT
    print(RULE)
    print(f"  themes          {report.themes_made}")
    print(f"  labels          {report.labels_considered}")
    if report.already_done:
        print("  already done    (label set unchanged)")
    if report.fallback_named:
        print(f"  fallback names  {report.fallback_named}")
    return EXIT_OK


def _print_trend(report: TrendReport) -> None:
    print(RULE)
    print(f"  baseline      {report.baseline_at.date().isoformat()}")
    print(f"  latest        {report.latest_at.date().isoformat()}")

    if report.trends:
        print("\n  drift, largest movement first")
        for trend in report.trends:
            print(
                f"    {trend.direction.value:<10}"
                f"  {trend.topic:<32}"
                f"  now {trend.strength:>5.2f}"
                f"  was {trend.baseline:>5.2f}"
            )


def _command_trend(args: argparse.Namespace) -> int:
    report = _pipeline_for(args).trend()
    if report is None:
        if args.json:
            print(json.dumps({"trends": None, "reason": "not enough history"}, indent=2))
        else:
            print(RULE)
            print(
                "  not enough history: the trend needs two profiles"
                f" at least {MIN_TREND_SPAN_DAYS} days apart"
            )
        return EXIT_OK
    if args.json:
        print(json.dumps(trend_payload(report), indent=2))
    else:
        _print_trend(report)
    return EXIT_OK


def _command_serve(args: argparse.Namespace) -> int:
    db_path = _paths_for(args).db_path
    serve(
        lambda: _pipeline_from(db_path),
        OllamaLanguageModel,
        host=args.host,
        port=args.port,
        ask_factory=_ask_factory(db_path),
    )
    return EXIT_OK


def _command_view(args: argparse.Namespace) -> int:
    paths = _paths_for(args)
    connection = connect(paths.db_path)
    photos = SqlitePhotoRepository(connection)
    pipeline = Pipeline(
        photos,
        SqliteOutingRepository(connection),
        SqliteAnchorRepository(connection),
        profiles=SqliteProfileRepository(connection),
        captions=SqliteCaptionRepository(connection),
        subjects=SqliteSubjectRepository(connection),
        themes=SqliteThemeSetRepository(connection),
        singles=SqliteSingleCaptionRepository(connection),
        screens=SqliteScreenshotReadingRepository(connection),
        corrections=SqliteCorrectionRepository(connection),
    )
    profile = pipeline.profile(keep=False)
    trend = pipeline.trend()
    topics = [interest.topic for interest in profile.interests]
    if trend is not None:
        topics += [item.topic for item in trend.trends]
    page = render_view(
        photos.all(),
        pipeline.report(),
        profile,
        trend,
        blur=not args.raw,
        names=place_names(topics, FileGazetteer(paths.gazetteer_path)),
        insights=_pipeline_from(_paths_for(args).db_path).insights(),
        comparison=_pipeline_from(_paths_for(args).db_path).compare(),
        feed=_pipeline_from(_paths_for(args).db_path).discover(),
    )
    destination = args.out if args.out is not None else paths.cache_dir / "kiseki-view.html"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(page, encoding="utf-8")
    print(f"written to {destination}")
    return EXIT_OK


def _command_screens(args: argparse.Namespace) -> int:
    paths = _paths_for(args)
    connection = connect(paths.db_path)
    report = run_screen_reading(
        photos=SqlitePhotoRepository(connection),
        readings=SqliteScreenshotReadingRepository(connection),
        thumbnails=FilesystemThumbnailSource(paths.thumbs_dir),
        reader=OllamaScreenshotReader(),
        limit=args.limit,
    )
    print(RULE)
    print(f"  read          {report.read}")
    print(f"  already done  {report.already}")
    print(f"  refused       {report.refused}")
    print(f"  unreferenced  {report.unreferenced}")
    if report.paused:
        print("\n  paused: the model was unavailable; run again to resume")
    return EXIT_OK


def _command_singles(args: argparse.Namespace) -> int:
    paths = _paths_for(args)
    connection = connect(paths.db_path)
    report = run_single_captioning(
        photos=SqlitePhotoRepository(connection),
        outings=SqliteOutingRepository(connection),
        singles=SqliteSingleCaptionRepository(connection),
        thumbnails=FilesystemThumbnailSource(paths.thumbs_dir),
        captioner=OllamaImageCaptioner(),
        limit=args.limit,
    )
    print(RULE)
    print(f"  captioned     {report.captioned}")
    print(f"  already done  {report.already_captioned}")
    print(f"  refused       {report.refused}")
    print(f"  unreferenced  {report.unreferenced}")
    if report.paused:
        print("\n  paused: the model was unavailable; run again to resume")
    return EXIT_OK


def _command_index(args: argparse.Namespace) -> int:
    connection = connect(_paths_for(args).db_path)
    try:
        report = run_indexing(
            photos=SqlitePhotoRepository(connection),
            captions=SqliteCaptionRepository(connection),
            singles=SqliteSingleCaptionRepository(connection),
            screens=SqliteScreenshotReadingRepository(connection),
            index=SqliteSearchIndex(connection),
            embedder=OllamaTextEmbedder(),
            embedding_model=DEFAULT_EMBEDDING_MODEL,
            limit=args.limit,
        )
    except ModelRefusedError as error:
        print(f"the model could not answer: {error}", file=sys.stderr)
        return EXIT_BAD_INPUT
    print(RULE)
    print(f"  documents     {report.documents_total} ({report.documents_added} new)")
    print(f"  embedded      {report.embedded}")
    print(f"  already done  {report.already_embedded}")
    if report.paused:
        print("\n  paused: the model was unavailable; run again to resume")
    return EXIT_OK


def _parse_moment(text: str, end_of_day: bool = False) -> datetime:
    moment = datetime.fromisoformat(text)
    if moment.tzinfo is None:
        moment = moment.astimezone()
    if end_of_day and len(text) == 10:
        moment += timedelta(hours=23, minutes=59, seconds=59)
    return moment


def _command_ask(args: argparse.Namespace) -> int:
    try:
        since = _parse_moment(args.since) if args.since else None
        until = _parse_moment(args.until, end_of_day=True) if args.until else None
    except ValueError as error:
        print(f"cannot read the date: {error}", file=sys.stderr)
        return EXIT_BAD_INPUT
    connection = connect(_paths_for(args).db_path)
    try:
        answer = ask(
            index=SqliteSearchIndex(connection),
            embedder=OllamaTextEmbedder(),
            embedding_model=DEFAULT_EMBEDDING_MODEL,
            language_model=OllamaLanguageModel(),
            question=args.question,
            language=args.lang,
            since=since,
            until=until,
            insights=_pipeline_from(_paths_for(args).db_path).insights(),
            excluded=active_exclusions(
                SqliteCorrectionRepository(connect(_paths_for(args).db_path)).all()
            ),
            near=_parse_near(args.near),
            within=Distance(args.within_km * 1000),
            locations=(
                _document_locations(_paths_for(args).db_path) if args.near is not None else None
            ),
        )
    except (ModelRefusedError, ModelUnavailableError) as error:
        print(f"the model could not answer: {error}", file=sys.stderr)
        return EXIT_BAD_INPUT
    if args.json:
        print(json.dumps(answer_payload(answer), ensure_ascii=False, indent=2))
        return EXIT_OK
    print(RULE)
    if not answer.answered:
        print("  no evidence found for this question")
        return EXIT_OK
    print(answer.answer)
    print()
    print(f"  confidence    {answer.confidence:.2f}")
    if answer.since is not None or answer.until is not None:
        left = f"{answer.since:%Y-%m-%d}" if answer.since else "open"
        right = f"{answer.until:%Y-%m-%d}" if answer.until else "open"
        print(f"  window        {left} to {right}")
    if answer.first_seen is not None and answer.last_seen is not None:
        print(f"  time range    {answer.first_seen:%Y-%m-%d} to {answer.last_seen:%Y-%m-%d}")
    print(f"  evidence      {len(answer.evidence)}")
    if answer.supporting_insights:
        print("\n  related findings")
        for item in answer.supporting_insights:
            print(f"    {item.kind.value:<10}  {item.topic}")
    for defect in validate_answer(answer):
        print(f"  check         {defect.value}")
    return EXIT_OK


def _ask_factory(
    db_path: Path,
) -> Callable[[str, str, datetime | None, datetime | None], Answer]:
    """Fresh connection per question: SQLite belongs to its thread."""

    def _answer(
        question: str,
        language: str,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> Answer:
        connection = connect(db_path)
        try:
            return ask(
                index=SqliteSearchIndex(connection),
                embedder=OllamaTextEmbedder(),
                embedding_model=DEFAULT_EMBEDDING_MODEL,
                language_model=OllamaLanguageModel(),
                question=question,
                language=language,
                since=since,
                until=until,
                insights=_pipeline_from(db_path).insights(),
                excluded=active_exclusions(SqliteCorrectionRepository(connect(db_path)).all()),
            )
        finally:
            connection.close()

    return _answer


def _command_lifecycle(args: argparse.Namespace) -> int:
    paths = _paths_for(args)
    report = _pipeline_from(paths.db_path).lifecycle()
    if report is None:
        if args.json:
            print(json.dumps({"lifecycles": None, "reason": "not enough history"}, indent=2))
        else:
            print(RULE)
            print(
                "  not enough history: the lifecycle needs two profiles"
                f" at least {MIN_TREND_SPAN_DAYS} days apart"
            )
        return EXIT_OK
    if args.json:
        print(json.dumps(lifecycle_payload(report), indent=2))
        return EXIT_OK
    names = place_names(
        (item.topic for item in report.lifecycles), FileGazetteer(paths.gazetteer_path)
    )
    print(RULE)
    print(f"  oldest        {report.oldest_at.date().isoformat()}")
    print(f"  latest        {report.latest_at.date().isoformat()}")
    if report.lifecycles:
        print("\n  where each topic stands")
        for item in report.lifecycles:
            print(
                f"    {item.stage.value:<10}"
                f"  {names.get(item.topic, item.topic):<32}"
                f"  now {item.strength:>5.2f}"
                f"  (was {item.baseline:>5.2f})"
                f"  seen {item.seen_profiles}"
            )
    return EXIT_OK


def _command_insights(args: argparse.Namespace) -> int:
    paths = _paths_for(args)
    report = _pipeline_from(paths.db_path).insights()
    if report is None:
        if args.json:
            print(json.dumps({"insights": None, "reason": "not enough history"}, indent=2))
        else:
            print(RULE)
            print(
                "  not enough history: insights need two profiles"
                f" at least {MIN_TREND_SPAN_DAYS} days apart"
            )
        return EXIT_OK
    if args.json:
        print(json.dumps(insights_payload(report), indent=2))
        return EXIT_OK
    names = place_names(
        (item.topic for item in report.insights), FileGazetteer(paths.gazetteer_path)
    )
    print(RULE)
    print(f"  oldest        {report.oldest_at.date().isoformat()}")
    print(f"  latest        {report.latest_at.date().isoformat()}")
    if not report.insights:
        print("\n  no findings yet: nothing new or moving in the history")
        return EXIT_OK
    if args.story:
        try:
            story = tell_insights(report, OllamaLanguageModel(), language=args.lang, names=names)
        except (ModelRefusedError, ModelUnavailableError) as error:
            print(f"the model could not answer: {error}", file=sys.stderr)
            return EXIT_BAD_INPUT
        print("\n" + story if story else "\n  no findings worth a story yet")
        return EXIT_OK
    print("\n  findings, the most novel first")
    for item in report.insights:
        arrow = {"up": "+", "down": "-", "flat": "="}[item.direction.value]
        print(
            f"    {item.kind.value:<10}"
            f"  {names.get(item.topic, item.topic):<32}"
            f"  {arrow}{item.magnitude:.2f}"
            f"  confidence {item.confidence:.2f}"
            f"  evidence {len(item.evidence)}"
        )
    said = read_from(reference for item in report.insights for reference in item.evidence)
    if said:
        print(f"\n  {said}")
    mixed = derive_mixed(report)
    if mixed:
        print("\n  held together -- both are you")
        for pair in mixed:
            held_label = names.get(pair.held, pair.held)
            rising_label = names.get(pair.rising, pair.rising)
            print(
                f"    {held_label} stayed strong ({pair.held_strength:.2f})"
                f" while {rising_label} grew (+{pair.rising_magnitude:.2f})"
            )
    return EXIT_OK


def _command_correct(args: argparse.Namespace) -> int:
    from datetime import UTC
    from datetime import datetime as _datetime

    connection = connect(_paths_for(args).db_path)
    repository = SqliteCorrectionRepository(connection)
    verdict = CorrectionVerdict.REINSTATED if args.reinstate else CorrectionVerdict.EXCLUDED
    repository.add(
        Correction(
            reference=args.reference,
            verdict=verdict,
            note=args.note,
            created_at=_datetime.now(UTC),
        )
    )
    print(f"corrected {args.reference} ({verdict.value})")
    return EXIT_OK


def _command_corrections(args: argparse.Namespace) -> int:
    connection = connect(_paths_for(args).db_path)
    records = SqliteCorrectionRepository(connection).all()
    active = active_exclusions(records)
    print(RULE)
    print(f"  corrections  {len(records)}")
    print(f"  excluded  {len(active)}")
    for record in records:
        note = f"  ({record.note})" if record.note else ""
        print(
            f"    {record.created_at.date().isoformat()}"
            f"  {record.verdict.value:<10}  {record.reference}{note}"
        )
    return EXIT_OK


def _command_compare(args: argparse.Namespace) -> int:
    from datetime import datetime as _datetime
    from datetime import timedelta as _timedelta

    if (args.from_date is None) != (args.to_date is None):
        print("compare needs both --from and --to, or neither", file=sys.stderr)
        return EXIT_BAD_INPUT
    from_at = to_at = None
    if args.from_date is not None and args.to_date is not None:
        try:
            from_at = _datetime.fromisoformat(args.from_date)
            to_at = _datetime.fromisoformat(args.to_date)
        except ValueError:
            print("dates must be ISO, like 2026-06-01", file=sys.stderr)
            return EXIT_BAD_INPUT
        if len(args.from_date) == 10:
            from_at = from_at + _timedelta(days=1) - _timedelta(microseconds=1)
        if len(args.to_date) == 10:
            to_at = to_at + _timedelta(days=1) - _timedelta(microseconds=1)
    paths = _paths_for(args)
    try:
        comparison = _pipeline_from(paths.db_path).compare(from_at, to_at)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return EXIT_BAD_INPUT
    if comparison is None:
        if args.json:
            print(json.dumps({"entries": None, "reason": "not enough history"}, indent=2))
        else:
            print(RULE)
            print("  not enough history: compare needs two kept profiles to pair")
        return EXIT_OK
    if args.json:
        print(json.dumps(comparison_payload(comparison), indent=2))
        return EXIT_OK
    names = place_names(
        (entry.topic for entry in comparison.entries), FileGazetteer(paths.gazetteer_path)
    )
    moved = [entry for entry in comparison.entries if entry.change is not ChangeKind.STEADY]
    print(RULE)
    print(f"  before        {comparison.before_at.date().isoformat()}")
    print(f"  after         {comparison.after_at.date().isoformat()}")
    if moved:
        print("\n  what changed, the loudest first")
        for entry in moved:
            print(
                f"    {entry.change.value:<9}"
                f"  {names.get(entry.topic, entry.topic):<32}"
                f"  {entry.strength_before:.2f} -> {entry.strength_after:.2f}"
                f"  evidence {entry.evidence_before} -> {entry.evidence_after}"
            )
    else:
        print("\n  nothing moved between the two readings")
    print(f"\n  steady        {len(comparison.entries) - len(moved)} topics")
    return EXIT_OK


def _command_privacy(args: argparse.Namespace) -> int:
    report = _pipeline_from(_paths_for(args).db_path).privacy()
    if args.json:
        print(json.dumps(privacy_payload(report), indent=2))
        return EXIT_OK
    print(RULE)
    print("  what is stored, in counts")
    print(f"    photographs       {report.photographs:>6}   located {report.located}")
    print(f"    stay captions     {report.stay_captions:>6}   refused {report.stay_refused}")
    print(f"    single captions   {report.single_captions:>6}   refused {report.single_refused}")
    print(
        f"    screen readings   {report.screen_readings:>6}"
        f"   label-silent {report.screens_label_silent}"
    )
    print(f"    subject readings  {report.subject_readings:>6}")
    print(f"    kept profiles     {report.kept_profiles:>6}")
    print(
        f"    corrections       {report.corrections:>6}   excluding now {report.active_exclusions}"
    )
    print("\n  what the owner has withheld")
    print(f"    from the preferences  {report.withheld_from_preference} photographs")
    print("\n  what is never stored, by construction")
    for name, reason in NEVER_STORED:
        print(f"    {name:<24}  {reason}")
    print(f"\n  {BLURRED_BY_DEFAULT}")
    return EXIT_OK


def _command_export(args: argparse.Namespace) -> int:
    from datetime import date as _date

    pipeline = _pipeline_from(_paths_for(args).db_path)
    document = interest_export(
        pipeline.profile(keep=False),
        pipeline.lifecycle(),
        _date.today(),
    )
    text = json.dumps(document, indent=2)
    if args.out is not None:
        target = Path(args.out)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text + "\n", encoding="utf-8")
        print(f"exported {len(document['interests'])} interests to {target}")
        return EXIT_OK
    print(text)
    return EXIT_OK


def _command_doctor(args: argparse.Namespace) -> int:
    from datetime import datetime as _datetime

    paths = _paths_for(args)
    report = _pipeline_from(paths.db_path).privacy()
    connection = connect(paths.db_path)
    readings: list[_datetime] = []
    for caption in SqliteCaptionRepository(connection).all():
        readings.append(caption.created_at)
    for single in SqliteSingleCaptionRepository(connection).all():
        readings.append(single.created_at)
    for screen in SqliteScreenshotReadingRepository(connection).all():
        readings.append(screen.created_at)
    history = SqliteProfileRepository(connection).history()

    print(RULE)
    print("  doctor")
    print(f"    [schema]       database at version {SCHEMA_VERSION}, the code's version")
    refusals = report.stay_refused + report.single_refused
    print(
        f"    [integrity]    {refusals} caption refusals recorded;"
        " a rerun will not retry them (ADR-0015)"
    )
    recoverable = sum(count_recoverable(connection, table) for table in RETRY_STAGES.values())
    if recoverable:
        print(
            f"                   {recoverable} of all refusals are recoverable"
            " (the image was missing); `kiseki retry` says which"
        )
    print(
        f"    [privacy]      {report.screens_label_silent} label-silent screens;"
        f" {report.active_exclusions} references excluded by correction"
    )
    if not history:
        print("    [evidence]     no kept profile yet; run `kiseki profile` once")
    else:
        last = history[-1].generated_at.replace(tzinfo=None)
        newer = sum(1 for moment in readings if moment.replace(tzinfo=None) > last)
        age = (_datetime.now() - last).days
        if newer:
            print(
                f"    [evidence]     {newer} readings newer than the last kept profile"
                f" ({age} days old); a `kiseki profile` would capture them"
            )
        else:
            print(f"    [evidence]     nothing newer than the last kept profile ({age} days old)")
    gazetteer = FileGazetteer(paths.gazetteer_path)
    if gazetteer.entries:
        print(f"    [consistency]  gazetteer present, {gazetteer.entries} entries")
    else:
        print("    [consistency]  no gazetteer file; places stay unnamed (docs/gazetteer.md)")
    photographs = SqlitePhotoRepository(connection).all()
    missing = sum(
        1
        for photograph in photographs
        if photograph.thumbnail_ref and not (paths.thumbs_dir / photograph.thumbnail_ref).is_file()
    )
    if missing:
        print(
            f"    [consistency]  {missing} photographs have no reduced copy"
            f" under {paths.thumbs_dir}; the readers will refuse them"
        )
    return EXIT_OK


def _command_discover(args: argparse.Namespace) -> int:
    paths = _paths_for(args)
    feed = _pipeline_from(paths.db_path).discover()
    if feed is None:
        if args.json:
            print(json.dumps({"discoveries": None, "reason": "not enough history"}, indent=2))
        else:
            print(RULE)
            print(
                "  not enough history: discovery needs two profiles"
                f" at least {MIN_TREND_SPAN_DAYS} days apart"
            )
        return EXIT_OK
    if args.json:
        print(json.dumps(discovery_payload(feed), indent=2))
        return EXIT_OK
    names = place_names(
        (entry.topic for entry in feed.entries), FileGazetteer(paths.gazetteer_path)
    )
    print(RULE)
    print(f"  oldest        {feed.oldest_at.date().isoformat()}")
    print(f"  latest        {feed.latest_at.date().isoformat()}")
    if not feed.entries:
        print("\n  nothing worth a look yet: nothing new or moving in the history")
        return EXIT_OK
    said = read_from(reference for entry in feed.entries for reference in entry.evidence)
    if said:
        print(f"  {said}")
    print("\n  worth a look, the most discovery-like first")
    for entry in feed.entries:
        print(
            f"    {entry.kind.value:<10}"
            f"  {names.get(entry.topic, entry.topic):<32}"
            f"  novelty {entry.novelty:.2f}"
            f"  importance {entry.importance:.2f}"
            f"  confidence {entry.confidence:.2f}"
        )
    return EXIT_OK


def _parse_near(text: str | None) -> GeoPoint | None:
    if text is None:
        return None
    try:
        latitude_text, longitude_text = text.split(",", 1)
        point = GeoPoint(float(latitude_text), float(longitude_text))
    except ValueError:
        print('--near must be "lat,lon", like "34.69,135.50"', file=sys.stderr)
        raise SystemExit(EXIT_BAD_INPUT) from None
    return point


def _document_locations(db_path: Path) -> dict[str, GeoPoint]:
    """doc_key -> location, read from the primary store at question time.

    The index never holds a coordinate (ADR-0036); a stay averages
    its photographs, a single is its photograph, and a screen
    reading has no chosen place, so it never appears here.
    """
    connection = connect(db_path)
    located = {
        photo.photo_id: photo.location
        for photo in SqlitePhotoRepository(connection).all()
        if photo.location is not None
    }
    mapping: dict[str, GeoPoint] = {}
    for caption in SqliteCaptionRepository(connection).all():
        points = [located[pid] for pid in caption.photo_ids if pid in located]
        if points:
            mapping[f"stay:{caption.key.value}"] = GeoPoint(
                sum(point.latitude for point in points) / len(points),
                sum(point.longitude for point in points) / len(points),
            )
    for photo_id, point in located.items():
        mapping[f"single:{photo_id.value}"] = point
    return mapping


def _command_drift(args: argparse.Namespace) -> int:
    """Three timelines on one axis, and what may not be concluded.

    Every series is counted by the moment in the owner's life. A screen
    reading carries created_at -- the day the model read it, which is
    the day the owner happened to run a command -- so the screens are
    counted by the capture of the photograph they read. Counting the
    first would measure this library rather than the person using it.

    Each verdict is printed with the number behind it. "No shared
    movement" at 0.05 and at 0.55 are different statements, and a
    reader who cannot see which one they have cannot judge the
    threshold that produced it (the posture of ADR-0045).
    """
    paths = _paths_for(args)
    connection = connect(paths.db_path)
    photographs = SqlitePhotoRepository(connection).all()
    taken_at = {photo.photo_id: photo.captured_at for photo in photographs}
    screens = [
        taken_at[reading.photo_id]
        for reading in SqliteScreenshotReadingRepository(connection).all()
        if reading.photo_id in taken_at
    ]
    outings = [outing.time_range.start for outing in SqliteOutingRepository(connection).all()]
    series = {
        "photographs": monthly_counts([photo.captured_at for photo in photographs]),
        "outings": monthly_counts(outings),
        "screens": monthly_counts(screens),
    }
    named = [(name, counts) for name, counts in series.items() if counts]
    print(RULE)
    if len(named) < 2:
        print("  not enough history: two timelines are needed to compare")
        return EXIT_OK
    print("  what moved with what")
    printed = 0
    for index, left in enumerate(named):
        for right in named[index + 1 :]:
            result = compare_timelines(left, right)
            print(
                f"    {result.left:<14} and {result.right:<14}"
                f"  {result.relation.value:<24}"
                f"  ({result.alignment:+.2f})"
                f"  over {result.months} months"
            )
            printed += 1
    if printed:
        print(f"\n  {compare_timelines(named[0], named[1]).caution}")
        print(
            f"  the number is how closely two series moved, from -1 to +1;"
            f" {ALIGNMENT_STRONG:+.2f} is where this library starts saying so"
        )
    print("\n  each against its own past")
    for name, counts in named:
        drift = derive_drift(name, counts)
        if drift is None:
            print(f"    {name:<14}  not enough history")
            continue
        print(
            f"    {name:<14}  {drift.stage.value:<38}"
            f"  {drift.latest:.0f} this month, {drift.baseline:.1f} before"
        )
    return EXIT_OK


def _command_trips(args: argparse.Namespace) -> int:
    """The nights away, as journeys rather than as separate days.

    The places the owner sets out from come from their own history
    (ADR-0055), and a trip is what stayed away from all of them across
    a night (ADR-0060).
    """
    paths = _paths_for(args)
    connection = connect(paths.db_path)
    outings = SqliteOutingRepository(connection).all()
    places = derive_place_profiles(outings)
    origins = [
        place.centroid
        for place in places
        if place.visits >= REGULAR_VISITS
        and (place.last_seen - place.first_seen).days >= REGULAR_SPAN_DAYS
    ]
    if not origins and places:
        origins = [max(places, key=lambda place: place.visits).centroid]
    trips = derive_trips(outings, origins)
    print(RULE)
    if not trips:
        print("  no trips yet: a trip is a night spent away from everywhere you")
        print("  usually set out from")
        return EXIT_OK
    gazetteer = FileGazetteer(paths.gazetteer_path)
    print(f"  trips         {len(trips)}, the most recent first")
    print()
    for trip in sorted(trips, key=lambda item: item.start, reverse=True)[:15]:
        farthest = max(
            (stop for outing in trip.outings for stop in outing.stops),
            key=lambda stop: max(origin.distance_to(stop.centroid).meters for origin in origins),
        )
        named = gazetteer.nearest(farthest.centroid, Distance(25_000))
        label = (
            named.label
            if named is not None
            else f"{farthest.centroid.latitude:.2f},{farthest.centroid.longitude:.2f}"
        )
        print(
            f"    {trip.start.date().isoformat()}"
            f"  {trip.nights} night{'s' if trip.nights != 1 else ''}"
            f"  {label:<28}"
            f"  {trip.farthest_km:.0f} km out"
            f"  {trip.photograph_count} photographs"
        )
    return EXIT_OK


def _origins_of(places: Sequence[PlaceProfile]) -> list[GeoPoint]:
    """The places the owner sets out from (ADR-0055)."""
    regular = [
        place.centroid
        for place in places
        if place.visits >= REGULAR_VISITS
        and (place.last_seen - place.first_seen).days >= REGULAR_SPAN_DAYS
    ]
    if regular:
        return regular
    return [max(places, key=lambda place: place.visits).centroid] if places else []


def _places_of(connection: sqlite3.Connection) -> tuple[PlaceProfile, ...]:
    """Places, knowing which of their visits happened on a trip.

    Read twice on purpose: the first reading finds the places the
    owner sets out from, the trips are derived against those, and the
    second reading knows which visits belong to one (ADR-0060).
    """
    outings = SqliteOutingRepository(connection).all()
    plain = derive_place_profiles(outings)
    trips = derive_trips(outings, _origins_of(plain))
    on_trips = {outing.id.value for trip in trips for outing in trip.outings}
    return derive_place_profiles(outings, on_trips)


def _command_retention(args: argparse.Namespace) -> int:
    """The rules, and what they would let go of (ADR-0062).

    Every rule is off unless it is given. Nothing runs on a timer, and
    nothing goes without --apply: a library that discarded the owner's
    past because a default said so would break the promise the rest of
    this code keeps.
    """
    from datetime import datetime as _datetime
    from datetime import timedelta as _timedelta

    policy = RetentionPolicy(
        keep_photographs_for=(
            _timedelta(days=round(365.25 * args.keep_photographs_years))
            if args.keep_photographs_years
            else None
        ),
        keep_refusals_for=(
            _timedelta(days=args.keep_refusals_days) if args.keep_refusals_days else None
        ),
        keep_profiles=args.keep_profiles,
    )
    connection = connect(_paths_for(args).db_path)
    print(RULE)
    if policy.is_empty:
        print("  nothing is forgotten: no rule is set")
        print("    --keep-photographs-years N   forget photographs older than N years")
        print("    --keep-refusals-days N       forget recorded refusals older than N days")
        print("    --keep-profiles N            keep the last N readings, then one a month")
        return EXIT_OK
    now = _datetime.now()
    plan = plan_retention(connection, policy, now)
    verb = "forgotten" if args.apply else "would forget"
    print(f"  {verb}")
    print(f"    photographs       {len(plan.photo_ids):>5}")
    print(f"    recorded refusals {plan.refusals:>5}")
    print(f"    kept readings     {plan.profiles:>5}")
    if plan.is_empty:
        print("\n  the rules reach nothing: everything stored is within them")
        return EXIT_OK
    if not args.apply:
        print("\n  nothing was changed; add --apply to let them go")
        return EXIT_OK
    apply_retention(connection, policy, now)
    print("\n  run `kiseki build` to rebuild the journeys without them")
    return EXIT_OK


def _command_forget(args: argparse.Namespace) -> int:
    """Remove photographs and everything that spoke about them.

    Counted and shown first; removed only on a second word. Journeys
    are not deleted here because they are derived: a rebuild without
    the photographs produces a history without them (ADR-0013,
    ADR-0061).
    """
    connection = connect(_paths_for(args).db_path)
    plan = plan_forget(connection, args.photo_ids)
    if plan.is_empty:
        print("no such photograph is stored", file=sys.stderr)
        return EXIT_BAD_INPUT
    print(RULE)
    verb = "forgotten" if args.apply else "would forget"
    print(f"  {verb}")
    print(f"    photographs       {len(plan.photo_ids):>5}")
    print(f"    stay captions     {len(plan.caption_keys):>5}")
    print(f"    single captions   {plan.single_captions:>5}")
    print(f"    screen readings   {plan.screen_readings:>5}")
    print(f"    subject readings  {plan.subjects:>5}")
    print(f"    indexed documents {plan.documents:>5}")
    print(f"    embeddings        {plan.embeddings:>5}")
    if not args.apply:
        print("\n  nothing was changed; add --apply to forget it")
        return EXIT_OK
    forget(connection, plan)
    print("\n  run `kiseki build` to rebuild the journeys without them,")
    print("  and `kiseki profile` to read what is left")
    return EXIT_OK


def _command_places(args: argparse.Namespace) -> int:
    paths = _paths_for(args)
    connection = connect(paths.db_path)
    places = _places_of(connection)
    print(RULE)
    if not places:
        print("  no places yet: run `kiseki build` once the photographs are in")
        return EXIT_OK
    gazetteer = FileGazetteer(paths.gazetteer_path)
    shown = places[:15]
    print(f"  places        {len(places)} (showing {len(shown)}, the most visited first)")
    print()
    for place in shown:
        named = gazetteer.nearest(place.centroid, Distance(25_000))
        label = (
            named.label
            if named is not None
            else f"{place.centroid.latitude:.2f},{place.centroid.longitude:.2f}"
        )
        gap = f"every ~{place.median_gap_days}d" if place.median_gap_days is not None else "once"
        print(
            f"    {label:<28}"
            f"  visits {place.visits:>3}"
            f"  first {place.first_seen.date().isoformat()}"
            f"  last {place.last_seen.date().isoformat()}"
            f"  {gap}"
        )
    return EXIT_OK


def _command_suggest(args: argparse.Namespace) -> int:
    from datetime import datetime as _datetime

    paths = _paths_for(args)
    connection = connect(paths.db_path)
    places = _places_of(connection)
    lifecycle = _pipeline_from(paths.db_path).lifecycle()
    suggestions = derive_suggestions(places, lifecycle, _datetime.now())
    suggestions = spread_out(suggestions)
    print(RULE)
    if not suggestions:
        print("  nothing to suggest: the evidence is thin, or everything is current")
        return EXIT_OK
    names = place_names(
        (item.reference for item in suggestions), FileGazetteer(paths.gazetteer_path)
    )
    print("  from your own evidence, the most overdue first")
    print()
    for item in suggestions:
        label = names.get(item.reference, item.reference)
        if item.kind is SuggestionKind.REVISIT:
            print(
                f"    go back    {label:<28}"
                f"  every ~{item.cadence_days}d, {item.days_since} days since"
                f"  confidence {item.confidence:.2f}"
            )
        else:
            print(
                f"    pick up    {label:<28}"
                f"  seen in {item.seen_profiles} readings, was {item.baseline:.2f}"
                f"  confidence {item.confidence:.2f}"
            )
    reach = derive_reach(SqliteOutingRepository(connection).all())
    trips = derive_day_trips(places, reach, _datetime.now()) if reach else ()
    trips = spread_out(trips)
    names.update(
        place_names(
            (trip.reference for trip in trips),
            FileGazetteer(paths.gazetteer_path),
        )
    )
    for trip in trips:
        label = names.get(trip.reference, trip.reference)
        distance = trip.distance_km or 0.0
        print(
            f"    day trip   {label:<28}"
            f"  {distance:.0f} km out, last seen {trip.days_since} days ago"
        )
    if reach is not None and trips:
        print(
            f"\n  {int(reach.share * 10)} in 10 of your outings cover under"
            f" {reach.usual_km:.0f} km; a day trip is measured against that"
        )
    said = read_from([item.reference for item in suggestions] + [trip.reference for trip in trips])
    if said:
        print(f"  {said}")
    return EXIT_OK


REREAD_STAGES = {
    "captions": ("captions", CAPTION_PROMPT_VERSION),
    "singles": ("single_captions", SINGLE_CAPTION_PROMPT_VERSION),
    "subjects": ("subjects", SUBJECT_PROMPT_VERSION),
    "themes": ("theme_sets", THEME_PROMPT_VERSION),
    "screens": ("screen_readings", SCREEN_PROMPT_VERSION),
}


RETRY_STAGES = {
    "captions": "captions",
    "singles": "single_captions",
    "subjects": "subjects",
    "screens": "screen_readings",
}


REFRESH_STAGES = (
    "build",
    "caption",
    "singles",
    "screens",
    "subjects",
    "themes",
    "index",
    "profile",
)
"""The weekly routine, in the order the pipeline needs.

Ingest is deliberately absent: taking in new records is its own act,
with its own source and its own risks. Refresh brings the readings
and the derivations up to date with what is already in.
"""


def _command_refresh(args: argparse.Namespace) -> int:
    if args.dry_run:
        print(RULE)
        print("  refresh would run, in order")
        for stage in REFRESH_STAGES:
            print(f"    kiseki {stage}")
        print("    kiseki doctor")
        print("\n  ingest is not included: taking in new records is its own act")
        return EXIT_OK
    parser = build_parser()
    base = ["--data-root", args.data_root] if getattr(args, "data_root", None) else []
    for stage in REFRESH_STAGES:
        print(RULE)
        print(f"  {stage}")
        parsed = parser.parse_args([*base, stage])
        code: int = parsed.run(parsed)
        if code != EXIT_OK:
            print(f"  {stage} stopped ({code}); nothing after it ran", file=sys.stderr)
            return code
    return _command_doctor(args)


def _command_demo(args: argparse.Namespace) -> int:
    """Build a synthetic library, show every derivation, sweep up.

    Reads no configuration on purpose: the sandbox path is the one
    given, and nothing else can redirect it.
    """
    import gc
    import shutil
    from datetime import datetime as _datetime

    from kiseki.adapters.sqlite.store import (
        SqliteCaptionRepository as _DemoCaptions,
    )
    from kiseki.adapters.sqlite.store import (
        SqlitePhotoRepository as _DemoPhotos,
    )
    from kiseki.adapters.sqlite.store import (
        SqliteProfileRepository as _DemoProfiles,
    )
    from kiseki.adapters.sqlite.store import (
        SqliteSubjectRepository as _DemoSubjects,
    )
    from kiseki.application.demo import demo_photographs, demo_profiles, demo_readings
    from kiseki.domain.services.suggesting import SuggestionKind, derive_suggestions

    root = Path(args.out) if args.out else Path.cwd() / "kiseki-demo"
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    db_path = root / "kiseki-demo.sqlite3"
    connection = connect(db_path)
    _DemoPhotos(connection).save_all(demo_photographs())
    demo_captions = _DemoCaptions(connection)
    demo_subjects = _DemoSubjects(connection)
    for caption, reading in demo_readings():
        demo_captions.save(caption)
        demo_subjects.save(reading)
    demo_profiles_store = _DemoProfiles(connection)
    for snapshot in demo_profiles():
        demo_profiles_store.save(snapshot)
    connection.close()

    pipeline = _pipeline_from(db_path)
    pipeline.rebuild()
    profile = pipeline.profile(keep=False)
    connection = connect(db_path)
    places = _places_of(connection)
    lifecycle = pipeline.lifecycle()
    insights = pipeline.insights()
    feed = pipeline.discover()
    comparison = pipeline.compare()
    suggestions = derive_suggestions(places, lifecycle, _datetime.now())
    suggestions = spread_out(suggestions)

    print(RULE)
    print("  a synthetic library, so the engine can be seen")
    print(f"\n  interests     {len(profile.interests)}")
    for interest in profile.ranked()[:8]:
        print(f"    {interest.topic:<22}  score {interest.score:.2f}")
    print(f"\n  places        {len(places)}")
    for place in places[:3]:
        cadence = (
            f"every ~{place.median_gap_days}d" if place.median_gap_days is not None else "once"
        )
        print(f"    {place.visits:>3} visits  {cadence}")
    print("\n  lifecycle")
    if lifecycle is None:
        print("    not enough history")
    else:
        for item in lifecycle.lifecycles[:4]:
            print(f"    {item.topic:<22}  {item.stage.value}")
    print("\n  insights")
    if insights is None:
        print("    not enough history")
    else:
        for finding in insights.insights[:4]:
            print(f"    {finding.topic:<22}  {finding.kind.value}")
    print("\n  discover")
    if feed is None:
        print("    not enough history")
    else:
        for entry in feed.entries[:4]:
            print(
                f"    {entry.topic:<22}  novelty {entry.novelty:.2f}"
                f"  importance {entry.importance:.2f}"
            )
    print("\n  compare")
    if comparison is None:
        print("    not enough history")
    else:
        for change in comparison.entries[:4]:
            print(
                f"    {change.topic:<22}  {change.change.value:<9}"
                f"  {change.strength_before:.2f} -> {change.strength_after:.2f}"
            )
    print("\n  suggest")
    if not suggestions:
        print("    nothing to suggest")
    for suggestion in suggestions[:4]:
        kind = "go back" if suggestion.kind is SuggestionKind.REVISIT else "pick up"
        print(f"    {kind:<9}  {suggestion.reference}")
    demo_reach = derive_reach(SqliteOutingRepository(connection).all())
    demo_trips = derive_day_trips(places, demo_reach, _datetime.now()) if demo_reach else ()
    for trip in demo_trips:
        distance = trip.distance_km or 0.0
        print(f"    day trip   {trip.reference}  {distance:.0f} km out")
    if demo_reach is not None:
        print(
            f"\n  {int(demo_reach.share * 10)} in 10 of your outings cover under"
            f" {demo_reach.usual_km:.0f} km"
        )

    connection.close()
    del pipeline
    gc.collect()
    # Windows will not delete a file another handle still holds, and the
    # pipeline keeps its own connection. Letting go is part of sweeping up.
    if args.keep:
        print(f"\n  kept at {root}")
    else:
        shutil.rmtree(root)
        print("\n  the sandbox was swept up; --keep leaves it in place")
    return EXIT_OK


def _command_retry(args: argparse.Namespace) -> int:
    if args.apply and args.stage is None:
        print("retry --apply needs --stage", file=sys.stderr)
        return EXIT_BAD_INPUT
    connection = connect(_paths_for(args).db_path)
    print(RULE)
    if args.apply:
        removed = clear_recoverable(connection, RETRY_STAGES[args.stage])
        print(f"  took back {removed} refusals the environment caused")
        print(f"  run `kiseki {args.stage}` to try them again")
        return EXIT_OK
    stages = [args.stage] if args.stage is not None else list(RETRY_STAGES)
    print("  refusals the environment caused, not the model")
    for stage in stages:
        table = RETRY_STAGES[stage]
        print(f"    {stage:<10}  {count_recoverable(connection, table):>5} recoverable")
    print("\n  the model's own refusals are never taken back (ADR-0015)")
    print("  nothing was changed; add --stage <name> --apply to take one back")
    return EXIT_OK


def _command_reread(args: argparse.Namespace) -> int:
    if args.apply and args.stage is None:
        print("reread --apply needs --stage", file=sys.stderr)
        return EXIT_BAD_INPUT
    connection = connect(_paths_for(args).db_path)
    print(RULE)
    if args.apply:
        table, current = REREAD_STAGES[args.stage]
        removed = clear_outdated(connection, table, current)
        print(f"  cleared {removed} readings older than {current}")
        print(f"  run `kiseki {args.stage}` to make them again")
        return EXIT_OK
    stages = [args.stage] if args.stage is not None else list(REREAD_STAGES)
    print("  reread")
    for stage in stages:
        table, current = REREAD_STAGES[stage]
        outdated = count_outdated(connection, table, current)
        total: int = connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"    {stage:<10}  {outdated:>5} of {total} readings predate {current}")
    print("\n  nothing was changed; add --stage <name> --apply to clear one")
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kiseki",
        description="Reconstruct journeys from photo timelines and measure them.",
    )
    parser.add_argument("--data-root", default=None, help="override where everything is stored")
    commands = parser.add_subparsers(dest="command")

    commands.add_parser("paths", help="show where things will be stored").set_defaults(
        run=_command_paths
    )

    ingest = commands.add_parser("ingest", help="take in a PhotoRecord document")
    ingest.add_argument("records", type=Path)
    ingest.set_defaults(run=_command_ingest)

    activity = commands.add_parser("activity", help="read days of movement (ActivityRecord v1)")
    activity.add_argument("records", help="the ActivityRecord v1 document")
    activity.set_defaults(run=_command_activity)

    commands.add_parser("build", help="recompute stops, outings and anchors").set_defaults(
        run=_command_build
    )

    report = commands.add_parser("report", help="print what the measures say")
    report.add_argument("--json", action="store_true", help="machine readable output")
    report.set_defaults(run=_command_report)

    profile = commands.add_parser("profile", help="read the measures as interests")
    profile.add_argument("--json", action="store_true", help="machine readable output")
    profile.set_defaults(run=_command_profile)

    caption = commands.add_parser("caption", help="describe the stays with a vision model")
    caption.add_argument("--limit", type=int, default=None, help="caption at most this many stays")
    caption.set_defaults(run=_command_caption)

    subjects = commands.add_parser("subjects", help="name the subjects of the captions")
    subjects.add_argument("--limit", type=int, default=None, help="read at most this many captions")
    subjects.set_defaults(run=_command_subjects)

    telling = commands.add_parser("tell", help="say what the profile says, in prose")
    telling.add_argument("--lang", default="ja", choices=["ja", "en"], help="output language")
    telling.set_defaults(run=_command_tell)

    themes = commands.add_parser("themes", help="gather the labels into themes")
    themes.set_defaults(run=_command_themes)

    trend = commands.add_parser("trend", help="read the drift between kept profiles")
    trend.add_argument("--json", action="store_true", help="machine readable output")
    trend.set_defaults(run=_command_trend)

    serving = commands.add_parser("serve", help="answer over local HTTP")
    serving.add_argument(
        "--host", default=DEFAULT_HOST, help="bind address; loopback unless told otherwise"
    )
    serving.add_argument("--port", type=int, default=DEFAULT_PORT, help="port to listen on")
    serving.set_defaults(run=_command_serve)

    viewing = commands.add_parser("view", help="write a self-contained HTML view")
    viewing.add_argument("--out", type=Path, default=None, help="where to write the file")
    viewing.add_argument(
        "--raw", action="store_true", help="keep raw topic labels; blurred by default"
    )
    viewing.set_defaults(run=_command_view)

    screens = commands.add_parser("screens", help="read the screenshots: category and labels only")
    screens.add_argument("--limit", type=int, default=None, help="read at most this many")
    screens.set_defaults(run=_command_screens)

    singles = commands.add_parser("singles", help="describe the photographs outside every stay")
    singles.add_argument(
        "--limit", type=int, default=None, help="caption at most this many photographs"
    )
    singles.set_defaults(run=_command_singles)

    indexing = commands.add_parser("index", help="index the readings for search")
    indexing.add_argument("--limit", type=int, default=None, help="embed at most this many")
    indexing.set_defaults(run=_command_index)

    asking = commands.add_parser("ask", help="answer a question from the readings")
    asking.add_argument("question", help="the question, in Japanese or English")
    asking.add_argument("--lang", default="ja", choices=["ja", "en"], help="answer language")
    asking.add_argument("--since", default=None, help="ISO date; overrides words like last year")
    asking.add_argument("--until", default=None, help="ISO date, inclusive")
    asking.add_argument("--json", action="store_true", help="machine readable output")
    asking.add_argument(
        "--near", default=None, help="lat,lon; keep evidence within --within-km of it"
    )
    asking.add_argument(
        "--within-km",
        dest="within_km",
        type=float,
        default=30.0,
        help="radius for --near, in kilometres (default 30)",
    )
    asking.set_defaults(run=_command_ask)

    lifecycle = commands.add_parser("lifecycle", help="where each topic stands in its life")
    lifecycle.add_argument("--json", action="store_true", help="machine readable output")
    lifecycle.set_defaults(run=_command_lifecycle)

    insights = commands.add_parser("insights", help="the current findings, with evidence")
    insights.add_argument("--story", action="store_true", help="narrate the findings")
    insights.add_argument("--lang", default="ja", choices=["ja", "en"], help="story language")
    insights.add_argument("--json", action="store_true", help="machine readable output")
    insights.set_defaults(run=_command_insights)

    correct = commands.add_parser(
        "correct", help="exclude a topic or a reading from every derivation"
    )
    correct.add_argument("reference", help="topic:<name>, caption:<key>, photo:<id> or screen:<id>")
    correct.add_argument("--note", default="", help="why, for future you")
    correct.add_argument("--reinstate", action="store_true", help="undo an exclusion")
    correct.set_defaults(run=_command_correct)

    corrections = commands.add_parser("corrections", help="the append-only correction log")
    corrections.set_defaults(run=_command_corrections)

    compare = commands.add_parser("compare", help="what changed between two kept readings")
    compare.add_argument(
        "--from",
        dest="from_date",
        default=None,
        help="ISO date; picks the latest kept profile at or before it",
    )
    compare.add_argument(
        "--to",
        dest="to_date",
        default=None,
        help="ISO date; picks the latest kept profile at or before it",
    )
    compare.add_argument("--json", action="store_true", help="machine readable output")
    compare.set_defaults(run=_command_compare)

    privacy = commands.add_parser("privacy", help="how the owner's data is treated, in counts")
    privacy.add_argument("--json", action="store_true", help="machine readable output")
    privacy.set_defaults(run=_command_privacy)

    export = commands.add_parser("export", help="the interest export: a one-way abstraction")
    export.add_argument("--out", default=None, help="write the JSON to this file instead of stdout")
    export.set_defaults(run=_command_export)

    doctor = commands.add_parser("doctor", help="categorised, deterministic health checks")
    doctor.set_defaults(run=_command_doctor)

    discover = commands.add_parser("discover", help="what is worth a look, ranked")
    discover.add_argument("--json", action="store_true", help="machine readable output")
    discover.set_defaults(run=_command_discover)

    places = commands.add_parser("places", help="what your journeys say about each place")
    places.set_defaults(run=_command_places)

    forgetting = commands.add_parser(
        "forget", help="remove photographs and everything said about them"
    )
    forgetting.add_argument("photo_ids", nargs="+", help="the photograph identifiers to forget")
    forgetting.add_argument("--apply", action="store_true", help="actually remove them")
    forgetting.set_defaults(run=_command_forget)

    retention = commands.add_parser("retention", help="what a decade should look like, as rules")
    retention.add_argument(
        "--keep-photographs-years",
        dest="keep_photographs_years",
        type=float,
        default=None,
        help="forget photographs older than this",
    )
    retention.add_argument(
        "--keep-refusals-days",
        dest="keep_refusals_days",
        type=int,
        default=None,
        help="forget recorded refusals older than this",
    )
    retention.add_argument(
        "--keep-profiles",
        dest="keep_profiles",
        type=int,
        default=None,
        help="keep the last N readings, then one a month before them",
    )
    retention.add_argument("--apply", action="store_true", help="let them go")
    retention.set_defaults(run=_command_retention)

    trips = commands.add_parser("trips", help="the nights away, as journeys")
    trips.set_defaults(run=_command_trips)

    drift = commands.add_parser("drift", help="what moved with what, and each against its own past")
    drift.set_defaults(run=_command_drift)

    suggest = commands.add_parser("suggest", help="from your own evidence, pointed forward")
    suggest.set_defaults(run=_command_suggest)

    reread = commands.add_parser("reread", help="what a newer prompt version left behind")
    reread.add_argument(
        "--stage", choices=sorted(REREAD_STAGES), default=None, help="one reading stage"
    )
    reread.add_argument(
        "--apply", action="store_true", help="clear the outdated readings of one stage"
    )
    reread.set_defaults(run=_command_reread)

    retry = commands.add_parser("retry", help="refusals the environment caused, not the model")
    retry.add_argument(
        "--stage", choices=sorted(RETRY_STAGES), default=None, help="one reading stage"
    )
    retry.add_argument(
        "--apply", action="store_true", help="take back one stage's recoverable refusals"
    )
    retry.set_defaults(run=_command_retry)

    demo = commands.add_parser("demo", help="a synthetic library, so the engine can be seen")
    demo.add_argument("--out", default=None, help="where to build the sandbox")
    demo.add_argument("--keep", action="store_true", help="leave the sandbox in place")
    demo.set_defaults(run=_command_demo)

    refresh = commands.add_parser("refresh", help="the weekly routine, in one idempotent command")
    refresh.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        help="print the order and run nothing",
    )
    refresh.set_defaults(run=_command_refresh)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is not None:
        reconfigure(errors="replace")
    args = parser.parse_args(argv)

    if getattr(args, "run", None) is None:
        parser.print_usage(sys.stderr)
        return EXIT_BAD_INPUT

    exit_code: int = args.run(args)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
