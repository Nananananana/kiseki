"""Command line interface.

Composition happens here and nowhere else: this is the only place that decides
SQLite is the storage and where the database sits. Everything below it is given
what it needs.
"""

import argparse
import json
import sys
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

from kiseki.adapters.filesystem.thumbnails import FilesystemThumbnailSource
from kiseki.adapters.ollama.models import (
    OllamaImageCaptioner,
    OllamaLanguageModel,
    OllamaTextEmbedder,
)
from kiseki.adapters.ollama.screens import OllamaScreenshotReader
from kiseki.adapters.sqlite.store import (
    SqliteAnchorRepository,
    SqliteCaptionRepository,
    SqliteOutingRepository,
    SqlitePhotoRepository,
    SqliteProfileRepository,
    SqliteScreenshotReadingRepository,
    SqliteSingleCaptionRepository,
    SqliteSubjectRepository,
    SqliteThemeSetRepository,
    connect,
)
from kiseki.application.captioning import run_captioning
from kiseki.application.narrative import tell
from kiseki.application.pipeline import Pipeline, Report
from kiseki.application.screen_reading import run_screen_reading
from kiseki.application.single_captioning import run_single_captioning
from kiseki.application.subject_extraction import run_subject_extraction
from kiseki.application.theming import run_theming
from kiseki.config.paths import StoragePaths, resolve_paths
from kiseki.domain.interests import Profile
from kiseki.domain.photo.observation import PhotoId, PhotoObservation
from kiseki.domain.services.trend_derivation import MIN_TREND_SPAN_DAYS
from kiseki.domain.shared.geo import GeoPoint
from kiseki.domain.trends import TrendReport
from kiseki.interfaces.api import DEFAULT_HOST, DEFAULT_PORT, serve
from kiseki.interfaces.payloads import (
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


def _print_profile(profile: Profile) -> None:
    print(RULE)
    print(f"  interests     {len(profile.interests)}")

    if profile.interests:
        print("\n  read as interests")
        for interest in profile.ranked():
            print(
                f"    {interest.topic:<32}"
                f"  score {interest.score:>5.2f}"
                f"  confidence {interest.confidence:>5.2f}"
                f"  evidence {len(interest.evidence)}"
            )


def _command_profile(args: argparse.Namespace) -> int:
    profile = _pipeline_for(args).profile()
    if args.json:
        print(json.dumps(profile_payload(profile), indent=2))
    else:
        _print_profile(profile)
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
    if report.paused:
        print("\n  paused: the model was unavailable; run again to resume")
    return EXIT_OK


def _command_subjects(args: argparse.Namespace) -> int:
    connection = connect(_paths_for(args).db_path)
    report = run_subject_extraction(
        captions=SqliteCaptionRepository(connection),
        subjects=SqliteSubjectRepository(connection),
        language_model=OllamaLanguageModel(),
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
    pipeline = _pipeline_for(args)
    report = pipeline.report()
    profile = pipeline.profile()
    try:
        story = tell(profile, report, OllamaLanguageModel(), language=args.lang)
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
    )
    page = render_view(
        photos.all(),
        pipeline.report(),
        pipeline.profile(keep=False),
        pipeline.trend(),
        blur=not args.raw,
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

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if getattr(args, "run", None) is None:
        parser.print_usage(sys.stderr)
        return EXIT_BAD_INPUT

    exit_code: int = args.run(args)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
