# 0018 Carry the thumbnail reference, and migrate the schema explicitly

## Status

Accepted

## Context

Captioning needs pixels, and the core has no path from a `PhotoId` to
an image. PhotoRecord v1 has always required `thumbnail_ref`, a
relative reference to a reduced copy of the photograph, resolved
against a configured thumbnail root -- but the core dropped the field
on ingestion. `PhotoObservation` did not carry it and the photos table
did not store it.

Carrying it forces the first real schema change. A new column cannot
arrive through `CREATE TABLE IF NOT EXISTS`, and `connect()` has so
far refused any database at a different version rather than guessing
at a migration.

## Decision

**The domain carries the reference as an opaque string.** A nullable
field with a default, so nothing that builds an observation changes.
The domain still never touches a file; the reference is a name, and an
adapter resolves it against `thumbs_dir`, which the configuration has
had from the start.

**The schema moves to version 2, through an explicit step.** A
version 1 database gains the column with `ALTER TABLE` and becomes
version 2 in place. Existing rows keep NULL, which reads back as an
observation without a reference: such photographs cannot be captioned,
and nothing else about them changes. Re-ingesting the same export
fills the column, because ingestion has always been idempotent.

**Refusal stays the default.** Only versions this code names are
handled. An unknown version is still an error, so a migration is
always something that was written and tested, never something guessed.

## Consequences

- The next issue can add an image source port: `PhotoId` to bytes,
  with a filesystem adapter joining `thumbs_dir` and the reference.
- Databases built before this change migrate on the first `connect()`.
  Records ingested before it carry no reference until re-ingested.
- Every future schema change follows the same shape: a numbered,
  explicit step from the version before it, and refusal for anything
  unrecognised.
