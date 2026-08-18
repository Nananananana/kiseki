# ADR-0051: Readings remember the prompt that made them



## Status

Accepted. Delivers proposals/0004, v0.6 item 5 (deferred to v0.7),
and the foundation of proposals/0005 item 4 and proposals/0006's
prompt regression.

## Context

Every stored reading already names the model that made it. The
model is half the answer: the same model under a rewritten prompt
is a different reader. Without the other half, `kiseki reread`
cannot say what is stale, and a prompt regression cannot say what
changed.

## Decision

Schema 5 adds `prompt_version TEXT` to the five reading tables --
captions, single_captions, subjects, theme_sets, screen_readings --
and the matching entities gain an optional `prompt_version`. The
migration is additive and asks before it adds, so a table created
fresh by this version is left alone; rows written before the column
keep NULL, which says the version was not recorded, not that it was
empty.

This issue delivers the vessel only. Stamping -- the prompt version
constants beside the prompts, and the writers that record them --
lands with `kiseki reread`, which is the only consumer that can act
on the difference.

## Consequences

- v0.5 and v0.6 databases migrate on connect; nothing is rewritten.
- `kiseki reread` can select exactly the readings made by an older
  prompt, and `kiseki compare` can show what the rereading changed.
- A reading whose prompt version is NULL is not wrong; it is
  unrecorded, and the tooling says so.
