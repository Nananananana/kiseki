"""Command line interface.

Composition happens here and nowhere else: this is the only place that decides
SQLite is the storage and where the database sits. Everything below it is given
what it needs.
"""

import argparse
import json
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
    connect,
)
from kiseki.application.asking import Answer, ask
from kiseki.application.captioning import run_captioning
from kiseki.application.exporting import interest_export
from kiseki.application.indexing import run_indexing
from kiseki.application.insight_narration import tell_insights
from kiseki.application.narrative import tell
from kiseki.application.pipeline import Pipeline, Report
from kiseki.application.screen_reading import run_screen_reading
from kiseki.application.single_captioning import run_single_captioning
from kiseki.application.subject_extraction import run_subject_extraction
from kiseki.application.theming import run_theming
from kiseki.config.paths import StoragePaths, resolve_paths
from kiseki.domain.comparison import ChangeKind
from kiseki.domain.correction import Correction, CorrectionVerdict, active_exclusions
from kiseki.domain.interests import Profile
from kiseki.domain.photo.observation import PhotoId, PhotoObservation
from kiseki.domain.services.trend_derivation import MIN_TREND_SPAN_DAYS
from kiseki.domain.shared.geo import GeoPoint
from kiseki.domain.trends import TrendReport
from kiseki.interfaces.api import DEFAULT_HOST, DEFAULT_PORT, serve
from kiseki.interfaces.naming import place_names
from kiseki.interfaces.payloads import (
    BLURRED_BY_DEFAULT,
    NEVER_STORED,
    answer_payload,
    comparison_payload,
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
