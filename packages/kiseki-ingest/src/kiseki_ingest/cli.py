"""Command line entry point for the reference producer."""

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from kiseki_ingest.classification import PHOTO
from kiseki_ingest.exif import parse_offset
from kiseki_ingest.records import Consent, Owner, Skipped, build_record, hash_file
from kiseki_ingest.selection import is_excluded, relative_to

SUPPORTED_SUFFIXES = {".jpg", ".jpeg", ".heic", ".heif", ".png", ".tif", ".tiff"}
RECORDS_FILE = "photo-records.json"
SKIPPED_FILE = "skipped.json"
THUMBNAIL_DIR = "thumbs"

EXIT_OK = 0
EXIT_NO_INPUT = 2


def _register_heif() -> None:
    try:
        import pillow_heif
    except ImportError:
        return
    pillow_heif.register_heif_opener()


def _sources(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kiseki-ingest",
        description="Turn a directory of photographs into a PhotoRecord document.",
    )
    parser.add_argument("source", type=Path, help="directory to scan, recursively")
    parser.add_argument("output", type=Path, help="directory to write records and thumbnails to")
    parser.add_argument("--owner", required=True, help="identifier for whoever took these photos")
    parser.add_argument("--device", default=None)
    parser.add_argument(
        "--platform",
        default=None,
        choices=["ios", "android", "desktop", "camera", "other"],
    )
    parser.add_argument(
        "--default-offset",
        required=True,
        help="UTC offset for photos with no OffsetTimeOriginal, for example +09:00",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="GLOB",
        help="skip paths matching this pattern, repeatable. A star crosses directories",
    )
    parser.add_argument(
        "--photos-only",
        action="store_true",
        help="drop anything classified as a screenshot or other content",
    )
    parser.add_argument("--no-preference-consent", action="store_true")
    parser.add_argument("--no-story-consent", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    if not args.source.is_dir():
        print(f"{args.source} is not a directory", file=sys.stderr)
        return EXIT_NO_INPUT

    _register_heif()
    default_offset = parse_offset(args.default_offset)
    owner = Owner(args.owner, args.device, args.platform)
    consent = Consent(
        use_for_preference=not args.no_preference_consent,
        use_for_story=not args.no_story_consent,
    )

    records: list[dict[str, Any]] = []
    skipped: list[Skipped] = []
    seen: dict[str, Path] = {}

    for path in _sources(args.source):
        relative = relative_to(args.source, path)
        if is_excluded(relative, args.exclude):
            skipped.append(Skipped(path, "excluded by pattern"))
            continue

        digest = hash_file(path)
        if digest in seen:
            skipped.append(Skipped(path, f"identical content to {seen[digest]}"))
            continue

        try:
            record = build_record(
                path,
                owner=owner,
                consent=consent,
                default_offset=default_offset,
                thumbnail_root=args.output / THUMBNAIL_DIR,
                digest=digest,
            )
        except (ValueError, OSError) as error:
            skipped.append(Skipped(path, str(error)))
            continue

        if args.photos_only and record["content_kind"] != PHOTO:
            skipped.append(Skipped(path, f"classified as {record['content_kind']}"))
            continue

        seen[digest] = path
        records.append(record)

    args.output.mkdir(parents=True, exist_ok=True)
    document = {"schema_version": "1.0", "records": records}
    (args.output / RECORDS_FILE).write_text(
        json.dumps(document, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (args.output / SKIPPED_FILE).write_text(
        json.dumps(
            [{"path": str(item.path), "reason": item.reason} for item in skipped],
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(f"{len(records)} record(s) written to {args.output / RECORDS_FILE}")
    if skipped:
        print(f"{len(skipped)} file(s) skipped, see {args.output / SKIPPED_FILE}")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
