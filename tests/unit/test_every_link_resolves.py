"""Every link in every document points at something that is there.

126 markdown files, and the documents are unusually interlinked for a
project this size: `docs/README.md` names fourteen documents by path,
`docs/records.md` links three contracts, `README.md` links into
`docs/adr/` by filename, and AGENTS.md cites files throughout. Every
one of those is a string that points at something on disk, and **a
string is not evidence of what it points at**.

None of them was broken when this was written. That is the state of
the repository today, not a property of it -- two sibling libraries
added the same check today and both found real breaks. This turns the
state into the property.

External links are deliberately not checked. Doing so needs the
network, which no test here has, and a check that reaches the internet
goes red when somebody else's site does.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).parents[2]

SKIP = {
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    ".import_linter_cache",
}

LINK = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")

EXTERNAL = ("http://", "https://", "mailto:")

HEADING = re.compile(r"^#{1,6}\s+(.*?)\s*$", re.MULTILINE)


def documents() -> list[Path]:
    found = [
        path
        for path in REPO_ROOT.rglob("*.md")
        if not any(part in SKIP for part in path.relative_to(REPO_ROOT).parts)
    ]
    assert found, "no markdown found, which means this test is looking in the wrong place"
    return sorted(found)


def slug(heading: str) -> str:
    """A heading as an anchor, near enough to the rule GitHub applies."""
    text = heading.strip().lower()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"\s+", "-", text)


def anchors_in(document: Path) -> set[str]:
    return {slug(heading) for heading in HEADING.findall(document.read_text(encoding="utf-8"))}


def links() -> list[tuple[Path, str]]:
    found: list[tuple[Path, str]] = []
    for document in documents():
        for target in LINK.findall(document.read_text(encoding="utf-8")):
            if not target.startswith(EXTERNAL):
                found.append((document, target))
    assert found, "no links found, which means the pattern stopped matching"
    return found


def test_every_local_link_points_at_something_that_exists() -> None:
    broken = [
        f"{document.relative_to(REPO_ROOT)} -> {target}"
        for document, target in links()
        if (path := target.split("#", 1)[0]) and not (document.parent / path).exists()
    ]
    assert not broken, "links with no target:\n" + "\n".join(broken)


def test_every_anchor_names_a_heading_that_is_there() -> None:
    """None of them does today. The check is here because one will."""
    broken: list[str] = []
    for document, target in links():
        path, _, anchor = target.partition("#")
        if not anchor:
            continue
        destination = (document.parent / path) if path else document
        if destination.suffix != ".md" or not destination.is_file():
            continue
        if anchor.lower() not in anchors_in(destination):
            broken.append(f"{document.relative_to(REPO_ROOT)} -> {target}")
    assert not broken, "anchors with no heading:\n" + "\n".join(broken)
