"""A document written to stdout is UTF-8, whatever the console is.

Relayed from the akashi session, and reproduced here before it was
fixed: `akashi audit --json > report.json` was written in cp932, was
not valid JSON for exchange (RFC 8259 section 8.1), and carried a hash
over bytes the file did not contain. **akashi wrote a document akashi
could not read.**

    kiseki was doing the same thing at cli.py:976.

`ask --lang` defaults to `ja`, so the answer is non-ASCII on the
ordinary path. Redirected, Python encodes stdout with the locale
encoding. Measured on this machine:

    $ chcp 932 && kiseki ask "onsen について" --json > answer.json
    EXIT=0
    decodes as UTF-8   NO   (byte 0x82 at position 24)
    decodes as cp932   YES

Exit zero, no warning, a file that says JSON and is not UTF-8. And a
character cp932 has no room for does not corrupt but kills:

    e-acute    UnicodeEncodeError: 'cp932' codec can't encode
    em dash    UnicodeEncodeError: 'cp932' codec can't encode
    bullet     UnicodeEncodeError: 'cp932' codec can't encode

Both halves reach here from outside: the question comes from argv and
the answer comes from the model.

**The line this draws.** Prose keeps the console's behaviour, because
a character lost from a sentence is a character lost from a sentence,
and a person reads it and knows. A document is different: a program
reads it, and a lost character is corruption that arrives looking like
data. So the rule is not "encode everything as UTF-8" -- it is *what
is read by a machine is written in a named encoding.*

The other thirteen `print(json.dumps(...))` calls took the default
`ensure_ascii=True` and emitted pure ASCII, which survives any
console. **They were safe by accident, not by decision** -- exactly
what the akashi session said about themselves: read deliberately,
wrote by chance. One helper makes it a decision, and this file is what
keeps it one.
"""

import io
import json

import pytest
from kiseki.interfaces.cli import write_document

IN_CP932 = "onsen について教えて"
NOT_IN_CP932 = ["café", "going out — less", "a • b", "✓ done"]


def written_to_a_console(payload: object, encoding: str) -> bytes:
    """What lands in the file when stdout is redirected on a machine
    whose locale is `encoding`."""
    buffer = io.BytesIO()
    stream = io.TextIOWrapper(buffer, encoding=encoding, newline="")
    write_document(payload, stream=stream)
    stream.flush()
    return buffer.getvalue()


class TestOnACp932Console:
    def test_a_japanese_document_is_still_utf8(self) -> None:
        raw = written_to_a_console({"question": IN_CP932}, "cp932")
        assert json.loads(raw.decode("utf-8"))["question"] == IN_CP932

    @pytest.mark.parametrize("text", NOT_IN_CP932, ids=lambda text: repr(text))
    def test_a_character_cp932_cannot_hold_does_not_kill_the_command(self, text: str) -> None:
        """The half this repository's own console cannot produce, and
        the half that ends the process rather than corrupting a file."""
        raw = written_to_a_console({"question": text}, "cp932")
        assert json.loads(raw.decode("utf-8"))["question"] == text

    def test_the_bytes_are_the_same_as_on_a_utf8_console(self) -> None:
        """A document that differs by where it was run is not a
        document, and a hash over it means nothing."""
        payload = {"question": IN_CP932, "answer": "café — onsen"}
        assert written_to_a_console(payload, "cp932") == written_to_a_console(payload, "utf-8")


class TestItIsStillJson:
    def test_it_ends_with_one_newline(self) -> None:
        raw = written_to_a_console({"a": 1}, "cp932")
        assert raw.endswith(b"\n") and not raw.endswith(b"\n\n")

    def test_it_is_indented_as_before(self) -> None:
        assert b'\n  "a": 1' in written_to_a_console({"a": 1}, "cp932")

    def test_it_carries_the_characters_rather_than_escapes(self) -> None:
        """`ensure_ascii=True` would also survive a cp932 console, by
        escaping every character into its code point. That is a second
        thing to remember rather than a rule, and it makes a document
        a reader cannot read."""
        assert IN_CP932.encode("utf-8") in written_to_a_console({"q": IN_CP932}, "cp932")


def test_a_stream_with_no_bytes_underneath_still_works() -> None:
    """A captured stdout, in this suite and in anybody else's."""
    stream = io.StringIO()
    write_document({"a": 1}, stream=stream)
    assert json.loads(stream.getvalue()) == {"a": 1}
