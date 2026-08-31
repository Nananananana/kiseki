# ADR-0086: A note is identified by where it sits, not by what it says

## Status

Accepted. Settles the half of #342 that does not depend on anybody
else, and records what the choice costs.

## Context

`kiseki-notes` identifies a note by a hash of its path relative to the
folder the owner named. Two other derivations were available, and each
dies in a different way.

**A content hash** survives a rename and a move, and dies on an edit.
**An absolute path** survives an edit and a rename inside the folder,
and dies when the folder moves -- and puts a user account's name into
a handle the core keeps forever. **A relative path** survives an edit,
and dies on a rename.

Measured while a cross-repository exchange was working out how a
note's identity travels, there is a fourth failure that belongs only
to the relative path and is not a vault event at all:

```text
same file, same content, two roots
  root = corpus              note:4b743d9119e01e18
  root = corpus/documents    note:32a68bbd4e346596
```

The producer session at the other end of that seam measured the same
thing from its side and drew the sharper statement of it: **the key
did not move and the reference did.** Everything downstream is a
function of the key, so a rename propagates predictably; the root is
outside the key entirely, and nothing on either side can see that it
changed.

## Decision

The relative path stands.

ADR-0076 rests the whole design on a note being recognisable **across
edits**: a note returned to over six months is six readings, and the
returning is the evidence -- the difference between a thought had once
and a thought lived with. A content hash makes every edit a new note,
which does not weaken that signal but inverts it: a trail of returns
becomes a trail of strangers.

So the choice is made on which failure the design cannot survive
rather than on which derivation has the fewest. The relative path has
two failure modes to the content hash's one, and neither of its two
touches the thing everything else is built on.

The absolute path is refused for the second reason rather than the
first: a reference that leaked `C:\Users\<name>` would name a person
in a handle stored forever, and no amount of stability is worth that.

## Consequences

- **A rename re-identifies a note**, and this is the known cost that
  `docs/note-record.md` has always named.
- **Naming a different root re-identifies everything under it**, with
  nothing renamed anywhere. This is worse than the rename in one
  respect: a rename happens to a vault, and a root is an argument
  somebody types. It is written where somebody choosing a folder will
  read it -- `kiseki-notes plan` says it, and so does the contract.
- **Neither is detectable from a document.** A re-identified folder
  produces valid records that share no references with what is held.
  Saying so -- *a document sharing no references with the readings for
  this owner and platform is either a first import or a
  re-identification* -- is a producer observation of the same kind as
  the flat-timestamp warning, and is not built here.
- **This could stop being true**, in one way and not the others: if a
  source arrives carrying an identifier of its own -- a page id, a
  message id, something the file did not invent -- then its identity
  is not derived here at all and this decision governs only the
  producer that walks a folder. That is a question for whoever brings
  such a source, and it does not reopen the choice made above.
- The digest itself promises nothing: sixteen characters, sha256,
  forward slashes are this producer's choices and not a contract. See
  `docs/note-record.md`.
