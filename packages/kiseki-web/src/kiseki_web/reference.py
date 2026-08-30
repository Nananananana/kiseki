"""A handle for a page that the core can tell apart and cannot look up.

`NoteRecord` identifies a note by a hash of its path, and that is
enough: a path is a private string, so testing whether a hash belongs
to `~/notes/diagnosis.md` means guessing that the file exists.

**A URL is public and enumerable.** Anybody holding a records file and
a list of URLs can hash the list and test for membership, and the
lists that matter -- clinics, forums, parties, dating sites -- are
short and easy to write. An unsalted hash of a URL is the URL with an
extra step. See ADR-0084.

So the hash is salted, and the salt never leaves this producer.

The salt is not a secret about the owner. Nothing is decrypted with
it, and it says nothing on its own. Its only job is to stop somebody
who holds a records file from testing what is in it, and the only ways
it can fail at that are by being predictable or by being shared.
"""

from __future__ import annotations

import hashlib
import secrets
from pathlib import Path

SALT_FILE = "salt"
"""Beside the mapping, which is the most sensitive thing this producer
owns. Losing one is losing the other, and both mean the same thing:
the owner can no longer ask which page a reading came from."""

SALT_BYTES = 32

REFERENCE_PREFIX = "page:"
REFERENCE_LENGTH = 16
"""The same shape a note's reference has. Sixteen hex characters is
enough to keep two pages apart in one person's browsing and short
enough to read in a listing."""


def salt_in(state: Path) -> bytes:
    """The salt for this installation, made once and read back after.

    Never regenerated. A new salt makes every page look new, and a page
    recognised across months is the entire value of this source
    (ADR-0076).
    """
    state.mkdir(parents=True, exist_ok=True)
    path = state / SALT_FILE
    if path.is_file():
        return path.read_bytes()
    salt = secrets.token_bytes(SALT_BYTES)
    path.write_bytes(salt)
    return salt


def reference_for(url: str, salt: bytes) -> str:
    """An opaque, stable handle for one page.

    Stable for one installation and meaningless in another, which is
    correct: two owners' histories are not meant to line up, and a
    reference that made them line up would be a way to build a graph of
    people out of what they read.
    """
    if not url.strip():
        raise ValueError("a page with no address has nothing to be a handle for")
    digest = hashlib.sha256(salt + url.strip().encode("utf-8")).hexdigest()
    return f"{REFERENCE_PREFIX}{digest[:REFERENCE_LENGTH]}"
