"""Validate the PhotoRecord v1 schema against known good and bad documents."""

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).parents[2]
SCHEMA_PATH = REPO_ROOT / "schemas" / "photo-record-v1.json"
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "photo_record"


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def validator() -> Draft202012Validator:
    schema = load_json(SCHEMA_PATH)
    return Draft202012Validator(schema)


def fixtures(prefix: str) -> list[Path]:
    found = sorted(FIXTURE_DIR.glob(f"{prefix}_*.json"))
    assert found, f"no fixtures found for prefix {prefix!r}"
    return found


def test_schema_itself_is_valid() -> None:
    Draft202012Validator.check_schema(load_json(SCHEMA_PATH))


@pytest.mark.parametrize("path", fixtures("valid"), ids=lambda p: p.stem)
def test_valid_documents_are_accepted(validator: Draft202012Validator, path: Path) -> None:
    errors = sorted(validator.iter_errors(load_json(path)), key=str)
    assert not errors, f"{path.name} should be valid: {[e.message for e in errors]}"


@pytest.mark.parametrize("path", fixtures("invalid"), ids=lambda p: p.stem)
def test_invalid_documents_are_rejected(validator: Draft202012Validator, path: Path) -> None:
    assert not validator.is_valid(load_json(path)), f"{path.name} should be rejected"


def test_interpolated_location_is_distinguishable(validator: Draft202012Validator) -> None:
    """A guessed coordinate must be marked, so anchor estimation can exclude it."""
    document = {
        "schema_version": "1.0",
        "records": [
            {
                "id": "sha256:" + "a3f2c9d81b4e7f60" * 4,  # pragma: allowlist secret
                "captured_at": "2025-05-03T10:24:31+09:00",
                "location": {"lat": 35.0094, "lon": 135.6669},
                "location_source": "interpolated",
                "media_type": "image",
                "content_kind": "photo",
                "thumbnail_ref": "2025/05/a3f2.jpg",
                "owner": {"owner_id": "u1"},
                "consent": {"use_for_preference": True, "use_for_story": True},
            }
        ],
    }
    assert validator.is_valid(document)
