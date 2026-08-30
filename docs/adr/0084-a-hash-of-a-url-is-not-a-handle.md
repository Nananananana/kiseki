# ADR-0084: A hash of a URL is not an opaque handle

## Status

Accepted. Settles the reference field of [WebRecord v1](../web-record.md),
before any producer exists.

## Context

NoteRecord v1 identifies a note by a hash of its path relative to the
folder the owner named (ADR-0075). The core can tell two readings of
the same note apart and cannot say which note; the mapping lives with
the producer. It has held up.

The web contract wants the same shape for a URL, and the same shape
does not hold, for a reason that is not a matter of degree.

**A path is a private string. A URL is a public one.** To test whether
a note reference belongs to `~/notes/diagnosis.md`, somebody must
first guess that a file of that name exists. To test whether a page
reference belongs to a clinic, a forum, a party or a dating site, they
need only the URL, which is published, and a hash function.

The lists that matter are short and easy to write. A records file that
left the machine -- in a backup, in a support attachment, in a folder
somebody synced -- would answer membership questions about exactly the
categories this contract spends seven unlabelled categories trying to
protect. An unsalted hash of a URL is the URL with an extra step.

## Decision

The reference is a **salted** hash of the URL. The salt is generated
once by the producer, kept beside the URL mapping the producer already
holds, and never appears in a record.

Two consequences follow, and both are wanted:

- The core keeps what it needs -- two readings of one page across
  months are recognisably the same page -- and gains nothing it should
  not have.
- **Records from two installations cannot be compared, even for the
  same page.** Two owners' histories are not meant to line up, and a
  contract that let them would be a contract for building a graph of
  people by what they read.

NoteRecord is left as it is. A path is not enumerable, its hash has
never been a membership oracle, and changing a contract that has
shipped, to fix a weakness it does not have, would cost every stored
reading for nothing.

## Consequences

- The producer holds a secret, which it did not before. It sits with
  the mapping, which is already the most sensitive thing the producer
  owns; losing the salt is losing the mapping, and both mean the same
  thing -- the owner can no longer ask *which page was that*.
- A rebuilt producer that generates a new salt makes every page look
  new. The trail is what has value here, so the salt is written down
  once and treated as part of the producer's own state, not derived
  from anything that moves.
- **This could stop being true.** If a later contract ever needs one
  page to be recognisable across two installations -- which nothing
  today does, and which proposals/0009 declines by default -- the
  argument has to be made in the open, with this ADR superseded rather
  than the salt quietly dropped.
- Nothing here changes what the core stores. It receives an opaque
  string either way; the difference is what that string can be made to
  admit.
