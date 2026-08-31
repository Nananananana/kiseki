"""Every table is counted by the privacy report, or named as not counted.

`kiseki privacy` reports what is stored, counted from storage
(ADR-0046). Three input contracts landed while nobody was watching it:
note readings at schema 7, daily activity at 6, page readings at 9.
The report counted none of them, and nothing said it had to.

That is worse than an incomplete command. A reader has no way to tell
a source that holds nothing from a source the report forgot -- both
print as absent, and the whole point of the dashboard is that the
owner does not have to take its word for anything.

So: adding a table is now a decision. Count it, or say here why not.
The list below is the saying.
"""

import tempfile
from pathlib import Path

from kiseki.adapters.sqlite.store import connect

COUNTED = {
    "photos": "photographs, located, withheld_from_preference",
    "captions": "stay_captions, stay_refused",
    "single_captions": "single_captions, single_refused",
    "screen_readings": "screen_readings, screens_label_silent",
    "subjects": "subject_readings",
    "note_readings": "note_readings, notes_label_silent",
    "page_readings": "page_readings, pages_label_silent",
    "daily_activity": "activity_days",
    "profiles": "kept_profiles",
    "corrections": "corrections, active_exclusions",
}

NOT_COUNTED = {
    "schema_version": "one row saying which migration ran; not the owner's data",
    "sqlite_sequence": "SQLite's own bookkeeping",
    "stops": "derived from photographs and replaced wholesale on rebuild (ADR-0013)",
    "stop_photos": "which photographs made a stop; rebuilt with them",
    "outings": "assembled from stops, and rebuilt with them",
    "anchors": "estimated from stops, rebuilt with them, and never named (ADR-0040)",
    "theme_sets": "derived from subject readings, and rebuilt with them",
}
"""Why each one is absent from the report. A derived table is not a
second copy of what it was derived from: counting it would tell the
owner that the same evidence is stored twice."""


def tables() -> set[str]:
    with tempfile.TemporaryDirectory() as raw:
        connection = connect(Path(raw) / "kiseki.sqlite3")
        try:
            found = {
                row[0]
                for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
            }
        finally:
            connection.close()
    assert found, "a fresh database has no tables, which means this is looking in the wrong place"
    return found


def test_every_table_is_counted_or_named_as_not_counted() -> None:
    undecided = tables() - set(COUNTED) - set(NOT_COUNTED)
    assert not undecided, (
        f"tables the privacy report neither counts nor excuses: {sorted(undecided)}. "
        "Count them, or say here why not."
    )


def test_nothing_is_claimed_that_does_not_exist() -> None:
    invented = (set(COUNTED) | set(NOT_COUNTED)) - tables()
    assert not invented, f"tables named here that the schema does not have: {sorted(invented)}"


def test_no_table_is_both_counted_and_excused() -> None:
    assert not set(COUNTED) & set(NOT_COUNTED)


def test_every_excuse_says_something() -> None:
    """A blank reason is a table nobody thought about."""
    silent = [name for name, reason in NOT_COUNTED.items() if len(reason.split()) < 3]
    assert not silent, f"excused without a reason: {silent}"


def test_the_report_carries_a_field_for_every_counted_table() -> None:
    """The names above are the report's fields, so a table counted here
    and nowhere else is caught."""
    from kiseki.application.pipeline import PrivacyReport

    fields = set(PrivacyReport.__dataclass_fields__)
    missing = [
        f"{table} -> {field}"
        for table, names in COUNTED.items()
        for field in (name.strip() for name in names.split(","))
        if field not in fields
    ]
    assert not missing, f"the report has no such field: {missing}"


def test_a_table_added_without_a_decision_is_caught() -> None:
    """The check itself, checked: a table this file does not name fails
    the first test rather than passing quietly."""
    with tempfile.TemporaryDirectory() as raw:
        path = Path(raw) / "kiseki.sqlite3"
        connection = connect(path)
        connection.execute("CREATE TABLE something_new (id TEXT PRIMARY KEY)")
        found = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        connection.close()
    assert "something_new" in found - set(COUNTED) - set(NOT_COUNTED)
