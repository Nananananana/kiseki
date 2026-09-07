"""Every document a command writes says what it is.

There was a guard for the eleven served routes and none for the
nineteen commands that write a document to stdout, which is the larger
number and the one an orchestrator actually uses -- it reads documents
and never opens a socket.

The gap mattered because a payload can be added, wired to a command and
shipped without ever being served, and nothing would notice that it
carried no name. `#363` recorded that as the state of the world: *nine
shapes, and not one of them has a name, a version or a schema*. That
was fixed by ADR-0081's `named()` and never guarded, so it could come
back one payload at a time.

This enumerates the commands **from the parser** rather than from a
list here, so a command added next year is checked without anybody
remembering to add it.
"""

import json
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest
from kiseki.adapters.sqlite.graph import SqliteEvidenceGraph
from kiseki.adapters.sqlite.store import connect
from kiseki.config.paths import resolve_paths
from kiseki.domain.evidence.graph import Edge, Node, NodeKind, graph_of
from kiseki.interfaces.cli import EXIT_OK, build_parser, main

WHEN = datetime(2026, 6, 1, 12, tzinfo=UTC)

NEEDS_A_MODEL = {"ask", "tell"}
"""The two that reach a model, so their document cannot be got at on a
machine with none. Their shapes are checked where they are built, and
the point of this file is the wiring rather than the shape."""

ARGUMENTS: dict[str, list[str]] = {"why": ["c1"]}
"""What a command needs beyond `--json` to answer at all."""


@pytest.fixture(autouse=True)
def isolated_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the test away from the developer's .env and KISEKI_* environment."""
    for key in [name for name in os.environ if name.startswith("KISEKI_")]:
        monkeypatch.delenv(key)
    monkeypatch.chdir(tmp_path)


def commands_that_write_a_document() -> list[str]:
    """Read from the parser, so a new one is included by existing."""
    parser = build_parser()
    subcommands = next(
        action for action in parser._actions if getattr(action, "_name_parser_map", None)
    )
    return sorted(
        name
        for name, sub in subcommands._name_parser_map.items()
        if any("--json" in (option.option_strings or []) for option in sub._actions)
    )


def _something_to_ask_about(tmp_path: Path) -> None:
    """One conclusion resting on one reading, so `why` has an answer."""
    paths = resolve_paths({"data_root": str(tmp_path)}, dotenv=Path(".env"))
    SqliteEvidenceGraph(connect(paths.db_path)).save(
        graph_of(
            [
                Node(id="c1", kind=NodeKind.CONCLUSION, label="something is rising"),
                Node(
                    id="o1",
                    kind=NodeKind.OBSERVATION,
                    label="a note the library read",
                    source="note",
                    occurred_at=WHEN,
                ),
            ],
            [Edge(id="e1", source="c1", target="o1", kind="derived_from")],
        )
    )


class TestEveryDocumentSaysWhatItIs:
    def test_the_list_is_read_from_the_parser(self) -> None:
        """If this ever returns a handful, the check below is green
        about almost nothing."""
        found = commands_that_write_a_document()
        assert len(found) >= 15, found
        assert "graph" in found and "now" in found

    @pytest.mark.parametrize("command", commands_that_write_a_document())
    def test_it_names_itself_and_says_its_version(
        self, command: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        if command in NEEDS_A_MODEL:
            pytest.skip("reaches a model; its shape is checked where it is built")
        _something_to_ask_about(tmp_path)
        capsys.readouterr()
        arguments = ARGUMENTS.get(command, [])
        assert main(["--data-root", str(tmp_path), command, *arguments, "--json"]) == EXIT_OK
        document = json.loads(capsys.readouterr().out)
        assert document.get("schema", "").startswith("kiseki-"), document.get("schema")
        assert isinstance(document.get("version"), int), document.get("version")

    def test_the_names_are_distinct(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Two documents under one name is worse than none: a consumer
        keyed on the name would treat one as the other."""
        _something_to_ask_about(tmp_path)
        seen: dict[str, str] = {}
        for command in commands_that_write_a_document():
            if command in NEEDS_A_MODEL:
                continue
            capsys.readouterr()
            main(["--data-root", str(tmp_path), command, *ARGUMENTS.get(command, []), "--json"])
            schema = json.loads(capsys.readouterr().out)["schema"]
            assert schema not in seen, f"{command} and {seen[schema]} both write {schema}"
            seen[schema] = command

    def test_a_document_is_the_only_thing_on_stdout(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """`--json` means a machine is reading. A rule line or a heading
        printed beside it makes the document unparseable, and the caller
        finds out at the parse rather than at the call."""
        _something_to_ask_about(tmp_path)
        for command in commands_that_write_a_document():
            if command in NEEDS_A_MODEL:
                continue
            capsys.readouterr()
            main(["--data-root", str(tmp_path), command, *ARGUMENTS.get(command, []), "--json"])
            written = capsys.readouterr().out
            json.loads(written)
            assert not written.lstrip().startswith("-"), command
