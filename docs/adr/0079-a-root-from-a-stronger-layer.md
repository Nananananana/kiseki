# ADR-0079: A root from a stronger layer sets aside the paths below it

## Status

Accepted. Found by writing a synthetic corpus into the owner's real
library, twice, while trying not to.

## Context

`kiseki --data-root C:\dev\corpus-db notes ...` wrote into the real
database. The flag moved the root; the dotenv file still named
`db_path` explicitly; an explicit path beats a derived one, so the
flag appeared to work and did nothing.

The rule it followed is right *within* a layer. A file that says both
"the root is here" and "the database is over there" means both. Across
layers it is wrong: the documented precedence is defaults, toml,
dotenv, environment, command line, and a setting from the second layer
was quietly beating a root from the fifth.

Nothing failed. The corpus went in, the counts looked plausible, and
only `doctor` reporting four thousand nine hundred and fifty
photographs gave it away.

## Decision

Each setting is tracked with the layer that set it. A path named in a
layer weaker than the one that named the root is set aside: somebody
who says where the root is on the command line has said where
everything goes, and a file cannot answer back. A path named in the
same layer or a stronger one still wins, so the ordinary case is
unchanged.

The command says what it set aside. A setting silently ignored is the
same failure as a setting silently applied -- which is why unknown
model settings are refused rather than dropped, and why this is
announced rather than merely fixed.

## Consequences

- `--data-root` means what it says, which matters most for the two
  things it is used for: trying something in a sandbox, and keeping
  synthetic data out of a real library.
- AGENTS.md carried "an .env path outranks --data-root" as a hazard to
  work around. It no longer does, and the note is corrected rather
  than softened.
- The CLI tests that chdir to a temporary directory can keep doing so.
  They were working around this, and the workaround is now belt and
  braces rather than the only defence.
